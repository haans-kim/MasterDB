# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**MasterDB**: Ontology-based survey question master database for organizational diagnostics.

- **7,343** unique survey questions from **355** surveys (2006-2025)
- **120+** client companies
- **3,274** master questions (cluster representatives)
- **Phase 1**: SQLite prototype with Claude Code validation

## Current Status

```
Phase 0: Data Cleansing [COMPLETED]
├── 17,556 raw questions → 7,343 unique questions
├── KoSBERT embeddings (768 dimensions)
├── Agglomerative clustering → 3,274 clusters
└── Legacy classification labels attached

Phase 1: Ontology-based MasterDB [IN PROGRESS]
├── SQLite schema design
├── Data migration (pkl → SQLite)
├── Taxonomy construction (~150 terms)
├── Auto-tagging system
└── Claude Code validation
```

## Key Documents

| Document | Description |
|----------|-------------|
| [MasterDB_Implementation_Plan.md](MasterDB_Implementation_Plan.md) | Main implementation plan |
| [docs/database_schema.md](docs/database_schema.md) | Database schema (13 tables) |
| [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) | Reference: ID conventions, patterns |
| [docs/DB_테이블명세서.xlsx](docs/DB_테이블명세서.xlsx) | Reference: Column specifications |

## Database Schema

```
┌─────────────────────────────────────────────────────────┐
│  Operational     │  Questions      │  Ontology          │
├──────────────────┼─────────────────┼────────────────────┤
│  companies (120) │  questions      │  taxonomy (~150)   │
│  surveys (355)   │  (7,343)        │  taxonomy_relations│
│  org_units       │  master_        │  question_tags     │
│  org_unit_surveys│  questions      │  scales            │
│  survey_questions│  (3,274)        │  scale_questions   │
│                  │  embeddings     │                    │
└──────────────────┴─────────────────┴────────────────────┘
```

## Survey Types (대분류)

| Code | Name | Count | Clusters |
|------|------|-------|----------|
| OD | 조직진단 (Organization Diagnosis) | 5,179 | 2,199 |
| LD | 리더십진단 (Leadership Diagnosis) | 1,590 | 697 |
| MA | 다면평가 (Multi-source Assessment) | 364 | 275 |
| DD | 사외이사평가 (Director Diagnosis) | 210 | 103 |

## Technical Stack

- **Database**: SQLite (Phase 1) → PostgreSQL (Phase 2)
- **Embeddings**: KoSBERT (`jhgan/ko-sroberta-multitask`, 768 dimensions)
- **Clustering**: Agglomerative (distance_threshold=0.15, cosine)
- **Language**: Python 3.x
- **Key packages**: pandas, numpy, sentence-transformers, scikit-learn, sqlite3

## Data Assets

| File | Description |
|------|-------------|
| `all_df_hybrid.pkl` | 7,343 questions with metadata |
| `all_embeddings_hybrid.npy` | Embeddings (7343 x 768) |
| `data/Survey Meta Data_251224.xlsx` | Source survey metadata |
| `results/Master_Questions.xlsx` | 3,274 cluster representatives |

## ID Conventions

| Table | Format | Example |
|-------|--------|---------|
| companies | `{CODE}` | `CJG`, `SKH` |
| surveys | `{COMPANY}-{YEAR}-{TYPE}` | `CJG-2024-OD` |
| questions | `Q_{5digits}` | `Q_00001` |
| master_questions | `{TYPE}_{4digits}` | `OD_0001` |

## Ontology Structure

```
THEME (대주제)
└── CONCEPT (핵심 개념)
    └── ASPECT (측정 측면)

Example:
경영전략 (THEME)
├── 비전 (CONCEPT)
│   ├── 이해도 (ASPECT)
│   ├── 공감도 (ASPECT)
│   └── 실천도 (ASPECT)
└── 전략 (CONCEPT)
    ├── 명확성 (ASPECT)
    └── 실행력 (ASPECT)
```

## Project Structure

```
c:\Project\MasterDB\
├── data/                          # Source data
│   └── Survey Meta Data_251224.xlsx
├── docs/                          # Documentation
│   ├── database_schema.md         # DB schema
│   ├── DATABASE_DESIGN.md         # Reference design
│   ├── DB_테이블명세서.xlsx
│   └── meta_data.xlsx
├── src/                           # Source code
│   ├── all_category_clustering.py # Phase 0: Clustering
│   ├── create_verification_excel.py
│   ├── db/                        # [Phase 1] DB modules
│   ├── migration/                 # [Phase 1] Migration scripts
│   └── tagging/                   # [Phase 1] Auto-tagging
├── db/                            # [Phase 1] SQLite database
│   └── masterdb.sqlite
├── results/                       # Output files
├── all_df_hybrid.pkl              # Cached DataFrame
├── all_embeddings_hybrid.npy      # Cached embeddings
├── MasterDB_Implementation_Plan.md
└── CLAUDE.md
```

## Known Issues

- **Hardcoded paths**: Scripts contain `os.chdir('c:/Project/CJ_Culture')` - needs refactoring
- **Encoding**: Some Korean text may have cp949/UTF-8 issues on Windows

## Next Steps (Phase 1)

1. **Step 1**: Create SQLite schema and migrate data
2. **Step 2**: Build initial taxonomy from legacy classifications
3. **Step 3**: Implement auto-tagging system
4. **Step 4**: Validate with Claude Code queries
