# MasterDB 온톨로지 기반 구현 계획서

**작성일**: 2024-12-24
**버전**: 1.0
**Phase**: Phase 1 - SQLite 기반 프로토타입

---

## 1. 현재 상황 정리

### 1.1 완료된 작업: 원천 데이터 정제

```
┌─────────────────────────────────────────────────────────────┐
│                    원천 데이터 정제 완료                      │
├─────────────────────────────────────────────────────────────┤
│  17,556개 원본 문항 (프로젝트별 중복 포함)                    │
│           ↓                                                 │
│  7,343개 고유 문항 (Cleansing 완료)                          │
│           ↓                                                 │
│  KoSBERT Hybrid Embedding (768차원)                         │
│           ↓                                                 │
│  Agglomerative Clustering (threshold=0.15)                  │
│           ↓                                                 │
│  3,274개 대표 문항 (Question Key) + 클러스터 매핑            │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 현재 데이터 자산

| 자산 | 내용 | 파일 |
|------|------|------|
| **정제된 문항** | 7,343개 고유 문항 | all_df_hybrid.pkl |
| **임베딩 벡터** | 7,343 × 768 (KoSBERT) | all_embeddings_hybrid.npy |
| **대표 문항** | 3,274개 클러스터 대표 | Master_Questions.xlsx |
| **분류 라벨** | 기존 분류체계 참조용 메타데이터 | 중분류/소분류 컬럼 |

### 1.3 현재 분류 라벨 현황 (참조용 메타데이터)

**대분류 (진단 유형)**: 4개
- OD (조직진단): 5,179개 → 2,199 클러스터
- LD (리더십진단): 1,590개 → 697 클러스터
- MA (다면평가): 364개 → 275 클러스터
- DD (사외이사평가): 210개 → 103 클러스터

**중분류**: 8개 카테고리
| 중분류 | 문항 수 | 비율 |
|--------|---------|------|
| 조직/프로세스 | 2,456 | 33.4% |
| 리더십 | 2,421 | 33.0% |
| 인사제도 | 898 | 12.2% |
| 비전/전략 | 483 | 6.6% |
| 조직문화 | 420 | 5.7% |
| 기타 | 378 | 5.1% |
| 몰입도 | 240 | 3.3% |
| 경영/전략 | 47 | 0.6% |

**소분류**: 65개 카테고리 (상위 20개)
| 소분류 | 문항 수 |
|--------|---------|
| 조직구조일반 | 942 |
| 업무프로세스 | 806 |
| 리더십일반 | 535 |
| 목표/방향 | 360 |
| 의사결정 | 320 |
| 보상제도 | 284 |
| 경영일반 | 265 |
| 코칭/육성 | 252 |
| ... | ... |

### 1.4 클러스터링 특성

| 지표 | 값 |
|------|-----|
| 총 클러스터 수 | 3,274개 |
| 평균 클러스터 크기 | 2.24개 |
| 싱글톤 클러스터 (1개) | 1,910개 (58.3%) |
| 2개 이상 클러스터 | 1,364개 (41.7%) |
| 5개 이상 클러스터 | 284개 (8.7%) |
| 최대 클러스터 크기 | 61개 |

### 1.5 현재 상태의 본질

```
현재 결과물의 의미:
┌──────────────────────────────────────────────────────────┐
│  ✓ 유사/중복 문항 그룹화 (클러스터)                        │
│  ✓ 각 그룹의 대표 문항 선정 (Question Key)                │
│  ✓ 기존 분류체계 라벨 부착 (익숙한 참조용)                 │
│                                                          │
│  ✗ 온톨로지 구조 (용어 간 관계)                           │
│  ✗ 다차원 태깅 (JSONB 태그)                               │
│  ✗ 의미 기반 검색 시스템                                  │
│  ✗ 척도/Construct 정의                                   │
└──────────────────────────────────────────────────────────┘
```

---

## 2. 목표: 온톨로지 기반 Master DB

### 2.1 최종 목표 아키텍처

```
                    ┌─────────────────────────────────────┐
                    │         Master DB (SQLite)          │
                    ├─────────────────────────────────────┤
