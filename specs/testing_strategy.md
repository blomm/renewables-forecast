# Testing Strategy

## Overview

This document specifies the testing approach, test types, coverage goals, and testing infrastructure for the renewable energy forecasting system.

## Testing Pyramid

```
        /\
       /  \      E2E Tests (5%)
      /----\     Integration Tests (20%)
     /------\    Unit Tests (75%)
    /--------\
```

**Distribution**:
- **Unit Tests**: 75% of tests - fast, isolated, test individual functions
- **Integration Tests**: 20% of tests - test component interactions, API contracts
- **E2E Tests**: 5% of tests - test full user flows

---

## Test Types

### 1. Unit Tests

**Purpose**: Test individual functions and modules in isolation

**Tools**:
- **Test Runner**: Vitest or Jest
- **Assertion**: Chai or Jest expect
- **Mocking**: Vitest mocks or Jest mocks

**Coverage Goal**: >80% of functions

**Location**: `tests/unit/` or colocated with source files

**Naming Convention**: `{module}.test.ts`

**Examples**:

```typescript
// tests/unit/solar-calculator.test.ts
import { calculateSolarOutput } from '../src/calculators/solar';

describe('Solar Calculator', () => {
  describe('calculateSolarOutput', () => {
    it('should calculate output for optimal south-facing system', () => {
      const result = calculateSolarOutput({
        capacity_kwp: 4.0,
        annual_ghi_kwh_m2: 1000,
        orientation: 'south',
        tilt_degrees: 35,
        shading_factor: 1.0,
        inverter_efficiency: 0.96
      });

      expect(result.annual_kwh).toBeCloseTo(3456, 0);
      expect(result.kwh_per_kwp).toBeCloseTo(864, 0);
    });

    it('should apply orientation penalty for west-facing', () => {
      const south = calculateSolarOutput({
        capacity_kwp: 4.0,
        annual_ghi_kwh_m2: 1000,
        orientation: 'south',
        tilt_degrees: 35
      });

      const west = calculateSolarOutput({
        capacity_kwp: 4.0,
        annual_ghi_kwh_m2: 1000,
        orientation: 'west',
        tilt_degrees: 35
      });

      expect(west.annual_kwh).toBeLessThan(south.annual_kwh * 0.90);
    });

    it('should throw error for invalid capacity', () => {
      expect(() => calculateSolarOutput({
        capacity_kwp: -1,
        annual_ghi_kwh_m2: 1000
      })).toThrow('Capacity must be positive');
    });
  });
});
```

```typescript
// tests/unit/postcode-lookup.test.ts
import { lookupPostcode } from '../src/services/postcode';
import { mockFetch } from '../test-utils/mock-fetch';

describe('Postcode Lookup', () => {
  afterEach(() => {
    mockFetch.restore();
  });

  it('should return lat/lon for valid postcode', async () => {
    mockFetch.mockResolvedValue({
      status: 200,
      json: async () => ({
        result: {
          postcode: 'SW1A 1AA',
          latitude: 51.501009,
          longitude: -0.141588,
          region: 'London'
        }
      })
    });

    const result = await lookupPostcode('SW1A1AA');

    expect(result.latitude).toBe(51.501009);
    expect(result.longitude).toBe(-0.141588);
    expect(result.region).toBe('London');
  });

  it('should throw InvalidPostcodeError for 404', async () => {
    mockFetch.mockResolvedValue({
      status: 404,
      json: async () => ({ error: 'Not found' })
    });

    await expect(lookupPostcode('INVALID')).rejects.toThrow('Invalid postcode');
  });
});
```

---

### 2. Integration Tests

**Purpose**: Test interactions between components, external APIs, database

**Tools**:
- **Test Runner**: Vitest or Jest
- **API Testing**: Supertest
- **DB Testing**: In-memory PostgreSQL or test database
- **API Mocking**: MSW (Mock Service Worker) or Nock

**Coverage Goal**: All major workflows and API endpoints

**Location**: `tests/integration/`

**Examples**:

```typescript
// tests/integration/api/calculate.test.ts
import request from 'supertest';
import { app } from '../src/app';
import { setupTestDB, teardownTestDB } from '../test-utils/db';
import { mockClimateAPI } from '../test-utils/mock-apis';

describe('POST /api/calculate', () => {
  beforeAll(async () => {
    await setupTestDB();
    mockClimateAPI.start();
  });

  afterAll(async () => {
    await teardownTestDB();
    mockClimateAPI.stop();
  });

  it('should calculate solar output for valid input', async () => {
    const response = await request(app)
      .post('/api/calculate')
      .send({
        postcode: 'SW1A 1AA',
        system_type: 'solar',
        system_specs: {
          capacity_kwp: 4.0,
          panel_orientation: 'south',
          panel_tilt_degrees: 35
        }
      });

    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({
      calculation_id: expect.any(String),
      location: {
        postcode: 'SW1A 1AA',
        latitude: expect.any(Number),
        longitude: expect.any(Number)
      },
      results: {
        annual_energy_kwh: expect.any(Number),
        monthly_energy_kwh: expect.arrayOf(expect.any(Number)),
        confidence_band_percent: expect.any(Number)
      },
      explanation: {
        summary: expect.any(String),
        assumptions: expect.any(Array)
      }
    });

    // Verify stored in database
    const calculation = await db.calculations.findById(response.body.calculation_id);
    expect(calculation).toBeDefined();
  });

  it('should return 400 for invalid postcode', async () => {
    const response = await request(app)
      .post('/api/calculate')
      .send({
        postcode: 'INVALID',
        system_type: 'solar',
        system_specs: { capacity_kwp: 4.0 }
      });

    expect(response.status).toBe(400);
    expect(response.body.error.code).toBe('INVALID_POSTCODE');
  });

  it('should use cache for repeated location requests', async () => {
    const spy = mockClimateAPI.spyOn('NASA_POWER');

    // First request - should hit API
    await request(app).post('/api/calculate').send({ postcode: 'SW1A 1AA', ... });
    expect(spy).toHaveBeenCalledTimes(1);

    // Second request - should use cache
    await request(app).post('/api/calculate').send({ postcode: 'SW1A 1AA', ... });
    expect(spy).toHaveBeenCalledTimes(1);  // Not called again
  });
});
```

```typescript
// tests/integration/feedback-learning.test.ts
import { submitFeedback, updateRegionalFactors } from '../src/services/feedback';
import { setupTestDB, teardownTestDB } from '../test-utils/db';

describe('Feedback Learning', () => {
  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await teardownTestDB();
  });

  it('should update regional correction factor after 10+ feedback samples', async () => {
    const region = 'Test Region';

    // Create a calculation
    const calculation = await createTestCalculation({
      region,
      system_type: 'solar',
      predicted_kwh: 3600
    });

    // Submit 10 feedback samples, all 10% lower than predicted
    for (let i = 0; i < 10; i++) {
      await submitFeedback({
        calculation_id: calculation.id,
        actual_annual_kwh: 3240  // 90% of predicted
      });
    }

    // Run learning job
    await updateRegionalFactors();

    // Check that correction factor was updated
    const factor = await db.regionalFactors.findOne({ region, system_type: 'solar' });
    expect(factor.correction_factor).toBeCloseTo(0.90, 2);
    expect(factor.sample_count).toBe(10);
  });
});
```

---

### 3. E2E Tests

**Purpose**: Test full user flows from UI to database

**Tools**:
- **Browser Automation**: Playwright or Cypress
- **API Testing**: Supertest (for API-only flows)

**Coverage Goal**: Critical user paths

**Location**: `tests/e2e/`

**Examples**:

```typescript
// tests/e2e/calculate-flow.spec.ts
import { test, expect } from '@playwright/test';

test('User can calculate solar output and ask follow-up question', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Enter postcode
  await page.fill('[data-testid="postcode-input"]', 'SW1A 1AA');

  // Select solar system
  await page.click('[data-testid="system-type-solar"]');

  // Enter system specs
  await page.fill('[data-testid="capacity-input"]', '4.0');
  await page.selectOption('[data-testid="orientation-select"]', 'south');

  // Submit
  await page.click('[data-testid="calculate-button"]');

  // Wait for results
  await page.waitForSelector('[data-testid="results"]');

  // Check results displayed
  const annualOutput = await page.textContent('[data-testid="annual-output"]');
  expect(annualOutput).toContain('kWh');

  // Ask follow-up question
  await page.fill('[data-testid="question-input"]', 'Why is my estimate lower than average?');
  await page.click('[data-testid="ask-button"]');

  // Wait for explanation
  await page.waitForSelector('[data-testid="explanation"]');
  const explanation = await page.textContent('[data-testid="explanation"]');
  expect(explanation.length).toBeGreaterThan(50);
});
```

