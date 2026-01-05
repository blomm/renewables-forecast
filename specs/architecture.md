# System Architecture

## High-Level Flow

```
User Input (Postcode + System Specs)
  ↓
Postcode → Lat/Lon Lookup
  ↓
Climate Data Retrieval (API)
  ↓
Deterministic Energy Model
  ↓
Energy Estimate (kWh/year)
  ↓
RAG Explainer System
  ↓
Results + Explanations to User
```

## Components

### 1. Input Layer
- **Postcode Service**: Converts UK postcode to lat/lon
- **System Specification Parser**: Validates and normalizes user input for solar/wind systems

### 2. Climate Data Layer
- **Climate API Client**: Retrieves climate normals from external APIs
  - ERA5/ERA5-Land (Copernicus)
  - NASA POWER
  - Global Wind Atlas
- **Data Cache**: Local caching to minimize API calls and costs

### 3. Energy Calculation Layer
- **Solar PV Calculator**: Deterministic calculation using industry formulas
- **Wind Turbine Calculator**: Power curve integration with Weibull distribution
- **Efficiency Factor Library**: Regional and system-specific adjustment factors

### 4. RAG Layer
- **Vector Store**: Embeddings of:
  - Calculation assumptions
  - UK performance benchmarks
  - Regional adjustment heuristics
  - Known error sources
  - Planning constraints
  - Explanatory content
- **RAG Retriever**: Semantic search for relevant context
- **LLM Integration**: Generates grounded explanations

### 5. Learning Layer (Simple MVP)
- **Feedback Store**: User-submitted actual performance data
- **Statistics Aggregator**: Regional correction factors
- **Confidence Band Adjuster**: Tightens estimates based on evidence

### 6. API Layer
- RESTful API for frontend consumption
- Optional webhook for async processing

## Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **API Framework**: FastAPI
- **Calculation Libraries**:
  - `pvlib` for solar PV calculations
  - `windpowerlib` for wind turbine calculations
  - `numpy`, `scipy` for numerical computations
- **Vector Store**: PostgreSQL with pgvector extension
- **LLM**: OpenAI GPT-4o (via API)
- **Embeddings**: OpenAI text-embedding-3-small
- **Cache**: In-memory (LRU cache) for MVP, Redis for production
- **HTTP Client**: `httpx` for async external API calls
- **Validation**: Pydantic (built into FastAPI)

### Data Storage
- **Database**: PostgreSQL 15+ with pgvector extension
  - User inputs, feedback, calculations (relational data)
  - Vector embeddings for RAG (pgvector)
- **File Storage**: Local filesystem for MVP, S3 for production

### External APIs
- Postcode lookup: Postcodes.io (free UK postcode API)
- Climate data:
  - NASA POWER API (solar irradiance)
  - Global Wind Atlas or ERA5-Land (wind data)

### Frontend
- **Framework**: Next.js 14+ with TypeScript
- **UI Library**: React 18+
- **Styling**: TailwindCSS (or your preference)
- **State Management**: React Query for API calls
- **Maps** (optional): Leaflet or Mapbox

## Deployment Considerations

- API rate limits and caching strategy for external climate APIs
- Cost management for LLM API calls
- Scalability: stateless compute, horizontal scaling possible
- Security: input validation, rate limiting, API key management

## Data Flow Security

- No PII storage beyond optional email for feedback
- Climate data is public domain
- User calculations stored anonymized
- GDPR compliance for UK users
