# Error Handling

## Overview

This document specifies error handling strategies, error codes, and recovery procedures for the renewable energy forecasting system.

## Error Categories

### 1. Client Errors (4xx)

Caused by invalid user input or client-side issues.

**Strategy**: Return descriptive error with guidance for correction.

**Recovery**: User must correct input and retry.

### 2. Server Errors (5xx)

Caused by internal failures or external API issues.

**Strategy**: Log error, attempt recovery if possible, return generic message to user.

**Recovery**: Automatic retry with exponential backoff, or fallback to cached data.

### 3. External API Errors

Caused by third-party service failures.

**Strategy**: Retry with backoff, use cached data if available, degrade gracefully.

**Recovery**: Automatic with caching fallback.

---

## Error Response Format

All errors follow this consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Context-specific error details
    },
    "timestamp": "2026-01-05T12:34:56Z",
    "request_id": "req_123456"  // For support/debugging
  }
}
```

---

## Client Errors (4xx)

### INVALID_POSTCODE (400)

**Cause**: Postcode format invalid or not found.

**Response**:
```json
{
  "error": {
    "code": "INVALID_POSTCODE",
    "message": "The postcode 'INVALID' is not a valid UK postcode.",
    "details": {
      "field": "postcode",
      "value": "INVALID",
      "expected_format": "A1 1AA or AA1 1AA format",
      "example": "SW1A 1AA"
    }
  }
}
```

**User Action**: Correct postcode and retry.

**Internal Action**: Log for pattern analysis (common typos).

---

### INVALID_SYSTEM_SPECS (400)

**Cause**: System specifications out of valid range.

**Response**:
```json
{
  "error": {
    "code": "INVALID_SYSTEM_SPECS",
    "message": "System capacity 100 kWp exceeds residential maximum.",
    "details": {
      "field": "capacity_kwp",
      "value": 100,
      "min": 0.5,
      "max": 50,
      "reason": "This service is designed for residential systems (0.5-50 kWp)."
    }
  }
}
```

**User Action**: Adjust system specs to valid range.

**Internal Action**: Log for potential product expansion (commercial systems).

---

### CALCULATION_NOT_FOUND (404)

**Cause**: Requested calculation ID doesn't exist.

**Response**:
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

**User Action**: Verify calculation ID.

**Internal Action**: None (expected for invalid/expired IDs).

---

### RATE_LIMIT_EXCEEDED (429)

**Cause**: User exceeded rate limit.

**Response**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again in 45 seconds.",
    "details": {
      "retry_after": 45,
      "limit": "10 requests per minute",
      "current_usage": 10
    }
  }
}
```

**Headers**:
```
Retry-After: 45
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704463545
```

**User Action**: Wait and retry.

**Internal Action**: Log excessive usage patterns, consider temporary IP block if abusive.

---

### DUPLICATE_FEEDBACK (409)

**Cause**: Feedback already submitted for this calculation.

**Response**:
```json
{
  "error": {
    "code": "DUPLICATE_FEEDBACK",
    "message": "Feedback has already been submitted for this calculation.",
    "details": {
      "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
      "existing_feedback_id": "660e8400-e29b-41d4-a716-446655440111",
      "submitted_at": "2026-01-03T10:20:30Z"
    }
  }
}
```

**User Action**: Cannot resubmit. Contact support if update needed.

**Internal Action**: None.

---

## Server Errors (5xx)

### CLIMATE_API_ERROR (503)

**Cause**: External climate API unavailable or failing.

**Response**:
```json
{
  "error": {
    "code": "CLIMATE_API_ERROR",
    "message": "Unable to retrieve climate data at this time. Please try again in a few minutes.",
    "details": {
      "service": "NASA_POWER",
      "status": "unavailable",
      "fallback": "none_available"
    }
  }
}
```

**User Action**: Retry after delay.

