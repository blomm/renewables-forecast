# API Contracts

## Overview

This document specifies the REST API contracts for the renewable energy forecasting system.

## Base URL

- Development: `http://localhost:3000/api`
- Production: `https://api.renewables-forecast.example.com/api`

## Authentication

**MVP**: No authentication required (public API with rate limiting)

**Future**: API key authentication
```
Authorization: Bearer {api_key}
```

## Rate Limiting

- **Anonymous**: 10 requests per minute, 100 requests per hour
- **Authenticated** (future): 60 requests per minute, 1000 requests per hour

**Headers**:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1609459200
```

**429 Response** (rate limit exceeded):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again in 45 seconds.",
    "retry_after": 45
  }
}
```

## Common Response Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: External API failure

## Common Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific_field",
      "reason": "validation error details"
    }
  }
}
```

---

## Endpoints

### 1. POST /api/calculate

Calculate energy generation estimate.

**Request**:
```http
POST /api/calculate
Content-Type: application/json

{
  "postcode": "SW1A 1AA",
  "system_type": "solar",
  "system_specs": {
    "capacity_kwp": 4.0,
    "panel_orientation": "south",
    "panel_tilt_degrees": 35,
    "shading_factor": 0.95
  }
}
```

**Request Schema**:
```typescript
{
  postcode: string;          // Required, UK postcode format
  system_type: 'solar' | 'wind';  // Required
  system_specs: SolarSpecs | WindSpecs;  // Required
  session_id?: string;       // Optional, for conversation continuity
  user_email?: string;       // Optional, for follow-up
}

// Solar
interface SolarSpecs {
  capacity_kwp: number;                    // Required, 0.5-50
  panel_orientation?: string;              // Optional, default 'south'
  panel_tilt_degrees?: number;             // Optional, default optimal
  shading_factor?: number;                 // Optional, 0-1, default 1.0
  inverter_efficiency?: number;            // Optional, 0.9-0.99, default 0.96
}

// Wind
interface WindSpecs {
  rated_power_kw: number;                  // Required, 0.5-20
  hub_height_m: number;                    // Required, 5-30
  turbine_model?: string;                  // Optional
  power_curve?: Array<[number, number]>;   // Optional, [[speed, power], ...]
}
```

**Success Response** (200 OK):
```json
{
  "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-05T12:34:56Z",

  "location": {
    "postcode": "SW1A 1AA",
    "latitude": 51.501009,
    "longitude": -0.141588,
    "region": "London"
  },

  "system": {
    "type": "solar",
    "specs": {
      "capacity_kwp": 4.0,
      "panel_orientation": "south",
      "panel_tilt_degrees": 35,
      "shading_factor": 0.95,
      "inverter_efficiency": 0.96
    }
  },

  "results": {
    "annual_energy_kwh": 3456.78,
    "monthly_energy_kwh": [
      120.5, 180.2, 290.8, 380.5, 450.2, 480.9,
      470.3, 420.6, 340.7, 250.4, 140.8, 110.2
    ],
    "confidence_band_percent": 15.0,

    "breakdown": {
      "theoretical_max_kwh": 4100.0,
      "efficiency_factor": 0.88,
      "regional_correction": 0.96
    }
  },

  "explanation": {
    "summary": "Your 4.0 kWp south-facing solar system in London is estimated to generate 3,457 kWh per year. This is typical for well-positioned systems in the London area, accounting for the UK's solar irradiance and typical system losses.",

    "assumptions": [
      "South-facing orientation (optimal for UK)",
      "35° tilt angle (near optimal for your latitude)",
      "5% shading losses (based on your input)",
      "4% inverter and cable losses",
      "Climate data: 20-year average from NASA POWER"
    ],

    "regional_context": "This estimate is in line with typical London installations, which generate 850-950 kWh per kWp annually. Your system is expected to perform at 864 kWh/kWp.",

    "caveats": [
      "Actual output varies ±15% year-to-year due to weather",
      "Micro-shading from nearby objects not accounted for",
      "System performance degrades ~0.5% per year",
      "Professional site survey recommended"
    ]
  },

  "disclaimer": "This is an estimate based on long-term climate averages. Actual performance may vary. Not a guarantee or warranty."
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": {
    "code": "INVALID_POSTCODE",
    "message": "The postcode 'INVALID' is not a valid UK postcode.",
    "details": {
      "field": "postcode",
      "value": "INVALID",
      "expected_format": "A1 1AA or AA1 1AA format"
    }
  }
}
```

**Error Codes**:
- `INVALID_POSTCODE`: Postcode format invalid or not found
- `INVALID_SYSTEM_SPECS`: System specifications out of range or incomplete
- `CLIMATE_API_ERROR`: Unable to retrieve climate data
- `CALCULATION_ERROR`: Internal calculation error

---

### 2. POST /api/explain

Ask follow-up questions about a calculation.

**Request**:
```http
POST /api/explain
Content-Type: application/json

