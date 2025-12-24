
**버전**: 1.0
**작성일**: 2025-11-19
**작성자**: AI Lab
**상태**: Draft

---

## 1. 개요

### 1.1 프로젝트 목적

Paradise 그룹의 조직진단 및 리더십진단 설문 데이터를 체계적으로 관리하고, Taxonomy 기반의 의미론적 분류 체계를 적용하여 다양한 분석과 인사이트 도출이 가능한 데이터베이스를 구축한다.

### 1.2 목표

1. **1차 목표**: Paradise 그룹 3개년(2023-2025) 데이터 DB화 및 Claude Code 조회 UI 구성
2. **2차 목표**: 연간 20여개 설문, 10년 이상 데이터를 포함하는 Master Table 구축
3. **최종 목표**: Taxonomy/Ontology 기반 의미론적 검색 및 자동 태깅 시스템 구현

### 1.3 설계 원칙

- **확장성**: 대용량 데이터(3천만+ 레코드) 처리 가능
- **일관성**: 통일된 ID 체계 및 네이밍 규칙
- **호환성**: SQLite(개발) → PostgreSQL(운영) 마이그레이션 용이
- **성능**: Long Format 채택, 적절한 인덱싱 및 파티셔닝

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│              (Claude Code UI / Web Interface)            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Application Layer                     │
│         (Query Engine / Analytics / Reporting)           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                      Data Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Master    │  │   Survey    │  │  Response   │      │
│  │   Tables    │  │  Questions  │  │    Data     │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                          │
│  SQLite (Dev) ──────────────────▶ PostgreSQL (Prod)     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 데이터베이스 선택

| 환경 | DBMS | 용도 | 데이터량 |
|------|------|------|----------|
| 개발/프로토타입 | SQLite | 로컬 개발, 빠른 테스트 | ~120만 레코드 |
| 운영/확장 | PostgreSQL | 대용량 처리, 동시 접속 | 3천만+ 레코드 |

### 2.3 데이터 흐름

```
Excel Files ──┐
              │
Survey.xlsx ──┼──▶ ETL Process ──▶ Database ──▶ Query/Analysis
              │
RawData.xlsx ─┘
```

---

## 3. 데이터베이스 스키마

### 3.1 테이블 관계도 (ERD)

```
┌──────────────────┐
│   company_info   │◀─────────────────────────────┐
│   (그룹/계열사)   │                              │
└────────┬─────────┘                              │
         │1                                       │
         │                                        │
         ▼n                                       │
┌──────────────────┐     ┌──────────────────┐     │
│  org_hierarchy   │     │  survey_master   │     │
│  (연도별 조직도)  │     │   (설문 정의)     │     │
└────────┬─────────┘     └────────┬─────────┘     │
         │1                       │1              │
         │                        │               │
         │                        ▼n              │
         │              ┌──────────────────┐      │
         │              │  questions_od    │      │
         │              │  (조직진단 문항)  │      │
         │              ├──────────────────┤      │
         │              │  questions_ld    │      │
         │              │  (리더십진단 문항) │      │
         │              └────────┬─────────┘      │
         │                       │1               │
         ▼n                      │                │
┌──────────────────┐             │                │
│   respondents    │             │                │
│    (응답자)       │             │                │
└────────┬─────────┘             │                │
         │1                      │                │
         │                       ▼n               │
         │              ┌──────────────────┐      │
         └─────────────▶│  responses_od    │──────┤
                   n    │  (조직진단 응답)   │      │
                        ├──────────────────┤      │
                        │  responses_ld    │──────┘
                        │  (리더십진단 응답) │
                        └──────────────────┘
```

### 3.2 테이블 목록

| 테이블명 | 설명 | 예상 레코드 수 |
|----------|------|----------------|
| `company_info` | 그룹 및 계열사 정보 | ~15 |
| `org_hierarchy` | 연도별 조직 구조 | ~1,000 |
| `survey_master` | 설문 정의 (연도/회사/유형별) | ~200+ |
| `questions_od` | 조직진단 문항 | ~1,000+ |
| `questions_ld` | 리더십진단 문항 | ~800+ |
| `respondents` | 응답자 정보 | ~100,000+ |
| `responses_od` | 조직진단 응답 (Long Format) | ~15,000,000+ |
| `responses_ld` | 리더십진단 응답 (Long Format) | ~10,000,000+ |
| `question_mapping` | 연도간 문항 매핑 | ~500+ |
| `taxonomy_terms` | 분류 용어 사전 | ~500+ |
| `taxonomy_relations` | 용어간 관계 | ~1,000+ |

