"""
Migrate Questions from pkl to SQLite

Migrates:
- questions table (7,343 rows)
- master_questions table (3,274 rows)
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import numpy as np

from db.connection import get_connection


def load_questions_df():
    """Load questions DataFrame from pkl file."""
    pkl_path = PROJECT_ROOT / "all_df_hybrid.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"pkl file not found: {pkl_path}")

    df = pd.read_pickle(pkl_path)
    print(f"Loaded {len(df)} questions from pkl")
    return df


def generate_question_id(idx):
    """Generate question ID in format Q_00001."""
    return f"Q_{idx:05d}"


def generate_master_id(diagnosis_type, cluster_num):
    """Generate master question ID in format OD_0001."""
    return f"{diagnosis_type}_{cluster_num:04d}"


def migrate_questions(conn, df):
    """Migrate questions to database."""
    cursor = conn.cursor()

    # Track cluster numbers per diagnosis type
    cluster_counters = {"OD": 0, "LD": 0, "MA": 0, "DD": 0}

    questions_data = []
    master_questions_data = []

    for idx, row in df.iterrows():
        question_id = generate_question_id(idx + 1)
        diagnosis_type = row.get("대분류", "OD")

        # Handle cluster info
        cluster_id = row.get("cluster_id")
        is_representative = row.get("is_representative", False)

        # Generate master_id if representative
        master_id = None
        if is_representative:
            cluster_counters[diagnosis_type] += 1
            master_id = generate_master_id(diagnosis_type, cluster_counters[diagnosis_type])

        # Prepare question data
        questions_data.append({
            "question_id": question_id,
            "question_text": row.get("문항", ""),
            "diagnosis_type": diagnosis_type,
            "source_year": row.get("년도"),
            "question_type": "LIKERT",
            "scale_min": 1,
            "scale_max": 5,
            "cluster_id": cluster_id,
            "is_representative": is_representative,
            "legacy_mid_category": row.get("중분류"),
            "legacy_sub_category": row.get("소분류"),
        })

        # Prepare master question data
        if is_representative and master_id:
            master_questions_data.append({
                "master_id": master_id,
                "question_id": question_id,
                "diagnosis_type": diagnosis_type,
                "cluster_size": 1,  # Will be updated later
            })

    # Insert questions
    cursor.executemany("""
        INSERT INTO questions (
            question_id, question_text, diagnosis_type, source_year,
            question_type, scale_min, scale_max, cluster_id,
            is_representative, legacy_mid_category, legacy_sub_category
        ) VALUES (
            :question_id, :question_text, :diagnosis_type, :source_year,
            :question_type, :scale_min, :scale_max, :cluster_id,
            :is_representative, :legacy_mid_category, :legacy_sub_category
        )
    """, questions_data)
    print(f"  Inserted {len(questions_data)} questions")

    # Insert master questions
    cursor.executemany("""
        INSERT INTO master_questions (
            master_id, question_id, diagnosis_type, cluster_size
        ) VALUES (
            :master_id, :question_id, :diagnosis_type, :cluster_size
        )
    """, master_questions_data)
    print(f"  Inserted {len(master_questions_data)} master questions")

    # Update master_question_id references and cluster sizes
    update_master_references(conn, df, questions_data, master_questions_data)

    conn.commit()
    return len(questions_data), len(master_questions_data)


def update_master_references(conn, df, questions_data, master_questions_data):
    """Update master_question_id references in questions table."""
    cursor = conn.cursor()

    # Build mapping from cluster_id + diagnosis_type to master_id
    cluster_to_master = {}
    for i, row in df.iterrows():
        if row.get("is_representative"):
            key = (row["대분류"], row["cluster_id"])
            question_id = questions_data[i]["question_id"]
            # Find corresponding master_id
            for mq in master_questions_data:
                if mq["question_id"] == question_id:
                    cluster_to_master[key] = mq["master_id"]
                    break

    # Update questions with master_question_id
    updates = []
    cluster_sizes = {}  # master_id -> count

    for i, row in df.iterrows():
        key = (row["대분류"], row.get("cluster_id"))
        if key in cluster_to_master:
            master_id = cluster_to_master[key]
            question_id = questions_data[i]["question_id"]
            updates.append((master_id, question_id))

            # Count cluster sizes
            cluster_sizes[master_id] = cluster_sizes.get(master_id, 0) + 1

    cursor.executemany("""
        UPDATE questions SET master_question_id = ? WHERE question_id = ?
    """, updates)
    print(f"  Updated {len(updates)} master_question_id references")

    # Update cluster sizes in master_questions
    for master_id, size in cluster_sizes.items():
        cursor.execute("""
            UPDATE master_questions SET cluster_size = ? WHERE master_id = ?
        """, (size, master_id))
    print(f"  Updated cluster sizes for {len(cluster_sizes)} master questions")


def migrate_embeddings(conn, df):
    """Migrate embeddings to database."""
    cursor = conn.cursor()

    # Load embeddings
    npy_path = PROJECT_ROOT / "all_embeddings_hybrid.npy"
    if not npy_path.exists():
        print(f"  Warning: Embeddings file not found: {npy_path}")
        return 0

    embeddings = np.load(npy_path)
    print(f"  Loaded embeddings: {embeddings.shape}")

    # Insert embeddings
    data = []
    for idx in range(len(df)):
        question_id = generate_question_id(idx + 1)
        embedding_blob = embeddings[idx].astype(np.float32).tobytes()
        data.append((question_id, embedding_blob))

    cursor.executemany("""
        INSERT INTO embeddings (question_id, embedding)
        VALUES (?, ?)
    """, data)
    print(f"  Inserted {len(data)} embeddings")

    conn.commit()
    return len(data)


def run_migration():
    """Run the full migration."""
    print("=" * 50)
    print("MasterDB Question Migration")
    print("=" * 50)

    # Load data
    print("\n1. Loading source data...")
    df = load_questions_df()

    # Connect to database
    print("\n2. Connecting to database...")
    conn = get_connection()

    # Check if already migrated
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions")
    existing = cursor.fetchone()[0]
    if existing > 0:
        print(f"  Warning: questions table already has {existing} rows")
        response = input("  Clear and re-migrate? (y/n): ")
        if response.lower() != 'y':
            print("  Migration cancelled")
            return

        # Clear existing data
        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM question_tags")
        cursor.execute("DELETE FROM master_questions")
        cursor.execute("DELETE FROM questions")
        conn.commit()
        print("  Cleared existing data")

    # Migrate questions
    print("\n3. Migrating questions...")
    q_count, m_count = migrate_questions(conn, df)

    # Migrate embeddings
    print("\n4. Migrating embeddings...")
    e_count = migrate_embeddings(conn, df)

    # Summary
    print("\n" + "=" * 50)
    print("Migration Complete!")
    print("=" * 50)
    print(f"  Questions: {q_count}")
    print(f"  Master Questions: {m_count}")
    print(f"  Embeddings: {e_count}")

    conn.close()


if __name__ == "__main__":
    run_migration()