┌──────────────┐    │  ┌─────────────┐  ┌─────────────┐  │
│ 3,274개      │───→│  │ questions   │  │ taxonomy    │  │
│ 대표 문항    │    │  │ (문항)      │  │ (용어)      │  │
└──────────────┘    │  └──────┬──────┘  └──────┬──────┘  │
                    │         │                 │         │
┌──────────────┐    │  ┌──────┴──────┐  ┌──────┴──────┐  │
│ 7,343개      │───→│  │ question_   │  │ taxonomy_   │  │
│ 전체 문항    │    │  │ tags (태깅) │  │ relations   │  │
└──────────────┘    │  └─────────────┘  └─────────────┘  │
                    │                                     │
┌──────────────┐    │  ┌─────────────┐  ┌─────────────┐  │
│ 임베딩 벡터  │───→│  │ embeddings  │  │ scales      │  │
│ (768D)       │    │  │ (벡터)      │  │ (척도)      │  │
└──────────────┘    │  └─────────────┘  └─────────────┘  │
                    └─────────────────────────────────────┘
```

### 2.2 핵심 개념 정의

| 개념 | 정의 | 예시 |
|------|------|------|
| **Question** | 개별 설문 문항 | "우리 회사의 비전이 무엇인지 이해하고 있다" |
| **Master Question** | 클러스터 대표 문항 (3,274개) | OD_0044 |
| **Taxonomy Term** | 온톨로지 용어 (개념) | "비전", "이해도", "리더십" |
| **Tag** | 문항에 부여된 다차원 라벨 | concepts: ["비전"], aspects: ["이해도"] |
| **Relation** | 용어 간 관계 | 비전 --PARENT--> 경영전략 |
| **Scale** | 측정 척도 (Construct) | "조직몰입도 척도" = [자긍심, 소속감, 충성도] |

### 2.3 테이블 구조 요약

```
┌─────────────────────────────────────────────────────────────────┐
│                     Master DB 테이블 구조                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [운영 데이터]                                                   │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  companies   │   surveys    │  org_units   │org_unit_     │ │
│  │  (고객사)    │   (설문)     │  (조직)      │surveys       │ │
│  │  120개       │   355개      │  확장예정    │              │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│                         │                                       │
│                         ▼                                       │
│  [문항 데이터]          survey_questions (설문-문항 매핑)        │
│  ┌──────────────┬──────────────┬──────────────┐                │
│  │  questions   │   master_    │  embeddings  │                │
│  │  (전체문항)  │  questions   │  (임베딩)    │                │
│  │  7,343개     │  3,274개     │  768차원     │                │
│  └──────────────┴──────────────┴──────────────┘                │
│         │                                                       │
│         ▼                                                       │
│  [온톨로지]             question_tags (문항-태그 매핑)           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │  taxonomy    │  taxonomy_   │   scales     │   scale_     │ │
│  │  (용어)      │  relations   │   (척도)     │  questions   │ │
│  │  ~150개      │  (관계)      │              │              │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1 구현 계획 (SQLite 기반)

### 3.1 Phase 1 목표

```
Phase 1 핵심 목표:
┌────────────────────────────────────────────────────────┐
│  1. SQLite 기반 프로토타입 DB 구축                      │
│  2. 현재 데이터 마이그레이션 (pkl → SQLite)             │
│  3. 온톨로지 기본 구조 구현                             │
│  4. Claude Code와 함께 검증 및 반복 개선                │
└────────────────────────────────────────────────────────┘
```

### 3.2 SQLite 스키마 설계

#### 3.2.1 Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  companies  │────<│  surveys    │────<│survey_questions│
│  (고객사)   │     │  (설문)     │     │ (설문-문항)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│ org_units   │────<│org_unit_    │            │
│ (조직단위)  │     │ surveys     │            │
└─────────────┘     └─────────────┘            │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  taxonomy   │────<│question_tags│>────│  questions  │
│  (온톨로지) │     │  (태깅)     │     │   (문항)    │
└──────┬──────┘     └─────────────┘     └──────┬──────┘
       │                                       │
       ▼                                       ▼