---

## Test Data Management

### Fixtures

**Location**: `tests/fixtures/`

**Examples**:

```typescript
// tests/fixtures/climate-data.ts
export const londonSolarData = {
  source: 'NASA_POWER',
  data: {
    monthly_ghi_kwh_m2_day: [1.2, 2.1, 3.5, 4.8, 5.9, 6.2, 5.8, 5.0, 3.8, 2.5, 1.4, 1.0],
    annual_ghi_kwh_m2: 1067
  }
};

export const manchesterWindData = {
  source: 'GLOBAL_WIND_ATLAS',
  data: {
    mean_wind_speed_ms: 6.2,
    weibull_a: 6.8,
    weibull_k: 2.0
  }
};
```

```typescript
// tests/fixtures/calculations.ts
export const sampleSolarCalculation = {
  postcode: 'SW1A 1AA',
  latitude: 51.501009,
  longitude: -0.141588,
  region: 'London',
  system_type: 'solar',
  system_specs: {
    capacity_kwp: 4.0,
    panel_orientation: 'south',
    panel_tilt_degrees: 35,
    shading_factor: 1.0,
    inverter_efficiency: 0.96
  },
  results: {
    annual_energy_kwh: 3456,
    monthly_energy_kwh: [120, 180, 290, 380, 450, 480, 470, 420, 340, 250, 140, 110],
    confidence_band_percent: 15
  }
};
```

### Test Database

**Strategy**: Use separate test database, reset before each test suite

```typescript
// test-utils/db.ts
import { Pool } from 'pg';

let testPool: Pool;

export async function setupTestDB() {
  testPool = new Pool({
    host: 'localhost',
    port: 5433,  // Separate test DB port
    database: 'renewables_test',
    user: 'test',
    password: 'test'
  });

  // Run migrations
  await runMigrations(testPool);

  // Seed with initial data
  await seedTestData(testPool);
}

export async function teardownTestDB() {
  await testPool.end();
}

export async function resetTestDB() {
  await testPool.query('TRUNCATE TABLE calculations, feedback, regional_factors CASCADE');
  await seedTestData(testPool);
}
```

### Mock External APIs

**Strategy**: Use MSW (Mock Service Worker) to intercept HTTP requests

```typescript
// test-utils/mock-apis.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export const mockClimateAPI = setupServer(
  rest.get('https://api.postcodes.io/postcodes/:postcode', (req, res, ctx) => {
    return res(ctx.json({
      result: {
        postcode: req.params.postcode,
        latitude: 51.501009,
        longitude: -0.141588,
        region: 'London'
      }
    }));
  }),

  rest.get('https://power.larc.nasa.gov/api/*', (req, res, ctx) => {
    return res(ctx.json({
      parameters: {
        ALLSKY_SFC_SW_DWN: {
          JAN: 1.2, FEB: 2.1, MAR: 3.5, APR: 4.8,
          MAY: 5.9, JUN: 6.2, JUL: 5.8, AUG: 5.0,
          SEP: 3.8, OCT: 2.5, NOV: 1.4, DEC: 1.0
        }
      }
    }));
  })
);
```

---

## Performance Testing

**Purpose**: Ensure system meets latency and throughput requirements

**Tools**:
- **Load Testing**: k6, Artillery, or Apache JMeter
- **Profiling**: Node.js built-in profiler, Clinic.js

**Scenarios**:

```javascript
// tests/performance/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests < 2s
    http_req_failed: ['rate<0.01'],     // <1% errors
  },
};

export default function () {
  const payload = JSON.stringify({
    postcode: 'SW1A 1AA',
    system_type: 'solar',
    system_specs: {
      capacity_kwp: 4.0,
      panel_orientation: 'south'
    }
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  const res = http.post('http://localhost:3000/api/calculate', payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response has calculation_id': (r) => JSON.parse(r.body).calculation_id !== undefined,
  });

  sleep(1);
}
```

**Performance Goals**:
- P95 latency < 2000ms for `/api/calculate`
- P95 latency < 500ms for `/api/explain`
- Throughput: 100 requests/second (single instance)
- Cache hit rate: >80% for climate data

---

## Security Testing

**Purpose**: Identify vulnerabilities before production

**Tools**:
- **SAST**: npm audit, Snyk, or SonarQube
- **DAST**: OWASP ZAP
- **Dependency Scanning**: Dependabot

**Tests**:

```typescript
// tests/security/sql-injection.test.ts
describe('SQL Injection Protection', () => {
  it('should not allow SQL injection in postcode field', async () => {
    const maliciousPostcode = "'; DROP TABLE calculations; --";

    const response = await request(app)
      .post('/api/calculate')
      .send({
        postcode: maliciousPostcode,
        system_type: 'solar',
        system_specs: { capacity_kwp: 4.0 }
      });

    expect(response.status).toBe(400);  // Rejected, not executed

    // Verify table still exists
    const tableExists = await db.query("SELECT to_regclass('calculations')");
    expect(tableExists.rows[0].to_regclass).not.toBeNull();
  });
});
```

```typescript
// tests/security/xss.test.ts
describe('XSS Protection', () => {
  it('should sanitize user notes in feedback', async () => {
    const xssPayload = '<script>alert("XSS")</script>';

    const response = await request(app)
      .post('/api/feedback')
      .send({
        calculation_id: 'valid-id',
        actual_annual_kwh: 3200,
        notes: xssPayload
      });

    expect(response.status).toBe(201);

    // Verify stored notes are sanitized
    const feedback = await db.feedback.findById(response.body.feedback_id);
    expect(feedback.notes).not.toContain('<script>');
  });
});
```

---

## Test Coverage

**Tools**: nyc (Istanbul) or c8

**Goal**: >80% code coverage

**Configuration** (package.json):
```json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:integration": "vitest tests/integration",
    "test:e2e": "playwright test"
  },
  "vitest": {
    "coverage": {
      "provider": "c8",
      "reporter": ["text", "html", "lcov"],
      "exclude": ["tests/**", "**/*.test.ts"]
    }
  }
}
```

**Coverage Report**:
```bash
npm run test:coverage

# Output:
File                     | % Stmts | % Branch | % Funcs | % Lines |
-------------------------|---------|----------|---------|---------|
All files                |   85.2  |   78.5   |   82.1  |   85.8  |
 src/calculators         |   92.3  |   88.1   |   90.5  |   93.0  |
  solar.ts               |   95.1  |   91.2   |   94.3  |   95.8  |
  wind.ts                |   89.5  |   85.0   |   86.7  |   90.2  |
 src/services            |   81.2  |   72.8   |   78.3  |   82.5  |
  postcode.ts            |   88.0  |   80.0   |   85.0  |   89.0  |
  climate.ts             |   74.4  |   65.6   |   71.6  |   76.0  |
```

---

## CI/CD Integration

**Pipeline** (GitHub Actions example):

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: renewables_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/renewables_test

      - name: Upload coverage
        uses: codecov/codecov-action@v3

      - name: Run security scan
        run: npm audit --audit-level=high
```

---

## Test Maintenance

**Principles**:
1. **Keep tests simple**: One assertion per test when possible
2. **Avoid brittle tests**: Don't assert on exact strings, use patterns
3. **DRY**: Use fixtures and helpers, but keep tests readable
4. **Fast feedback**: Run unit tests on every change, integration tests before commit
5. **Update tests with code**: Refactor tests when refactoring code

**Review Checklist**:
- [ ] All new code has unit tests
- [ ] Changed behavior has updated tests
- [ ] Integration tests cover API contracts
- [ ] No flaky tests (inconsistent pass/fail)
- [ ] Coverage >80%
- [ ] Tests run in <30 seconds (unit), <5 minutes (integration)