### 3.3 ID 체계

#### 명명 규칙

| 테이블 | ID 형식 | 예시 |
|--------|---------|------|
| company_info | `{회사코드}` | `PARADISE`, `PARADISE_HTL` |
| org_hierarchy | `{회사}-{연도}-ORG-{4자리}` | `PARADISE-2025-ORG-0001` |
| survey_master | `{회사}-{연도}-{유형}` | `PARADISE-2025-OD` |
| questions_od | `{회사}-{연도}-OD-{3자리}` | `PARADISE-2025-OD-001` |
| questions_ld | `{회사}-{연도}-LD-{3자리}` | `PARADISE-2025-LD-001` |
| respondents | `{회사}-{연도}-{5자리}` | `PARADISE-2025-00001` |
| responses_* | `{자동증가}` | `1`, `2`, `3`... |

#### 규칙

1. **문항번호는 3자리 고정**: `001`, `002`, ... `999`
2. **응답자번호는 5자리 고정**: `00001`, ... `99999`
3. **연도는 4자리**: `2023`, `2024`, `2025`
4. **진단유형 코드**: `OD`(조직진단), `LD`(리더십진단)

### 3.4 데이터 타입 규칙

| 용도 | SQLite | PostgreSQL | 비고 |
|------|--------|------------|------|
| Primary Key (문자) | VARCHAR(50) | VARCHAR(50) | |
| Primary Key (숫자) | INTEGER AUTOINCREMENT | BIGSERIAL | |
| 텍스트 (짧은) | VARCHAR(n) | VARCHAR(n) | |
| 텍스트 (긴) | TEXT | TEXT | |
| 숫자 (정수) | INT | INT | |
| 숫자 (실수) | REAL | REAL | |
| 불리언 | BOOLEAN | BOOLEAN | |
| 날짜/시간 | TIMESTAMP | TIMESTAMP | |
| JSON | JSON | JSONB | PostgreSQL은 JSONB 권장 |

---

## 4. 테이블 상세 명세

### 4.1 company_info (회사 정보)

그룹사 및 계열사 기본 정보를 관리한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| company_id | VARCHAR(20) | PK | 회사 코드 |
| company_name | TEXT | NOT NULL | 회사명 (한글) |
| company_name_en | TEXT | | 회사명 (영문) |
| parent_company_id | VARCHAR(20) | FK | 상위 회사 (그룹사) |
| company_type | VARCHAR(20) | | GROUP, AFFILIATE |
| industry | TEXT | | 업종 |
| established_date | DATE | | 설립일 |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.2 org_hierarchy (조직도)

연도별 조직 구조를 관리한다. 매년 조직 개편을 반영한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| org_id | VARCHAR(50) | PK | 조직 ID |
| company_id | VARCHAR(20) | FK, NOT NULL | 회사 코드 |
| year | INT | NOT NULL | 기준 연도 |
| org_code | VARCHAR(50) | | 내부 조직코드 (연도 무관) |
| org_name | TEXT | NOT NULL | 조직명 |
| org_name_short | TEXT | | 조직 약칭 |
| org_level | INT | NOT NULL | 조직 레벨 (1~6) |
| parent_org_id | VARCHAR(50) | FK | 상위 조직 |
| org_path | TEXT | | 전체 경로 |
| org_type | VARCHAR(20) | | HQ, DIVISION, DEPT, TEAM |
| headcount | INT | | 인원수 |
| sort_order | INT | | 정렬 순서 |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.3 survey_master (설문 정의)

설문 단위(연도/회사/진단유형별)를 정의한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| survey_id | VARCHAR(50) | PK | 설문 ID |
| company_id | VARCHAR(20) | FK, NOT NULL | 회사 코드 |
| year | INT | NOT NULL | 설문 연도 |
| diagnosis_type | VARCHAR(10) | NOT NULL | OD, LD |
| survey_name | TEXT | | 설문명 |
| survey_description | TEXT | | 설문 설명 |
| survey_period_start | DATE | | 설문 시작일 |
| survey_period_end | DATE | | 설문 종료일 |
| total_questions | INT | | 총 문항수 |
| total_responses | INT | | 총 응답자수 |
| scale_type | VARCHAR(20) | DEFAULT 'LIKERT_5' | 척도 유형 |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.4 questions_od (조직진단 문항)

