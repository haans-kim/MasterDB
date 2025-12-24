"""
MasterDB Full Migration Script

Runs all migrations in order:
1. Companies and Surveys (from Excel)
2. Questions and Master Questions (from pkl)
3. Embeddings (from npy)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import numpy as np

from db.connection import get_connection, get_db_info
from db.schema import create_all_tables, get_table_counts


def migrate_questions_and_embeddings(conn):
    """Migrate questions, master_questions, and embeddings."""

    # Load data
    pkl_path = PROJECT_ROOT / "all_df_hybrid.pkl"
    npy_path = PROJECT_ROOT / "all_embeddings_hybrid.npy"

    if not pkl_path.exists():
        print(f"  Error: {pkl_path} not found")
        return 0, 0, 0

    df = pd.read_pickle(pkl_path)
    print(f"  Loaded {len(df)} questions from pkl")

    cursor = conn.cursor()

    # Track cluster numbers per diagnosis type for master_id generation
    cluster_counters = {"OD": 0, "LD": 0, "MA": 0, "DD": 0}
    cluster_to_master = {}  # (diagnosis_type, cluster_id) -> master_id

    # First pass: identify representatives and assign master_ids
    for idx, row in df.iterrows():
        if row.get("is_representative", False):
            diagnosis_type = row.get("대분류", "OD")
            cluster_id = row.get("cluster_id")
            cluster_counters[diagnosis_type] += 1
            master_id = f"{diagnosis_type}_{cluster_counters[diagnosis_type]:04d}"
            cluster_to_master[(diagnosis_type, cluster_id)] = master_id

    # Second pass: insert questions
    questions_data = []
    master_questions_data = []

    for idx, row in df.iterrows():
        question_id = f"Q_{idx + 1:05d}"
        diagnosis_type = row.get("대분류", "OD")
        cluster_id = row.get("cluster_id")
        is_representative = row.get("is_representative", False)

        # Get master_id for this cluster
        master_id = cluster_to_master.get((diagnosis_type, cluster_id))

        questions_data.append((
            question_id,
            row.get("문항", ""),
            diagnosis_type,
            row.get("년도"),
            "LIKERT",
            1,
            5,
            cluster_id,
            master_id,
            1 if is_representative else 0,
            row.get("중분류"),
            row.get("소분류"),
        ))

        if is_representative and master_id:
            master_questions_data.append((
                master_id,
                question_id,
                diagnosis_type,
                1,  # cluster_size placeholder
            ))

    # Insert questions
    cursor.executemany("""
        INSERT INTO questions (
            question_id, question_text, diagnosis_type, source_year,
            question_type, scale_min, scale_max, cluster_id,
            master_question_id, is_representative,
            legacy_mid_category, legacy_sub_category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, questions_data)
    print(f"  Inserted {len(questions_data)} questions")

    # Insert master questions
    cursor.executemany("""
        INSERT INTO master_questions (
            master_id, question_id, diagnosis_type, cluster_size
        ) VALUES (?, ?, ?, ?)
    """, master_questions_data)
    print(f"  Inserted {len(master_questions_data)} master questions")

    # Update cluster sizes
    cluster_sizes = {}
    for idx, row in df.iterrows():
        key = (row.get("대분류", "OD"), row.get("cluster_id"))
        master_id = cluster_to_master.get(key)
        if master_id:
            cluster_sizes[master_id] = cluster_sizes.get(master_id, 0) + 1

    for master_id, size in cluster_sizes.items():
        cursor.execute(
            "UPDATE master_questions SET cluster_size = ? WHERE master_id = ?",
            (size, master_id)
        )
    print(f"  Updated cluster sizes")

    # Migrate embeddings
    embeddings_count = 0
    if npy_path.exists():
        embeddings = np.load(npy_path)
        print(f"  Loaded embeddings: {embeddings.shape}")

        embeddings_data = []
        for idx in range(len(df)):
            question_id = f"Q_{idx + 1:05d}"
            embedding_blob = embeddings[idx].astype(np.float32).tobytes()
            embeddings_data.append((question_id, embedding_blob))

        cursor.executemany("""
            INSERT INTO embeddings (question_id, embedding)
            VALUES (?, ?)
        """, embeddings_data)
        embeddings_count = len(embeddings_data)
        print(f"  Inserted {embeddings_count} embeddings")
    else:
        print(f"  Warning: {npy_path} not found, skipping embeddings")

    conn.commit()
    return len(questions_data), len(master_questions_data), embeddings_count


