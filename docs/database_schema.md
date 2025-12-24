# MasterDB Database Schema

**버전**: 1.1
**데이터베이스**: SQLite (Phase 1) → PostgreSQL (Phase 2)
**최종 수정**: 2024-12-24

> **설계 참조**: [DATABASE_DESIGN.md](../DATABASE_DESIGN.md), [DB_테이블명세서.xlsx](../DB_테이블명세서.xlsx)

---

## 1. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────┐      ┌─────────────┐      ┌──────────────────┐        │
│  │  companies  │─────<│  surveys    │─────<│ survey_questions │        │
│  │  (고객사)   │ 1:N  │  (설문)     │ 1:N  │  (설문-문항)     │        │
│  └─────────────┘      └──────┬──────┘      └────────┬─────────┘        │
│         │                    │                      │                   │
│         │ 1:N                │                      │ N:1               │
│         ▼                    │                      ▼                   │
│  ┌─────────────┐             │              ┌─────────────┐            │
│  │  org_units  │             │              │  questions  │            │
│  │  (조직단위) │             │              │  (문항)     │            │
│  └──────┬──────┘             │              └──────┬──────┘            │
│         │ 1:N                │                     │                    │
│         ▼                    │                     │ 1:1                │
│  ┌──────────────┐            │                     ▼                    │
│  │ org_unit_    │            │              ┌─────────────┐            │
│  │ surveys      │────────────┘              │   master_   │            │
│  └──────────────┘                           │  questions  │            │
│                                             └──────┬──────┘            │
│                                                    │                    │
│  ┌─────────────┐      ┌──────────────┐            │                    │
│  │  taxonomy   │─────<│question_tags │>───────────┘                    │
│  │  (온톨로지) │ 1:N  │  (태깅)      │ N:1                             │
│  └──────┬──────┘      └──────────────┘                                 │
│         │ 1:N                                                           │
│         ▼                                                               │
│  ┌──────────────┐     ┌─────────────┐      ┌──────────────┐            │
│  │  taxonomy_   │     │   scales    │─────<│   scale_     │            │
│  │  relations   │     │   (척도)    │ 1:N  │  questions   │            │
│  └──────────────┘     └─────────────┘      └──────────────┘            │
│                                                                         │
│  ┌─────────────┐                                                        │
│  │ embeddings  │ (questions 1:1)                                        │
│  │ (임베딩)    │                                                        │
│  └─────────────┘                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 테이블 그룹 개요

| 그룹 | 테이블 | 설명 |
|------|--------|------|
| **운영 데이터** | companies, surveys, org_units, org_unit_surveys, survey_questions | 고객사, 설문, 조직 정보 |
| **문항 데이터** | questions, master_questions, embeddings | 문항 및 임베딩 |
| **온톨로지** | taxonomy, taxonomy_relations, question_tags | 분류 체계 및 태깅 |
| **척도** | scales, scale_questions | 측정 척도 정의 |

---

## 2.1 ID 체계 (DATABASE_DESIGN.md 참조)

| 테이블 | ID 형식 | 예시 |
|--------|---------|------|
| companies | `{회사코드}` | `CJG`, `SKH`, `PARADISE` |
| surveys | `{회사}-{연도}-{유형}` 또는 `IG{YYMMNN}` | `PARADISE-2025-OD`, `IG200601001` |
| org_units | `{회사}_{조직경로}` | `CJG_HQ_HR` |
| questions | `Q_{5자리}` | `Q_00001` ~ `Q_07343` |
| master_questions | `{대분류}_{4자리}` | `OD_0001`, `LD_0697` |

---

## 3. 운영 데이터 테이블 (Operational Data)

### 3.1 companies (고객사)

고객사 정보를 저장합니다. (120개사)

```sql
CREATE TABLE companies (
    company_id TEXT PRIMARY KEY,           -- 회사 코드 (예: CJG, SKG, DGB)
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
```