조직진단 설문 문항을 관리한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| question_id | VARCHAR(50) | PK | 문항 ID |
| survey_id | VARCHAR(50) | FK, NOT NULL | 설문 ID |
| question_no | VARCHAR(10) | NOT NULL | 문항 번호 (001, 002...) |
| question_text | TEXT | NOT NULL | 문항 내용 |
| category_1 | TEXT | | 대분류 |
| category_2 | TEXT | | 중분류 |
| category_3 | TEXT | | 소분류 |
| question_type | VARCHAR(20) | DEFAULT 'LIKERT' | 문항 유형 (LIKERT, CHOICE_SINGLE, CHOICE_MULTI, ESSAY) |
| scale_min | INT | DEFAULT 1 | 최소 척도값 |
| scale_max | INT | DEFAULT 5 | 최대 척도값 |
| choices | JSON | | 선택지 목록 (객관식용) |
| max_choices | INT | | 최대 선택 가능 수 (CHOICE_MULTI용) |
| is_required | BOOLEAN | DEFAULT TRUE | 필수 여부 |
| is_reverse | BOOLEAN | DEFAULT FALSE | 역문항 여부 |
| tags | JSON | | 의미론적 태그 (Taxonomy) |
| master_question_id | VARCHAR(50) | | 동일문항 그룹 ID |
| sort_order | INT | | 정렬 순서 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

**question_type 유형:**
- `LIKERT`: 5점/7점 척도 (기본)
- `CHOICE_SINGLE`: 단일 선택
- `CHOICE_MULTI`: 다중 선택 (max_choices 지정)
- `ESSAY`: 주관식

**choices 구조 예시 (다중 선택):**
```json
{
    "1": "근무 환경에 대한 만족",
    "2": "조직문화 및 분위기",
    "3": "상사의 리더십",
    "4": "충분한 복리후생 지원",
    "5": "다양한 업무 경험",
    "6": "교육 프로그램",
    "7": "적절한 권한위임",
    "8": "성과, 능력에 따른 평가",
    "9": "높은 금전적 보상 수준",
    "10": "일과 개인생활의 조화",
    "11": "회사의 성장 가능성",
    "12": "경력 개발"
}
```

**tags 구조 예시:**
```json
{
    "themes": ["조직문화"],
    "concepts": ["비전", "이해도"],
    "aspects": ["인지", "공감"],
    "subjects": ["조직"],
    "methods": ["자기평가"]
}
```

### 4.5 questions_ld (리더십진단 문항)

리더십진단 설문 문항을 관리한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| question_id | VARCHAR(50) | PK | 문항 ID |
| survey_id | VARCHAR(50) | FK, NOT NULL | 설문 ID |
| question_no | VARCHAR(10) | NOT NULL | 문항 번호 |
| question_text | TEXT | NOT NULL | 문항 내용 |
| category_1 | TEXT | | 대분류 |
| category_2 | TEXT | | 중분류 |
| category_3 | TEXT | | 소분류 |
| keyword | TEXT | | 리더십 키워드 |
| question_type | VARCHAR(20) | DEFAULT 'LIKERT' | 문항 유형 (LIKERT, CHOICE_SINGLE, CHOICE_MULTI, ESSAY) |
| scale_min | INT | DEFAULT 1 | 최소 척도값 |
| scale_max | INT | DEFAULT 5 | 최대 척도값 |
| choices | JSON | | 선택지 목록 (객관식용) |
| max_choices | INT | | 최대 선택 가능 수 |
| is_required | BOOLEAN | DEFAULT TRUE | 필수 여부 |
| tags | JSON | | 의미론적 태그 |
| master_question_id | VARCHAR(50) | | 동일문항 그룹 ID |
| sort_order | INT | | 정렬 순서 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.6 respondents (응답자)

