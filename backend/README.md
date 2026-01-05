# Renewables Forecast Backend

FastAPI backend for renewable energy generation forecasting.

## Setup

### Prerequisites

- Python 3.11+
- Docker Desktop (running)
- Poetry or pip

### 1. Start PostgreSQL with pgvector

```bash
# From project root
docker-compose up -d
```

This starts PostgreSQL with the pgvector extension on port 5432.

### 2. Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

### 5. Initialize Database

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Run migrations
alembic upgrade head
```

### 6. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:
- Main API: http://localhost:8000
- Swagger docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes
│   ├── calculators/      # Solar/wind calculation logic
│   ├── core/             # Config, security, dependencies
│   ├── db/               # Database session management
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic (postcode, climate, RAG)
│   └── main.py           # FastAPI app entry point
├── alembic/              # Database migrations
├── tests/                # Tests
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (gitignored)
```

## Database

PostgreSQL with pgvector extension running in Docker.

**Connection details:**
- Host: localhost
- Port: 5433 (to avoid conflict with other local Postgres)
- Database: renewables_forecast
- User: renewables
- Password: renewables_dev

**Access psql:**
```bash
docker exec -it renewables-postgres psql -U renewables -d renewables_forecast
```

## Development

### Run Tests
```bash
pytest
```

### Format Code
```bash
black app/
```

### Lint
```bash
ruff check app/
```

### Type Check
```bash
mypy app/
```

## API Documentation

Once the server is running, visit http://localhost:8000/api/v1/docs for interactive API documentation.
