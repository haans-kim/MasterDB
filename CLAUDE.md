# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Survey Question Analysis & Master Database project for organizational diagnostics. Clusters and classifies ~7,343 Korean survey questions from 355 surveys (2006-2025) across 120+ client companies into a master question database.

**Survey Types (대분류)**:
- OD (조직진단): Organization Diagnosis - 70.5%
- LD (리더십진단): Leadership Diagnosis - 21.7%
- MA (다면평가): Multi-source Assessment - 5.0%
- DD (사외이사평가): Director Diagnosis - 2.9%

## Running the Pipeline

Scripts must be run in this order:

```bash
# 1. Main clustering pipeline - generates embeddings and clusters
python src/all_category_clustering.py

# 2. Generate verification Excel reports
python src/create_verification_excel.py

# 3. LLM classification for remaining unclassified items (requires ANTHROPIC_API_KEY)
python src/llm_classify_unclassified.py
```

**Environment Setup**:
- Set `ANTHROPIC_API_KEY` environment variable for LLM classification step
- Required packages: pandas, numpy, sentence-transformers, scikit-learn, openpyxl, anthropic

## Architecture

### Data Flow

```
data/Survey Meta Data_251224.xlsx
    ↓
[all_category_clustering.py]
  - Applies keyword-based category tags (~79% coverage)
  - Generates KoSBERT embeddings (jhgan/ko-sroberta-multitask, 768 dimensions)
  - Performs Agglomerative Clustering (distance_threshold=0.15)
    ↓
all_df_hybrid.pkl + all_embeddings_hybrid.npy
    ↓
[create_verification_excel.py]
  - Generates 4-sheet Excel workbook for validation
    ↓
results/*.xlsx
    ↓
[llm_classify_unclassified.py]
  - Uses Claude API for unclassified items (batch of 10, 1s rate limit)
    ↓
100% classified dataset
```

### Key Technical Decisions

- **Hybrid Embedding**: Combines survey text with classification tags (e.g., `[경영전략] [비전/전략]`) before embedding to improve clustering quality
- **KoSBERT over TF-IDF**: TF-IDF failed to distinguish semantic meaning (e.g., "비전 이해" vs "비전 적절성" clustered together due to shared keywords like "방식", "존재")
- **Agglomerative Clustering**: Preferred over K-means for variable cluster sizes and semantic coherence
- **Centroid-based Representative Selection**: Each cluster's representative question (Question Key) is the item closest to cluster centroid

### Classification Hierarchy

```
대분류 (Major Category: OD/LD/MA/DD)
  └── 중분류 (Mid Category: e.g., 경영전략, 리더십, 인사제도)
      └── 소분류 (Sub Category: e.g., 비전/전략, 동기부여)
```

## Known Issues

**Hardcoded paths**: All Python scripts contain `os.chdir('c:/Project/CJ_Culture')` pointing to a different directory. This should be refactored to relative paths.

## Output Files

| File | Description |
|------|-------------|
| `results/Master_Questions.xlsx` | 3,274 representative questions with Question Keys |
| `results/전체_문항_클러스터링_Hybrid.xlsx` | Full clustering results |
| `results/전체_분류체계_검증용.xlsx` | 4-sheet verification workbook |
| `all_df_hybrid.pkl` | Cached DataFrame with classifications |
| `all_embeddings_hybrid.npy` | Cached embeddings (7343 x 768) |