설문 응답자 정보를 관리한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| respondent_id | VARCHAR(50) | PK | 응답자 ID |
| company_id | VARCHAR(20) | FK, NOT NULL | 회사 코드 |
| year | INT | NOT NULL | 응답 연도 |
| name | TEXT | | 이름 |
| email | TEXT | | 이메일 |
| org_id | VARCHAR(50) | FK | 소속 조직 |
| org_level1 | TEXT | | 조직 레벨1 |
| org_level2 | TEXT | | 조직 레벨2 |
| org_level3 | TEXT | | 조직 레벨3 |
| rank | TEXT | | 직급 |
| position | TEXT | | 직책 |
| is_executive | BOOLEAN | DEFAULT FALSE | 임원 여부 |
| target_type | TEXT | | SELF, SUBORDINATE (리더십용) |
| target_leader_id | VARCHAR(50) | | 평가 대상 리더 |
| completed_at | TIMESTAMP | | 응답 완료 시간 |
| is_valid | BOOLEAN | DEFAULT TRUE | 유효 응답 여부 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.7 responses_od (조직진단 응답)

조직진단 응답 데이터를 Long Format으로 저장한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| response_id | INTEGER | PK, AUTO | 응답 ID |
| respondent_id | VARCHAR(50) | FK, NOT NULL | 응답자 ID |
| question_id | VARCHAR(50) | FK, NOT NULL | 문항 ID |
| survey_id | VARCHAR(50) | FK, NOT NULL | 설문 ID |
| response_value | REAL | | 응답값 (1~5) |
| response_text | TEXT | | 주관식 응답 |
| company_id | VARCHAR(20) | | 회사 (비정규화) |
| year | INT | | 연도 (비정규화) |

### 4.8 responses_ld (리더십진단 응답)

리더십진단 응답 데이터를 Long Format으로 저장한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| response_id | INTEGER | PK, AUTO | 응답 ID |
| respondent_id | VARCHAR(50) | FK, NOT NULL | 응답자 ID |
| question_id | VARCHAR(50) | FK, NOT NULL | 문항 ID |
| survey_id | VARCHAR(50) | FK, NOT NULL | 설문 ID |
| response_value | REAL | | 응답값 |
| response_text | TEXT | | 주관식 응답 |
| company_id | VARCHAR(20) | | 회사 (비정규화) |
| year | INT | | 연도 (비정규화) |

### 4.9 question_mapping (문항 매핑)

연도간 동일/유사 문항을 매핑한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| mapping_id | INTEGER | PK, AUTO | 매핑 ID |
| year_from | INT | NOT NULL | 기준 연도 |
| year_to | INT | NOT NULL | 대상 연도 |
| question_id_from | VARCHAR(50) | FK | 기준 문항 |
| question_id_to | VARCHAR(50) | FK | 대상 문항 |
| mapping_type | VARCHAR(20) | | EXACT, SIMILAR, NEW, REMOVED |
| similarity_score | REAL | | 유사도 점수 (0~1) |
| notes | TEXT | | 비고 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.10 taxonomy_terms (분류 용어)

Taxonomy 분류 체계의 용어 사전이다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| term_id | INTEGER | PK, AUTO | 용어 ID |
| term | VARCHAR(100) | UNIQUE, NOT NULL | 용어 |
| term_type | VARCHAR(20) | NOT NULL | THEME, CONCEPT, ASPECT, SUBJECT, METHOD |
| aliases | JSON | | 동의어/별칭 |
| description | TEXT | | 설명 |
| parent_terms | JSON | | 상위 개념 |
| related_terms | JSON | | 관련 개념 |
| usage_count | INT | DEFAULT 0 | 사용 빈도 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

### 4.11 taxonomy_relations (용어 관계)

용어간 관계를 정의한다.

| 컬럼명 | 타입 | NULL | 설명 |
|--------|------|------|------|
| relation_id | INTEGER | PK, AUTO | 관계 ID |
| from_term | VARCHAR(100) | FK, NOT NULL | 출발 용어 |
| to_term | VARCHAR(100) | FK, NOT NULL | 도착 용어 |
| relation_type | VARCHAR(20) | NOT NULL | PARENT, CHILD, RELATED, SYNONYM, HAS_COMPONENT |
| strength | REAL | DEFAULT 1.0 | 관계 강도 (0~1) |
| context | JSON | | 관계 맥락 |
| created_at | TIMESTAMP | DEFAULT NOW | 생성일시 |