def migrate_companies_and_surveys(conn):
    """Migrate companies and surveys from Excel."""

    excel_path = PROJECT_ROOT / "data" / "Survey Meta Data_251224.xlsx"

    if not excel_path.exists():
        print(f"  Warning: {excel_path} not found, skipping company/survey migration")
        return 0, 0

    try:
        # Use sheet index 5 (참고1. Survey목록) to avoid encoding issues
        df = pd.read_excel(excel_path, sheet_name=5)
        print(f"  Loaded {len(df)} rows from Excel")
    except Exception as e:
        print(f"  Error reading Excel: {e}")
        return 0, 0

    cursor = conn.cursor()

    # Column mapping by index (to avoid encoding issues):
    # Col 0: 번호, Col 1: 프로젝트명, Col 6: 회사 코드, Col 7: 설문 코드
    # Col 8: 연도, Col 9: 진단유형

    # Extract and insert companies
    companies = {}
    for idx, row in df.iterrows():
        company_code = row.iloc[6]  # 회사 코드
        if pd.isna(company_code) or not company_code:
            continue

        company_id = str(company_code).strip().upper()

        if company_id not in companies:
            companies[company_id] = (
                company_id,
                company_id,  # company_name (use code as name for now)
                company_id,  # short name
                True,
            )

    cursor.executemany("""
        INSERT OR IGNORE INTO companies (
            company_id, company_name, company_name_short, is_active
        ) VALUES (?, ?, ?, ?)
    """, list(companies.values()))
    print(f"  Inserted {len(companies)} companies")

    # Insert surveys
    surveys = {}
    for idx, row in df.iterrows():
        company_code = row.iloc[6]  # 회사 코드
        if pd.isna(company_code) or not company_code:
            continue

        company_id = str(company_code).strip().upper()
        survey_code = row.iloc[7]  # 설문 코드
        project_name = row.iloc[1]  # 프로젝트명
        year = row.iloc[8]  # 연도
        diag_type = row.iloc[9]  # 진단유형

        if pd.isna(year):
            year = 2024
        year = int(year)

        if pd.isna(diag_type):
            diag_type = "OD"
        diag_type = str(diag_type).strip()

        # Generate survey_id from survey_code
        if survey_code and not pd.isna(survey_code):
            survey_id = str(survey_code).strip()
        else:
            survey_id = f"{company_id}-{year}-{diag_type}"

        if survey_id not in surveys:
            survey_name = project_name if not pd.isna(project_name) else f"{company_id} {year} {diag_type}"
            surveys[survey_id] = (
                survey_id,
                str(survey_name),
                company_id,
                diag_type,
                year,
                None,  # question_count
                "COMPLETED",
            )

    cursor.executemany("""
        INSERT OR IGNORE INTO surveys (
            survey_id, survey_name, company_id, diagnosis_type,
            survey_year, question_count, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, list(surveys.values()))
    print(f"  Inserted {len(surveys)} surveys")

    conn.commit()
    return len(companies), len(surveys)


def run_full_migration():
    """Run the complete migration."""
    print("=" * 60)
    print("  MasterDB Full Migration")
    print("=" * 60)

    # Get connection
    print("\n[1/4] Initializing database...")
    conn = get_connection()

    # Create tables (if not exist)
    create_all_tables(conn)

    # Check existing data
    counts = get_table_counts(conn)
    total_existing = sum(counts.values())

    if total_existing > 0:
        print(f"\n  Warning: Database already has {total_existing} total rows")
        print("  Current counts:")
        for table, count in counts.items():
            if count > 0:
                print(f"    {table}: {count}")

        print("\n  Options:")
        print("    1. Clear all and re-migrate")
        print("    2. Skip (keep existing data)")
        print("    3. Cancel")

        choice = input("  Enter choice (1/2/3): ").strip()

        if choice == "1":
            print("\n  Clearing existing data...")
            cursor = conn.cursor()
            # Clear in reverse dependency order
            tables_to_clear = [
                "scale_questions", "scales",
                "question_tags", "taxonomy_relations", "taxonomy",
                "embeddings", "survey_questions", "master_questions", "questions",
                "org_unit_surveys", "org_units", "surveys", "companies"
            ]
            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM {table}")
            conn.commit()
            print("  Cleared all data")
        elif choice == "2":
            print("\n  Keeping existing data, migration skipped")
            conn.close()
            return
        else:
            print("\n  Migration cancelled")
            conn.close()
            return

    # Migrate companies and surveys
    print("\n[2/4] Migrating companies and surveys...")
    c_count, s_count = migrate_companies_and_surveys(conn)

    # Migrate questions
    print("\n[3/4] Migrating questions and master questions...")
    q_count, m_count, e_count = migrate_questions_and_embeddings(conn)

    # Final summary
    print("\n[4/4] Verifying migration...")
    final_counts = get_table_counts(conn)
    db_info = get_db_info(conn)

    print("\n" + "=" * 60)
    print("  Migration Complete!")
    print("=" * 60)
    print("\n  Table Counts:")
    for table, count in final_counts.items():
        print(f"    {table}: {count}")
    print(f"\n  Database Size: {db_info['file_size_mb']} MB")
    print(f"  Total Indexes: {db_info['index_count']}")

    conn.close()
    print("\n  Done!")


if __name__ == "__main__":
    run_full_migration()
