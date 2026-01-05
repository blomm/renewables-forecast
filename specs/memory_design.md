# Memory Design

## Overview

This document specifies how the system stores and retrieves different types of memory and state.

## Memory Categories

### 1. Climate Data Cache (Short-term Memory)

**Purpose**: Avoid repeated API calls for the same location

**Storage**: Redis or in-memory cache

**Schema**:
```typescript
{
  key: `climate:solar:${lat}:${lon}`,
  value: {
    source: 'NASA_POWER',
    retrieved_at: '2026-01-05T12:00:00Z',
    data: {
      monthly_ghi: [/* 12 values in kWh/m²/day */],
      annual_ghi: 1234.5
    }
  },
  ttl: 2592000  // 30 days in seconds
}
```

```typescript
{
  key: `climate:wind:${lat}:${lon}:${hub_height}`,
  value: {
    source: 'GLOBAL_WIND_ATLAS',
    retrieved_at: '2026-01-05T12:00:00Z',
    data: {
      mean_wind_speed: 5.8,  // m/s
      weibull_a: 6.2,
      weibull_k: 2.1
    }
  },
  ttl: 2592000
}
```

**Eviction Policy**: LRU (Least Recently Used)

**Cache Warming**: Pre-populate for major UK cities (optional optimization)

### 2. Calculation History (Long-term Memory)

**Purpose**: Store user calculations for later reference, feedback linkage, and trend analysis

**Storage**: PostgreSQL

**Schema**: See [data_models.md](data_models.md) - `calculations` table

**Retention Policy**:
- Keep all calculations indefinitely for statistical analysis
- Anonymize personal identifiers after 90 days (GDPR compliance)

**Indexes**:
- Primary key: `calculation_id`
- Location index: `(latitude, longitude)` for regional queries
- Timestamp index: `created_at` for time-series analysis

### 3. User Feedback (Long-term Memory)

**Purpose**: Store actual performance data to improve future estimates

**Storage**: PostgreSQL

**Schema**: See [data_models.md](data_models.md) - `feedback` table

**Retention Policy**:
- Keep all feedback indefinitely (anonymized)
- Link to original calculation via `calculation_id`

**Privacy Considerations**:
- No PII stored
- Location anonymized to region after aggregation
- Optional email stored only if user opts in for follow-up

### 4. Regional Adjustment Factors (Learned Memory)

**Purpose**: Store statistically derived correction factors by region

**Storage**: PostgreSQL

**Schema**: See [data_models.md](data_models.md) - `regional_factors` table

**Update Frequency**: Weekly background job

**Algorithm**:
```python
# Pseudocode
for region in UK_REGIONS:
    feedback_data = query_feedback(region, min_samples=10)
    if feedback_data.count >= 10:
        mean_deviation = feedback_data.actual / feedback_data.predicted
        if abs(mean_deviation - 1.0) > 0.05:  # >5% systematic error
            regional_factors[region].correction *= mean_deviation
            regional_factors[region].confidence_band = stdev(deviations)
```

**Confidence Threshold**: Only update if ≥10 samples in region

### 5. RAG Vector Store (Semantic Memory)

**Purpose**: Store embeddings of context documents for retrieval

**Storage**: Pinecone, Weaviate, or Qdrant

**Schema**:
```typescript
{
  id: 'doc_solar_efficiency_factors',
  embedding: [/* 1536-dim vector */],
  metadata: {
    category: 'assumption',
    system_type: 'solar',
    region: 'UK',
    title: 'Solar PV Efficiency Factors',
    content: '...',  // Full text
    source: 'MCS Installation Standards',
    last_updated: '2026-01-05'
  }
}
```

**Categories**:
- `assumption`: Calculation assumptions and defaults
- `benchmark`: Performance benchmarks and comparisons
- `error_source`: Known sources of error or variation
- `constraint`: Planning, legal, or physical constraints
- `explanation`: General educational content

**Update Frequency**: Manual updates when content changes

**Retrieval Strategy**:
- Semantic search by embedding similarity (cosine)
- Filter by system_type and region if specified
- Top-k retrieval (k=5 typical)

### 6. Session State (Ephemeral Memory)

**Purpose**: Track conversation state for follow-up questions

