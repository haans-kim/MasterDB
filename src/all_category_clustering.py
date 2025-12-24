"""
전체 대분류(OD/LD/MA/DD) Hybrid 클러스터링
"""
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import warnings
warnings.filterwarnings('ignore')

print('=== 전체 대분류(OD/LD/MA/DD) Hybrid 클러스터링 ===\n')

# 1. 원본 데이터 로드
import os
os.chdir('c:/Project/CJ_Culture')
df = pd.read_excel('Survey Meta Data_251215.xlsx', sheet_name='4. Question_Cleansing(7343문항)')
print(f'전체 문항: {len(df)}')

# 2. 확장된 키워드 사전 (전체 대분류용)
category_keywords = {
    # OD
    ('OD', '경영전략', '비전/전략'): ['비전', '전략', '미션', '방향', '목표', '경영', '중장기'],
    ('OD', '조직문화', '조직에너지'): ['에너지', '분위기', '활력', '열정', '사기'],
    ('OD', '조직문화', '핵심가치'): ['핵심가치', '가치', 'Value', '원칙'],
    ('OD', '조직/프로세스', '조직구조'): ['조직구조', 'R&R', '역할', '책임', '부서', '팀'],
    ('OD', '조직/프로세스', '인력운영'): ['업무량', '인력', '업무배분', '워크로드', '인원'],
    ('OD', '조직/프로세스', '업무 프로세스'): ['프로세스', '절차', '업무방식', '효율', '보고', '결재'],
    ('OD', '조직/프로세스', '의사소통'): ['의사소통', '소통', '커뮤니케이션', '협조', '협력', '협업'],
    ('OD', '조직/프로세스', '의사결정'): ['의사결정', '결정', '권한위임', '위임', '자율'],
    ('OD', '조직/프로세스', '업무인프라'): ['인프라', '시스템', '장비', '환경', 'WLB', '워라밸', '근무환경'],
    ('OD', '리더십', '리더행동'): ['리더', '상사', '팀장', '부서장', '임원', '경영진'],
    ('OD', '리더십', '역량발휘'): ['방향제시', '동기부여', '육성', '코칭', '피드백', '멘토'],
    ('OD', '인사제도', '직급/승진제도'): ['승진', '직급', '직책', '직위', '진급', '경력'],
    ('OD', '인사제도', '평가제도'): ['평가', '성과관리', 'KPI', '목표관리', 'MBO'],
    ('OD', '인사제도', '보상제도'): ['보상', '급여', '연봉', '인센티브', '복리후생', '복지', '수당'],
    ('OD', '인사제도', '채용'): ['채용', '인재', '확보', '영입', '이직', '퇴사'],
    ('OD', '인사제도', '교육'): ['교육', '훈련', '연수', '학습', '성장', '역량개발', '자기개발'],
    ('OD', '조직몰입도', '조직몰입도'): ['몰입', '만족', '자부심', 'Pride', '추천', '재직', '이직의향'],
    ('OD', '기타', '윤리'): ['윤리', '컴플라이언스', '준법', '규범', '청렴'],
    ('OD', '기타', '다양성'): ['다양성', '포용', 'DEI', '차별'],
    ('OD', '기타', '고객지향성'): ['고객', '서비스', '품질'],
    # LD
    ('LD', '비전/전략', '비전/전략'): ['비전', '전략', '방향', '목표'],
    ('LD', '리더십 역량', '동기부여'): ['동기부여', '격려', '도전', '실패'],
    ('LD', '리더십 역량', '인재육성'): ['육성', '성장', '기회', '코칭', '피드백'],
    ('LD', '리더십 역량', '변화관리'): ['변화', '트렌드', '혁신', '전환'],
    ('LD', '리더십 역량', '권한위임'): ['위임', '권한', '자율', '신뢰', '인정'],
    ('LD', '리더십 역량', '업무지시'): ['지시', '명확', '업무'],
    ('LD', '리더십 역량', '의사결정'): ['의사결정', '판단', '결정'],
    ('LD', '리더십 역량', '목표관리'): ['목표', '점검', '관리'],
    ('LD', 'Derailment', '자기과신'): ['자기과신', '옳다', '정답'],
    ('LD', 'Derailment', '공격성향'): ['공격', '비난', '화'],
    ('LD', 'Derailment', '냉소적'): ['냉소', '비관', '부정'],
    ('LD', 'Derailment', '자기방어'): ['방어', '변명', '책임전가'],
    ('LD', 'Derailment', '스트레스취약'): ['스트레스', '압박', '불안'],
    ('LD', 'Derailment', '편향적선호'): ['편향', '선호', '특정'],
    ('LD', 'Derailment', '과도한관리'): ['과도', '세세', '통제'],
    ('LD', 'Derailment', '비일관적'): ['비일관', '일관성', '예측'],
    ('LD', '기타', '강점'): ['강점', '장점', '잘하는'],
    ('LD', '기타', '보완점'): ['보완', '개선', '약점'],
    # MA
    ('MA', '성과지향', '성과추구'): ['성과', '목표달성', '업무추진'],
    ('MA', '역량', '업무역량'): ['전문성', '문제해결', '의사결정'],
    ('MA', '역량', '관계역량'): ['소통', '협업', '배려'],
    ('MA', '리더십', '리더역량'): ['동기부여', '육성', '권한위임'],
    ('MA', '고객지향', '고객서비스'): ['고객', '고객만족'],
    ('MA', '변화혁신', '혁신추진'): ['변화', '개선'],
    ('MA', '협업/소통', '협업'): ['정보공유', '갈등해결', '협력'],
    ('MA', '전문성', '전문성'): ['지식', '전문'],
    # DD
    ('DD', '전략적역량', '전략사고'): ['경영전략', '의사결정', '전략'],
    ('DD', '전문성', '전문지식'): ['재무', '이슈', '자격', '전문'],
    ('DD', '이사회참여', '참여도'): ['참여', '적극', '공정', '규정'],
    ('DD', '감독/견제', '경영감독'): ['윤리', '책임', '투명', '감독'],
}

