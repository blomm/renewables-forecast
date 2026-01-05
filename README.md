# Renewables Forecast

AI-powered renewable energy forecasting system for UK residential solar PV and wind turbine installations.

## Overview

This system estimates annual energy generation potential based on postcode location, using climate normals and deterministic calculations. It provides transparent, explainable results through RAG-based AI explanations.

### Key Features

- **Scientifically Grounded**: Uses climate normals from NASA POWER and Global Wind Atlas
- **Deterministic Calculations**: Industry-standard formulas via `pvlib` and `windpowerlib`
- **AI Explanations**: RAG system provides transparent reasoning about estimates
- **Learning System**: Gradually improves regional accuracy from user feedback
- **UK-Focused**: Optimized for UK postcodes and climate patterns

### MVP Scope

**Core Promise**: "Enter your postcode and system type, get a credible annual energy estimate with an explanation you can interrogate."

What we build (MVP):
- ✅ Postcode to lat/lon conversion
- ✅ Climate data retrieval (NASA POWER, Global Wind Atlas)
- ✅ Energy calculations (solar PV and wind turbines)
- ✅ RAG-based explanations (OpenAI GPT-4o)
- ✅ User feedback collection for learning

What we don't build (yet):
- ❌ Real-time weather data ingestion
- ❌ Custom ML model training
- ❌ Microclimate modeling
- ❌ Commercial-scale systems

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 with pgvector extension
- **ORM**: SQLAlchemy 2.0 + Alembic migrations
- **Calculations**: pvlib (solar), windpowerlib (wind)
- **AI/RAG**: OpenAI GPT-4o + text-embedding-3-small
- **External APIs**: Postcodes.io, NASA POWER

### Frontend (Planned)
- **Framework**: Next.js 14+ with TypeScript
- **UI**: React 18+ with TailwindCSS
- **State**: React Query

## Project Structure

```
renewables-forecast/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes (to be built)
│   │   ├── calculators/    # Solar/wind calculations (to be built)
│   │   ├── core/           # Configuration ✅
│   │   ├── db/             # Database session ✅
│   │   ├── models/         # SQLAlchemy models ✅
│   │   ├── schemas/        # Pydantic schemas (to be built)
│   │   ├── services/       # Business logic (to be built)
│   │   └── main.py         # FastAPI app ✅
│   ├── alembic/            # Database migrations ✅
│   └── requirements.txt    # Python dependencies ✅
├── specs/                  # Detailed specifications ✅
└── docker-compose.yml      # PostgreSQL + pgvector ✅
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop
- OpenAI API key

### 1. Start Database

```bash
docker-compose up -d
```

### 2. Set Up Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start API Server

```bash
uvicorn app.main:app --reload
```

API will be available at:
- Root: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health

## Development Status

### ✅ Completed
- Project structure and specifications
- Docker Compose with PostgreSQL + pgvector
- SQLAlchemy models (calculations, feedback, regional_factors, rag_documents)
- Alembic migrations
- FastAPI application skeleton
- Configuration management

### 🚧 In Progress
- Solar PV calculator (pvlib)
- Wind turbine calculator (windpowerlib)
- API endpoints (`/api/calculate`, `/api/explain`, `/api/feedback`)
- External API integrations (Postcodes.io, NASA POWER)
- RAG system (OpenAI + pgvector)

### 📋 Planned
- Pydantic request/response schemas
- Unit and integration tests
- Frontend (Next.js)
- Deployment configuration
- Documentation site

## API Documentation

Once running, visit http://localhost:8000/api/v1/docs for interactive Swagger documentation.

### Planned Endpoints

- `POST /api/v1/calculate` - Calculate energy estimate
- `POST /api/v1/explain` - Ask follow-up questions
- `POST /api/v1/feedback` - Submit actual performance data
- `GET /api/v1/calculation/{id}` - Retrieve past calculation
- `GET /api/v1/regions` - Regional statistics

## Database Schema

### Tables

- **calculations** - Energy generation estimates
- **feedback** - User-submitted actual performance
- **regional_factors** - Learned regional corrections
- **rag_documents** - Context documents with vector embeddings

See [specs/data_models.md](specs/data_models.md) for detailed schema.

## Design Principles

1. **Climate Normals Over History**: Use 20-30 year averages instead of raw time-series
2. **AI for Explanation, Not Prediction**: RAG explains results; deterministic models predict
3. **Gradual Learning**: Statistical adjustments from feedback, not immediate ML retraining
4. **Transparency**: Users can interrogate assumptions and understand calculations
5. **Scientifically Defensible**: Follow established renewable energy assessment methods

## Contributing

This is an early-stage project. Contributions, feedback, and suggestions are welcome!

### Development

```bash
# Format code
black app/

# Lint
ruff check app/

# Type check
mypy app/

# Run tests (when available)
pytest
```

## Documentation

- [Setup Guide](SETUP_COMPLETE.md) - Detailed setup walkthrough
- [System Overview](specs/system_overview.md) - Project goals and scope
- [Architecture](specs/architecture.md) - Technical architecture
- [Data Models](specs/data_models.md) - Database schema
- [API Contracts](specs/api_contracts.md) - API specification

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Climate data from [NASA POWER](https://power.larc.nasa.gov/)
- Wind data from [Global Wind Atlas](https://globalwindatlas.info/)
- Postcode lookup via [Postcodes.io](https://postcodes.io/)
- Solar calculations using [pvlib](https://pvlib-python.readthedocs.io/)
- Wind calculations using [windpowerlib](https://windpowerlib.readthedocs.io/)

---

**Status**: 🚧 In Development - Backend foundation complete, calculation logic in progress

Built with [Claude Code](https://claude.com/claude-code)