---

## 5. 인덱스 전략

### 5.1 필수 인덱스

```sql
-- org_hierarchy
CREATE INDEX idx_org_company_year ON org_hierarchy(company_id, year);
CREATE INDEX idx_org_parent ON org_hierarchy(parent_org_id);

-- survey_master
CREATE INDEX idx_survey_company ON survey_master(company_id);
CREATE INDEX idx_survey_year ON survey_master(year);
CREATE INDEX idx_survey_type ON survey_master(diagnosis_type);

-- questions_od
CREATE INDEX idx_qod_survey ON questions_od(survey_id);
CREATE INDEX idx_qod_category1 ON questions_od(category_1);
CREATE INDEX idx_qod_master ON questions_od(master_question_id);

-- questions_ld
CREATE INDEX idx_qld_survey ON questions_ld(survey_id);
CREATE INDEX idx_qld_keyword ON questions_ld(keyword);

-- respondents
CREATE INDEX idx_resp_company_year ON respondents(company_id, year);
CREATE INDEX idx_resp_org ON respondents(org_id);
CREATE INDEX idx_resp_valid ON respondents(is_valid);

-- responses_od (성능 핵심)
CREATE INDEX idx_rod_survey ON responses_od(survey_id);
CREATE INDEX idx_rod_question ON responses_od(question_id);
CREATE INDEX idx_rod_respondent ON responses_od(respondent_id);
CREATE INDEX idx_rod_company_year ON responses_od(company_id, year);

-- responses_ld
CREATE INDEX idx_rld_survey ON responses_ld(survey_id);
CREATE INDEX idx_rld_question ON responses_ld(question_id);
CREATE INDEX idx_rld_respondent ON responses_ld(respondent_id);
CREATE INDEX idx_rld_company_year ON responses_ld(company_id, year);
```

### 5.2 PostgreSQL 전용 인덱스

```sql
-- JSONB GIN 인덱스 (Taxonomy 검색용)
CREATE INDEX idx_qod_tags ON questions_od USING GIN(tags);
CREATE INDEX idx_qld_tags ON questions_ld USING GIN(tags);
CREATE INDEX idx_taxonomy_aliases ON taxonomy_terms USING GIN(aliases);
```

---

## 6. 파티셔닝 전략 (PostgreSQL)

대용량 운영 환경에서 연도별 파티셔닝을 적용한다.

### 6.1 responses_od 파티셔닝

```sql
CREATE TABLE responses_od (
    response_id BIGSERIAL,
    respondent_id VARCHAR(50) NOT NULL,
    question_id VARCHAR(50) NOT NULL,
    survey_id VARCHAR(50) NOT NULL,
    response_value REAL,
    response_text TEXT,
    company_id VARCHAR(20),
    year INT NOT NULL,

    PRIMARY KEY (response_id, year)
) PARTITION BY RANGE (year);

-- 연도별 파티션 생성
CREATE TABLE responses_od_2015 PARTITION OF responses_od FOR VALUES FROM (2015) TO (2016);
CREATE TABLE responses_od_2016 PARTITION OF responses_od FOR VALUES FROM (2016) TO (2017);
-- ... 계속
CREATE TABLE responses_od_2025 PARTITION OF responses_od FOR VALUES FROM (2025) TO (2026);
```

### 6.2 파티션 장점

- 연도별 쿼리 시 해당 파티션만 스캔 (Partition Pruning)
- 오래된 데이터 아카이빙/삭제 용이
- 파티션별 독립적 인덱스 관리
- 병렬 쿼리 성능 향상

---

## 7. 데이터 마이그레이션 전략

### 7.1 현재 데이터 구조

| 원본 테이블/파일 | 대상 테이블 |
|------------------|-------------|
| `hierarchy` | `org_hierarchy` |
| `question_org` | `questions_od` |
| `question_leadership` | `questions_ld` |
| `RawData(23)` | `respondents`, `responses_od`, `responses_ld` |
| `RawData(24)` | `respondents`, `responses_od`, `responses_ld` |
| `Paradise 2025.10.27_470` | `respondents`, `responses_od`, `responses_ld` |
| `0. paradise_survey_question_2023.xlsx` | `questions_od`, `questions_ld` |
| `0. paradise_survey_question_2025.xlsx` | `questions_od`, `questions_ld` |

