# Architecture Guide - How Everything Connects

## 🔄 Request Flow (Future)

Here's how a request will flow through the system once we build the API endpoints:

```
1. User Request
   ↓
   POST http://localhost:8000/api/v1/calculate
   {
     "postcode": "SW1A 1AA",
     "system_type": "solar",
     "system_specs": {"capacity_kwp": 4.0}
   }

2. FastAPI (main.py)
   ↓
   Route to calculate endpoint (api/v1/calculate.py)

3. Postcode Service
   ↓
   Call Postcodes.io API
   → Get lat/lon: 51.501009, -0.141588

4. Climate Service
   ↓
   Call NASA POWER API for solar irradiance
   → Get climate normals (monthly GHI values)

5. Solar Calculator (calculators/solar.py)
   ↓
   Use pvlib to calculate:
   - Optimal tilt angle for latitude
   - Annual energy output
   - Monthly breakdown
   → Result: 3,456 kWh/year

6. Database (models/calculation.py)
   ↓
   Save calculation to PostgreSQL
   → Return calculation_id

7. RAG Service
   ↓
   a. Convert assumptions to embedding (OpenAI)
   b. Query rag_documents table (pgvector similarity search)
   c. Retrieve relevant context documents
   d. Send to GPT-4o with context
   → Generate explanation

8. Response
   ↓
   {
     "calculation_id": "uuid-here",
     "location": {...},
     "results": {
       "annual_energy_kwh": 3456,
       "monthly_energy_kwh": [...]
     },
     "explanation": {
       "summary": "Your 4.0 kWp system...",
       "assumptions": [...],
       "regional_context": "..."
     }
   }
```

## 📦 File Dependency Map

```
main.py (Entry Point)
├── core/config.py (Settings)
│   └── .env (Environment Variables)
│
├── db/session.py (Database Connection)
│   ├── core/config.py (DATABASE_URL)
│   └── models/*.py (Table Definitions)
│
└── api/v1/ (Future - API Routes)
    ├── calculate.py
    │   ├── services/postcode.py (Postcode → Lat/Lon)
    │   ├── services/climate.py (Lat/Lon → Climate Data)
    │   ├── calculators/solar.py (Climate → Energy)
    │   ├── models/calculation.py (Save to DB)
    │   └── services/rag.py (Generate Explanation)
    │
    ├── explain.py
    │   ├── models/calculation.py (Load from DB)
    │   └── services/rag.py (Answer Question)
    │
    └── feedback.py
        ├── models/feedback.py (Save Feedback)
        └── models/regional_factor.py (Update Stats)
```

## 🎯 Key Components Explained

### 1. **Configuration Layer**

```python
# backend/.env
DATABASE_URL=postgresql+asyncpg://renewables:renewables_dev@localhost:5433/renewables_forecast
OPENAI_API_KEY=sk-...

# app/core/config.py
settings = get_settings()
# Reads .env and provides typed access:
settings.database_url
settings.openai_api_key
```

**Purpose**: Single source of truth for configuration. Change `.env` to switch between dev/staging/production.

---

### 2. **Database Layer**

```python
# app/db/session.py
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

**Purpose**: Manages database connections. Automatically handles connection pooling and cleanup.

---

### 3. **Model Layer (ORM)**

```python
# app/models/calculation.py
class Calculation(Base):
    __tablename__ = "calculations"
    id = Column(UUID, primary_key=True)
    annual_energy_kwh = Column(Numeric(10, 2))
    # ...
```

**Purpose**: Python classes that map to database tables. SQLAlchemy translates Python operations to SQL.

**How you'll use it**:
```python
# Create
calc = Calculation(annual_energy_kwh=3456.78, ...)
db.add(calc)
await db.commit()

# Read
calc = await db.get(Calculation, calculation_id)

# Update
calc.annual_energy_kwh = 3500.00
await db.commit()

# Delete
await db.delete(calc)
await db.commit()
```

---

### 4. **Migration Layer (Alembic)**

```
alembic/versions/
└── abaf779661aa_initial_migration.py
    ↓