{
  "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "Why is my estimate lower than my neighbor's?",
  "session_id": "optional-session-id"
}
```

**Request Schema**:
```typescript
{
  calculation_id: string;   // Required, UUID
  question: string;         // Required, max 500 chars
  session_id?: string;      // Optional
}
```

**Success Response** (200 OK):
```json
{
  "answer": "Your estimate may differ from your neighbor's due to several factors:\n\n1. **System Size**: Your 4.0 kWp system will generate less than a larger system.\n2. **Orientation**: If your neighbor's panels face more south than yours, they'll capture more sunlight.\n3. **Shading**: You indicated 5% shading losses. If your neighbor has less shading, their output will be higher.\n4. **System Efficiency**: Differences in panel quality, inverter efficiency, and age affect output.\n\nYour estimate of 864 kWh/kWp is within the normal range for London (850-950 kWh/kWp). If your neighbor's is higher per kWp, their site conditions may be more favorable.",

  "sources": [
    "Solar PV Orientation and Tilt Effects (MCS Standards)",
    "Regional Solar Performance Benchmarks - London",
    "Shading Impact on Solar Output"
  ],

  "related_questions": [
    "How much does shading affect solar output?",
    "What orientation is best for solar panels?",
    "How do I improve my system's performance?"
  ]
}
```

**Error Response** (404 Not Found):
```json
{
  "error": {
    "code": "CALCULATION_NOT_FOUND",
    "message": "No calculation found with ID '550e8400-e29b-41d4-a716-446655440000'.",
    "details": {
      "calculation_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

**Error Codes**:
- `CALCULATION_NOT_FOUND`: Calculation ID doesn't exist
- `QUESTION_TOO_LONG`: Question exceeds max length
- `RAG_ERROR`: Error retrieving or generating explanation

---

### 3. POST /api/feedback

Submit actual performance data.

**Request**:
```http
POST /api/feedback
Content-Type: application/json

{
  "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
  "actual_annual_kwh": 3200.5,
  "installation_date": "2025-03-15",
  "performance_period_months": 10,
  "notes": "System experienced 2 weeks downtime in August due to inverter replacement.",
  "user_email": "user@example.com"
}
```

**Request Schema**:
```typescript
{
  calculation_id: string;          // Required, UUID
  actual_annual_kwh: number;       // Required, >0
  installation_date: string;       // Required, ISO date
  performance_period_months: number;  // Required, 1-60
  notes?: string;                  // Optional, max 1000 chars
  user_email?: string;             // Optional, valid email
}
```

**Success Response** (201 Created):
```json
{
  "feedback_id": "660e8400-e29b-41d4-a716-446655440111",
  "submitted_at": "2026-01-05T14:30:00Z",

  "thank_you_message": "Thank you for sharing your actual performance data! Your contribution helps improve estimates for other users in the London area.",

  "impact": {
    "deviation_percent": -7.4,
    "interpretation": "Your system generated 7.4% less than predicted. This is within normal variation and may be due to the downtime you mentioned.",
    "contribution_to_learning": "Your data is the 48th feedback submission for London solar systems, helping refine regional accuracy."
  }
}
```

**Error Codes**:
- `CALCULATION_NOT_FOUND`: Calculation ID doesn't exist
- `INVALID_PERFORMANCE_DATA`: Data out of reasonable bounds
- `DUPLICATE_FEEDBACK`: Feedback already submitted for this calculation

---

### 4. GET /api/calculation/:id

Retrieve a previous calculation.

**Request**:
```http
GET /api/calculation/550e8400-e29b-41d4-a716-446655440000
```

**Success Response** (200 OK):
Same format as POST /api/calculate response.

**Error Response** (404 Not Found):
```json
{
  "error": {
    "code": "CALCULATION_NOT_FOUND",
    "message": "No calculation found with ID '550e8400-e29b-41d4-a716-446655440000'."
  }
}
```

---

### 5. GET /api/regions

List supported regions and their statistics.

**Request**:
```http
GET /api/regions?system_type=solar
```

**Query Parameters**:
- `system_type` (optional): Filter by 'solar' or 'wind'

**Success Response** (200 OK):
```json
{
  "regions": [
    {
      "name": "London",
      "system_type": "solar",
      "statistics": {
        "sample_count": 48,
        "mean_output_kwh_per_kwp": 864,
        "confidence_band_percent": 12.0,
        "correction_factor": 0.96
      }
    },
    {
      "name": "South West",
      "system_type": "solar",
      "statistics": {
        "sample_count": 32,
        "mean_output_kwh_per_kwp": 920,
        "confidence_band_percent": 14.0,
        "correction_factor": 1.02
      }
    }
  ]
}
```

---

### 6. GET /api/health

Health check endpoint.

**Request**:
```http
GET /api/health
```

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-01-05T12:34:56Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "vector_store": "connected",
    "climate_api": "available",
    "cache": "connected"
  }
}
```

**Degraded Response** (200 OK):
```json
{
  "status": "degraded",
  "timestamp": "2026-01-05T12:34:56Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "vector_store": "connected",
    "climate_api": "unavailable",  // Using cached data
    "cache": "connected"
  },
  "warnings": [
    "Climate API unavailable, using cached data only"
  ]
}
```

---

## Webhooks (Future)

### Async Calculation Webhook

For long-running calculations (future feature).

**Callback Format**:
```http
POST {callback_url}
Content-Type: application/json

{
  "event": "calculation.completed",
  "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-05T12:34:56Z",
  "data": {
    // Same as /api/calculate response
  }
}
```

---

## CORS

**Allowed Origins**:
- Development: `http://localhost:*`
- Production: `https://renewables-forecast.example.com`

**Allowed Methods**: `GET, POST, OPTIONS`

**Allowed Headers**: `Content-Type, Authorization`

---

## Versioning

**Current Version**: v1

**URL Format**: `/api/v1/calculate` (optional, default is v1)

**Deprecation Policy**:
- 6 months notice before deprecating an API version
- Old versions supported for 12 months after deprecation notice

---

## SDK Support (Future)

Planned SDKs:
- JavaScript/TypeScript (npm package)
- Python (pip package)

Example usage:
```typescript
import { RenewablesAPI } from '@renewables-forecast/sdk';

const api = new RenewablesAPI({ apiKey: 'your-key' });

const result = await api.calculate({
  postcode: 'SW1A 1AA',
  system_type: 'solar',
  system_specs: {
    capacity_kwp: 4.0
  }
});

console.log(`Annual output: ${result.results.annual_energy_kwh} kWh`);
```