**예시 데이터**:
| company_id | company_name | group_name | industry |
|------------|--------------|------------|----------|
| CJG | CJ그룹 | CJ | 식품/유통 |
| SKH | SK하이닉스 | SK | 반도체 |
| DGB | DGB대구은행 | DGB금융 | 금융 |

---

### 3.2 surveys (설문 프로젝트)

설문 프로젝트 정보를 저장합니다. (355개)

```sql
CREATE TABLE surveys (
    survey_id TEXT PRIMARY KEY,            -- 프로젝트 코드 (예: IG200601)
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
```

**진단 유형 (diagnosis_type)**:
| 코드 | 설명 | 비고 |
|------|------|------|
| OD | 조직진단 (Organization Diagnosis) | 171개 |
| LD | 리더십진단 (Leadership Diagnosis) | 126개 |
| MA | 다면평가 (Multi-source Assessment) | 15개 |
| DD | 사외이사평가 (Director Diagnosis) | 16개 |
| ES | 직원만족도 (Employee Satisfaction) | 기타 |

---

### 3.3 org_units (조직 단위)

회사의 조직 구조를 계층적으로 저장합니다.

```sql
CREATE TABLE org_units (
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
```

**조직 레벨 예시**:
```
Level 1: 본부/사업부
Level 2: 실/센터
Level 3: 팀
Level 4: 파트/셀
```

---

### 3.4 org_unit_surveys (조직-설문 매핑)

특정 설문에 참여한 조직 단위와 응답 정보를 저장합니다.

```sql
CREATE TABLE org_unit_surveys (
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
```

---

### 3.5 survey_questions (설문-문항 매핑)

각 설문에 포함된 문항과 순서를 저장합니다.

```sql
CREATE TABLE survey_questions (
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
```

**scale_labels 예시** (JSON):
```json
["전혀 그렇지 않다", "그렇지 않다", "보통이다", "그렇다", "매우 그렇다"]
```

---

## 4. 문항 데이터 테이블 (Question Data)

### 4.1 questions (문항)

전체 고유 문항을 저장합니다. (7,343개)

```sql
CREATE TABLE questions (
    question_id TEXT PRIMARY KEY,          -- 문항 ID (예: Q_00001)
    question_text TEXT NOT NULL,           -- 문항 텍스트

    -- 구조적 메타데이터
    diagnosis_type TEXT NOT NULL,          -- OD, LD, MA, DD
    source_survey_id TEXT REFERENCES surveys(survey_id),  -- 최초 등장 설문
    source_year INTEGER,                   -- 최초 등장 연도
    reuse_count INTEGER DEFAULT 1,         -- 재사용 횟수

    -- 문항 유형 (DATABASE_DESIGN.md 참조)
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
```

**question_type 유형** (DATABASE_DESIGN.md 참조):
| 유형 | 설명 | 비고 |
|------|------|------|
| LIKERT | 5점/7점 척도 | 기본값 |
| CHOICE_SINGLE | 단일 선택 | 객관식 |
| CHOICE_MULTI | 다중 선택 | max_choices 활용 |
| ESSAY | 주관식/서술형 | 텍스트 응답 |

**choices 예시** (JSON):
```json
{
    "1": "근무 환경에 대한 만족",
    "2": "조직문화 및 분위기",
    "3": "상사의 리더십",
    "4": "충분한 복리후생 지원"
}
```

---

### 4.2 master_questions (대표 문항)

클러스터 대표 문항을 저장합니다. (3,274개)

```sql
CREATE TABLE master_questions (
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
```

**master_id 형식**:
```
{대분류}_{클러스터번호 4자리}

예시:
- OD_0001 ~ OD_2199 (2,199개)
- LD_0001 ~ LD_0697 (697개)
- MA_0001 ~ MA_0275 (275개)
- DD_0001 ~ DD_0103 (103개)
```

---

### 4.3 embeddings (임베딩 벡터)

문항의 KoSBERT 임베딩 벡터를 저장합니다.