**Internal Action**:
1. Retry with exponential backoff (3 attempts)
2. Check cache for recent data (<7 days old)
3. If cache available, use with warning
4. If no cache, return 503
5. Alert on-call engineer if down >10 minutes

**Fallback Strategy**:
```typescript
async function getClimateData(lat, lon) {
  // Try cache first
  const cached = await cache.get(`climate:solar:${lat}:${lon}`);
  if (cached && cached.age < 7 * 24 * 60 * 60 * 1000) {
    return { data: cached.data, source: 'cache', warning: 'Using cached data' };
  }

  // Try API with retry
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const data = await climateAPI.fetch(lat, lon);
      await cache.set(`climate:solar:${lat}:${lon}`, data, TTL_30_DAYS);
      return { data, source: 'api' };
    } catch (err) {
      if (attempt === 3) throw new ClimateAPIError();
      await sleep(Math.pow(2, attempt) * 1000);  // Exponential backoff
    }
  }
}
```

---

### CALCULATION_ERROR (500)

**Cause**: Internal calculation logic failure.

**Response**:
```json
{
  "error": {
    "code": "CALCULATION_ERROR",
    "message": "An unexpected error occurred during calculation. Our team has been notified.",
    "details": {
      "request_id": "req_123456"
    }
  }
}
```

**User Action**: Retry. If persists, contact support with request_id.

**Internal Action**:
1. Log full error with stack trace
2. Alert on-call engineer immediately
3. Log input data for reproduction
4. Add to error dashboard

**Never Expose**: Internal error details, stack traces, or DB errors to user.

---

### DATABASE_ERROR (500)

**Cause**: Database connection or query failure.

**Response**:
```json
{
  "error": {
    "code": "DATABASE_ERROR",
    "message": "A temporary database issue occurred. Please try again.",
    "details": {
      "request_id": "req_123456"
    }
  }
}
```

**User Action**: Retry.

**Internal Action**:
1. Retry query once
2. If persist, alert on-call
3. Check DB health metrics
4. Consider read-replica failover

---

### RAG_ERROR (500)

**Cause**: Vector store or LLM API failure.

**Response**:
```json
{
  "error": {
    "code": "RAG_ERROR",
    "message": "Unable to generate explanation at this time. Your calculation was successful, but the explanation service is temporarily unavailable.",
    "details": {
      "calculation_id": "550e8400-e29b-41d4-a716-446655440000",
      "partial_response": true
    }
  }
}
```

**User Action**: Calculation still valid. Can retry explanation later via `/api/explain`.

**Internal Action**:
1. Return calculation result without explanation
2. Log RAG failure for debugging
3. Alert if RAG failure rate >5%

**Graceful Degradation**:
```typescript
try {
  const explanation = await generateRAGExplanation(calculation);
  return { calculation, explanation };
} catch (ragError) {
  logger.error('RAG failed', { ragError, calculation_id });
  return {
    calculation,
    explanation: {
      summary: 'Explanation temporarily unavailable. Please try /api/explain later.',
      error: 'RAG_ERROR'
    }
  };
}
```

---

## External API Error Handling

### NASA POWER API

**Failure Modes**:
- Timeout (30s)
- Rate limit (429)
- Service unavailable (503)
- Invalid response (malformed JSON)

