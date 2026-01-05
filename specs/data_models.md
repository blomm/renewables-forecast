# Data Models

## Overview

This document specifies all data models and database schemas used in the system.

## Database: PostgreSQL

### Table: `calculations`

Stores all energy generation calculations and their inputs.

```sql
CREATE TABLE calculations (
  -- Identity
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Location (anonymized after 90 days)
  postcode_hash VARCHAR(64),  -- SHA256 hash of postcode
  latitude DECIMAL(9, 6) NOT NULL,
  longitude DECIMAL(9, 6) NOT NULL,
  region VARCHAR(50),  -- e.g., 'London', 'South West', 'Scotland'

  -- System specification
  system_type VARCHAR(10) NOT NULL CHECK (system_type IN ('solar', 'wind')),
  system_specs JSONB NOT NULL,  -- Flexible JSON for different system types

  -- Climate data used
  climate_data JSONB NOT NULL,  -- Store the climate inputs used
  climate_source VARCHAR(50),  -- e.g., 'NASA_POWER', 'GLOBAL_WIND_ATLAS'

  -- Calculation results
  annual_energy_kwh DECIMAL(10, 2) NOT NULL,
  monthly_energy_kwh DECIMAL(10, 2)[],  -- Array of 12 values
  confidence_band_percent DECIMAL(5, 2),  -- e.g., 15.0 for ±15%

  -- Calculation metadata
  assumptions JSONB,  -- Record what assumptions were made
  regional_factors_applied JSONB,  -- Record any correction factors used
  calculation_version VARCHAR(20)  -- Track calculation algorithm version
);

CREATE INDEX idx_calculations_location ON calculations(latitude, longitude);
CREATE INDEX idx_calculations_created_at ON calculations(created_at);
CREATE INDEX idx_calculations_region ON calculations(region);
CREATE INDEX idx_calculations_system_type ON calculations(system_type);
```

**Example `system_specs` for Solar**:
```json
{
  "type": "solar",
  "capacity_kwp": 4.0,
  "panel_orientation": "south",
  "panel_tilt_degrees": 35,
  "shading_factor": 0.95,
  "inverter_efficiency": 0.96
}
```

**Example `system_specs` for Wind**:
```json
{
  "type": "wind",
  "rated_power_kw": 5.0,
  "hub_height_m": 12,
  "turbine_model": "Generic 5kW",
  "power_curve": [[0, 0], [3, 0.2], [10, 5.0], [25, 5.0]]  // [wind_speed, power_kw]
}
```

### Table: `feedback`

Stores user-submitted actual performance data.

```sql
CREATE TABLE feedback (
  -- Identity
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Link to original calculation
  calculation_id UUID REFERENCES calculations(id) ON DELETE SET NULL,

  -- Actual performance
  actual_annual_kwh DECIMAL(10, 2) NOT NULL,
  installation_date DATE,
  performance_period_months INT,  -- How long the system has been running

  -- Deviation analysis
  predicted_annual_kwh DECIMAL(10, 2),  -- Copied from calculation for convenience
  deviation_percent DECIMAL(6, 2),  -- (actual - predicted) / predicted * 100

  -- Context
  notes TEXT,  -- User-provided notes (e.g., "shading from new building")
  user_email VARCHAR(255),  -- Optional, only if user opts in

  -- Quality flags
  validated BOOLEAN DEFAULT FALSE,  -- Manual review for outliers
  validation_notes TEXT
);

CREATE INDEX idx_feedback_calculation ON feedback(calculation_id);
CREATE INDEX idx_feedback_submitted_at ON feedback(submitted_at);
CREATE INDEX idx_feedback_deviation ON feedback(deviation_percent);
```

### Table: `regional_factors`

Stores statistically derived correction factors by region.

```sql
CREATE TABLE regional_factors (
  -- Identity
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Region and system type
  region VARCHAR(50) NOT NULL,
  system_type VARCHAR(10) NOT NULL CHECK (system_type IN ('solar', 'wind')),

  -- Statistical factors
  correction_factor DECIMAL(6, 4) DEFAULT 1.0,  -- Multiply baseline by this
  confidence_band_percent DECIMAL(5, 2) DEFAULT 15.0,

  -- Evidence
  sample_count INT DEFAULT 0,  -- How many feedback samples inform this
  mean_deviation DECIMAL(6, 4),  -- Mean of (actual / predicted)
  std_deviation DECIMAL(6, 4),  -- Standard deviation of deviations

  -- Metadata
  last_recalculated_at TIMESTAMPTZ,
  notes TEXT,

  UNIQUE(region, system_type)
);

CREATE INDEX idx_regional_factors_region ON regional_factors(region, system_type);
```

