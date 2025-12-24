# MasterDB 사용 가이드

MasterDB는 여러 클라이언트(파라다이스, 스타벅스 등)의 설문조사 데이터를 통합 관리하는 SQLite 데이터베이스입니다.

## 목차
- [데이터베이스 개요](#데이터베이스-개요)
- [클라이언트별 데이터 구조](#클라이언트별-데이터-구조)
- [기본 조회 쿼리](#기본-조회-쿼리)
- [고급 분석 쿼리](#고급-분석-쿼리)
- [Python을 이용한 분석](#python을-이용한-분석)

## 데이터베이스 개요

### 위치
```
/Users/hanskim/Projects/Paradise/MasterDB.db
```

### 핵심 테이블
```
company_info        - 클라이언트 회사 정보
respondents         - 설문 응답자 정보
questions_od        - 조직진단 문항
questions_ld        - 리더십진단 문항
responses_od_opt    - 조직진단 응답 (Long Format, INTEGER FK)
responses_ld_opt    - 리더십진단 응답 (Long Format, INTEGER FK)
survey_master       - 설문 메타데이터
```

### 데이터 현황 (2025-11-27 기준)

| 클라이언트 | 연도 | 설문 유형 | 응답자 수 | 응답 데이터 수 |
|-----------|------|----------|----------|--------------|
| PARADISE | 2023 | OD | 2,539 | ~160,000 |
| PARADISE | 2024 | OD | 3,507 | ~221,000 |
| PARADISE | 2025 | OD | 5,246 | ~330,000 |
| STARBUCKS | 2023 | 360° LD | 7,748 | ~95,000 |
| STARBUCKS | 2024 | 360° LD | 8,575 | ~184,000 |
| STARBUCKS | 2023 | PES (OD) | 20,393 | ~441,000 |
| STARBUCKS | 2024 | PES (OD) | 19,742 | ~481,000 |
| STARBUCKS | 2025 | PES (OD) | 19,969 | ~520,000 |
| **Total** | | | **87,719** | **~2,432,000** |

## 클라이언트별 데이터 구조

### 1. PARADISE (파라다이스 그룹)

#### 설문 유형
- **OD (Organizational Diagnostics)**: 조직진단
- **연도**: 2023, 2024, 2025

#### Survey ID 구조
```
PARADISE-{year}-OD
예: PARADISE-2023-OD, PARADISE-2024-OD, PARADISE-2025-OD
```

#### 조직 구조
```sql
-- org_level1: 계열사 (㈜파라다이스 HQ, ㈜파라다이스 제주, 비노파라다이스 등)
-- org_level2~6: 하위 조직 (부서, 팀 등)
```

#### 문항 구조
- 2023년: 64개 문항 (R01-R64, 대문자)
- 2024년: 67개 문항 (r001-r067)
- 2025년: 96개 문항 (r001-r096)

#### 기본 조회 예시

```sql
-- 2024년 파라다이스 응답자 조회
SELECT
    respondent_id,
    name,
    rank,
    position,
    org_level1,
    org_level2
FROM respondents
WHERE company_id = 'PARADISE'
  AND year = 2024
LIMIT 10;

-- 2024년 문항별 평균 점수
SELECT
    q.question_no,
    q.question_text,
    q.category_1,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_od q
JOIN responses_od_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
GROUP BY q.question_no, q.question_text, q.category_1
ORDER BY q.question_no;
```

### 2. STARBUCKS (스타벅스)

#### 설문 유형
- **360° Feedback (다면평가)**: 리더십 진단 (LD) - 2023, 2024
- **PES (Partner Engagement Survey)**: 조직진단 (OD) - 2024, 2025

#### Survey ID 구조

**2023년** (8개 survey_id - 직급별 × 평가자 그룹별):
```
STARBUCKS-2023-360-{job_grade}-{evaluator_group}

직급(job_grade): 담당, 팀장, 파트장, 파트너
평가자그룹(evaluator_group):
  - 상사본인 (상사평가 + 본인평가): 20개 문항
  - 동료부하 (동료평가 + 부하평가): 18개 문항

예시:
- STARBUCKS-2023-360-담당-상사본인 (20 questions)
- STARBUCKS-2023-360-담당-동료부하 (18 questions)
- STARBUCKS-2023-360-팀장-상사본인 (20 questions)
- STARBUCKS-2023-360-팀장-동료부하 (18 questions)
```

**2024년** (단일 survey_id):
```
STARBUCKS-2024-360
- 20개 문항 (r001-r020)
- 모든 직급, 모든 평가자 유형 통합
```

#### 평가자 유형 (evaluator_type)
- `본인평가`: Self evaluation
- `상사평가`: Supervisor evaluation
- `동료평가`: Peer evaluation
- `부하평가`: Subordinate evaluation

#### 직급 구분
- `담당`: 담당자급
- `팀장`: 팀장급
- `파트장`: 파트장/DM급
- `파트너`: 파트너급

#### 문항 구조 및 카테고리

**2023년 카테고리** (광범위한 3개 영역):
- `Leadership`: 리더십 역량 (9개 문항)
- `Value`: 가치관/태도 (6개 문항)
- `Professionals`: 전문성 (2개 문항)

**2024년 카테고리** (세분화된 20개 역량):
```
긍정적 분위기조성, 신뢰 형성, 도전 정신, 아이디어 수용, 최고 지향,
인정/칭찬, 코칭, 문제 해결, 의사결정, 변화 관리,
업무지시, 동기부여, 비전 제시, 권한 위임, 전략실행,
사업적 통찰력, 직무전문성, 손익 마인드, 협업, 커뮤니케이션
```

#### 기본 조회 예시

```sql
-- 2024년 스타벅스 응답자 조회 (담당급)
SELECT
    respondent_id,
    name,
    rank,
    evaluator_type,
    target_name,
    org_level1
FROM respondents
WHERE company_id = 'STARBUCKS'
  AND year = 2024
  AND (survey_subtype LIKE '%담당%' OR rank LIKE '%담당%')
LIMIT 10;

-- 2024년 담당급 부하평가 영역별 평균
SELECT
    q.category_1 as category,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'STARBUCKS'
  AND r.year = 2024
  AND r.evaluator_type = '부하평가'
  AND (r.survey_subtype LIKE '%담당%' OR r.rank LIKE '%담당%')
  AND q.category_1 IS NOT NULL
GROUP BY q.category_1
ORDER BY avg_score DESC;

-- 2023년 담당급 부하평가 (동료부하 설문)
SELECT
    q.question_no,
    q.question_text,
    q.category_1,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.survey_id = 'STARBUCKS-2023-360-담당-동료부하'
  AND r.evaluator_type = '부하평가'
GROUP BY q.question_no, q.question_text, q.category_1
ORDER BY q.question_no;
```

### 3. STARBUCKS PES (Partner Engagement Survey)

#### 설문 유형
- **PES (Partner Engagement Survey)**: 파트너 몰입도 조사 (조직진단)
- **연도**: 2023, 2024, 2025

#### Survey ID 구조
```
STARBUCKS-{year}-PES-{type}

유형(type):
  - SC (Support Center): 본사/지원 조직
  - STORE: 매장

예시:
- STARBUCKS-2023-PES-SC (41 questions)
- STARBUCKS-2023-PES-STORE (32 questions)
- STARBUCKS-2024-PES-SC (40 questions)
- STARBUCKS-2024-PES-STORE (30 questions)
- STARBUCKS-2025-PES-SC (30 questions)
- STARBUCKS-2025-PES-STORE (35 questions)
```

#### 데이터 규모
| Year | Type | Respondents | Questions | Responses |
|------|------|-------------|-----------|-----------|
| 2023 | SC | 613 | 41 | ~21,000 |
| 2023 | STORE | 19,780 | 32 | ~420,000 |
| 2024 | SC | 672 | 40 | ~23,000 |
| 2024 | STORE | 19,070 | 30 | ~402,000 |
| 2025 | SC | 684 | 30 | ~16,000 |
| 2025 | STORE | 19,285 | 35 | ~467,000 |
| **Total** | | **60,104** | | **~1,349,000** |

#### 문항 카테고리 (2024 STORE 기준)

**6개 주요 영역:**
- `My Company`: 회사에 대한 인식 (7 문항)
- `My Team`: 팀 관련 (5 문항)
- `My Job`: 업무 관련 (9 문항)
- `My Manager`: 매니저 평가 (4 문항)
- `My Pay & Benefits`: 급여/복리후생 (3 문항)
- `Engagement`: 몰입도 (2 문항)

#### 기본 조회 예시

```sql
-- PES 응답자 조회 (2024 STORE)
SELECT
    respondent_id,
    name,
    rank,
    org_level1,
    org_level2
FROM respondents
WHERE company_id = 'STARBUCKS'
  AND year = 2024
  AND survey_id = 'STARBUCKS-2024-PES-STORE'
LIMIT 10;

-- PES 영역별 평균 (2024 STORE)
SELECT
    q.category_1 as category,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_od q
JOIN responses_od_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.survey_id = 'STARBUCKS-2024-PES-STORE'
  AND q.category_1 IS NOT NULL
GROUP BY q.category_1
ORDER BY avg_score DESC;

-- 2024 vs 2025 PES 비교 (STORE)
WITH year_2024 AS (
    SELECT
        q.question_text,
        ROUND(AVG(res.response_value), 2) as avg_2024
    FROM questions_od q
    JOIN responses_od_opt res ON res.question_idx = q.rowid
    JOIN respondents r ON res.respondent_idx = r.rowid
    WHERE r.survey_id = 'STARBUCKS-2024-PES-STORE'
    GROUP BY q.question_text
),
year_2025 AS (
    SELECT
        q.question_text,
        ROUND(AVG(res.response_value), 2) as avg_2025
    FROM questions_od q
    JOIN responses_od_opt res ON res.question_idx = q.rowid
    JOIN respondents r ON res.respondent_idx = r.rowid
    WHERE r.survey_id = 'STARBUCKS-2025-PES-STORE'
    GROUP BY q.question_text
)
SELECT
    a.question_text,
    a.avg_2024,
    b.avg_2025,
    ROUND(b.avg_2025 - a.avg_2024, 2) as difference
FROM year_2024 a
INNER JOIN year_2025 b ON a.question_text = b.question_text
ORDER BY difference DESC;
```

## 기본 조회 쿼리

### 1. 응답자 정보 조회

```sql
-- 특정 클라이언트/연도 응답자 수
SELECT
    company_id,
    year,
    COUNT(*) as respondent_count
FROM respondents
GROUP BY company_id, year
ORDER BY company_id, year;

-- 스타벅스 평가자 유형별 분포
SELECT
    year,
    evaluator_type,
    COUNT(*) as count
FROM respondents
WHERE company_id = 'STARBUCKS'
GROUP BY year, evaluator_type
ORDER BY year, evaluator_type;

-- 스타벅스 직급별 분포
SELECT
    year,
    survey_subtype,
    COUNT(*) as count
FROM respondents
WHERE company_id = 'STARBUCKS'
GROUP BY year, survey_subtype
ORDER BY year, survey_subtype;
```

### 2. 문항 정보 조회

```sql
-- 파라다이스 2024년 문항 목록
SELECT
    question_no,
    question_text,
    category_1,
    category_2,
    question_type
FROM questions_od
WHERE survey_id = 'PARADISE-2024-OD'
ORDER BY question_no;

-- 스타벅스 2024년 문항 목록
SELECT
    question_no,
    question_text,
    category_1,
    question_type
FROM questions_ld
WHERE survey_id = 'STARBUCKS-2024-360'
ORDER BY question_no;

-- 카테고리별 문항 수
SELECT
    survey_id,
    category_1,
    COUNT(*) as question_count
FROM questions_ld
WHERE company_id = 'STARBUCKS'
GROUP BY survey_id, category_1
ORDER BY survey_id, category_1;
```

### 3. 응답 데이터 조회

```sql
-- 특정 응답자의 모든 응답
SELECT
    r.respondent_id,
    r.name,
    q.question_no,
    q.question_text,
    res.response_value
FROM respondents r
JOIN responses_od_opt res ON res.respondent_idx = r.rowid
JOIN questions_od q ON res.question_idx = q.rowid
WHERE r.respondent_id = 'PARADISE-2024-OD-0001'
ORDER BY q.question_no;

-- 문항별 응답 분포
SELECT
    res.response_value,
    COUNT(*) as count
FROM responses_od_opt res
JOIN respondents r ON res.respondent_idx = r.rowid
JOIN questions_od q ON res.question_idx = q.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
  AND q.question_no = 'r001'
GROUP BY res.response_value
ORDER BY res.response_value;
```

## 고급 분석 쿼리

### 1. 연도별 비교 분석

```sql
-- 파라다이스 연도별 평균 점수 추이
SELECT
    r.year,
    COUNT(DISTINCT r.rowid) as respondent_count,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM respondents r
JOIN responses_od_opt res ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
GROUP BY r.year
ORDER BY r.year;

-- 스타벅스 2023 vs 2024 동일 문항 비교 (담당 부하평가)
WITH year_2023 AS (
    SELECT
        q.question_text,
        q.category_1 as category_2023,
        ROUND(AVG(res.response_value), 2) as avg_2023
    FROM questions_ld q
    JOIN responses_ld_opt res ON res.question_idx = q.rowid
    JOIN respondents r ON res.respondent_idx = r.rowid
    WHERE r.survey_id = 'STARBUCKS-2023-360-담당-동료부하'
      AND r.evaluator_type = '부하평가'
    GROUP BY q.question_text, q.category_1
),
year_2024 AS (
    SELECT
        q.question_text,
        q.category_1 as category_2024,
        ROUND(AVG(res.response_value), 2) as avg_2024
    FROM questions_ld q
    JOIN responses_ld_opt res ON res.question_idx = q.rowid
    JOIN respondents r ON res.respondent_idx = r.rowid
    WHERE r.year = 2024
      AND r.evaluator_type = '부하평가'
      AND (r.survey_subtype LIKE '%담당%' OR r.rank LIKE '%담당%')
    GROUP BY q.question_text, q.category_1
)
SELECT
    a.question_text,
    a.category_2023,
    b.category_2024,
    a.avg_2023,
    b.avg_2024,
    ROUND(b.avg_2024 - a.avg_2023, 2) as difference,
    ROUND((b.avg_2024 - a.avg_2023) / a.avg_2023 * 100, 1) as change_pct
FROM year_2023 a
JOIN year_2024 b ON a.question_text = b.question_text
ORDER BY difference DESC;
```

### 2. 카테고리별 분석

```sql
-- 파라다이스 카테고리별 평균 점수
SELECT
    q.category_1,
    COUNT(DISTINCT q.question_no) as question_count,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score,
    ROUND(MIN(res.response_value), 2) as min_score,
    ROUND(MAX(res.response_value), 2) as max_score
FROM questions_od q
JOIN responses_od_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
  AND q.category_1 IS NOT NULL
GROUP BY q.category_1
ORDER BY avg_score DESC;

-- 스타벅스 2024 평가자 유형별 × 영역별 평균
SELECT
    r.evaluator_type,
    q.category_1,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'STARBUCKS'
  AND r.year = 2024
  AND q.category_1 IS NOT NULL
GROUP BY r.evaluator_type, q.category_1
ORDER BY r.evaluator_type, avg_score DESC;
```

### 3. 조직별 분석

```sql
-- 파라다이스 계열사별 평균
SELECT
    r.org_level1,
    COUNT(DISTINCT r.rowid) as respondent_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM respondents r
JOIN responses_od_opt res ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
  AND r.org_level1 IS NOT NULL
GROUP BY r.org_level1
ORDER BY avg_score DESC;

-- 스타벅스 리전별 평균 (org_level1 = 리전)
SELECT
    r.org_level1,
    r.evaluator_type,
    COUNT(DISTINCT r.rowid) as respondent_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM respondents r
JOIN responses_ld_opt res ON res.respondent_idx = r.rowid
WHERE r.company_id = 'STARBUCKS'
  AND r.year = 2024
  AND r.org_level1 IS NOT NULL
GROUP BY r.org_level1, r.evaluator_type
ORDER BY r.org_level1, r.evaluator_type;
```

### 4. TOP/BOTTOM 문항 분석

```sql
-- 파라다이스 2024 점수 높은 문항 TOP 10
SELECT
    q.question_no,
    q.question_text,
    q.category_1,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_od q
JOIN responses_od_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
GROUP BY q.question_no, q.question_text, q.category_1
ORDER BY avg_score DESC
LIMIT 10;

-- 파라다이스 2024 점수 낮은 문항 BOTTOM 10
SELECT
    q.question_no,
    q.question_text,
    q.category_1,
    COUNT(res.rowid) as response_count,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_od q
JOIN responses_od_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
GROUP BY q.question_no, q.question_text, q.category_1
ORDER BY avg_score ASC
LIMIT 10;
```

## Python을 이용한 분석

### 1. 기본 연결 및 조회

```python
import sqlite3
import pandas as pd

# 데이터베이스 연결
conn = sqlite3.connect('MasterDB.db')

# 파라다이스 2024 데이터 조회
query = """
SELECT
    r.respondent_id,
    r.name,
    r.rank,
    r.org_level1,
    q.question_no,
    q.question_text,
    q.category_1,
    res.response_value
FROM respondents r
JOIN responses_od_opt res ON res.respondent_idx = r.rowid
JOIN questions_od q ON res.question_idx = q.rowid
WHERE r.company_id = 'PARADISE'
  AND r.year = 2024
"""

df = pd.read_sql_query(query, conn)
conn.close()

# 기본 통계
print(df.describe())
print(df.groupby('category_1')['response_value'].mean())
```

### 2. 스타벅스 연도별 비교

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect('MasterDB.db')

# 2023 vs 2024 비교 (담당 부하평가)
query_2023 = """
SELECT
    q.question_text,
    q.category_1 as category,
    ROUND(AVG(res.response_value), 2) as avg_2023
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.survey_id = 'STARBUCKS-2023-360-담당-동료부하'
  AND r.evaluator_type = '부하평가'
GROUP BY q.question_text, q.category_1
"""

query_2024 = """
SELECT
    q.question_text,
    q.category_1 as category,
    ROUND(AVG(res.response_value), 2) as avg_2024
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.year = 2024
  AND r.evaluator_type = '부하평가'
  AND (r.survey_subtype LIKE '%담당%' OR r.rank LIKE '%담당%')
GROUP BY q.question_text, q.category_1
"""

df_2023 = pd.read_sql_query(query_2023, conn)
df_2024 = pd.read_sql_query(query_2024, conn)

# 데이터 병합
merged = pd.merge(df_2023, df_2024, on='question_text', how='inner')
merged['difference'] = merged['avg_2024'] - merged['avg_2023']
merged['change_pct'] = (merged['difference'] / merged['avg_2023'] * 100).round(1)

# 결과 출력
print("\n=== 연도별 비교 ===")
print(f"전체 평균 - 2023: {merged['avg_2023'].mean():.2f}, 2024: {merged['avg_2024'].mean():.2f}")
print(f"평균 변화: {merged['difference'].mean():.2f}점 ({merged['change_pct'].mean():.1f}%)")

print("\n=== 개선도 TOP 5 ===")
print(merged.nlargest(5, 'difference')[['question_text', 'avg_2023', 'avg_2024', 'difference', 'change_pct']])

print("\n=== 개선도 BOTTOM 5 ===")
print(merged.nsmallest(5, 'difference')[['question_text', 'avg_2023', 'avg_2024', 'difference', 'change_pct']])

conn.close()
```

### 3. 카테고리별 시각화

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

conn = sqlite3.connect('MasterDB.db')

# 스타벅스 2024 영역별 평균
query = """
SELECT
    q.category_1 as category,
    ROUND(AVG(res.response_value), 2) as avg_score
FROM questions_ld q
JOIN responses_ld_opt res ON res.question_idx = q.rowid
JOIN respondents r ON res.respondent_idx = r.rowid
WHERE r.company_id = 'STARBUCKS'
  AND r.year = 2024
  AND r.evaluator_type = '부하평가'
  AND q.category_1 IS NOT NULL
GROUP BY q.category_1
ORDER BY avg_score DESC
"""

df = pd.read_sql_query(query, conn)
conn.close()

# 막대 그래프
plt.figure(figsize=(12, 8))
plt.barh(df['category'], df['avg_score'])
plt.xlabel('평균 점수')
plt.title('스타벅스 2024 영역별 평균 점수 (부하평가)')
plt.tight_layout()
plt.savefig('starbucks_2024_category_scores.png', dpi=300, bbox_inches='tight')
plt.show()
```

## 데이터 구조 요약

### 응답자 테이블 (respondents)
```
rowid              - Primary key (INTEGER)
respondent_id      - 고유 ID (PARADISE-2024-OD-0001 등)
survey_id          - 설문 ID (FK)
company_id         - 클라이언트 코드 (PARADISE, STARBUCKS)
year               - 설문 연도
name               - 이름
rank               - 직급
position           - 직책
org_level1~6       - 조직 계층
survey_subtype     - 설문 하위 유형 (스타벅스: 직급)
evaluator_type     - 평가자 유형 (스타벅스: 본인평가, 상사평가, 동료평가, 부하평가)
target_name        - 평가 대상자 (360° 피드백)
```

### 문항 테이블 (questions_od, questions_ld)
```
rowid              - Primary key (INTEGER)
survey_id          - 설문 ID
question_no        - 문항 번호 (r001, r002, ...)
question_text      - 문항 내용
question_type      - 문항 유형 (LIKERT, CHOICE_SINGLE, ESSAY)
category_1~3       - 카테고리 계층
```

### 응답 테이블 (responses_od_opt, responses_ld_opt)
```
rowid              - Primary key (INTEGER)
respondent_idx     - 응답자 FK (respondents.rowid)
question_idx       - 문항 FK (questions_*.rowid)
response_value     - 응답 값 (숫자)
response_text      - 응답 텍스트 (ESSAY 문항)
```

## 주의사항

1. **rowid 사용**: 모든 JOIN은 rowid를 사용 (INTEGER FK 최적화)
2. **company_id 필터**: 항상 클라이언트 필터링 필요
3. **year 필터**: 연도별 데이터 구조가 다를 수 있음
4. **NULL 처리**: category_1, org_level1 등은 NULL 가능
5. **문항 번호 형식**:
   - 파라다이스 2023: R01 (대문자)
   - 파라다이스 2024/2025: r001 (소문자, 3자리)
   - 스타벅스: r001 (소문자, 3자리)

## 추가 리소스

- [데이터베이스 설계 문서](DATABASE_DESIGN.md)
- [마이그레이션 스크립트](scripts/)
- [CLAUDE.md](CLAUDE.md) - 프로젝트 전체 개요
