"""
MasterDB Schema Definition

Defines all tables for the ontology-based survey question database.
Based on database_schema.md specification.
"""

SCHEMA_VERSION = "1.1"

# ============================================================
# 1. OPERATIONAL DATA TABLES
# ============================================================

COMPANIES_TABLE = """
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,           -- 회사 코드 (예: CJG, SKH)
    company_name TEXT NOT NULL,            -- 정식 회사명
    company_name_short TEXT,               -- 약칭

    -- 그룹 정보
    group_name TEXT,                       -- 소속 그룹 (예: CJ그룹, SK그룹)

    -- 회사 분류
    industry TEXT,                         -- 업종 (제조, IT, 금융, 서비스 등)
    company_size TEXT,                     -- 규모 (대기업, 중견기업, 중소기업, 스타트업)
    employee_count_range TEXT,             -- 직원 수 범위 (예: 1000-5000)

    -- 관계 정보
    is_active BOOLEAN DEFAULT TRUE,        -- 현재 거래 여부
    first_project_year INTEGER,            -- 첫 프로젝트 연도
    total_project_count INTEGER,           -- 총 프로젝트 수

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SURVEYS_TABLE = """
CREATE TABLE IF NOT EXISTS surveys (
    survey_id TEXT PRIMARY KEY,            -- 프로젝트 코드 (예: IG200601, CJG-2024-OD)
    survey_name TEXT NOT NULL,             -- 프로젝트 전체명

    -- 연결
    company_id TEXT REFERENCES companies(company_id),

    -- 설문 유형
    diagnosis_type TEXT NOT NULL,          -- OD, LD, MA, DD, ES 등
    survey_purpose TEXT,                   -- 진단 목적 설명

    -- 일정
    survey_year INTEGER NOT NULL,          -- 실시 연도
    survey_month INTEGER,                  -- 실시 월
    survey_start_date DATE,                -- 시작일
    survey_end_date DATE,                  -- 종료일

    -- 규모
    target_respondent_count INTEGER,       -- 목표 응답자 수
    actual_respondent_count INTEGER,       -- 실제 응답자 수
    question_count INTEGER,                -- 문항 수

    -- 상태
    status TEXT DEFAULT 'COMPLETED',       -- PLANNED, IN_PROGRESS, COMPLETED, ARCHIVED

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ORG_UNITS_TABLE = """
CREATE TABLE IF NOT EXISTS org_units (
    org_unit_id TEXT PRIMARY KEY,          -- 조직 코드 (예: CJG_HQ_HR)
    company_id TEXT REFERENCES companies(company_id),

    -- 조직 계층
    org_name TEXT NOT NULL,                -- 조직명 (예: 인사팀)
    org_level INTEGER,                     -- 조직 레벨 (1=본부, 2=실, 3=팀, 4=파트)
    org_type TEXT,                         -- 조직 유형 (본부, 사업부, 실, 팀, 파트)
    parent_org_unit_id TEXT REFERENCES org_units(org_unit_id),

    -- 조직 경로 (빠른 조회용)
    org_path TEXT,                         -- 예: /본사/경영지원본부/인사실/인사팀

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    valid_from DATE,                       -- 유효 시작일
    valid_to DATE,                         -- 유효 종료일

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ORG_UNIT_SURVEYS_TABLE = """
CREATE TABLE IF NOT EXISTS org_unit_surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT REFERENCES surveys(survey_id),
    org_unit_id TEXT REFERENCES org_units(org_unit_id),

    -- 참여 정보
    respondent_count INTEGER,              -- 응답자 수
    response_rate REAL,                    -- 응답률 (0.0 ~ 1.0)

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(survey_id, org_unit_id)
);
"""

SURVEY_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS survey_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT REFERENCES surveys(survey_id),
    question_id TEXT REFERENCES questions(question_id),

    -- 설문 내 위치
    section_name TEXT,                     -- 섹션명 (예: 비전/전략, 조직문화)
    question_order INTEGER,                -- 문항 순서 (1, 2, 3...)

    -- 문항 설정
    is_required BOOLEAN DEFAULT TRUE,      -- 필수 응답 여부
    scale_type TEXT,                       -- LIKERT_5, LIKERT_7, OPEN, CHOICE 등
    scale_labels TEXT,                     -- JSON: 척도 라벨

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(survey_id, question_id)
);
"""

# ============================================================
# 2. QUESTION DATA TABLES
# ============================================================

QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,          -- 문항 ID (예: Q_00001)
    question_text TEXT NOT NULL,           -- 문항 텍스트

    -- 구조적 메타데이터
    diagnosis_type TEXT NOT NULL,          -- OD, LD, MA, DD
    source_survey_id TEXT REFERENCES surveys(survey_id),  -- 최초 등장 설문
    source_year INTEGER,                   -- 최초 등장 연도
    reuse_count INTEGER DEFAULT 1,         -- 재사용 횟수

    -- 문항 유형
    question_type TEXT DEFAULT 'LIKERT',   -- LIKERT, CHOICE_SINGLE, CHOICE_MULTI, ESSAY
    scale_min INTEGER DEFAULT 1,           -- 최소 척도값
    scale_max INTEGER DEFAULT 5,           -- 최대 척도값 (5점, 7점 등)
    choices TEXT,                          -- JSON: 선택지 (객관식용)
    is_reverse BOOLEAN DEFAULT FALSE,      -- 역문항 여부

    -- 클러스터 정보
    cluster_id INTEGER,                    -- 클러스터 번호 (대분류 내)
    master_question_id TEXT,               -- 소속 대표 문항 ID
    is_representative BOOLEAN DEFAULT FALSE, -- 대표 문항 여부

    -- 레거시 분류 (참조용)
    legacy_mid_category TEXT,              -- 기존 중분류
    legacy_sub_category TEXT,              -- 기존 소분류

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MASTER_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS master_questions (
    master_id TEXT PRIMARY KEY,            -- 대표 문항 ID (예: OD_0001)
    question_id TEXT REFERENCES questions(question_id),
    diagnosis_type TEXT NOT NULL,          -- OD, LD, MA, DD
    cluster_size INTEGER,                  -- 클러스터 내 문항 수

    -- 의미론적 태그 (JSON)
    tags TEXT,                             -- {"concepts": [...], "aspects": [...]}

    -- 품질 지표
    centroid_distance REAL,                -- 중심점과의 거리 (낮을수록 대표성 높음)
    coherence_score REAL,                  -- 클러스터 응집도

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

EMBEDDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS embeddings (
    question_id TEXT PRIMARY KEY REFERENCES questions(question_id),
    embedding BLOB NOT NULL,               -- 768차원 float32 벡터 (직렬화)
    model_name TEXT DEFAULT 'jhgan/ko-sroberta-multitask',

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ============================================================
# 3. ONTOLOGY TABLES
# ============================================================

TAXONOMY_TABLE = """
CREATE TABLE IF NOT EXISTS taxonomy (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT UNIQUE NOT NULL,             -- 용어 (예: "비전", "리더십", "이해도")
    term_type TEXT NOT NULL,               -- THEME, CONCEPT, ASPECT, SUBJECT, METHOD

    -- 다국어/동의어
    aliases TEXT,                          -- JSON: {"ko": [...], "en": [...]}

    -- 설명
    description TEXT,                      -- 용어 설명
    examples TEXT,                         -- JSON: 예시 문항 ID 목록

    -- 통계
    usage_count INTEGER DEFAULT 0,         -- 태깅된 문항 수
    first_used_year INTEGER,               -- 최초 사용 연도

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
"""

TAXONOMY_RELATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS taxonomy_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_term_id INTEGER REFERENCES taxonomy(term_id),
    to_term_id INTEGER REFERENCES taxonomy(term_id),

    relation_type TEXT NOT NULL,           -- PARENT, CHILD, HAS_COMPONENT, RELATED, SIMILAR, SYNONYM, OPPOSITE
    strength REAL DEFAULT 1.0,             -- 관계 강도 (0.0 ~ 1.0)

    -- 맥락 정보
    context TEXT,                          -- JSON: 특정 맥락에서만 유효한 관계

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(from_term_id, to_term_id, relation_type)
);
"""

QUESTION_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS question_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT REFERENCES questions(question_id),
    term_id INTEGER REFERENCES taxonomy(term_id),

    tag_type TEXT,                         -- concepts, aspects, subjects, themes
    confidence REAL,                       -- 태깅 신뢰도 (0.0 ~ 1.0)
    is_auto_tagged BOOLEAN DEFAULT FALSE,  -- 자동 태깅 여부

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(question_id, term_id, tag_type)
);
"""

# ============================================================
# 4. SCALES TABLES
# ============================================================

SCALES_TABLE = """
CREATE TABLE IF NOT EXISTS scales (
    scale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scale_name TEXT UNIQUE NOT NULL,       -- 척도명 (예: "조직몰입도", "리더십효과성")
    description TEXT,                      -- 척도 설명

    -- 온톨로지 연결
    root_term_id INTEGER REFERENCES taxonomy(term_id),  -- 척도의 루트 개념

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
"""

SCALE_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS scale_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scale_id INTEGER REFERENCES scales(scale_id),
    master_question_id TEXT REFERENCES master_questions(master_id),

    sub_scale TEXT,                        -- 하위 척도 (예: "정서적몰입")
    weight REAL DEFAULT 1.0,               -- 가중치
    is_reverse_scored BOOLEAN DEFAULT FALSE, -- 역문항 여부

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(scale_id, master_question_id)
);
"""

# ============================================================
# INDEXES
# ============================================================

INDEXES = """
-- companies
CREATE INDEX IF NOT EXISTS idx_companies_group ON companies(group_name);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry);
CREATE INDEX IF NOT EXISTS idx_companies_size ON companies(company_size);

-- surveys
CREATE INDEX IF NOT EXISTS idx_surveys_company ON surveys(company_id);
CREATE INDEX IF NOT EXISTS idx_surveys_year ON surveys(survey_year);
CREATE INDEX IF NOT EXISTS idx_surveys_type ON surveys(diagnosis_type);
CREATE INDEX IF NOT EXISTS idx_surveys_status ON surveys(status);
CREATE INDEX IF NOT EXISTS idx_surveys_company_year ON surveys(company_id, survey_year);