**Example Row**:
```
region: 'London'
system_type: 'solar'
correction_factor: 0.94  (London solar slightly underperforms baseline)
confidence_band_percent: 12.0  (tighter than default ±15%)
sample_count: 47
mean_deviation: 0.94
std_deviation: 0.12
```

### Table: `system_versions`

Track calculation algorithm versions for reproducibility.

```sql
CREATE TABLE system_versions (
  version VARCHAR(20) PRIMARY KEY,  -- e.g., 'v1.0.0'
  deployed_at TIMESTAMPTZ NOT NULL,
  description TEXT,

  -- Calculation parameters
  solar_efficiency_defaults JSONB,
  wind_calculation_params JSONB,

  active BOOLEAN DEFAULT TRUE
);
```

## Vector Store Schema (Pinecone/Weaviate/Qdrant)

### Document Schema

```typescript
interface VectorDocument {
  id: string;  // e.g., 'doc_solar_efficiency_factors'
  embedding: number[];  // 1536-dim for text-embedding-3-small

  metadata: {
    // Classification
    category: 'assumption' | 'benchmark' | 'error_source' | 'constraint' | 'explanation';
    system_type?: 'solar' | 'wind' | 'both';
    region?: string;  // Optional regional specificity

    // Content
    title: string;
    content: string;  // Full text content
    summary?: string;  // Optional short summary

    // Provenance
    source: string;  // e.g., 'MCS Installation Standards'
    source_url?: string;
    last_updated: string;  // ISO date

    // Metadata for filtering
    tags?: string[];  // e.g., ['urban', 'shading', 'performance']
    priority?: number;  // Higher priority docs retrieved first (1-10)
  };
}
```

### Example Documents

**Document 1: Solar Efficiency Assumptions**
```json
{
  "id": "doc_solar_efficiency_uk",
  "embedding": [0.012, -0.034, ...],
  "metadata": {
    "category": "assumption",
    "system_type": "solar",
    "region": "UK",
    "title": "Solar PV System Efficiency Factors",
    "content": "Solar PV systems in the UK experience several efficiency losses...",
    "source": "MCS Installation Standards 2025",
    "last_updated": "2025-06-01",
    "tags": ["efficiency", "losses", "inverter", "temperature"],
    "priority": 9
  }
}
```

**Document 2: Regional Wind Performance**
```json
{
  "id": "doc_wind_urban_penalty",
  "embedding": [0.045, -0.012, ...],
  "metadata": {
    "category": "error_source",
    "system_type": "wind",
    "title": "Urban Wind Turbulence Effects",
    "content": "Wind turbines in urban or suburban areas experience 10-30% reduction...",
    "source": "Carbon Trust Small-scale Wind Report",
    "source_url": "https://example.com/report",
    "last_updated": "2024-03-15",
    "tags": ["urban", "turbulence", "wind", "performance"],
    "priority": 8
  }
}
```

## API Request/Response Models

### POST /api/calculate

**Request Body**:
```typescript
interface CalculationRequest {
  postcode: string;  // e.g., "SW1A 1AA"
  system_type: 'solar' | 'wind';
  system_specs: SolarSpecs | WindSpecs;

  // Optional
  user_email?: string;  // For optional follow-up
  session_id?: string;  // For conversation continuity
}

interface SolarSpecs {
  capacity_kwp: number;
  panel_orientation?: 'north' | 'south' | 'east' | 'west' | 'south-east' | 'south-west';  // Default: 'south'
  panel_tilt_degrees?: number;  // Default: optimal for latitude
  shading_factor?: number;  // 0-1, default: 1.0 (no shading)
  inverter_efficiency?: number;  // 0-1, default: 0.96
}

interface WindSpecs {
  rated_power_kw: number;
  hub_height_m: number;
  turbine_model?: string;  // If known, use specific power curve
  power_curve?: Array<[number, number]>;  // [[wind_speed, power_kw], ...]
}
```