def get_category_tag(row):
    """문항에서 가장 적합한 분류 태그 반환"""
    text = str(row['문항'])
    major = row['대분류']

    matches = []
    for (cat_major, mid, small), keywords in category_keywords.items():
        if cat_major != major:
            continue
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            matches.append((mid, small, score))

    if matches:
        matches.sort(key=lambda x: x[2], reverse=True)
        return f"[{matches[0][0]}] [{matches[0][1]}]"
    return ''

# 3. 분류 태그 적용
print('분류 태그 적용 중...')
df['category_tag'] = df.apply(get_category_tag, axis=1)

# 통계
for cat in ['OD', 'LD', 'MA', 'DD']:
    cat_df = df[df['대분류'] == cat]
    tagged = (cat_df['category_tag'] != '').sum()
    print(f'  {cat}: {len(cat_df)}개 중 {tagged}개 태그됨 ({tagged/len(cat_df)*100:.1f}%)')

# 4. Hybrid 텍스트 생성
df['hybrid_text'] = df.apply(lambda x: f"{x['문항']} {x['category_tag']}", axis=1)

# 5. KoSBERT 임베딩
print('\nKoSBERT 임베딩 생성 중...')
model = SentenceTransformer('jhgan/ko-sroberta-multitask')
embeddings = model.encode(df['hybrid_text'].tolist(), show_progress_bar=True)
print(f'임베딩 shape: {embeddings.shape}')

# 6. 대분류별 클러스터링
print('\n대분류별 클러스터링...')
df['cluster_id'] = -1

for cat in ['OD', 'LD', 'MA', 'DD']:
    cat_mask = df['대분류'] == cat
    cat_indices = df[cat_mask].index.tolist()
    cat_embeddings = embeddings[cat_mask]

    # Agglomerative Clustering
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0.15,
        metric='cosine',
        linkage='average'
    )
    labels = clustering.fit_predict(cat_embeddings)

    # 클러스터 ID에 대분류 prefix 추가
    for i, idx in enumerate(cat_indices):
        df.loc[idx, 'cluster_id'] = labels[i]

    cluster_sizes = Counter(labels)
    print(f'  {cat}: {len(cluster_sizes)}개 클러스터, 평균 {np.mean(list(cluster_sizes.values())):.2f}개')

# 7. 저장
print('\n저장 중...')
np.save('all_embeddings_hybrid.npy', embeddings)
df.to_pickle('all_df_hybrid.pkl')
df.to_excel('results/전체_문항_클러스터링_Hybrid.xlsx', index=False)
print('저장 완료')