**Handling**:
```typescript
async function fetchNASAPower(lat, lon) {
  const cacheKey = `climate:solar:${lat}:${lon}`;

  // Check cache first
  const cached = await cache.get(cacheKey);
  if (cached) return cached;

  // Fetch from API
  try {
    const response = await fetch(
      `https://power.larc.nasa.gov/api/...`,
      { timeout: 30000 }
    );

    if (!response.ok) {
      if (response.status === 429) {
        throw new RateLimitError('NASA POWER');
      }
      throw new APIError(`NASA POWER returned ${response.status}`);
    }

    const data = await response.json();
    await cache.set(cacheKey, data, TTL_30_DAYS);
    return data;

  } catch (err) {
    logger.error('NASA POWER fetch failed', { err, lat, lon });

    // Fallback to stale cache
    const staleCache = await cache.get(cacheKey, { allowStale: true });
    if (staleCache) {
      logger.warn('Using stale cache for NASA POWER', { age: staleCache.age });
      return staleCache;
    }

    throw new ClimateAPIError('NASA POWER unavailable and no cache');
  }
}
```

---

### Postcode Lookup API (Postcodes.io)

**Failure Modes**:
- Invalid postcode (404)
- Service unavailable (503)

**Handling**:
```typescript
async function lookupPostcode(postcode) {
  try {
    const response = await fetch(`https://api.postcodes.io/postcodes/${postcode}`);

    if (response.status === 404) {
      throw new InvalidPostcodeError(postcode);
    }

    if (!response.ok) {
      throw new APIError(`Postcodes.io returned ${response.status}`);
    }

    return await response.json();

  } catch (err) {
    if (err instanceof InvalidPostcodeError) {
      throw err;  // Don't retry invalid postcodes
    }

    logger.error('Postcode lookup failed', { err, postcode });
    throw new PostcodeAPIError('Postcode lookup unavailable');
  }
}
```

---

### Vector Store (Pinecone/Weaviate/Qdrant)

**Failure Modes**:
- Query timeout
- Connection failure
- Rate limit

**Handling**:
```typescript
async function retrieveRAGContext(query, filters) {
  try {
    const embedding = await generateEmbedding(query);
    const results = await vectorStore.query({
      vector: embedding,
      filter: filters,
      topK: 5,
      timeout: 5000
    });
    return results;

  } catch (err) {
    logger.error('Vector store query failed', { err, query });

    // Fallback to keyword search or generic context
    return getFallbackContext(filters.system_type);
  }
}

function getFallbackContext(systemType) {
  // Return generic, cached context documents
  return {
    assumptions: DEFAULT_ASSUMPTIONS[systemType],
    benchmarks: DEFAULT_BENCHMARKS[systemType],
    caveats: DEFAULT_CAVEATS
  };
}
```

---

### LLM API (OpenAI/Anthropic)

**Failure Modes**:
- Timeout (30s)
- Rate limit (429)
- Context length exceeded (400)
- Service unavailable (503)

**Handling**:
```typescript
async function generateExplanation(context, calculation) {
  try {
    const response = await llm.complete({
      prompt: buildPrompt(context, calculation),
      max_tokens: 1000,
      timeout: 30000
    });
    return response.text;

  } catch (err) {
    if (err.code === 'context_length_exceeded') {
      // Truncate context and retry
      const truncatedContext = truncateContext(context);
      return await generateExplanation(truncatedContext, calculation);
    }

    if (err.code === 'rate_limit') {
      logger.warn('LLM rate limit hit', { err });
      // Use template-based explanation
      return generateTemplateExplanation(calculation);
    }

    logger.error('LLM generation failed', { err });
    throw new RAGError('Explanation generation failed');
  }
}