```sql
CREATE TABLE embeddings (
    question_id TEXT PRIMARY KEY REFERENCES questions(question_id),
    embedding BLOB NOT NULL,               -- 768차원 float32 벡터 (직렬화)
    model_name TEXT DEFAULT 'jhgan/ko-sroberta-multitask',

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**저장 형식**:
- Python: `numpy.ndarray.tobytes()` 로 직렬화
- 복원: `numpy.frombuffer(blob, dtype=np.float32)`
- 크기: 768 × 4 bytes = 3,072 bytes per row

---

## 5. 온톨로지 테이블 (Ontology)

### 5.1 taxonomy (분류 용어)

온톨로지 용어(개념)를 저장합니다. (~150개)

```sql
CREATE TABLE taxonomy (
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
```

**term_type 정의**:
| 타입 | 설명 | 예시 |
|------|------|------|
| THEME | 대주제 | 경영전략, 조직문화, 리더십, 인사제도 |
| CONCEPT | 핵심 개념 | 비전, 소통, 협력, 권한위임, 코칭 |
| ASPECT | 측정 측면 | 이해도, 만족도, 중요도, 실천도 |
| SUBJECT | 평가 대상 | 조직, 팀, 리더, 개인, 동료 |
| METHOD | 평가 방법 | 자기평가, 타인평가, 상향평가 |

---

### 5.2 taxonomy_relations (용어 관계)

용어 간의 관계를 저장합니다.

```sql
CREATE TABLE taxonomy_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_term_id INTEGER REFERENCES taxonomy(term_id),
    to_term_id INTEGER REFERENCES taxonomy(term_id),

    relation_type TEXT NOT NULL,           -- 관계 유형
    strength REAL DEFAULT 1.0,             -- 관계 강도 (0.0 ~ 1.0)

    -- 맥락 정보
    context TEXT,                          -- JSON: 특정 맥락에서만 유효한 관계

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(from_term_id, to_term_id, relation_type)
);
```

**relation_type 정의**:
| 관계 | 설명 | 예시 |
|------|------|------|
| PARENT | 상위 개념 | 경영전략 → 비전 |
| CHILD | 하위 개념 | 비전 → 경영전략 |
| HAS_COMPONENT | 구성 요소 | 몰입도 → 자긍심, 소속감 |
| RELATED | 관련 개념 | 코칭 ↔ 피드백 |
| SIMILAR | 유사 개념 | 소통 ↔ 커뮤니케이션 |
| SYNONYM | 동의어 | 워라밸 = 일생활균형 |
| OPPOSITE | 반대 개념 | 신뢰 ↔ 불신 |

---

### 5.3 question_tags (문항-태그 매핑)

문항과 온톨로지 용어의 다대다 관계를 저장합니다.

```sql
CREATE TABLE question_tags (
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
```

**tag_type과 term_type 매핑**:
| tag_type | term_type |
|----------|-----------|
| themes | THEME |
| concepts | CONCEPT |
| aspects | ASPECT |
| subjects | SUBJECT |

---

## 6. 척도 테이블 (Scales)

### 6.1 scales (측정 척도)

측정 척도(Construct)를 정의합니다.

```sql
CREATE TABLE scales (
    scale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scale_name TEXT UNIQUE NOT NULL,       -- 척도명 (예: "조직몰입도", "리더십효과성")
    description TEXT,                      -- 척도 설명

    -- 온톨로지 연결
    root_term_id INTEGER REFERENCES taxonomy(term_id),  -- 척도의 루트 개념

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
```

**척도 예시**:
```
조직몰입도 (root_term: "몰입도")
├── 정서적몰입: 자긍심, 소속감, 정서적애착
├── 지속적몰입: 이직비용, 대안부족
└── 규범적몰입: 의무감, 충성도
```

---

### 6.2 scale_questions (척도-문항 매핑)

척도를 구성하는 문항을 정의합니다.

```sql
CREATE TABLE scale_questions (
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
```

---

## 7. 인덱스

### 7.1 운영 데이터 인덱스

```sql
-- companies
CREATE INDEX idx_companies_group ON companies(group_name);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_size ON companies(company_size);

-- surveys
CREATE INDEX idx_surveys_company ON surveys(company_id);
CREATE INDEX idx_surveys_year ON surveys(survey_year);
CREATE INDEX idx_surveys_type ON surveys(diagnosis_type);
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_surveys_company_year ON surveys(company_id, survey_year);

-- org_units
CREATE INDEX idx_org_units_company ON org_units(company_id);
CREATE INDEX idx_org_units_parent ON org_units(parent_org_unit_id);
CREATE INDEX idx_org_units_level ON org_units(org_level);

-- org_unit_surveys
CREATE INDEX idx_org_unit_surveys_survey ON org_unit_surveys(survey_id);
CREATE INDEX idx_org_unit_surveys_org ON org_unit_surveys(org_unit_id);

-- survey_questions
CREATE INDEX idx_survey_questions_survey ON survey_questions(survey_id);
CREATE INDEX idx_survey_questions_question ON survey_questions(question_id);
CREATE INDEX idx_survey_questions_section ON survey_questions(section_name);
```

### 7.2 문항 데이터 인덱스

```sql
-- questions
CREATE INDEX idx_questions_diagnosis ON questions(diagnosis_type);
CREATE INDEX idx_questions_cluster ON questions(cluster_id);
CREATE INDEX idx_questions_master ON questions(master_question_id);
CREATE INDEX idx_questions_source_survey ON questions(source_survey_id);
CREATE INDEX idx_questions_representative ON questions(is_representative);

-- master_questions
CREATE INDEX idx_master_diagnosis ON master_questions(diagnosis_type);
CREATE INDEX idx_master_cluster_size ON master_questions(cluster_size);
```

### 7.3 온톨로지 인덱스

```sql
-- taxonomy
CREATE INDEX idx_taxonomy_type ON taxonomy(term_type);
CREATE INDEX idx_taxonomy_term ON taxonomy(term);
CREATE INDEX idx_taxonomy_usage ON taxonomy(usage_count DESC);

-- taxonomy_relations
CREATE INDEX idx_relations_from ON taxonomy_relations(from_term_id);
CREATE INDEX idx_relations_to ON taxonomy_relations(to_term_id);
CREATE INDEX idx_relations_type ON taxonomy_relations(relation_type);

-- question_tags
CREATE INDEX idx_tags_question ON question_tags(question_id);
CREATE INDEX idx_tags_term ON question_tags(term_id);
CREATE INDEX idx_tags_type ON question_tags(tag_type);
CREATE INDEX idx_tags_confidence ON question_tags(confidence DESC);

-- scales
CREATE INDEX idx_scales_root ON scales(root_term_id);

-- scale_questions
CREATE INDEX idx_scale_questions_scale ON scale_questions(scale_id);
CREATE INDEX idx_scale_questions_master ON scale_questions(master_question_id);
CREATE INDEX idx_scale_questions_subscale ON scale_questions(sub_scale);
```

---

## 8. 데이터 통계 요약

| 테이블 | 예상 행 수 | 비고 |
|--------|-----------|------|
| companies | 120 | 고객사 |
| surveys | 355 | 설문 프로젝트 (2006-2025) |
| org_units | 0 (확장 예정) | 조직 구조 |
| org_unit_surveys | 0 (확장 예정) | 조직-설문 매핑 |
| survey_questions | ~8,000+ | 설문-문항 매핑 |
| questions | 7,343 | 고유 문항 |
| master_questions | 3,274 | 대표 문항 |
| embeddings | 7,343 | 임베딩 벡터 |
| taxonomy | ~150 | 온톨로지 용어 |
| taxonomy_relations | ~300 | 용어 관계 |
| question_tags | ~15,000 | 문항-태그 매핑 |
| scales | ~20 | 측정 척도 |
| scale_questions | ~200 | 척도-문항 매핑 |

---

## 9. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2024-12-24 | 초기 스키마 설계 |
| 1.1 | 2024-12-24 | DATABASE_DESIGN.md 패턴 반영 (ID 체계, question_type, choices 등) |

---

*참조 문서: DATABASE_DESIGN.md, DB_테이블명세서.xlsx, meta_data.xlsx*