Creates: calculations, feedback, regional_factors, rag_documents tables
```

**Purpose**: Track database schema changes over time. Like Git commits for your database structure.

**Common commands**:
```bash
# Create migration after changing models
alembic revision --autogenerate -m "Add email column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# See history
alembic history
```

---

### 5. **API Layer (Future)**

```python
# app/api/v1/calculate.py (to be built)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/calculate")
async def calculate_energy(
    request: CalculationRequest,  # Pydantic validation
    db: AsyncSession = Depends(get_db)  # Database session
):
    # 1. Validate input (automatic with Pydantic)
    # 2. Call postcode service
    # 3. Call climate service
    # 4. Run calculation
    # 5. Save to database
    # 6. Generate explanation
    # 7. Return response
    return CalculationResponse(...)
```

---

### 6. **Service Layer (To Build)**

```python
# app/services/postcode.py
async def lookup_postcode(postcode: str) -> Location:
    """Call Postcodes.io API and return lat/lon"""

# app/services/climate.py
async def get_solar_climate_data(lat: float, lon: float) -> ClimateData:
    """Call NASA POWER API and return GHI"""

# app/services/rag.py
async def generate_explanation(calculation: Calculation) -> Explanation:
    """Use OpenAI + pgvector to explain results"""
```

---

### 7. **Calculator Layer (To Build)**

```python
# app/calculators/solar.py
import pvlib

def calculate_solar_output(
    capacity_kwp: float,
    annual_ghi: float,
    latitude: float,
    orientation: str,
    tilt: float
) -> SolarOutput:
    """
    Use pvlib to calculate:
    - Optimal tilt angle
    - Orientation penalty
    - System losses
    - Annual kWh output
    """
    return SolarOutput(
        annual_kwh=3456.78,
        monthly_kwh=[...],
        capacity_factor=0.12
    )
```

---

## 🔍 Data Flow Example

Let's trace a single calculation through the system:

### User Input
```json
{
  "postcode": "SW1A 1AA",
  "system_type": "solar",
  "system_specs": {
    "capacity_kwp": 4.0,
    "panel_orientation": "south",
    "panel_tilt_degrees": 35
  }
}
```

### 1. Postcode Service
```python
location = await lookup_postcode("SW1A 1AA")
# → {lat: 51.501009, lon: -0.141588, region: "London"}
```

### 2. Climate Service
```python
climate = await get_solar_climate_data(51.501009, -0.141588)
# → {
#     annual_ghi_kwh_m2: 1067,
#     monthly_ghi: [1.2, 2.1, 3.5, ...]
# }
```

### 3. Solar Calculator
```python
result = calculate_solar_output(
    capacity_kwp=4.0,
    annual_ghi=1067,
    orientation="south",
    tilt=35
)
# → {annual_kwh: 3456, monthly_kwh: [...]}
```

### 4. Save to Database
```python
calc = Calculation(
    latitude=51.501009,
    longitude=-0.141588,
    region="London",
    system_type="solar",
    system_specs={"capacity_kwp": 4.0, ...},
    climate_data={"annual_ghi": 1067, ...},
    annual_energy_kwh=3456,
    monthly_energy_kwh=[120, 180, ...]
)
db.add(calc)
await db.commit()
# → Saved with ID: 550e8400-e29b-41d4-a716-446655440000
```

### 5. RAG Explanation
```python
# a. Retrieve relevant documents
query_embedding = await openai.embeddings.create(
    input="solar south-facing London efficiency",
    model="text-embedding-3-small"
)

docs = await db.execute(
    select(RAGDocument)
    .order_by(RAGDocument.embedding.cosine_distance(query_embedding))
    .limit(5)
)

