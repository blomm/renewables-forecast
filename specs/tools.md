# Tools

## Overview

This document specifies the tools and external services used by the system.

## External APIs

### 1. Postcode Lookup API

**Purpose**: Convert UK postcode to lat/lon coordinates

**Options**:
- **Postcodes.io** (Free, Open Source)
  - Endpoint: `https://api.postcodes.io/postcodes/{postcode}`
  - Rate limit: Generous for personal use
  - Response includes: latitude, longitude, region, country

**Example Request**:
```
GET https://api.postcodes.io/postcodes/SW1A1AA
```

**Example Response**:
```json
{
  "status": 200,
  "result": {
    "postcode": "SW1A 1AA",
    "latitude": 51.501009,
    "longitude": -0.141588,
    "region": "London"
  }
}
```

**Error Handling**:
- 404: Invalid postcode
- 500: Service unavailable
- Rate limiting: Implement exponential backoff

### 2. NASA POWER API

**Purpose**: Retrieve solar irradiance climate normals

**Endpoint**: `https://power.larc.nasa.gov/api/temporal/climatology/point`

**Parameters**:
- `latitude`, `longitude`
- `parameters`: `ALLSKY_SFC_SW_DWN` (GHI - Global Horizontal Irradiance)
- `community`: `RE` (Renewable Energy)
- `format`: `JSON`

**Example Request**:
```
GET https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=-0.141588&latitude=51.501009&format=JSON
```

**Response**: Monthly average irradiance (kWh/m²/day)

**Rate Limits**: Generally permissive, implement caching

**Cache Strategy**: Climate normals change rarely, cache for 30+ days

### 3. Global Wind Atlas API

**Purpose**: Retrieve wind speed data and Weibull parameters

**Endpoint**: `https://globalwindatlas.info/api/gis/country/{country}/wind-speed`

**Note**: May require registration and API key

**Alternative**: Use ERA5-Land via Copernicus Climate Data Store (CDS)

**Parameters**:
- Latitude, longitude
- Hub height (e.g., 10m, 50m, 100m)

**Response**: Mean wind speed, Weibull A and k parameters

**Cache Strategy**: Same as NASA POWER (30+ days)

### 4. ERA5-Land (Optional, for Wind)

**Purpose**: High-resolution climate reanalysis data

**Access**: Copernicus Climate Data Store (CDS)
- Requires free account and API key
- Python client: `cdsapi`

**Parameters**:
- `10m_u_component_of_wind`
- `10m_v_component_of_wind`
- Monthly means

**Note**: More complex but higher quality than Global Wind Atlas for UK

## Internal Tools

### 5. Vector Database

**Purpose**: Store and retrieve RAG context documents

**Options**:
- **Pinecone** (Managed, simple API)
- **Weaviate** (Open source, self-hosted option)
- **Qdrant** (Open source, Python-native)

**Schema**:
```typescript
{
  id: string,
  embedding: number[],
  metadata: {
    category: 'assumption' | 'benchmark' | 'error_source' | 'constraint',
    region?: string,
    system_type?: 'solar' | 'wind',
    content: string
  }
}
```

**Operations**:
- Upsert documents with embeddings
- Semantic search by query embedding
- Filter by metadata (region, system type)

### 6. Embedding Model

**Purpose**: Generate embeddings for RAG retrieval

**Options**:
- **OpenAI text-embedding-3-small** (Cost-effective, good quality)
- **Sentence Transformers** (Open source, self-hosted)

**Usage**:
- Embed user questions
- Embed context documents (one-time or infrequent)

### 7. LLM for RAG

**Purpose**: Generate grounded explanations from retrieved context

**Options**:
- **OpenAI GPT-4o** (High quality, streaming support)
- **Anthropic Claude 3.5 Sonnet** (Long context, good at following instructions)

**Prompt Template** (see [prompts.md](prompts.md))

**Usage**:
- Pass retrieved documents as context
- Generate explanation or answer user question
- Stream response for better UX

## Calculation Libraries

### 8. Solar Position Algorithm

**Purpose**: Calculate sun position, optimal tilt angle

**Library**: `pvlib` (Python) or `suncalc` (JavaScript)

**Functions Needed**:
- Solar declination
- Hour angle
- Optimal tilt angle for latitude
- Transposition factor (horizontal to tilted irradiance)

### 9. Wind Power Calculation

**Purpose**: Integrate power curve against wind distribution

**Library**: Custom implementation or `windpowerlib` (Python)

**Functions Needed**:
- Hub height wind speed scaling (power law or log profile)
- Weibull distribution probability density
- Numerical integration of power curve
- Standard power curves for common turbines

## Caching Layer

### 10. Redis (or In-Memory for MVP)

**Purpose**: Cache expensive API calls and calculations

**Keys**:
- `climate:solar:{lat}:{lon}` → NASA POWER data
- `climate:wind:{lat}:{lon}:{height}` → Wind data
- `postcode:{postcode}` → Lat/lon lookup

**TTL**:
- Climate data: 30 days (changes infrequently)
- Postcode lookup: 90 days (static)

## Database

### 11. PostgreSQL

**Purpose**: Store user calculations, feedback, regional factors

**Tables**:
- `calculations` (see [data_models.md](data_models.md))
- `feedback` (see [data_models.md](data_models.md))
- `regional_factors` (see [data_models.md](data_models.md))

**Features Used**:
- JSONB for flexible system specifications
- Spatial queries (PostGIS) if needed for regional aggregation
- Indexes on location, timestamp

## Development Tools

### 12. Testing

- **Vitest** or **Jest**: Unit and integration tests
- **Supertest**: API endpoint testing
- **Mock Service Worker (MSW)**: Mock external APIs

### 13. Observability

- **Logging**: Winston or Pino (structured JSON logs)
- **Monitoring**: Prometheus + Grafana (optional)
- **Error Tracking**: Sentry (optional)

## Security Tools

### 14. Input Validation

- **Zod** (TypeScript): Schema validation
- **Joi** (JavaScript): Alternative validation library

### 15. Rate Limiting

- **express-rate-limit** or similar
- Protect API endpoints from abuse

### 16. API Key Management

- **Environment variables** for development
- **Secrets manager** (AWS Secrets Manager, etc.) for production
