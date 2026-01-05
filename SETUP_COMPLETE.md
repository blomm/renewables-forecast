# ✅ Setup Complete!

Your renewable energy forecasting backend is now running!

## What's Running

### 1. PostgreSQL Database (Docker)
- **Port**: 5433
- **Database**: renewables_forecast
- **Username**: renewables
- **Password**: renewables_dev
- **Extensions**: pgvector (for vector embeddings)

**Tables Created**:
- `calculations` - Stores energy generation estimates
- `feedback` - Stores user-submitted actual performance data
- `regional_factors` - Stores learned regional correction factors
- `rag_documents` - Stores context documents with embeddings for RAG

### 2. FastAPI Server
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/health

## Quick Start Guide

### View API Documentation
Open in your browser:
```
http://localhost:8000/api/v1/docs
```

This shows interactive API documentation where you can test endpoints.

### Stop/Start Services

**Stop the API server**:
```bash
# Press Ctrl+C in the terminal where uvicorn is running
# Or find and kill the process
```

**Stop the database**:
```bash
docker-compose down
```

**Start everything again**:
```bash
# Start database
docker-compose up -d

# Start API server
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## Project Structure Explained

```
backend/
├── app/
│   ├── api/              # API routes (endpoints) - EMPTY (ready for you to build)
│   ├── calculators/      # Solar/wind calculation logic - EMPTY (next step!)
│   ├── core/
│   │   └── config.py     # Configuration (reads from .env)
│   ├── db/
│   │   ├── session.py    # Database connection
│   │   └── init.sql      # pgvector initialization
│   ├── models/           # Database models (SQLAlchemy) ✅
│   │   ├── calculation.py       # Calculation records
│   │   ├── feedback.py          # User feedback
│   │   ├── regional_factor.py   # Regional corrections
│   │   └── rag_document.py      # RAG context docs
│   ├── schemas/          # Request/Response schemas (Pydantic) - EMPTY
│   ├── services/         # Business logic - EMPTY (postcode, climate, RAG)
│   └── main.py           # FastAPI app entry point ✅
├── alembic/              # Database migrations ✅
├── requirements.txt      # Python dependencies ✅
└── .env                  # Your environment variables ✅
```

## What We've Built So Far

### ✅ Completed
1. **Docker Compose** - PostgreSQL with pgvector running on port 5433
2. **Database Schema** - All 4 tables created and ready
3. **FastAPI App** - Basic app structure with CORS, health check
4. **SQLAlchemy Models** - Database models for calculations, feedback, etc.
5. **Configuration** - Settings loaded from .env file
6. **Migrations** - Alembic configured and initial migration applied

### 🚧 What's Next (Not Yet Built)
1. **API Endpoints** - `/api/calculate`, `/api/explain`, `/api/feedback`
2. **Calculation Logic** - Solar PV and wind turbine calculators
3. **External API Services** - Postcode lookup, NASA POWER, etc.
4. **RAG System** - OpenAI integration for explanations
5. **Pydantic Schemas** - Request/response validation
6. **Tests** - Unit and integration tests

## Understanding the Key Concepts

### SQLAlchemy Models (What You're Looking At)

The file you have open (`calculation.py`) defines the **database table structure** for calculations.

```python
class Calculation(Base):
    """Energy generation calculation record."""

    __tablename__ = "calculations"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Location
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    region = Column(String(50))

    # System specification (flexible JSON)
    system_type = Column(String(10), nullable=False)  # 'solar' or 'wind'
    system_specs = Column(JSONB, nullable=False)      # Stores panel tilt, capacity, etc.

    # Results
    annual_energy_kwh = Column(Numeric(10, 2), nullable=False)
    monthly_energy_kwh = Column(ARRAY(Numeric(10, 2)))

    # ... etc
```

**Key Features**:
- **UUID primary keys** - Unique IDs for each record
- **JSONB columns** - Flexible JSON storage (system_specs, climate_data, assumptions)
- **Timestamps** - Automatically track when records are created
- **Arrays** - Store 12 monthly values
- **Relationships** - `feedback` table links back to calculations

### How Data Flows

```
1. User Request
   POST /api/calculate
   { postcode: "SW1A 1AA", system_type: "solar", ... }

2. Postcode → Lat/Lon
   Call Postcodes.io API

3. Lat/Lon → Climate Data
   Call NASA POWER API for solar irradiance

4. Calculate Energy Output
   Use pvlib to calculate expected kWh/year

5. Store in Database
   Save to calculations table

6. Generate Explanation (RAG)
   Query vector DB for relevant context
   Ask OpenAI to generate explanation

7. Return Response
   { calculation_id, results, explanation }
```

### Environment Variables (.env)

Your `.env` file controls configuration:
```bash
DATABASE_URL=postgresql+asyncpg://renewables:renewables_dev@localhost:5433/renewables_forecast
OPENAI_API_KEY=your-key-here  # 👈 Add your OpenAI key here when ready
DEBUG=true
```

The `config.py` file reads these values:
```python
settings = get_settings()  # Loads from .env
print(settings.database_url)  # Access the values
```

## Common Commands

### Database Management

**Connect to database**:
```bash
docker exec -it renewables-postgres psql -U renewables -d renewables_forecast
```

**Run migrations after model changes**:
```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

**Rollback migration**:
```bash
alembic downgrade -1
```

### Development

**Format code**:
```bash
black app/
```

**Lint code**:
```bash
ruff check app/
```

**Type check**:
```bash
mypy app/
```

**Run tests** (when we add them):
```bash
pytest
```

## Next Steps

Now that the foundation is set up, we can start building the actual functionality:

1. **Build the Solar Calculator** - Implement `pvlib` calculations
2. **Create API Endpoints** - `/api/calculate` endpoint
3. **Integrate External APIs** - Postcode lookup, climate data
4. **Add RAG System** - OpenAI integration for explanations
5. **Build Frontend** - Next.js app to consume the API

## Troubleshooting

**Port 5433 already in use**:
```bash
docker ps  # Find conflicting container
docker stop <container-id>
```

**Database connection errors**:
```bash
# Check database is running
docker ps | grep renewables-postgres

# Restart if needed
docker-compose restart
```

**Module import errors**:
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall if needed
pip install -r requirements.txt
```

**Migration errors**:
```bash
# Check current migration state
alembic current

# See migration history
alembic history

# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/en/20/
- **Alembic Docs**: https://alembic.sqlalchemy.org
- **pvlib Docs**: https://pvlib-python.readthedocs.io
- **pgvector Docs**: https://github.com/pgvector/pgvector

---

**Status**: ✅ Backend is running and ready for development!

**What's working**: Database, API server, health checks, database models
**What's next**: Build calculation logic and API endpoints