┌─────────────┐                         ┌─────────────┐
│ taxonomy_   │                         │   master_   │
│ relations   │                         │  questions  │
└─────────────┘                         └─────────────┘
```

#### 3.2.2 운영 데이터 테이블 (Operational Data)

```sql
-- ============================================
-- 1. companies: 고객사 정보 (120개사)
-- ============================================
CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,       -- 예: CJG, SKG, DGB
    company_name TEXT NOT NULL,        -- 정식 회사명
    company_name_short TEXT,           -- 약칭

    -- 그룹 정보
    group_name TEXT,                   -- 소속 그룹 (예: CJ그룹, SK그룹)

    -- 회사 분류
    industry TEXT,                     -- 업종 (제조, IT, 금융, 서비스 등)
    company_size TEXT,                 -- 규모 (대기업, 중견기업, 중소기업, 스타트업)
    employee_count_range TEXT,         -- 직원 수 범위 (예: 1000-5000)

    -- 연락처/관계
    is_active BOOLEAN DEFAULT TRUE,    -- 현재 거래 여부
    first_project_year INTEGER,        -- 첫 프로젝트 연도
    total_project_count INTEGER,       -- 총 프로젝트 수

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. surveys: 설문 프로젝트 정보 (355개)
-- ============================================
CREATE TABLE surveys (
    survey_id TEXT PRIMARY KEY,        -- 예: IG200601
    survey_name TEXT NOT NULL,         -- 프로젝트 전체명

    -- 연결
    company_id TEXT REFERENCES companies(company_id),

    -- 설문 유형
    diagnosis_type TEXT NOT NULL,      -- OD, LD, MA, DD, ES 등
    survey_purpose TEXT,               -- 진단 목적 (조직진단, 리더십진단 등)

    -- 일정
    survey_year INTEGER NOT NULL,      -- 실시 연도
    survey_month INTEGER,              -- 실시 월
    survey_start_date DATE,            -- 시작일
    survey_end_date DATE,              -- 종료일

    -- 규모
    target_respondent_count INTEGER,   -- 목표 응답자 수
    actual_respondent_count INTEGER,   -- 실제 응답자 수
    question_count INTEGER,            -- 문항 수

    -- 상태
    status TEXT DEFAULT 'COMPLETED',   -- PLANNED, IN_PROGRESS, COMPLETED, ARCHIVED

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. org_units: 조직 단위 정보
-- ============================================
CREATE TABLE org_units (
    org_unit_id TEXT PRIMARY KEY,      -- 예: CJG_HQ_HR
    company_id TEXT REFERENCES companies(company_id),

    -- 조직 계층
    org_name TEXT NOT NULL,            -- 조직명 (예: 인사팀)
    org_level INTEGER,                 -- 조직 레벨 (1=본부, 2=실, 3=팀)
    org_type TEXT,                     -- 조직 유형 (본부, 사업부, 실, 팀, 파트)
    parent_org_unit_id TEXT REFERENCES org_units(org_unit_id),

    -- 조직 경로 (빠른 조회용)
    org_path TEXT,                     -- 예: /본사/경영지원본부/인사실/인사팀

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    valid_from DATE,
    valid_to DATE,

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 4. org_unit_surveys: 조직-설문 매핑
-- ============================================
CREATE TABLE org_unit_surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT REFERENCES surveys(survey_id),
    org_unit_id TEXT REFERENCES org_units(org_unit_id),

    -- 해당 조직의 설문 참여 정보
    respondent_count INTEGER,          -- 응답자 수
    response_rate REAL,                -- 응답률

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 5. survey_questions: 설문-문항 매핑
-- ============================================
CREATE TABLE survey_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT REFERENCES surveys(survey_id),
    question_id TEXT REFERENCES questions(question_id),

    -- 설문 내 위치
    section_name TEXT,                 -- 섹션명 (예: 비전/전략, 조직문화)
    question_order INTEGER,            -- 문항 순서

    -- 문항 설정
    is_required BOOLEAN DEFAULT TRUE,  -- 필수 여부
    scale_type TEXT,                   -- LIKERT_5, LIKERT_7, OPEN 등
    scale_labels TEXT,                 -- JSON: 척도 라벨 (예: ["매우 그렇다", ...])

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(survey_id, question_id)
);
```

#### 3.2.3 문항 데이터 테이블 (Question Data)

```sql
-- ============================================
-- 6. questions: 전체 문항 (7,343개)
-- ============================================
CREATE TABLE questions (
    question_id TEXT PRIMARY KEY,      -- 예: Q_00001
    question_text TEXT NOT NULL,       -- 문항 텍스트

    -- 구조적 메타데이터 (Structural)
    diagnosis_type TEXT NOT NULL,      -- OD, LD, MA, DD
    source_survey_id TEXT REFERENCES surveys(survey_id),  -- 최초 등장 설문
    source_year INTEGER,               -- 최초 등장 연도
    reuse_count INTEGER DEFAULT 1,     -- 재사용 횟수 (No1~No6 기반)

    -- 클러스터 정보
    cluster_id INTEGER,                -- 클러스터 번호
    master_question_id TEXT,           -- 소속 대표 문항 ID
    is_representative BOOLEAN,         -- 대표 문항 여부

    -- 레거시 분류 (참조용)
    legacy_mid_category TEXT,          -- 기존 중분류
    legacy_sub_category TEXT,          -- 기존 소분류

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. master_questions: 대표 문항 (3,274개)
-- ============================================
CREATE TABLE master_questions (
    master_id TEXT PRIMARY KEY,        -- 예: OD_0001
    question_id TEXT REFERENCES questions(question_id),
    diagnosis_type TEXT NOT NULL,
    cluster_size INTEGER,              -- 클러스터 내 문항 수

    -- 의미론적 태그 (JSON)
    tags TEXT,                         -- JSON: {"concepts": [...], "aspects": [...]}

    -- 품질 지표
    centroid_distance REAL,            -- 중심점과의 거리
    coherence_score REAL,              -- 클러스터 응집도

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. taxonomy: 온톨로지 용어
-- ============================================
CREATE TABLE taxonomy (
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT UNIQUE NOT NULL,         -- 용어 (예: "비전", "리더십")
    term_type TEXT NOT NULL,           -- THEME, CONCEPT, ASPECT, SUBJECT, METHOD

    -- 다국어/동의어
    aliases TEXT,                      -- JSON: {"ko": [...], "en": [...]}

    -- 설명
    description TEXT,
    examples TEXT,                     -- JSON: 예시 문항 ID 목록

    -- 통계
    usage_count INTEGER DEFAULT 0,
    first_used_year INTEGER,

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

-- ============================================
-- 4. taxonomy_relations: 용어 간 관계
-- ============================================
CREATE TABLE taxonomy_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_term_id INTEGER REFERENCES taxonomy(term_id),
    to_term_id INTEGER REFERENCES taxonomy(term_id),

    relation_type TEXT NOT NULL,       -- PARENT, CHILD, RELATED, SIMILAR,
                                       -- HAS_COMPONENT, SYNONYM, OPPOSITE
    strength REAL DEFAULT 1.0,         -- 관계 강도 (0-1)

    context TEXT,                      -- JSON: 맥락 정보

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(from_term_id, to_term_id, relation_type)
);

-- ============================================
-- 5. question_tags: 문항-용어 매핑 (다대다)
-- ============================================
CREATE TABLE question_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT REFERENCES questions(question_id),
    term_id INTEGER REFERENCES taxonomy(term_id),

    tag_type TEXT,                     -- concepts, aspects, subjects, themes
    confidence REAL,                   -- 태깅 신뢰도 (0-1)
    is_auto_tagged BOOLEAN,            -- 자동 태깅 여부

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(question_id, term_id, tag_type)
);

-- ============================================
-- 6. embeddings: 임베딩 벡터 저장
-- ============================================
CREATE TABLE embeddings (
    question_id TEXT PRIMARY KEY REFERENCES questions(question_id),
    embedding BLOB,                    -- 768차원 float32 벡터 (직렬화)
    model_name TEXT DEFAULT 'jhgan/ko-sroberta-multitask',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. scales: 측정 척도 정의
-- ============================================
CREATE TABLE scales (
    scale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scale_name TEXT UNIQUE NOT NULL,   -- 예: "조직몰입도", "리더십효과성"
    description TEXT,

    -- 척도 구성 요소 (온톨로지 관계로 정의)
    root_term_id INTEGER REFERENCES taxonomy(term_id),

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

-- ============================================
-- 8. scale_questions: 척도-문항 매핑
-- ============================================
CREATE TABLE scale_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scale_id INTEGER REFERENCES scales(scale_id),
    master_question_id TEXT REFERENCES master_questions(master_id),

    sub_scale TEXT,                    -- 하위 척도 (예: "정서적몰입")
    weight REAL DEFAULT 1.0,           -- 가중치

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.5 인덱스

```sql
-- ============================================
-- 운영 데이터 인덱스
-- ============================================
CREATE INDEX idx_companies_group ON companies(group_name);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_surveys_company ON surveys(company_id);
CREATE INDEX idx_surveys_year ON surveys(survey_year);
CREATE INDEX idx_surveys_type ON surveys(diagnosis_type);
CREATE INDEX idx_surveys_company_year ON surveys(company_id, survey_year);
CREATE INDEX idx_org_units_company ON org_units(company_id);
CREATE INDEX idx_org_units_parent ON org_units(parent_org_unit_id);
CREATE INDEX idx_survey_questions_survey ON survey_questions(survey_id);
CREATE INDEX idx_survey_questions_question ON survey_questions(question_id);

-- ============================================
-- 문항 데이터 인덱스
-- ============================================
CREATE INDEX idx_questions_diagnosis ON questions(diagnosis_type);
CREATE INDEX idx_questions_cluster ON questions(cluster_id);
CREATE INDEX idx_questions_master ON questions(master_question_id);
CREATE INDEX idx_questions_source_survey ON questions(source_survey_id);
CREATE INDEX idx_master_diagnosis ON master_questions(diagnosis_type);

-- ============================================
-- 온톨로지 인덱스
-- ============================================
CREATE INDEX idx_taxonomy_type ON taxonomy(term_type);
CREATE INDEX idx_taxonomy_term ON taxonomy(term);
CREATE INDEX idx_relations_from ON taxonomy_relations(from_term_id);
CREATE INDEX idx_relations_to ON taxonomy_relations(to_term_id);
CREATE INDEX idx_relations_type ON taxonomy_relations(relation_type);
CREATE INDEX idx_tags_question ON question_tags(question_id);
CREATE INDEX idx_tags_term ON question_tags(term_id);
CREATE INDEX idx_scale_questions_scale ON scale_questions(scale_id);
CREATE INDEX idx_scale_questions_master ON scale_questions(master_question_id);
```

### 3.3 구현 단계

#### Step 1: 기본 스키마 생성 및 데이터 마이그레이션 (2-3일)

```
작업 내용:
├── SQLite DB 파일 생성 (masterdb.sqlite)
├── 전체 테이블 스키마 생성
│
├── [운영 데이터 마이그레이션]
│   ├── Survey Meta Data 엑셀 → companies 테이블 (120개사)
│   ├── Survey 목록 시트 → surveys 테이블 (355개)
│   └── 조직 정보 추출 → org_units 테이블
│
├── [문항 데이터 마이그레이션]
│   ├── all_df_hybrid.pkl → questions 테이블 (7,343개)
│   ├── Master Questions → master_questions 테이블 (3,274개)
│   ├── 문항-설문 매핑 → survey_questions 테이블
│   └── 임베딩 벡터 → embeddings 테이블
│
└── 데이터 무결성 검증
```

**데이터 소스 매핑**:

| 대상 테이블 | 소스 | 예상 행 수 |
|------------|------|-----------|
| companies | Survey목록 시트에서 추출 | 120 |
| surveys | Survey목록 시트 | 355 |
| org_units | (초기에는 빈 테이블, 향후 확장) | 0 |
| questions | all_df_hybrid.pkl | 7,343 |
| master_questions | is_representative=True 필터 | 3,274 |
| survey_questions | No1~No6 컬럼 기반 매핑 | ~8,000+ |
| embeddings | all_embeddings_hybrid.npy | 7,343 |

**산출물**:
- `db/masterdb.sqlite` 파일
- 마이그레이션 스크립트 (`src/migration/*.py`)
- 검증 리포트

#### Step 2: Taxonomy 초기 구축 (2-3일)

```
작업 내용:
├── 현재 중분류/소분류에서 Taxonomy 용어 추출
├── 용어 타입 분류 (THEME, CONCEPT, ASPECT 등)
├── 기본 관계 정의 (PARENT-CHILD)
├── 동의어/유사어 그룹화
└── taxonomy, taxonomy_relations 테이블 구축
```

**Taxonomy 용어 추출 계획**:

| 소스 | 추출 대상 | 예상 용어 수 |
|------|----------|-------------|
| 중분류 8개 | THEME 용어 | ~15개 |
| 소분류 65개 | CONCEPT/ASPECT 용어 | ~80개 |
| 키워드 사전 | 추가 CONCEPT 용어 | ~50개 |
| **합계** | | **~150개** |

**관계 정의 예시**:
```
경영전략 (THEME)
├── PARENT → 비전 (CONCEPT)
├── PARENT → 전략 (CONCEPT)
└── PARENT → 목표 (CONCEPT)

비전 (CONCEPT)
├── HAS_COMPONENT → 인지 (ASPECT)
├── HAS_COMPONENT → 이해 (ASPECT)
├── HAS_COMPONENT → 공감 (ASPECT)
└── HAS_COMPONENT → 실천 (ASPECT)
```

#### Step 3: 자동 태깅 시스템 구현 (2-3일)

```
작업 내용:
├── 문항 → Taxonomy 용어 매핑 로직 구현
├── 키워드 기반 태깅 (1차)
├── 임베딩 유사도 기반 태깅 (2차)
├── 태깅 신뢰도 계산
└── question_tags 테이블 구축
```

**태깅 파이프라인**:
```
문항 텍스트
    ↓
[1차: 키워드 매칭]
  - taxonomy 용어와 직접 매칭
  - 동의어(aliases) 매칭
    ↓
[2차: 임베딩 유사도]
  - 문항 임베딩과 용어 임베딩 비교
  - 상위 k개 후보 선정
    ↓
[3차: 그래프 확장]
  - 부모/자식 관계로 태그 확장
    ↓
[신뢰도 계산]
  - 명시적 매칭 vs 추론 비율
    ↓
question_tags 저장
```

#### Step 4: 검증 및 반복 개선 (지속적)

```
Claude Code와 함께 검증:
├── 쿼리 테스트 (의미 기반 검색)
├── 태깅 품질 검토 (샘플링)
├── 관계 정합성 확인
├── 누락된 용어/관계 발견
└── 개선 사항 반영
```

**검증 시나리오**:
1. "리더십 관련 모든 문항 검색" → 관련 개념 자동 확장 확인
2. "비전 이해도 vs 비전 공감" → 다른 클러스터로 분리 확인
3. "조직몰입도 척도 구성" → HAS_COMPONENT 관계 활용 확인
4. "2023년 CJ 조직진단 문항" → 구조적 메타데이터 필터링 확인

---

## 4. 상세 구현 계획

### 4.1 파일 구조

```
c:\Project\MasterDB\
├── data\
│   └── Survey Meta Data_251224.xlsx   # 원본 데이터
├── results\
│   ├── Master_Questions.xlsx          # 대표 문항
│   └── 전체_문항_클러스터링_Hybrid.xlsx
├── src\
│   ├── all_category_clustering.py     # 기존: 클러스터링
│   ├── create_verification_excel.py   # 기존: 검증용 엑셀
│   ├── llm_classify_unclassified.py   # 기존: LLM 분류
│   │
│   ├── db\                            # [신규] DB 관련
│   │   ├── __init__.py
│   │   ├── schema.py                  # 스키마 정의
│   │   ├── connection.py              # DB 연결 관리
│   │   └── queries.py                 # 쿼리 함수
│   │
│   ├── migration\                     # [신규] 마이그레이션
│   │   ├── __init__.py
│   │   ├── migrate_questions.py       # 문항 마이그레이션
│   │   ├── migrate_embeddings.py      # 임베딩 마이그레이션
│   │   └── build_taxonomy.py          # Taxonomy 구축
│   │
│   ├── tagging\                       # [신규] 태깅 시스템
│   │   ├── __init__.py
│   │   ├── keyword_tagger.py          # 키워드 기반 태깅
│   │   ├── embedding_tagger.py        # 임베딩 기반 태깅
│   │   └── auto_tagger.py             # 통합 자동 태깅
│   │
│   └── search\                        # [신규] 검색 시스템
│       ├── __init__.py
│       ├── semantic_search.py         # 의미 기반 검색
│       └── taxonomy_navigator.py      # 온톨로지 탐색
│
├── db\
│   └── masterdb.sqlite                # [신규] SQLite DB
│
├── tests\                             # [신규] 테스트
│   ├── test_migration.py
│   ├── test_tagging.py
│   └── test_search.py
│
├── all_df_hybrid.pkl                  # 캐시: DataFrame
├── all_embeddings_hybrid.npy          # 캐시: 임베딩
├── CLAUDE.md
├── Survey_Question_Analysis.md
├── Taxonomy_and_Ontology.md
└── MasterDB_Implementation_Plan.md    # 본 문서
```

### 4.2 구현 우선순위

| 순위 | 작업 | 중요도 | 복잡도 | 예상 시간 |
|------|------|--------|--------|-----------|
| 1 | SQLite 스키마 생성 | 높음 | 낮음 | 2시간 |
| 2 | 문항 데이터 마이그레이션 | 높음 | 중간 | 4시간 |
| 3 | 임베딩 마이그레이션 | 중간 | 낮음 | 2시간 |
| 4 | Taxonomy 용어 추출 | 높음 | 중간 | 4시간 |
| 5 | Taxonomy 관계 정의 | 높음 | 높음 | 8시간 |
| 6 | 키워드 기반 태깅 | 중간 | 중간 | 4시간 |
| 7 | 임베딩 기반 태깅 | 중간 | 높음 | 6시간 |
| 8 | 검색 기능 구현 | 중간 | 중간 | 4시간 |
| 9 | 검증 및 반복 개선 | 높음 | 중간 | 지속적 |

### 4.3 검증 전략

#### 4.3.1 데이터 무결성 검증

```python
# 마이그레이션 후 검증 항목
assertions = [
    "questions 테이블 행 수 == 7,343",
    "master_questions 테이블 행 수 == 3,274",
    "embeddings 테이블 행 수 == 7,343",
    "모든 question_id가 유일함",
    "모든 master_question_id가 questions에 존재함",
    "임베딩 차원 == 768",
]
```

#### 4.3.2 Taxonomy 검증

```python
# Taxonomy 구축 후 검증 항목
assertions = [
    "모든 CONCEPT은 최소 1개 THEME에 연결됨",
    "순환 참조 없음 (PARENT 관계)",
    "동의어 그룹 내 중복 없음",
    "모든 용어가 최소 1개 문항에 사용됨",
]
```

#### 4.3.3 태깅 품질 검증

```python
# 샘플 기반 수동 검증
sample_size = 100
metrics = {
    "precision": "태그가 문항에 적합한 비율",
    "recall": "누락된 태그 비율",
    "consistency": "유사 문항 간 태그 일관성",
}
```

---

## 5. Claude Code 협업 계획

### 5.1 협업 방식

```
┌─────────────────────────────────────────────────────────┐
│                 Claude Code 협업 루프                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [구현] → [검증 요청] → [Claude 분석] → [피드백]        │
│      ↑                                          │       │
│      └──────────── [개선] ←─────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 검증 요청 유형

| 유형 | 내용 | 예시 |
|------|------|------|
| **쿼리 테스트** | 검색 결과 검토 | "비전 관련 문항 검색 결과가 적절한가?" |
| **태깅 검토** | 자동 태깅 품질 | "이 문항에 [리더십, 코칭] 태그가 맞는가?" |
| **관계 검증** | 온톨로지 관계 | "비전 → 인지/이해/공감 관계가 완전한가?" |
| **누락 발견** | 빠진 용어/관계 | "권한위임 관련 용어가 누락되지 않았나?" |
| **일관성 검사** | 전체 정합성 | "OD와 LD의 리더십 분류가 일관적인가?" |

### 5.3 반복 개선 사이클

```
Week 1: 기본 구축
├── Day 1-2: 스키마 + 마이그레이션
├── Day 3-4: Taxonomy 초기 구축
└── Day 5: 1차 검증 및 피드백

Week 2: 태깅 + 검색
├── Day 1-2: 자동 태깅 구현
├── Day 3-4: 검색 기능 구현
└── Day 5: 2차 검증 및 피드백

Week 3+: 반복 개선
├── 태깅 품질 개선
├── 누락 용어/관계 추가
├── 검색 정확도 향상
└── 사용 시나리오 검증
```

---

## 6. 예상 산출물

### Phase 1 완료 시 산출물

| 산출물 | 설명 |
|--------|------|
| `db/masterdb.sqlite` | SQLite 기반 Master DB |
| `src/db/*.py` | DB 스키마 및 쿼리 모듈 |
| `src/migration/*.py` | 마이그레이션 스크립트 |
| `src/tagging/*.py` | 자동 태깅 시스템 |
| `src/search/*.py` | 의미 기반 검색 |
| `tests/*.py` | 테스트 코드 |
| 검증 리포트 | 품질 검증 결과 문서 |

### Phase 2 이후 계획 (PostgreSQL 전환)

```
Phase 2: PostgreSQL 전환
├── SQLite → PostgreSQL 마이그레이션
├── JSONB 네이티브 지원 활용
├── 전문 검색 (Full-text Search) 구현
└── 성능 최적화 (인덱싱, 파티셔닝)

Phase 3: 고급 기능
├── 자동 학습 기반 태깅 개선
├── 척도 자동 구성
├── 벤치마킹 지원
└── API 서버 구축
```

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 방안 |
|--------|------|------|-----------|
| Taxonomy 설계 오류 | 높음 | 중간 | 반복 검증, 소규모 시작 |
| 자동 태깅 정확도 낮음 | 중간 | 중간 | 수동 보정 프로세스 |
| SQLite 성능 한계 | 낮음 | 낮음 | Phase 2에서 PostgreSQL 전환 |
| 임베딩 저장 비효율 | 낮음 | 중간 | BLOB 직렬화 최적화 |

---

## 8. 시작점

### 다음 작업: Step 1 - 기본 스키마 생성

```bash
# 첫 번째 작업
1. src/db/schema.py 생성 (SQLite 스키마 정의)
2. src/db/connection.py 생성 (DB 연결 관리)
3. masterdb.sqlite 초기화
4. 마이그레이션 스크립트 작성 시작
```

---

*작성일: 2024-12-24*
*다음 업데이트: Step 1 완료 후*