### 7.2 매핑 전략

#### 7.2.1 문항 번호 매핑

| 원본 | 변환 | 예시 |
|------|------|------|
| 2023 `R01` | `PARADISE-2023-OD-001` | 대문자 → 3자리 |
| 2024/25 `r001` | `PARADISE-2025-OD-001` | 소문자 → 그대로 |
| 2023 LD `1` | `PARADISE-2023-LD-001` | 숫자 → 3자리 |

#### 7.2.2 RawData Wide → Long 변환

```python
# 변환 예시
# Wide Format (원본)
# id | r001 | r002 | r003 | ...
# 1  | 4    | 5    | 3    | ...

# Long Format (변환 후)
# respondent_id | question_id | response_value
# PARADISE-2025-00001 | PARADISE-2025-OD-001 | 4
# PARADISE-2025-00001 | PARADISE-2025-OD-002 | 5
# PARADISE-2025-00001 | PARADISE-2025-OD-003 | 3
```

### 7.3 2024년 데이터 특수 처리

2024년 RawData는 조직진단(`r001~r040`)과 리더십진단(`r01~r67`)이 혼재되어 있다.

```python
# 분리 로직
for column in rawdata_2024.columns:
    if column.startswith('r0') and len(column) == 3:
        # r01~r67 → 리더십진단
        target_table = 'responses_ld'
    elif column.startswith('r') and len(column) == 4:
        # r001~r040 → 조직진단
        target_table = 'responses_od'
```

---

## 8. 구현 단계

### Phase 1: 기반 구축 (1주)

#### 1.1 환경 설정
- [ ] SQLite 데이터베이스 파일 생성
- [ ] 스키마 스크립트 실행
- [ ] 기본 인덱스 생성

#### 1.2 마스터 데이터 구축
- [ ] `company_info` 데이터 입력 (Paradise 그룹 + 계열사)
- [ ] `org_hierarchy` 데이터 마이그레이션 (3개년)
- [ ] `survey_master` 데이터 생성 (6개 설문 정의)

### Phase 2: 설문 문항 구축 (1주)

#### 2.1 문항 데이터 입력
- [ ] 2023년 조직진단 문항 → `questions_od`
- [ ] 2023년 리더십진단 문항 → `questions_ld`
- [ ] 2024/25년 조직진단 문항 → `questions_od`
- [ ] 2024/25년 리더십진단 문항 → `questions_ld`

#### 2.2 문항 매핑
- [ ] 2023 ↔ 2024/25 문항 텍스트 유사도 분석
- [ ] `question_mapping` 테이블 구축
- [ ] `master_question_id` 설정

### Phase 3: 응답 데이터 마이그레이션 (1~2주)

#### 3.1 응답자 데이터 구축
- [ ] 2023년 응답자 → `respondents`
- [ ] 2024년 응답자 → `respondents`
- [ ] 2025년 응답자 → `respondents`

#### 3.2 응답 데이터 변환
- [ ] 2023년 RawData → `responses_od`, `responses_ld`
- [ ] 2024년 RawData → `responses_od`, `responses_ld`
- [ ] 2025년 RawData → `responses_od`, `responses_ld`

#### 3.3 데이터 검증
- [ ] 레코드 수 검증
- [ ] 무결성 검증 (FK 관계)
- [ ] 샘플 쿼리 테스트

### Phase 4: Taxonomy 구축 (1주)

#### 4.1 기본 Taxonomy 구축
- [ ] `taxonomy_terms` 핵심 용어 입력 (50~100개)
- [ ] `taxonomy_relations` 관계 정의

#### 4.2 문항 태깅
- [ ] 자동 태깅 스크립트 개발
- [ ] 문항별 `tags` 필드 업데이트
- [ ] 수동 검토 및 보정

### Phase 5: 조회 인터페이스 (1~2주)

#### 5.1 기본 쿼리 개발
- [ ] 설문별 평균 점수 조회
- [ ] 연도별 추이 분석
- [ ] 조직별 비교 분석
- [ ] 문항별 상세 분석

#### 5.2 Claude Code 연동
- [ ] 자연어 → SQL 변환 로직
- [ ] 결과 포맷팅
- [ ] 시각화 연동

