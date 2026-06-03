# Legacy Code Archive

This directory contains the original flat-script implementation of the GradCareer-CommentAnalysis project, preserved for reference and comparison testing.

## Migration Map

| Original File | Migrated To | Status |
|--------------|-------------|--------|
| `main.py` | `backend/app/main.py` + `scripts/seed_db.py` | Migrated |
| `config.py` | `backend/app/config.py` | Migrated |
| `data_cleaner.py` | `backend/app/services/cleaner.py` + `backend/app/services/data_loader.py` | Migrated |
| `text_analyzer.py` | `backend/app/services/keyword.py` (data) + `frontend/src/components/charts/` (rendering) | Migrated |
| `sentiment_analyzer.py` | `backend/app/services/sentiment.py` | Migrated |
| `cluster_classifier.py` | Replaced by `KBinsDiscretizer` in sentiment service | Deprecated |
| `lda_modeler.py` | `backend/app/services/topic.py` | Migrated |
| `utils.py` | `backend/app/utils/` | Migrated |

## Bug Fixes Applied in Migration

1. **Wordcloud frequency bug**: `text_analyzer.py:25` — Was ignoring word frequencies. Fixed by using `generate_from_frequencies()` or frontend rendering.
2. **TF-IDF data leakage**: `sentiment_analyzer.py:34` — Global fit_transform before CV. Fixed by using sklearn `Pipeline`.
3. **Chinese `\b` regex bug**: `data_cleaner.py:50` — `\b` doesn't work for Chinese. Fixed with direct `str.replace`.
4. **1D clustering**: `cluster_classifier.py:24` — KMeans on single feature. Replaced with `KBinsDiscretizer`.
5. **Time column discard**: `data_cleaner.py:74` — `usecols=["content"]` dropped all metadata. Fixed by reading all columns.
6. **temp.csv race condition**: `data_cleaner.py:71` — Fixed by reading CSV directly with detected encoding.

## Original Data Flow

```
CSV → DataCleaner → TextAnalyzer → SentimentAnalyzer → ClusterClassifier → LDAModeler
```

All stages mutated the same DataFrame in-place, creating implicit temporal coupling.
The new architecture persists each stage's output to SQLite, enabling independent API access.
