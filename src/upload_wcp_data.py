# -*- coding: utf-8 -*-
"""
W컨셉 신규 데이터 MasterDB 업로드 스크립트
"""
import pandas as pd
import sqlite3
import sys
import json

def create_response_tables(cursor):
    """응답 데이터 저장용 테이블 생성"""

    # 응답자 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS respondents (
            respondent_id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id TEXT NOT NULL,
            original_id TEXT,              -- 원본 ID

            -- 인구통계
            gender TEXT,                   -- 성별
            age INTEGER,                   -- 나이
            tenure INTEGER,                -- 근속연수
            experience INTEGER,            -- 경력연수
            rank TEXT,                     -- 직급
            position TEXT,                 -- 직책
            job_group TEXT,                -- 직군
            job_function TEXT,             -- 직무

            -- 조직 정보
            org_level_1 TEXT,
            org_level_2 TEXT,
            org_level_3 TEXT,
            org_level_4 TEXT,
            org_level_5 TEXT,

            -- MA 전용 (피평가자 정보)
            target_info TEXT,              -- 피평가자 정보
            target_name TEXT,              -- 피평가자 이름
            target_org TEXT,               -- 피평가자 조직
            target_position TEXT,          -- 피평가자 직책
            evaluator_type TEXT,           -- 평가 유형 (본인/상향/하향/동료)

            -- 유효성
            is_valid INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (survey_id) REFERENCES surveys(survey_id)
        )
    """)

    # 응답 데이터 테이블 (Long format - 정규화)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            respondent_id INTEGER NOT NULL,
            question_no TEXT NOT NULL,     -- r001, r002, ...
            response_value TEXT,           -- 응답값 (문자열로 저장)

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (respondent_id) REFERENCES respondents(respondent_id)
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_respondents_survey ON respondents(survey_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_respondent ON responses(respondent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_no)")

def main():
    conn = sqlite3.connect('db/masterdb.sqlite')
    cursor = conn.cursor()

    # 응답 테이블 생성
    create_response_tables(cursor)
    conn.commit()

    # =====================================================
    # 1. OD Survey 업로드
    # =====================================================
    print('=== 1. 조직진단(OD) Survey 업로드 ===')

    survey_id = 'IG202512WCPOD'
    survey_name = 'IG202512_더블유컨셉코리아 조직진단'
    company_id = 'WCP'
    diagnosis_type = 'OD'
    survey_year = 2025
    survey_month = 12

    # 기존 데이터 삭제
    cursor.execute(f"DELETE FROM surveys WHERE survey_id = ?", (survey_id,))
    cursor.execute(f"DELETE FROM survey_questions WHERE survey_id = ?", (survey_id,))

    # Survey 등록
    cursor.execute("""
        INSERT INTO surveys (survey_id, survey_name, company_id, diagnosis_type, survey_year, survey_month)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (survey_id, survey_name, company_id, diagnosis_type, survey_year, survey_month))
    print(f'  Survey 등록: {survey_id}')

    # OD 문항 읽기
    df_od = pd.read_excel('ExcelTable/SurveyQuestion/IG202512WCPOD_Survey.xlsx', sheet_name='sheet1')

    # 문항 등록
    new_questions = 0
    linked_questions = 0

    for idx, row in df_od.iterrows():
        question_text = row['question_text']

        # questions 테이블에서 동일 문항 찾기
        existing_q = pd.read_sql("SELECT question_id FROM questions WHERE question_text = ?", conn, params=(question_text,))

        if len(existing_q) > 0:
            q_id = existing_q.iloc[0]['question_id']
        else:
            # 새 question_id 생성
            max_id = pd.read_sql("SELECT MAX(CAST(SUBSTR(question_id, 3) AS INTEGER)) as max_id FROM questions", conn)
            next_num = (max_id.iloc[0]['max_id'] or 0) + 1
            q_id = f'Q_{next_num:05d}'

            # questions 테이블에 등록
            legacy_mid = row.get('category_1')
            legacy_sub = row.get('category_2')
            question_type = row.get('question_type', 'LIKERT')
            scale_min = row.get('scale_min', 1)
            scale_max = row.get('scale_max', 5)
            is_reverse = 1 if row.get('is_reverse', False) else 0

            cursor.execute("""
                INSERT INTO questions (question_id, question_text, diagnosis_type, source_survey_id, source_year,
                                       question_type, scale_min, scale_max, is_reverse,
                                       legacy_mid_category, legacy_sub_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (q_id, question_text, diagnosis_type, survey_id, survey_year,
                  question_type.upper() if question_type else 'LIKERT', scale_min, scale_max, is_reverse,
                  legacy_mid, legacy_sub))
            new_questions += 1

        # survey_questions 연결
        is_required = 1 if row.get('is_required', True) else 0
        scale_type = row.get('question_type', 'likert_5')
        section_name = row.get('category_1')

        cursor.execute("""
            INSERT INTO survey_questions (survey_id, question_id, question_order, is_required, scale_type, section_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (survey_id, q_id, idx + 1, is_required, scale_type, section_name))
        linked_questions += 1

    print(f'  신규 문항: {new_questions}개')
    print(f'  연결된 문항: {linked_questions}개')

    # RawData 업로드
    print('  RawData 업로드 중...')
    df_od_raw = pd.read_excel('ExcelTable/SurveyRawData/IG202512WCPOD_RawData.xlsx', sheet_name='Sheet1')

    # 기존 응답 데이터 삭제
    cursor.execute("DELETE FROM respondents WHERE survey_id = ?", (survey_id,))

    # 응답 컬럼 식별
    response_cols = [c for c in df_od_raw.columns if str(c).startswith('r')]

    # 응답자 및 응답 데이터 저장
    for idx, row in df_od_raw.iterrows():
        # 응답자 정보 저장
        cursor.execute("""
            INSERT INTO respondents (
                survey_id, original_id, gender, age, tenure, experience,
                rank, position, job_group, job_function,
                org_level_1, org_level_2, org_level_3, org_level_4, org_level_5,
                is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            survey_id,
            str(row.get('ID', '')),
            str(row.get('성별', '')) if pd.notna(row.get('성별')) else None,
            int(row.get('나이')) if pd.notna(row.get('나이')) else None,
            int(row.get('근속연수')) if pd.notna(row.get('근속연수')) else None,
            int(row.get('경력연수')) if pd.notna(row.get('경력연수')) else None,
            str(row.get('직급', '')) if pd.notna(row.get('직급')) else None,
            str(row.get('직책', '')) if pd.notna(row.get('직책')) else None,
            str(row.get('직군', '')) if pd.notna(row.get('직군')) else None,
            str(row.get('직무', '')) if pd.notna(row.get('직무')) else None,
            str(row.get('조직 Lv.1', '')) if pd.notna(row.get('조직 Lv.1')) else None,
            str(row.get('조직 Lv.2', '')) if pd.notna(row.get('조직 Lv.2')) else None,
            str(row.get('조직 Lv.3', '')) if pd.notna(row.get('조직 Lv.3')) else None,
            str(row.get('조직 Lv.4', '')) if pd.notna(row.get('조직 Lv.4')) else None,
            str(row.get('조직 Lv.5', '')) if pd.notna(row.get('조직 Lv.5')) else None,
            int(row.get('유효응답여부', 1)) if pd.notna(row.get('유효응답여부')) else 1
        ))
        respondent_id = cursor.lastrowid

        # 응답 데이터 저장
        for col in response_cols:
            val = row.get(col)
            if pd.notna(val):
                cursor.execute("""
                    INSERT INTO responses (respondent_id, question_no, response_value)
                    VALUES (?, ?, ?)
                """, (respondent_id, col, str(val)))

    # Survey 테이블에 응답자 수 업데이트
    cursor.execute("""
        UPDATE surveys SET question_count = ?, actual_respondent_count = ?
        WHERE survey_id = ?
    """, (len(df_od), len(df_od_raw), survey_id))

    conn.commit()
    print(f'  응답자 수: {len(df_od_raw)}명')
    print(f'  응답 데이터: {len(df_od_raw) * len(response_cols)}건')
    print()

    # =====================================================
    # 2. MA Survey 업로드 (서브타입별)
    # =====================================================
    print('=== 2. 다면평가(MA) Survey 업로드 ===')

    # MA 서브타입 정의
    ma_subtypes = [
        ('LS', '리더급 본인평가', '리더급', '본인평가'),
        ('LO', '리더급 타인평가', '리더급', '타인평가'),
        ('SS', '시니어급 본인평가', '시니어급', '본인평가'),
        ('SO', '시니어급 타인평가', '시니어급', '타인평가'),
        ('JS', '주니어급 본인평가', '주니어급', '본인평가'),
        ('JO', '주니어급 타인평가', '주니어급', '타인평가'),
    ]

    diagnosis_type_ma = 'MA'
    total_new_questions = 0
    total_linked_questions = 0
    processed_questions_global = set()  # 전체 MA에서 이미 등록한 문항

    for subtype_code, sheet_name, target_group, evaluator_type in ma_subtypes:
        survey_id_ma = f'IG202512WCPMA_{subtype_code}'
        survey_name_ma = f'IG202512_더블유컨셉코리아 다면평가 ({sheet_name})'

        # 기존 데이터 삭제
        cursor.execute("DELETE FROM surveys WHERE survey_id = ?", (survey_id_ma,))
        cursor.execute("DELETE FROM survey_questions WHERE survey_id = ?", (survey_id_ma,))

        # Survey 등록
        cursor.execute("""
            INSERT INTO surveys (survey_id, survey_name, company_id, diagnosis_type, survey_year, survey_month)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (survey_id_ma, survey_name_ma, company_id, diagnosis_type_ma, survey_year, survey_month))
        print(f'  Survey 등록: {survey_id_ma}')

        # 해당 시트에서 문항 읽기
        try:
            df_ma = pd.read_excel('ExcelTable/SurveyQuestion/IG202512WCPMA_Survey.xlsx', sheet_name=sheet_name)
        except Exception as e:
            print(f'    시트 읽기 실패: {sheet_name} - {e}')
            continue

        # 문항 등록
        new_questions_ma = 0
        linked_questions_ma = 0

        for idx, row in df_ma.iterrows():
            question_text = row['question_text']

            # questions 테이블에서 동일 문항 찾기
            existing_q = pd.read_sql("SELECT question_id FROM questions WHERE question_text = ?", conn, params=(question_text,))

            if len(existing_q) > 0:
                q_id = existing_q.iloc[0]['question_id']
            elif question_text in processed_questions_global:
                # 이번 세션에서 이미 등록한 문항 - 다시 조회
                existing_q = pd.read_sql("SELECT question_id FROM questions WHERE question_text = ?", conn, params=(question_text,))
                q_id = existing_q.iloc[0]['question_id']
            else:
                # 새 question_id 생성
                max_id = pd.read_sql("SELECT MAX(CAST(SUBSTR(question_id, 3) AS INTEGER)) as max_id FROM questions", conn)
                next_num = (max_id.iloc[0]['max_id'] or 0) + 1
                q_id = f'Q_{next_num:05d}'

                # questions 테이블에 등록
                legacy_mid = row.get('category_1')
                legacy_sub = row.get('category_2')
                question_type = row.get('question_type', 'LIKERT')
                scale_min = row.get('scale_min', 1)
                scale_max = row.get('scale_max', 5)
                is_reverse = 1 if row.get('is_reverse', False) else 0

                cursor.execute("""
                    INSERT INTO questions (question_id, question_text, diagnosis_type, source_survey_id, source_year,
                                           question_type, scale_min, scale_max, is_reverse,
                                           legacy_mid_category, legacy_sub_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (q_id, question_text, diagnosis_type_ma, survey_id_ma, survey_year,
                      question_type.upper() if question_type else 'LIKERT', scale_min, scale_max, is_reverse,
                      legacy_mid, legacy_sub))
                conn.commit()  # 즉시 커밋하여 다음 조회에서 찾을 수 있게
                new_questions_ma += 1
                processed_questions_global.add(question_text)

            # survey_questions 연결
            is_required = 1 if row.get('is_required', True) else 0
            scale_type = row.get('question_type', 'likert_5')
            section_name = row.get('분류', sheet_name)

            cursor.execute("""
                INSERT INTO survey_questions (survey_id, question_id, question_order, is_required, scale_type, section_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (survey_id_ma, q_id, idx + 1, is_required, scale_type, section_name))
            linked_questions_ma += 1

        # Survey 테이블에 문항 수 업데이트
        cursor.execute("""
            UPDATE surveys SET question_count = ?
            WHERE survey_id = ?
        """, (linked_questions_ma, survey_id_ma))

        conn.commit()
        print(f'    신규 문항: {new_questions_ma}개, 연결된 문항: {linked_questions_ma}개')
        total_new_questions += new_questions_ma
        total_linked_questions += linked_questions_ma

    print(f'  MA 전체: 신규 문항 {total_new_questions}개, 연결된 문항 {total_linked_questions}개')
    print()

    # =====================================================
    # 3. MA RawData 업로드
    # =====================================================
    print('=== 3. 다면평가(MA) RawData 업로드 ===')

    df_ma_raw = pd.read_excel('ExcelTable/SurveyRawData/IG202512WCPMA_RawData.xlsx', sheet_name='Sheet1')

    # survey_type → survey_id 매핑
    survey_type_mapping = {
        501: 'IG202512WCPMA_LS',
        502: 'IG202512WCPMA_LO',
        503: 'IG202512WCPMA_SS',
        504: 'IG202512WCPMA_SO',
        505: 'IG202512WCPMA_JS',
        506: 'IG202512WCPMA_JO',
    }

    # 기존 MA 응답 데이터 삭제
    for sid in survey_type_mapping.values():
        cursor.execute("DELETE FROM respondents WHERE survey_id = ?", (sid,))

    # 응답 컬럼 식별
    response_cols_ma = [c for c in df_ma_raw.columns if str(c).startswith('r')]

    # 서브타입별 카운트
    subtype_counts = {}

    # 응답자 및 응답 데이터 저장
    for idx, row in df_ma_raw.iterrows():
        survey_type = row.get('survey_type')
        survey_id_ma = survey_type_mapping.get(survey_type)

        if not survey_id_ma:
            continue

        # 카운트
        subtype_counts[survey_id_ma] = subtype_counts.get(survey_id_ma, 0) + 1

        # 응답자 정보 저장 (MA 전용 필드 포함)
        cursor.execute("""
            INSERT INTO respondents (
                survey_id, original_id, gender, age, tenure, experience,
                rank, position, job_group, job_function,
                org_level_1, org_level_2, org_level_3, org_level_4, org_level_5,
                target_info, target_name, target_org, target_position, evaluator_type,
                is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            survey_id_ma,
            str(row.get('ID', '')),
            str(row.get('성별', '')) if pd.notna(row.get('성별')) else None,
            int(row.get('나이')) if pd.notna(row.get('나이')) else None,
            int(row.get('근속연수')) if pd.notna(row.get('근속연수')) else None,
            int(row.get('경력연수')) if pd.notna(row.get('경력연수')) else None,
            str(row.get('직급', '')) if pd.notna(row.get('직급')) else None,
            str(row.get('직책', '')) if pd.notna(row.get('직책')) else None,
            str(row.get('직군', '')) if pd.notna(row.get('직군')) else None,
            str(row.get('직무', '')) if pd.notna(row.get('직무')) else None,
            str(row.get('조직 Lv.1', '')) if pd.notna(row.get('조직 Lv.1')) else None,
            str(row.get('조직 Lv.2', '')) if pd.notna(row.get('조직 Lv.2')) else None,
            str(row.get('조직 Lv.3', '')) if pd.notna(row.get('조직 Lv.3')) else None,
            str(row.get('조직 Lv.4', '')) if pd.notna(row.get('조직 Lv.4')) else None,
            str(row.get('조직 Lv.5', '')) if pd.notna(row.get('조직 Lv.5')) else None,
            str(row.get('피평가자 정보', '')) if pd.notna(row.get('피평가자 정보')) else None,
            str(row.get('피평가자 이름', '')) if pd.notna(row.get('피평가자 이름')) else None,
            str(row.get('피평가자 조직 Lv.1', '')) if pd.notna(row.get('피평가자 조직 Lv.1')) else None,
            str(row.get('피평가자 직책', '')) if pd.notna(row.get('피평가자 직책')) else None,
            str(row.get('평가 유형', '')) if pd.notna(row.get('평가 유형')) else None,
            int(row.get('유효응답여부', 1)) if pd.notna(row.get('유효응답여부')) else 1
        ))
        respondent_id = cursor.lastrowid

        # 응답 데이터 저장
        for col in response_cols_ma:
            val = row.get(col)
            if pd.notna(val):
                cursor.execute("""
                    INSERT INTO responses (respondent_id, question_no, response_value)
                    VALUES (?, ?, ?)
                """, (respondent_id, col, str(val)))

    conn.commit()

    # 서브타입별 응답자 수 업데이트
    for survey_id_ma, count in subtype_counts.items():
        cursor.execute("""
            UPDATE surveys SET actual_respondent_count = ?
            WHERE survey_id = ?
        """, (count, survey_id_ma))

    conn.commit()

    print(f'  MA RawData 업로드 완료:')
    for sid, count in sorted(subtype_counts.items()):
        print(f'    {sid}: {count}명')
    print(f'  MA 전체 응답자: {sum(subtype_counts.values())}명')
    print()

    # =====================================================
    # 4. 결과 확인
    # =====================================================
    print('=== 업로드 결과 ===')
    surveys = pd.read_sql("""
        SELECT survey_id, survey_name, diagnosis_type, question_count, actual_respondent_count
        FROM surveys WHERE company_id = 'WCP'
        ORDER BY survey_id
    """, conn)
    print(surveys.to_string(index=False))
    print()

    # 응답 데이터 통계
    respondent_stats = pd.read_sql("""
        SELECT survey_id, COUNT(*) as respondent_count
        FROM respondents
        WHERE survey_id LIKE 'IG202512WCP%'
        GROUP BY survey_id
        ORDER BY survey_id
    """, conn)
    print('=== 응답 데이터 통계 ===')
    print(respondent_stats.to_string(index=False))
    print()

    response_count = pd.read_sql("""
        SELECT COUNT(*) as cnt FROM responses r
        JOIN respondents rp ON r.respondent_id = rp.respondent_id
        WHERE rp.survey_id LIKE 'IG202512WCP%'
    """, conn).iloc[0]['cnt']
    print(f'  전체 응답 데이터: {response_count}건')
    print()

    # 전체 통계
    total_surveys = pd.read_sql("SELECT COUNT(*) as cnt FROM surveys", conn).iloc[0]['cnt']
    total_questions = pd.read_sql("SELECT COUNT(*) as cnt FROM questions", conn).iloc[0]['cnt']
    total_respondents = pd.read_sql("SELECT COUNT(*) as cnt FROM respondents", conn).iloc[0]['cnt']
    total_responses = pd.read_sql("SELECT COUNT(*) as cnt FROM responses", conn).iloc[0]['cnt']
    print(f'=== MasterDB 전체 통계 ===')
    print(f'  전체 설문 수: {total_surveys}')
    print(f'  전체 문항 수: {total_questions}')
    print(f'  전체 응답자 수: {total_respondents}')
    print(f'  전체 응답 데이터: {total_responses}')

    conn.close()
    print()
    print('=== 업로드 완료 ===')

if __name__ == '__main__':
    main()