**Storage**: In-memory or Redis with short TTL

**Schema**:
```typescript
{
  session_id: 'uuid',
  user_id?: 'optional',
  context: {
    last_calculation_id: 'calc_123',
    system_type: 'solar',
    location: { lat: 51.501, lon: -0.141 },
    conversation_history: [
      { role: 'user', content: '...' },
      { role: 'assistant', content: '...' }
    ]
  },
  expires_at: '2026-01-05T14:00:00Z'
}
```

**TTL**: 1 hour of inactivity

**Purpose**: Allows follow-up questions like "Why is my estimate lower than average?" without re-specifying the system

## Memory Access Patterns

### Write Patterns

1. **Calculation Request**:
   - Write to climate cache (if miss)
   - Write to `calculations` table
   - Write to session state

2. **Feedback Submission**:
   - Write to `feedback` table
   - Trigger async aggregation job

3. **Background Learning**:
   - Read from `feedback` table
   - Update `regional_factors` table
   - Log changes for audit

### Read Patterns

1. **Initial Estimate**:
   - Read from climate cache (or API)
   - Read from `regional_factors` for correction
   - Write to `calculations`

2. **RAG Explanation**:
   - Read from vector store (semantic search)
   - Read from session state (conversation context)
   - Read from `calculations` (original estimate metadata)

3. **Statistical Analysis**:
   - Read from `feedback` table (aggregated by region)
   - Read from `regional_factors` (current correction factors)

## Data Migration Strategy

### Initial Population

1. **Vector Store**:
   - Manually curate 50-100 context documents
   - Generate embeddings using chosen model
   - Upsert to vector DB

2. **Regional Factors**:
   - Initialize with neutral values (correction=1.0, confidence=±15%)
   - Update as feedback accumulates

3. **Climate Cache**:
   - Start empty, populate on demand
   - Optional: Pre-warm for top 100 UK postcodes

### Ongoing Maintenance

- **Vector Store**: Manual updates when new guidance/benchmarks available
- **Regional Factors**: Automatic weekly updates via Learning Agent
- **Cache**: Automatic eviction and refresh based on TTL

## Backup and Recovery

### Critical Data (Must Backup)
- `calculations` table
- `feedback` table
- `regional_factors` table
- Vector store documents (can regenerate embeddings if needed)

### Non-Critical Data (Can Rebuild)
- Climate cache (re-fetch from APIs)
- Session state (ephemeral by nature)

### Backup Frequency
- PostgreSQL: Daily incremental, weekly full
- Vector store: Weekly export to JSON

### Recovery Testing
- Quarterly restore drill to staging environment

## GDPR Compliance

### Personal Data Handling

**What We Store**:
- Postcode (hashed after calculation)
- System specifications (anonymized)
- Calculation results (anonymized)
- Optional: Email (if user opts in for feedback follow-up)

**What We Don't Store**:
- Names
- Full addresses
- Payment information
- IP addresses (beyond standard server logs)

### User Rights

1. **Right to Access**: Provide calculation history via email lookup
2. **Right to Deletion**: Delete calculation and feedback records
3. **Right to Portability**: Export user's calculation history as JSON

### Data Retention

- **Active Data**: Until user requests deletion
- **Aggregated Stats**: Indefinite (fully anonymized)
- **Logs**: 90 days

### Implementation

- Anonymization job runs nightly: hash postcodes, remove granular location
- Deletion endpoint: `/api/user/delete?email={email}`
- Export endpoint: `/api/user/export?email={email}`

## Scalability Considerations

### Current MVP Scale
- ~1000 calculations/day
- ~100 feedback submissions/day
- ~10,000 vector documents

### Future Scale (Year 1)
- ~10,000 calculations/day
- ~1,000 feedback submissions/day
- ~50,000 vector documents

### Scaling Strategy

1. **Horizontal Scaling**: Stateless API servers
2. **Database**: Read replicas for analytics queries
3. **Cache**: Redis cluster if single instance saturates
4. **Vector Store**: Managed services scale automatically

### Monitoring

- Cache hit rate (target: >80% for climate data)
- Database query latency (target: <100ms p95)
- RAG retrieval time (target: <500ms)
- Feedback accumulation rate by region