# b. Generate explanation
explanation = await openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": f"Context: {docs}"},
        {"role": "user", "content": "Explain this solar estimate"}
    ]
)
```

### 6. Return Response
```python
return {
    "calculation_id": "550e8400-...",
    "location": {...},
    "results": {
        "annual_energy_kwh": 3456,
        "monthly_energy_kwh": [...]
    },
    "explanation": {
        "summary": "Your 4.0 kWp south-facing solar system...",
        "assumptions": [...]
    }
}
```

---

## 🗄️ Database Schema Visual

```
┌─────────────────────┐
│   calculations      │
├─────────────────────┤
│ id (UUID) PK        │
│ created_at          │
│ latitude            │
│ longitude           │
│ region              │
│ system_type         │ → 'solar' or 'wind'
│ system_specs (JSON) │ → {capacity_kwp: 4.0, ...}
│ climate_data (JSON) │ → {annual_ghi: 1067, ...}
│ annual_energy_kwh   │
│ monthly_energy (ARR)│ → [120, 180, 290, ...]
│ assumptions (JSON)  │
└─────────────────────┘
         ↑
         │ calculation_id
         │
┌─────────────────────┐
│     feedback        │
├─────────────────────┤
│ id (UUID) PK        │
│ calculation_id FK   │
│ actual_annual_kwh   │
│ deviation_percent   │
│ notes               │
└─────────────────────┘


┌─────────────────────┐
│  regional_factors   │
├─────────────────────┤
│ id (UUID) PK        │
│ region              │ → 'London'
│ system_type         │ → 'solar'
│ correction_factor   │ → 0.96
│ confidence_band_%   │ → 12.0
│ sample_count        │ → 47
└─────────────────────┘


┌─────────────────────┐
│   rag_documents     │
├─────────────────────┤
│ id (UUID) PK        │
│ title               │
│ content (TEXT)      │
│ embedding (VECTOR)  │ → [0.012, -0.034, ...]
│ category            │ → 'assumption'
│ system_type         │ → 'solar'
│ tags (ARRAY)        │
└─────────────────────┘
  │
  └─→ pgvector similarity search
      SELECT * ORDER BY embedding <=> query_vector
```

---

## 🚀 What We'll Build Next

### Phase 1: Core Calculation (Next)
1. ✅ Database and models
2. 🚧 **Solar calculator** (pvlib integration)
3. 🚧 **Postcode service** (Postcodes.io API)
4. 🚧 **Climate service** (NASA POWER API)
5. 🚧 **API endpoint** `/api/v1/calculate`

### Phase 2: RAG System
6. 🚧 **Seed RAG documents** (populate rag_documents table)
7. 🚧 **RAG service** (OpenAI embeddings + similarity search)
8. 🚧 **API endpoint** `/api/v1/explain`

### Phase 3: Learning
9. 🚧 **Feedback endpoint** `/api/v1/feedback`
10. 🚧 **Regional learning job** (update correction factors)

### Phase 4: Frontend
11. 🚧 **Next.js app** (React frontend)
12. 🚧 **API integration** (React Query)
13. 🚧 **Map visualization** (optional)

---

## 💡 Key Concepts Recap

1. **FastAPI** = Web framework (like Express for Node.js)
2. **SQLAlchemy** = ORM (translate Python ↔ SQL)
3. **Alembic** = Database migrations (version control for schema)
4. **Pydantic** = Data validation (request/response schemas)
5. **Async/Await** = Non-blocking operations (handles many users)
6. **pgvector** = Vector similarity search (for RAG)
7. **Dependency Injection** = `Depends(get_db)` (clean, testable code)
8. **JSONB** = Flexible JSON storage in PostgreSQL
9. **UUID** = Unique identifiers (better than auto-increment integers)
10. **LRU Cache** = `@lru_cache()` (cache expensive operations)

---

## 📚 Further Reading

- **FastAPI Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **SQLAlchemy 2.0 Tutorial**: https://docs.sqlalchemy.org/en/20/tutorial/
- **pvlib Documentation**: https://pvlib-python.readthedocs.io/
- **pgvector Guide**: https://github.com/pgvector/pgvector
- **Alembic Tutorial**: https://alembic.sqlalchemy.org/en/latest/tutorial.html

---

**Remember**: This is a living document. As we build more, we'll update this guide to reflect the actual implementation!