function generateTemplateExplanation(calculation) {
  // Fallback to template-based explanation
  return `Your ${calculation.system.specs.capacity_kwp} kWp ${calculation.system.type} system is estimated to generate ${calculation.results.annual_energy_kwh} kWh per year, based on climate data for your location.`;
}
```

---

## Logging and Monitoring

### Error Logging

**What to Log**:
```typescript
logger.error('Error type', {
  error_code: 'CLIMATE_API_ERROR',
  message: err.message,
  stack: err.stack,
  request_id: req.id,
  user_input: sanitize(req.body),  // Remove PII
  timestamp: new Date().toISOString(),
  service: 'NASA_POWER',
  retry_attempt: 3
});
```

**Log Levels**:
- `ERROR`: Failures requiring immediate attention
- `WARN`: Degraded service, using fallbacks
- `INFO`: Normal operations, rate limit hits
- `DEBUG`: Detailed traces (dev only)

### Alerting Thresholds

**Immediate Alerts** (page on-call):
- Any 500 error rate >1% over 5 minutes
- External API failure rate >50% over 5 minutes
- Database connection failures

**Warning Alerts** (Slack/email):
- 4xx error rate >10% over 15 minutes
- External API failure rate >20% over 15 minutes
- RAG failure rate >5% over 15 minutes

### Monitoring Dashboard

**Key Metrics**:
- Request rate (requests/min)
- Error rate by code (%)
- P50/P95/P99 latency (ms)
- External API success rate (%)
- Cache hit rate (%)
- RAG retrieval success rate (%)

**Tools**: Prometheus + Grafana, Datadog, or New Relic

---

## User-Facing Error Messages

### Principle: Be Helpful, Not Technical

**Bad**:
```
Error: Database query failed: relation "calculations" does not exist
```

**Good**:
```
We're experiencing a temporary issue. Please try again in a moment. If the problem persists, contact support at support@example.com with reference ID req_123456.
```

### Error Message Templates

**General Server Error**:
```
Something went wrong on our end. We've been notified and are looking into it. Please try again in a few minutes.
```

**External API Failure**:
```
We're temporarily unable to retrieve climate data. This usually resolves quickly. Please try again in a few minutes.
```

**Invalid Input**:
```
[Specific field] is invalid. [Explain expected format/range]. Example: [provide example].
```

---

## Error Recovery Procedures

### 1. External API Down

**Symptom**: Climate API failures >50%

**Procedure**:
1. Check API status page
2. Enable "use stale cache" mode (up to 7 days old)
3. Add warning to all responses: "Using recent cached data"
4. Monitor API recovery
5. Disable stale cache mode once API recovers

### 2. Database Outage

**Symptom**: Database connection failures

**Procedure**:
1. Check DB health (CPU, connections, replication lag)
2. If read-replica healthy, failover reads
3. If primary down, enable read-only mode (no new calculations)
4. Display maintenance message to users
5. Once recovered, verify data integrity
6. Resume normal operations

### 3. Vector Store Outage

**Symptom**: RAG queries failing

**Procedure**:
1. Enable fallback mode: return calculations without explanations
2. Add message: "Explanations temporarily unavailable"
3. Users can still request explanations later via `/api/explain`
4. Monitor vector store recovery
5. Resume normal RAG operations

### 4. LLM API Rate Limit

**Symptom**: 429 errors from LLM provider

**Procedure**:
1. Enable template-based explanations
2. Queue explanation requests for retry
3. Process queue when rate limit resets
4. Consider upgrading API tier if frequent

---

## Testing Error Scenarios

### Unit Tests

Test each error type:
```typescript
describe('Error Handling', () => {
  it('should return INVALID_POSTCODE for malformed postcode', async () => {
    const res = await request(app)
      .post('/api/calculate')
      .send({ postcode: 'INVALID', system_type: 'solar', system_specs: {...} });

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('INVALID_POSTCODE');
  });

  it('should use cache when climate API fails', async () => {
    mockClimateAPI.mockRejectedValue(new Error('API Down'));
    mockCache.get.mockResolvedValue(cachedClimateData);

    const res = await request(app).post('/api/calculate').send({...});

    expect(res.status).toBe(200);
    expect(res.body.warning).toContain('cached data');
  });
});
```

### Integration Tests

Simulate external API failures:
```typescript
it('should handle NASA POWER timeout gracefully', async () => {
  nock('https://power.larc.nasa.gov')
    .get(/.*/)
    .delayConnection(31000)  // Exceed 30s timeout
    .reply(200, {});

  const res = await request(app).post('/api/calculate').send({...});

  expect(res.status).toBe(503);
  expect(res.body.error.code).toBe('CLIMATE_API_ERROR');
});
```

### Chaos Testing (Production)

Periodically inject failures to test resilience:
- Random API timeouts (5% of requests)
- Simulated cache misses
- Database connection drops

**Tool**: Chaos Monkey, Gremlin, or custom middleware
