# Agent Workflows

## Overview

This system uses a multi-agent approach where specialized agents handle different aspects of the energy forecasting and explanation pipeline.

## Agent Types

### 1. Input Validation Agent

**Purpose**: Validate and normalize user input

**Inputs**:
- Postcode (string)
- System type (solar/wind)
- System specifications (JSON)

**Workflow**:
1. Validate postcode format (UK)
2. Convert postcode to lat/lon
3. Validate system specifications against schema
4. Normalize units (kWp, hub height, etc.)
5. Return validated input object or error

**Error Handling**:
- Invalid postcode → suggest correction or ask for re-entry
- Out-of-bounds specs → return sensible ranges
- Missing required fields → request clarification

### 2. Climate Data Agent

**Purpose**: Retrieve and cache relevant climate data

**Inputs**:
- Lat/lon coordinates
- System type (determines which data to fetch)

**Workflow**:
1. Check cache for existing data at this location
2. If cache miss, call appropriate external API(s):
   - Solar: NASA POWER for GHI (Global Horizontal Irradiance)
   - Wind: Global Wind Atlas or ERA5 for wind speed distribution
3. Parse and normalize API response
4. Store in cache with TTL (e.g., 30 days for climate normals)
5. Return climate data object

**Error Handling**:
- API timeout → retry with exponential backoff
- API rate limit → use cached data or delay
- Invalid coordinates → return error to Input Agent

### 3. Energy Calculation Agent

**Purpose**: Perform deterministic energy calculations

**Inputs**:
- Validated system specifications
- Climate data
- Regional adjustment factors

**Workflow**:

#### For Solar PV:
1. Calculate optimal tilt angle (if not provided)
2. Apply orientation penalty (if not south-facing)
3. Calculate annual irradiance at tilted surface
4. Apply system efficiency factors:
   - Inverter efficiency (~96%)
   - Temperature coefficient
   - Soiling/shading losses
   - Cable losses
5. Calculate monthly breakdown
6. Calculate confidence band based on regional variance

#### For Wind Turbine:
1. Scale wind speed to hub height (power law or log profile)
2. Extract or fit Weibull distribution parameters
3. Integrate power curve against wind speed distribution
4. Apply availability factor (~95%)
5. Apply regional turbulence/urban penalties if applicable
6. Calculate confidence band

**Outputs**:
- Annual energy estimate (kWh/year)
- Monthly breakdown (optional)
- Confidence interval (±%)
- Calculation metadata (assumptions used)

**Error Handling**:
- Impossible combinations → flag and explain
- Out-of-range power curve → interpolate or warn

### 4. RAG Explainer Agent

**Purpose**: Generate human-readable explanations of results and answer user questions

**Inputs**:
- Calculation results and metadata
- User question (optional)
- Calculation assumptions used

**Workflow**:
1. Embed user question (if provided) or default explanation request
2. Retrieve relevant documents from vector store:
   - Assumption explanations
   - Regional performance benchmarks
   - Known error sources
   - Comparative context
3. Generate grounded explanation using LLM:
   - Why this estimate?
   - What assumptions were made?
   - What could affect actual performance?
   - How does this compare to regional averages?
4. Return explanation with source citations

**RAG Vector Store Contents**:
- UK solar performance benchmarks by region
- Wind turbulence effects in urban/rural areas
- Shading impact explanations
- Orientation and tilt penalties
- Seasonal variation context
- Installation best practices
- Planning permission considerations
- Common misconceptions

**Error Handling**:
- No relevant documents found → general explanation
- LLM timeout → return cached explanation template

### 5. Feedback Collection Agent

**Purpose**: Collect and store user-submitted actual performance data

**Inputs**:
- Original estimate ID
- Actual annual output (kWh)
- Installation date
- Optional notes

**Workflow**:
1. Validate feedback data
2. Calculate deviation from predicted value
3. Store in feedback database with:
   - Location (anonymized to region)
   - System type and specs
   - Predicted vs actual
   - Timestamp
4. Trigger statistical aggregation (async)
5. Return confirmation to user

**Error Handling**:
- Impossible values (e.g., 10x predicted) → flag for review
- Missing estimate ID → cannot link feedback

### 6. Learning Agent (Background)

**Purpose**: Aggregate feedback to improve regional correction factors

**Inputs**:
- Feedback database

**Workflow** (runs periodically, e.g., weekly):
1. Query all feedback for a region
2. Calculate statistical deviation from baseline
3. Update regional correction factors if significant
4. Adjust confidence bands based on actual variance
5. Log changes for audit

**Outputs**:
- Updated regional adjustment factors
- Updated confidence intervals
- Statistical summary report

**Note**: This is NOT real-time ML training, just statistical adjustment

## Agent Orchestration

### Primary Flow (Single Estimate)
```
User Request
  ↓
Input Validation Agent
  ↓
Climate Data Agent (parallel if multiple sources)
  ↓
Energy Calculation Agent
  ↓
RAG Explainer Agent
  ↓
Response to User
```

### Follow-up Question Flow
```
User Question
  ↓
RAG Explainer Agent (with original calculation context)
  ↓
Response to User
```

### Feedback Flow
```
User Feedback Submission
  ↓
Feedback Collection Agent
  ↓
(Background: Learning Agent updates stats)
  ↓
Confirmation to User
```

## Error Recovery

- Each agent can fail independently
- Upstream agents provide fallback data when possible
- Critical failures bubble up to user with explanation
- Non-critical failures log warnings but continue

## Observability

- Each agent logs inputs, outputs, duration
- RAG retrieval logs which documents were used
- Calculation logs show which factors were applied
- Feedback logs show statistical drift over time