### Phase 6: PostgreSQL 마이그레이션 (선택, 2주)

#### 6.1 환경 구축
- [ ] PostgreSQL 서버 설정
- [ ] 스키마 마이그레이션
- [ ] 파티셔닝 적용

#### 6.2 데이터 이관
- [ ] SQLite → PostgreSQL 데이터 덤프
- [ ] 인덱스 재생성
- [ ] 성능 테스트

---

## 9. 예상 쿼리 및 성능

### 9.1 기본 쿼리 예시

#### 특정 설문 전체 평균
```sql
SELECT AVG(response_value) as avg_score
FROM responses_od
WHERE survey_id = 'PARADISE-2025-OD';
-- 예상: 30-50ms (SQLite), 10-30ms (PostgreSQL)
```

#### 문항별 평균 점수
```sql
SELECT
    q.category_1,
    q.category_2,
    q.question_text,
    AVG(r.response_value) as avg_score,
    COUNT(*) as response_count
FROM responses_od r
JOIN questions_od q ON r.question_id = q.question_id
WHERE r.survey_id = 'PARADISE-2025-OD'
GROUP BY q.question_id
ORDER BY q.sort_order;
-- 예상: 50-100ms (SQLite), 30-50ms (PostgreSQL)
```

#### 연도별 추이
```sql
SELECT
    r.year,
    q.category_1,
    AVG(r.response_value) as avg_score
FROM responses_od r
JOIN questions_od q ON r.question_id = q.question_id
WHERE q.master_question_id IS NOT NULL
GROUP BY r.year, q.category_1
ORDER BY r.year, q.category_1;
-- 예상: 200-500ms (SQLite), 100-200ms (PostgreSQL)
```

#### 조직별 비교
```sql
SELECT
    resp.org_level1,
    AVG(r.response_value) as avg_score
FROM responses_od r
JOIN respondents resp ON r.respondent_id = resp.respondent_id
WHERE r.survey_id = 'PARADISE-2025-OD'
  AND resp.is_valid = TRUE
GROUP BY resp.org_level1
ORDER BY avg_score DESC;
-- 예상: 80-150ms (SQLite), 40-80ms (PostgreSQL)
```

#### Taxonomy 기반 검색 (PostgreSQL)
```sql
SELECT
    q.question_text,
    AVG(r.response_value) as avg_score
FROM responses_od r
JOIN questions_od q ON r.question_id = q.question_id
WHERE q.tags @> '{"concepts": ["리더십"]}'
  AND r.year = 2025
GROUP BY q.question_id;
-- 예상: 100-300ms (PostgreSQL with GIN index)
```

### 9.2 성능 최적화 팁

1. **비정규화 활용**: `responses_*` 테이블에 `company_id`, `year` 중복 저장
2. **복합 인덱스**: 자주 사용하는 WHERE 조합에 복합 인덱스
3. **Materialized View**: 자주 사용하는 집계는 미리 계산
4. **파티션 프루닝**: 연도 조건 명시로 스캔 범위 제한

---

## 10. 파일 구조

```
Paradise/
├── docs/
│   ├── DATABASE_DESIGN.md          # 본 문서
│   └── API_REFERENCE.md            # API 명세 (추후)
├── schema/
│   ├── 01_create_tables.sql        # 테이블 생성
│   ├── 02_create_indexes.sql       # 인덱스 생성
│   ├── 03_create_views.sql         # 뷰 생성
│   └── 04_postgresql_partition.sql # PostgreSQL 파티션
├── scripts/
│   ├── migrate_master_data.py      # 마스터 데이터 마이그레이션
│   ├── migrate_questions.py        # 문항 마이그레이션
│   ├── migrate_responses.py        # 응답 마이그레이션
│   └── auto_tagging.py             # 자동 태깅
├── data/
│   ├── raw/                        # 원본 데이터
│   └── processed/                  # 처리된 데이터
└── Paradise2025.db                 # SQLite 데이터베이스
```

---

## 11. 참고 문서

- [Taxonomy_and_Ontology.md](../Taxonomy_and_Ontology.md) - 분류 체계 설계 문서
- [CLAUDE.md](../CLAUDE.md) - 프로젝트 개요

---

## 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0 | 2025-11-19 | AI Lab | 최초 작성 |
