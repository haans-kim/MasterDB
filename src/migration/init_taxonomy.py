"""
Initialize Taxonomy from Legacy Categories

Builds initial taxonomy structure from existing mid/sub categories
and creates question_tags mappings.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from db.connection import get_connection


# Taxonomy term types
TERM_TYPES = {
    "THEME": "대주제 (진단 유형별 최상위)",
    "CONCEPT": "개념 (중분류 수준)",
    "ASPECT": "관점/측면 (소분류 수준)",
}

# Theme definitions (diagnosis types as top-level themes)
THEMES = {
    "OD": {"term": "조직진단", "description": "조직 전반의 효과성과 건강성 진단"},
    "LD": {"term": "리더십진단", "description": "리더의 역량과 행동 진단"},
    "MA": {"term": "다면평가", "description": "360도 다면적 역량 평가"},
    "DD": {"term": "사외이사평가", "description": "이사회 및 사외이사 효과성 평가"},
}

# Concept mappings (mid categories -> normalized concepts)
CONCEPT_MAPPINGS = {
    "리더십": {"term": "리더십", "description": "리더의 행동, 스타일, 역량"},
    "조직/프로세스": {"term": "조직프로세스", "description": "업무 프로세스와 조직 구조"},
    "비전/전략": {"term": "비전전략", "description": "조직의 비전, 미션, 전략 방향"},
    "인사제도": {"term": "인사제도", "description": "평가, 보상, 승진 등 HR 제도"},
    "조직문화": {"term": "조직문화", "description": "조직의 가치, 규범, 분위기"},
    "경영/전략": {"term": "경영전략", "description": "경영 일반 및 전략적 의사결정"},
    "몰입도": {"term": "구성원몰입", "description": "직원 몰입도와 동기부여"},
    "기타": {"term": "기타", "description": "기타 분류"},
}

# Aspect mappings (sub categories -> normalized aspects)
# Group similar sub-categories under unified aspects
ASPECT_GROUPS = {
    # 리더십 관련
    "리더십일반": ["리더십일반"],
    "코칭육성": ["코칭/육성", "육성"],
    "소통경청": ["소통/경청", "의사소통", "커뮤니케이션"],
    "동기부여": ["동기부여", "동기유발"],
    "권한위임": ["권한위임", "위임"],
    "배려관계": ["배려/관계", "관계", "배려"],
    "공정성": ["공정성"],
    "신뢰": ["신뢰"],
    "역할책임": ["역할/책임", "역할책임", "책임"],

    # 조직/프로세스 관련
    "조직구조": ["조직구조일반", "조직구조"],
    "업무프로세스": ["업무프로세스", "프로세스"],
    "의사결정": ["의사결정"],
    "업무효율성": ["업무효율성", "효율성"],
    "협업팀워크": ["협업/팀워크", "팀워크", "협업"],
    "고객서비스": ["고객서비스", "고객지향"],

    # 비전/전략 관련
    "목표방향": ["목표/방향", "목표/전략", "목표설정"],
    "목표KPI": ["목표/KPI", "KPI"],
    "이해실천": ["이해및실천", "전략이해"],
    "변화혁신": ["변화/혁신", "도전/혁신", "혁신"],

    # 인사제도 관련
    "평가제도": ["평가제도", "성과평가"],
    "보상제도": ["보상제도", "보상"],
    "승진제도": ["직급/승진제도", "승진"],
    "교육연수": ["교육/연수", "교육"],

    # 조직문화 관련
    "조직문화유형": ["조직문화유형", "문화유형"],
    "조직몰입": ["조직몰입도", "몰입도"],

    # 경영 관련
    "경영일반": ["경영일반"],
}


def init_taxonomy(conn):
    """Initialize taxonomy with themes, concepts, and aspects."""
    cursor = conn.cursor()

    # Clear existing taxonomy data
    cursor.execute("DELETE FROM question_tags")
    cursor.execute("DELETE FROM taxonomy_relations")
    cursor.execute("DELETE FROM taxonomy")
    conn.commit()

    term_id_map = {}  # term -> term_id

    # 1. Insert Themes (diagnosis types)
    print("\n[1] Inserting Themes...")
    for diag_type, info in THEMES.items():
        cursor.execute("""
            INSERT INTO taxonomy (term, term_type, description)
            VALUES (?, 'THEME', ?)
        """, (info["term"], info["description"]))
        term_id = cursor.lastrowid
        term_id_map[f"THEME_{diag_type}"] = term_id
        print(f"  + {info['term']} (THEME)")

    # 2. Insert Concepts (mid categories)
    print("\n[2] Inserting Concepts...")
    for legacy_name, info in CONCEPT_MAPPINGS.items():
        cursor.execute("""
            INSERT INTO taxonomy (term, term_type, description)
            VALUES (?, 'CONCEPT', ?)
        """, (info["term"], info["description"]))
        term_id = cursor.lastrowid
        term_id_map[f"CONCEPT_{legacy_name}"] = term_id
        term_id_map[f"CONCEPT_{info['term']}"] = term_id
        print(f"  + {info['term']} (CONCEPT)")

    # 3. Insert Aspects (sub categories)
    print("\n[3] Inserting Aspects...")
    for aspect_name, legacy_names in ASPECT_GROUPS.items():
        cursor.execute("""
            INSERT INTO taxonomy (term, term_type, aliases)
            VALUES (?, 'ASPECT', ?)
        """, (aspect_name, str(legacy_names)))
        term_id = cursor.lastrowid
        term_id_map[f"ASPECT_{aspect_name}"] = term_id
        for legacy in legacy_names:
            term_id_map[f"ASPECT_{legacy}"] = term_id
        print(f"  + {aspect_name} (ASPECT) <- {legacy_names}")

    conn.commit()

    # 4. Create taxonomy relations
    print("\n[4] Creating Taxonomy Relations...")

    # Theme -> Concept relations (based on typical associations)
    theme_concept_map = {
        "OD": ["조직/프로세스", "비전/전략", "인사제도", "조직문화", "리더십", "몰입도"],
        "LD": ["리더십", "조직/프로세스", "비전/전략"],
        "MA": ["리더십", "조직/프로세스", "비전/전략"],
        "DD": ["리더십", "경영/전략", "조직/프로세스"],
    }

    for diag_type, concepts in theme_concept_map.items():
        theme_id = term_id_map.get(f"THEME_{diag_type}")
        if not theme_id:
            continue
        for concept in concepts:
            concept_id = term_id_map.get(f"CONCEPT_{concept}")
            if concept_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO taxonomy_relations
                    (from_term_id, to_term_id, relation_type, strength)
                    VALUES (?, ?, 'HAS_COMPONENT', 1.0)
                """, (theme_id, concept_id))

    # Concept -> Aspect relations
    concept_aspect_map = {
        "리더십": ["리더십일반", "코칭육성", "소통경청", "동기부여", "권한위임", "배려관계", "공정성", "신뢰", "역할책임"],
        "조직/프로세스": ["조직구조", "업무프로세스", "의사결정", "업무효율성", "협업팀워크", "고객서비스"],
        "비전/전략": ["목표방향", "목표KPI", "이해실천", "변화혁신"],
        "인사제도": ["평가제도", "보상제도", "승진제도", "교육연수"],
        "조직문화": ["조직문화유형", "조직몰입"],
        "경영/전략": ["경영일반"],
        "몰입도": ["조직몰입", "동기부여"],
    }

    for concept, aspects in concept_aspect_map.items():
        concept_id = term_id_map.get(f"CONCEPT_{concept}")
        if not concept_id:
            continue
        for aspect in aspects:
            aspect_id = term_id_map.get(f"ASPECT_{aspect}")
            if aspect_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO taxonomy_relations
                    (from_term_id, to_term_id, relation_type, strength)
                    VALUES (?, ?, 'HAS_COMPONENT', 1.0)
                """, (concept_id, aspect_id))

    conn.commit()

    # Count relations
    cursor.execute("SELECT COUNT(*) FROM taxonomy_relations")
    rel_count = cursor.fetchone()[0]
    print(f"  Created {rel_count} relations")

    return term_id_map


def create_question_tags(conn, term_id_map):
    """Create question_tags from legacy categories."""
    cursor = conn.cursor()

    print("\n[5] Creating Question Tags...")

    # Get all questions with legacy categories
    cursor.execute("""
        SELECT question_id, diagnosis_type, legacy_mid_category, legacy_sub_category
        FROM questions
        WHERE legacy_mid_category IS NOT NULL OR legacy_sub_category IS NOT NULL
    """)
    questions = cursor.fetchall()

    tags_created = 0

    for q in questions:
        question_id, diag_type, mid_cat, sub_cat = q

        # Tag with theme (diagnosis type)
        theme_id = term_id_map.get(f"THEME_{diag_type}")
        if theme_id:
            cursor.execute("""
                INSERT OR IGNORE INTO question_tags
                (question_id, term_id, tag_type, confidence, is_auto_tagged)
                VALUES (?, ?, 'themes', 1.0, 0)
            """, (question_id, theme_id))
            tags_created += 1

        # Tag with concept (mid category)
        if mid_cat:
            concept_id = term_id_map.get(f"CONCEPT_{mid_cat}")
            if concept_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO question_tags
                    (question_id, term_id, tag_type, confidence, is_auto_tagged)
                    VALUES (?, ?, 'concepts', 1.0, 0)
                """, (question_id, concept_id))
                tags_created += 1

        # Tag with aspect (sub category)
        if sub_cat:
            aspect_id = term_id_map.get(f"ASPECT_{sub_cat}")
            if aspect_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO question_tags
                    (question_id, term_id, tag_type, confidence, is_auto_tagged)
                    VALUES (?, ?, 'aspects', 1.0, 0)
                """, (question_id, aspect_id))
                tags_created += 1

    conn.commit()
    print(f"  Created {tags_created} question tags")

    # Update usage counts
    print("\n[6] Updating Usage Counts...")
    cursor.execute("""
        UPDATE taxonomy SET usage_count = (
            SELECT COUNT(*) FROM question_tags WHERE question_tags.term_id = taxonomy.term_id
        )
    """)
    conn.commit()

    return tags_created


def run_taxonomy_init():
    """Run full taxonomy initialization."""
    print("=" * 60)
    print("  MasterDB Taxonomy Initialization")
    print("=" * 60)

    conn = get_connection()

    # Initialize taxonomy
    term_id_map = init_taxonomy(conn)

    # Create question tags
    tags_count = create_question_tags(conn, term_id_map)

    # Summary
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    cursor.execute("SELECT term_type, COUNT(*) FROM taxonomy GROUP BY term_type")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute("SELECT COUNT(*) FROM taxonomy_relations")
    print(f"  Relations: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM question_tags")
    print(f"  Question Tags: {cursor.fetchone()[0]}")

    # Top used terms
    print("\n[Top 10 Used Terms]")
    cursor.execute("""
        SELECT term, term_type, usage_count
        FROM taxonomy
        ORDER BY usage_count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]} ({row[1]}): {row[2]}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    run_taxonomy_init()