**Response Body**:
```typescript
interface CalculationResponse {
  calculation_id: string;
  created_at: string;  // ISO timestamp

  location: {
    postcode: string;  // Echoed back
    latitude: number;
    longitude: number;
    region: string;
  };

  results: {
    annual_energy_kwh: number;
    monthly_energy_kwh: number[];  // 12 values
    confidence_band_percent: number;

    // Breakdown (optional, for transparency)
    breakdown?: {
      theoretical_max_kwh: number;
      efficiency_factor: number;
      regional_correction: number;
    };
  };

  explanation: {
    summary: string;  // Generated by RAG
    assumptions: string[];  // List of key assumptions
    regional_context: string;  // How this compares locally
    caveats: string[];  // Important limitations
  };

  disclaimer: string;  // Legal disclaimer
}
```

### POST /api/explain

Ask follow-up questions about a calculation.

**Request Body**:
```typescript
interface ExplainRequest {
  calculation_id: string;
  question: string;
  session_id?: string;
}
```

**Response Body**:
```typescript
interface ExplainResponse {
  answer: string;  // RAG-generated answer
  sources: string[];  // Citations
  related_questions?: string[];  // Suggested follow-ups
}
```

### POST /api/feedback

Submit actual performance data.

**Request Body**:
```typescript
interface FeedbackRequest {
  calculation_id: string;
  actual_annual_kwh: number;
  installation_date: string;  // ISO date
  performance_period_months: number;
  notes?: string;
  user_email?: string;
}
```

**Response Body**:
```typescript
interface FeedbackResponse {
  feedback_id: string;
  thank_you_message: string;
  impact: {
    deviation_percent: number;
    contribution_to_learning: string;  // e.g., "Your data helps improve estimates for South West region"
  };
}
```

## Cache Data Models

### Climate Data Cache (Redis)

**Key**: `climate:solar:{lat}:{lon}`

**Value**:
```json
{
  "source": "NASA_POWER",
  "retrieved_at": "2026-01-05T12:00:00Z",
  "data": {
    "monthly_ghi_kwh_m2_day": [1.2, 2.1, 3.5, 4.8, 5.9, 6.2, 5.8, 5.0, 3.8, 2.5, 1.4, 1.0],
    "annual_ghi_kwh_m2": 1234.5
  }
}
```

**Key**: `climate:wind:{lat}:{lon}:{hub_height}`

**Value**:
```json
{
  "source": "GLOBAL_WIND_ATLAS",
  "retrieved_at": "2026-01-05T12:00:00Z",
  "data": {
    "mean_wind_speed_ms": 5.8,
    "weibull_a": 6.2,
    "weibull_k": 2.1,
    "power_density_w_m2": 280
  }
}
```

## Session State (Redis)

**Key**: `session:{session_id}`

**Value**:
```json
{
  "session_id": "uuid",
  "user_id": null,
  "context": {
    "last_calculation_id": "calc_123",
    "system_type": "solar",
    "location": {
      "lat": 51.501,
      "lon": -0.141,
      "region": "London"
    },
    "conversation_history": [
      {"role": "user", "content": "Calculate for SW1A 1AA with 4kWp solar"},
      {"role": "assistant", "content": "Your estimated annual output is 3600 kWh..."}
    ]
  },
  "expires_at": "2026-01-05T14:00:00Z"
}
```

**TTL**: 3600 seconds (1 hour)

## Validation Rules

### Input Validation

**Postcode**:
- Must match UK postcode regex: `^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$`

**Solar System**:
- `capacity_kwp`: 0.5 - 50 kWp (residential range)
- `panel_tilt_degrees`: 0 - 90
- `shading_factor`: 0 - 1
- `inverter_efficiency`: 0.9 - 0.99

**Wind System**:
- `rated_power_kw`: 0.5 - 20 kW (residential/small commercial)
- `hub_height_m`: 5 - 30 m
- `power_curve`: Must be monotonically increasing up to rated power

### Output Validation

- Annual energy cannot exceed theoretical maximum by >10%
- Confidence band must be 5% - 30%
- Monthly values must sum to within 1% of annual value

## Migration Scripts

### Initial Schema Setup

```bash
# Run migrations
npm run migrate

# Seed regional factors with neutral values
npm run seed:regional-factors

# Populate vector store with initial documents
npm run seed:vector-store
```

### Version Upgrades

- All schema changes via migrations (tracked in `migrations/` directory)
- Backwards-compatible API changes only
- Calculation version tracked in `system_versions` table