-- org_units
CREATE INDEX IF NOT EXISTS idx_org_units_company ON org_units(company_id);
CREATE INDEX IF NOT EXISTS idx_org_units_parent ON org_units(parent_org_unit_id);
CREATE INDEX IF NOT EXISTS idx_org_units_level ON org_units(org_level);

-- org_unit_surveys
CREATE INDEX IF NOT EXISTS idx_org_unit_surveys_survey ON org_unit_surveys(survey_id);
CREATE INDEX IF NOT EXISTS idx_org_unit_surveys_org ON org_unit_surveys(org_unit_id);

-- survey_questions
CREATE INDEX IF NOT EXISTS idx_survey_questions_survey ON survey_questions(survey_id);
CREATE INDEX IF NOT EXISTS idx_survey_questions_question ON survey_questions(question_id);
CREATE INDEX IF NOT EXISTS idx_survey_questions_section ON survey_questions(section_name);

-- questions
CREATE INDEX IF NOT EXISTS idx_questions_diagnosis ON questions(diagnosis_type);
CREATE INDEX IF NOT EXISTS idx_questions_cluster ON questions(cluster_id);
CREATE INDEX IF NOT EXISTS idx_questions_master ON questions(master_question_id);
CREATE INDEX IF NOT EXISTS idx_questions_source_survey ON questions(source_survey_id);
CREATE INDEX IF NOT EXISTS idx_questions_representative ON questions(is_representative);

-- master_questions
CREATE INDEX IF NOT EXISTS idx_master_diagnosis ON master_questions(diagnosis_type);
CREATE INDEX IF NOT EXISTS idx_master_cluster_size ON master_questions(cluster_size);

-- taxonomy
CREATE INDEX IF NOT EXISTS idx_taxonomy_type ON taxonomy(term_type);
CREATE INDEX IF NOT EXISTS idx_taxonomy_term ON taxonomy(term);
CREATE INDEX IF NOT EXISTS idx_taxonomy_usage ON taxonomy(usage_count DESC);

-- taxonomy_relations
CREATE INDEX IF NOT EXISTS idx_relations_from ON taxonomy_relations(from_term_id);
CREATE INDEX IF NOT EXISTS idx_relations_to ON taxonomy_relations(to_term_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON taxonomy_relations(relation_type);

-- question_tags
CREATE INDEX IF NOT EXISTS idx_tags_question ON question_tags(question_id);
CREATE INDEX IF NOT EXISTS idx_tags_term ON question_tags(term_id);
CREATE INDEX IF NOT EXISTS idx_tags_type ON question_tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_tags_confidence ON question_tags(confidence DESC);

-- scales
CREATE INDEX IF NOT EXISTS idx_scales_root ON scales(root_term_id);

-- scale_questions
CREATE INDEX IF NOT EXISTS idx_scale_questions_scale ON scale_questions(scale_id);
CREATE INDEX IF NOT EXISTS idx_scale_questions_master ON scale_questions(master_question_id);
CREATE INDEX IF NOT EXISTS idx_scale_questions_subscale ON scale_questions(sub_scale);
"""

# ============================================================
# TABLE CREATION ORDER (respecting foreign key dependencies)
# ============================================================

ALL_TABLES = [
    # 1. Operational (no dependencies first)
    ("companies", COMPANIES_TABLE),
    ("surveys", SURVEYS_TABLE),
    ("org_units", ORG_UNITS_TABLE),
    ("org_unit_surveys", ORG_UNIT_SURVEYS_TABLE),

    # 2. Questions (surveys must exist)
    ("questions", QUESTIONS_TABLE),
    ("master_questions", MASTER_QUESTIONS_TABLE),
    ("embeddings", EMBEDDINGS_TABLE),
    ("survey_questions", SURVEY_QUESTIONS_TABLE),

    # 3. Ontology
    ("taxonomy", TAXONOMY_TABLE),
    ("taxonomy_relations", TAXONOMY_RELATIONS_TABLE),
    ("question_tags", QUESTION_TAGS_TABLE),

    # 4. Scales
    ("scales", SCALES_TABLE),
    ("scale_questions", SCALE_QUESTIONS_TABLE),
]


def create_all_tables(conn):
    """Create all tables and indexes in the database."""
    cursor = conn.cursor()

    # Create tables
    for table_name, table_sql in ALL_TABLES:
        cursor.execute(table_sql)
        print(f"  Created table: {table_name}")

    # Create indexes
    for index_sql in INDEXES.strip().split(";"):
        if index_sql.strip():
            cursor.execute(index_sql)
    print("  Created all indexes")

    conn.commit()
    return True


def get_table_counts(conn):
    """Get row counts for all tables."""
    cursor = conn.cursor()
    counts = {}
    for table_name, _ in ALL_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        counts[table_name] = cursor.fetchone()[0]
    return counts
