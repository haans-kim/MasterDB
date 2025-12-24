"""
Migrate Surveys and Companies from Excel to SQLite

Migrates:
- companies table (~120 rows)
- surveys table (~355 rows)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
from db.connection import get_connection


def load_survey_meta():
    """Load survey metadata from Excel file."""
    excel_path = PROJECT_ROOT / "data" / "Survey Meta Data_251224.xlsx"
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Read the Survey 목록 sheet
    df = pd.read_excel(excel_path, sheet_name="Survey 목록")
    print(f"Loaded {len(df)} surveys from Excel")
    return df


def extract_companies(df):
    """Extract unique companies from survey data."""
    companies = {}

    for _, row in df.iterrows():
        company_name = row.get("회사명", "")
        if pd.isna(company_name) or not company_name:
            continue

        # Generate company_id from name (first 3-4 chars uppercase)
        company_id = generate_company_id(company_name)

        if company_id not in companies:
            companies[company_id] = {
                "company_id": company_id,
                "company_name": company_name,
                "company_name_short": company_name[:10] if len(company_name) > 10 else company_name,
                "is_active": True,
            }

    return list(companies.values())


def generate_company_id(company_name):
    """Generate a company ID from company name."""
    # Remove common suffixes
    name = company_name.replace("(주)", "").replace("주식회사", "").strip()

    # Use first word or abbreviation
    if len(name) <= 4:
        return name.upper()

    # Extract initials for Korean names
    initials = ""
    for char in name[:5]:
        if '\uAC00' <= char <= '\uD7A3':  # Korean character range
            initials += char
        elif char.isalpha():
            initials += char.upper()

    return initials[:6].upper() if initials else name[:6].upper()


def generate_survey_id(row):
    """Generate survey ID from row data."""
    # Try to use IG number if available
    ig_no = row.get("IG", row.get("IG No", row.get("프로젝트번호", "")))
    if ig_no and not pd.isna(ig_no):
        return f"IG{str(ig_no).replace('IG', '').strip()}"

    # Fall back to company-year-type format
    company = row.get("회사명", "UNKNOWN")
    year = row.get("년도", row.get("연도", 2024))
    diag_type = row.get("진단유형", row.get("대분류", "OD"))

    company_id = generate_company_id(company)
    return f"{company_id}-{year}-{diag_type}"


def migrate_companies(conn, companies_data):
    """Migrate companies to database."""
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR IGNORE INTO companies (
            company_id, company_name, company_name_short, is_active
        ) VALUES (
            :company_id, :company_name, :company_name_short, :is_active
        )
    """, companies_data)

    conn.commit()
    print(f"  Inserted {len(companies_data)} companies")
    return len(companies_data)


def migrate_surveys(conn, df):
    """Migrate surveys to database."""
    cursor = conn.cursor()

    surveys_data = []
    for _, row in df.iterrows():
        company_name = row.get("회사명", "")
        if pd.isna(company_name) or not company_name:
            continue

        survey_id = generate_survey_id(row)
        company_id = generate_company_id(company_name)

        # Extract year
        year = row.get("년도", row.get("연도"))
        if pd.isna(year):
            year = 2024

        # Extract diagnosis type
        diag_type = row.get("진단유형", row.get("대분류", "OD"))
        if pd.isna(diag_type):
            diag_type = "OD"

        surveys_data.append({
            "survey_id": survey_id,
            "survey_name": row.get("프로젝트명", f"{company_name} {year} {diag_type}"),
            "company_id": company_id,
            "diagnosis_type": diag_type,
            "survey_year": int(year),
            "question_count": row.get("문항수"),
            "status": "COMPLETED",
        })

    # Remove duplicates by survey_id
    seen = set()
    unique_surveys = []
    for s in surveys_data:
        if s["survey_id"] not in seen:
            seen.add(s["survey_id"])
            unique_surveys.append(s)

    cursor.executemany("""
        INSERT OR IGNORE INTO surveys (
            survey_id, survey_name, company_id, diagnosis_type,
            survey_year, question_count, status
        ) VALUES (
            :survey_id, :survey_name, :company_id, :diagnosis_type,
            :survey_year, :question_count, :status
        )
    """, unique_surveys)

    conn.commit()
    print(f"  Inserted {len(unique_surveys)} surveys")
    return len(unique_surveys)


def run_migration():
    """Run the survey migration."""
    print("=" * 50)
    print("MasterDB Survey/Company Migration")
    print("=" * 50)

    # Load data
    print("\n1. Loading source data...")
    try:
        df = load_survey_meta()
    except FileNotFoundError as e:
        print(f"  Error: {e}")
        print("  Skipping survey migration (file not found)")
        return

    # Extract companies
    print("\n2. Extracting companies...")
    companies = extract_companies(df)
    print(f"  Found {len(companies)} unique companies")

    # Connect to database
    print("\n3. Connecting to database...")
    conn = get_connection()

    # Check if already migrated
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    existing = cursor.fetchone()[0]
    if existing > 0:
        print(f"  Warning: companies table already has {existing} rows")
        response = input("  Clear and re-migrate? (y/n): ")
        if response.lower() != 'y':
            print("  Migration cancelled")
            return

        cursor.execute("DELETE FROM surveys")
        cursor.execute("DELETE FROM companies")
        conn.commit()
        print("  Cleared existing data")

    # Migrate companies
    print("\n4. Migrating companies...")
    c_count = migrate_companies(conn, companies)

    # Migrate surveys
    print("\n5. Migrating surveys...")
    s_count = migrate_surveys(conn, df)

    # Summary
    print("\n" + "=" * 50)
    print("Migration Complete!")
    print("=" * 50)
    print(f"  Companies: {c_count}")
    print(f"  Surveys: {s_count}")

    conn.close()


if __name__ == "__main__":
    run_migration()
