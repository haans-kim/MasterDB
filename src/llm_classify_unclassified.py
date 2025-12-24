"""
Claude API를 사용하여 미분류 문항 분류
"""
import pandas as pd
import anthropic
import json
import time
import os

os.chdir('c:/Project/CJ_Culture')

# API 키 설정 (환경변수에서 로드)
API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

client = anthropic.Anthropic(api_key=API_KEY)

# 분류 체계 정의
CLASSIFICATION_SYSTEM = """
당신은 설문 문항을 분류하는 전문가입니다.
주어진 문항을 아래 분류 체계에 따라 가장 적합한 중분류와 소분류로 분류해주세요.

## 분류 체계

### 1. 리더십
- 목표/전략: 비전, 목표 설정, 전략 수립, 방향 제시
- 경영전반: 경영, 운영, 관리 전반
- 권한위임: 권한, 위임, 자율성, 책임 부여
- 코칭/육성: 육성, 코칭, 피드백, 성장 지원
- 조직관리: 조직, 팀, 부서 관리
- 업무지시: 업무 지시, 배분, 할당
- 소통/경청: 소통, 대화, 경청, 커뮤니케이션
- 의사결정: 결정, 판단, 의사결정
- 위기/갈등: 위기, 갈등, 문제 상황 대응
- 신뢰: 신뢰, 믿음
- 공정성: 공정, 공평, 형평성
- 의견개진: 의견 제시, 제안
- 변화/혁신: 변화, 혁신, 개선
- 리더십일반: 리더십 전반

### 2. 조직문화
- 가치/비전워크: 핵심가치, 비전, 미션
- 신뢰/존중: 신뢰, 존중, 배려
- 근무환경: 근무 환경, 복지
- 조직문화일반: 조직문화 전반

### 3. 조직/프로세스
- 부서간협력: 부서간 협력, 협업
- 업무/프로세스: 업무 프로세스, 절차
- 업무효율성: 효율, 생산성
- 권한/책임: 권한, 책임, 역할
- 의사결정: 조직 의사결정 프로세스
- 의사소통: 조직 내 소통
- 조직프로세스일반: 조직/프로세스 전반

### 4. 인사제도
- 보상급여: 급여, 보상, 성과급
- 평가제도: 평가, 성과관리
- 교육/경력개발: 교육, 훈련, 경력개발
- 인력확보배치: 채용, 배치
- 승진/이동: 승진, 이동, 경력경로
- 인사일반: 인사제도 전반

### 5. 몰입도
- 조직몰입도: 몰입, 충성도, 소속감

### 6. 경영/전략
- 경영일반: 경영 전반
- 성과및성장: 성과, 성장, 실적
- 목표/KPI: 목표, KPI, 지표

### 7. 기타
- 고객지향: 고객, 서비스
- 윤리경영: 윤리, 준법
- 다양성: 다양성, 포용
- 안전: 안전, 보건
- 워라밸행복: 일과 삶의 균형
- 갈등관리: 갈등, 분쟁

## 응답 형식
반드시 아래 JSON 형식으로만 응답하세요:
{"중분류": "분류명", "소분류": "소분류명"}
"""

def classify_question(question):
    """단일 문항 분류"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": f"다음 설문 문항을 분류해주세요:\n\n{question}"}
            ],
            system=CLASSIFICATION_SYSTEM
        )

        response_text = message.content[0].text.strip()

        # JSON 파싱
        if '{' in response_text:
            json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
            result = json.loads(json_str)
            return result.get('중분류', '미분류'), result.get('소분류', '미분류')

        return '미분류', '미분류'

    except Exception as e:
        print(f"  에러: {e}")
        return '미분류', '미분류'

def classify_batch(questions, batch_size=10):
    """배치 분류 (여러 문항을 한 번에)"""
    prompt = "다음 설문 문항들을 각각 분류해주세요. 각 문항에 대해 JSON 형식으로 응답해주세요:\n\n"
    for i, q in enumerate(questions):
        prompt += f"{i+1}. {q}\n"

    prompt += "\n응답 형식 (각 문항별로):\n1. {\"중분류\": \"...\", \"소분류\": \"...\"}\n2. {\"중분류\": \"...\", \"소분류\": \"...\"}\n..."

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system=CLASSIFICATION_SYSTEM
        )

        response_text = message.content[0].text.strip()

        # 각 라인에서 JSON 추출
        results = []
        lines = response_text.split('\n')
        for line in lines:
            if '{' in line and '}' in line:
                try:
                    json_str = line[line.find('{'):line.rfind('}')+1]
                    result = json.loads(json_str)
                    results.append((result.get('중분류', '미분류'), result.get('소분류', '미분류')))
                except:
                    pass

        # 결과가 부족하면 미분류로 채우기
        while len(results) < len(questions):
            results.append(('미분류', '미분류'))

        return results[:len(questions)]

    except Exception as e:
        print(f"  배치 에러: {e}")
        return [('미분류', '미분류')] * len(questions)

# 메인 실행
if __name__ == "__main__":
    print("=== Claude API 미분류 문항 분류 ===\n")

    # 데이터 로드
    df = pd.read_pickle('all_df_hybrid.pkl')
    unclassified_mask = df['중분류'] == '미분류'
    unclassified_df = df[unclassified_mask].copy()

    print(f"미분류 문항: {len(unclassified_df)}개")

    # 배치 처리
    batch_size = 10
    total = len(unclassified_df)

    new_mid = []
    new_small = []

    for i in range(0, total, batch_size):
        batch = unclassified_df.iloc[i:i+batch_size]['문항'].tolist()
        print(f"처리 중: {i+1}-{min(i+batch_size, total)} / {total}")

        results = classify_batch(batch)

        for mid, small in results:
            new_mid.append(mid)
            new_small.append(small)

        # Rate limit 방지
        time.sleep(1)

    # 결과 적용
    unclassified_indices = unclassified_df.index.tolist()
    for idx, (mid, small) in zip(unclassified_indices, zip(new_mid, new_small)):
        if mid != '미분류':
            df.loc[idx, '중분류'] = mid
        if small != '미분류':
            df.loc[idx, '소분류'] = small

    # 결과 저장
    df.to_pickle('all_df_hybrid.pkl')

    # 통계
    remaining_unclassified = (df['중분류'] == '미분류').sum()
    newly_classified = total - remaining_unclassified + (df.loc[unclassified_indices, '중분류'] != '미분류').sum() - len(unclassified_indices)

    print(f"\n=== 분류 완료 ===")
    print(f"LLM 분류 시도: {total}개")
    print(f"새로 분류됨: {len([m for m in new_mid if m != '미분류'])}개")
    print(f"남은 미분류: {remaining_unclassified}개")

    print(f"\n중분류 분포:")
    print(df['중분류'].value_counts())
