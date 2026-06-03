# GradCareer-CommentAnalysis

## Project Goal
Chinese NLP analysis platform for Bilibili comments on graduate school discussions. Transforms raw comments into sentiment analysis, topic modeling, keyword networks, and trend insights via a FastAPI backend + Vue3 frontend. The platform specializes in Applied Statistics (应用统计学) graduate school entrance exam (考研) comment analysis, supporting students in understanding public sentiment, hot topics, and decision-making trends around graduate education choices.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy (async), SQLite (aiosqlite), Pydantic v2, Pydantic Settings
- **NLP**: jieba, SnowNLP, scikit-learn, Gensim (LDA), BERTopic, networkx
- **Frontend**: Vue3, Vite, TypeScript, Element Plus, ECharts, Pinia
- **Infrastructure**: Docker, docker-compose, GitHub Actions

## Architecture

### Backend Layer Map
```
backend/app/
├── api/          # FastAPI route handlers (thin: validate → call service → return JSON)
├── services/     # Business logic layer (NLP pipeline, analysis, persistence)
├── models/       # SQLAlchemy ORM models (comments, keywords, topics, sentiment, network)
├── schemas/      # Pydantic request/response models
└── utils/        # Chinese text helpers, NLPResources singleton
```

### Frontend Layer Map
```
frontend/src/
├── views/            # 7 pages: Dashboard, Sentiment, Topics, TopicSentiment, Trends, Network, Predict
├── stores/           # 8 Pinia stores (one per page + shared)
├── components/charts/ # 8 ECharts components
├── api/              # Axios client and API modules
├── router/           # Vue Router configuration
└── types/            # TypeScript type definitions
```

### Data Flow
```
CSV → DataLoaderService → SQLite → API → Axios → Pinia → ECharts
```

## Agent Responsibilities

- **Backend Agent**: FastAPI app, SQLAlchemy models, API routes, service layer, data import
- **Frontend Agent**: Vue3 scaffold, router, pages, Pinia stores, API client
- **NLP Agent**: Bug fixes, BERTopic integration, TopicSentiment, Trend, Predictor services
- **Visualization Agent**: ECharts chart components (8 total), responsive resize handling
- **QA Agent**: pytest tests (unit + API integration), coverage >80%
- **Documentation Agent**: README, CLAUDE.md, API docs, data dictionary

## Development Guidelines

### Code Style
- Use `async/await` for all FastAPI endpoints and service methods
- Chinese comments for business logic, English for technical code
- `pathlib.Path` for all file operations
- Pydantic v2 style (`model_validate`, `model_dump`)
- Type hints on all function signatures
- Ruff line-length: 100

### Known Bugs to Avoid
- Chinese `\b` regex: use direct `str.replace()` instead of regex word boundaries
- TF-IDF leakage: use `Pipeline` to prevent train-test contamination
- WordCloud frequency: use `generate_from_frequencies()` with frequency dict, not `generate_from_text()`
- Time column discard: read ALL CSV columns explicitly, do not drop time-related columns

### Testing
- Run `pytest` before committing
- Minimum 80% test coverage
- Use `pytest-asyncio` for async tests with `asyncio_mode = "auto"`
- Integration tests against an in-memory SQLite database

### Project Conventions
- Database migrations managed by Alembic
- Environment variables via Pydantic Settings with `GC_` prefix
- API versioning: `/api/v1/` prefix on all routes
- CSV data sources in `backend/data/`, generated artifacts in `outputs/`
- Frontend dev server on port 5173, backend on port 8000
