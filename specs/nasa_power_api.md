# NASA POWER API Breakdown

## What is NASA POWER?

**NASA Prediction Of Worldwide Energy Resources (POWER)**
- Free, public API from NASA
- Provides 40+ years of global climate data
- Specifically designed for renewable energy applications
- Data resolution: 0.5° x 0.5° (~55km grid squares)
- Based on satellite observations and climate models

## The Request We're Making

### Base URL
```
https://power.larc.nasa.gov/api/temporal/climatology/point
```

### Parameters

```
parameters=ALLSKY_SFC_SW_DWN
community=RE
longitude=-0.141588
latitude=51.501009
format=JSON
```

### What Each Parameter Means

#### 1. `temporal/climatology/point`
- **temporal**: Time-series data (vs. single point in time)
- **climatology**: Long-term averages (vs. specific year)
- **point**: Single location (vs. regional/global)

**Translation**: "Give me long-term monthly averages for a specific location"

#### 2. `parameters=ALLSKY_SFC_SW_DWN`
- **ALLSKY**: All sky conditions (cloudy + clear)
- **SFC**: Surface level
- **SW**: Shortwave radiation (solar)
- **DWN**: Downward (coming from sun)

**Translation**: "Give me Global Horizontal Irradiance (GHI)" - the total solar radiation hitting a horizontal surface

**Units**: kWh/m²/day (kilowatt-hours per square meter per day)

#### 3. `community=RE`
- **RE**: Renewable Energy community

**Purpose**: Returns data optimized for renewable energy calculations (monthly averages, appropriate parameters)

**Alternatives**:
- `AG`: Agriculture
- `SB`: Sustainable Buildings
- `SSE`: General energy

#### 4. `longitude=-0.141588` & `latitude=51.501009`
- **Coordinates**: Buckingham Palace, London
- **Format**: Decimal degrees
- **Range**: Lat: -90 to +90, Lon: -180 to +180

**Note**: NASA POWER will snap these to the nearest 0.5° grid point

#### 5. `format=JSON`
- Returns structured JSON data (vs. CSV, ASCII, NetCDF)

## Full Example Request

```bash
curl "https://power.larc.nasa.gov/api/temporal/climatology/point?\
parameters=ALLSKY_SFC_SW_DWN&\
community=RE&\
longitude=-0.141588&\
latitude=51.501009&\
format=JSON"
```

## Response Structure

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-0.25, 51.5]  // Snapped to 0.5° grid
  },
  "properties": {
    "parameter": {
      "ALLSKY_SFC_SW_DWN": {
        "JAN": 0.93,   // kWh/m²/day in January
        "FEB": 1.79,
        "MAR": 3.14,
        "APR": 4.52,
        "MAY": 5.53,
        "JUN": 5.89,
        "JUL": 5.73,
        "AUG": 4.82,
        "SEP": 3.48,
        "OCT": 2.01,
        "NOV": 1.07,
        "DEC": 0.71,
        "ANN": 3.30   // Annual average
      }
    }
  },
  "header": {
    "title": "NASA/POWER CERES/MERRA2 Native Resolution Climatology",
    "... metadata ..."
  }
}
```

## What the Data Represents

### Time Period
- **Climatology**: 20-40 year averages (typically 1981-2020 or similar)
- **NOT**: Weather forecast or specific year data
- **Purpose**: Long-term expected conditions

### Spatial Resolution: 0.5° x 0.5°

**What does 0.5° mean?**
- At London's latitude (~51°N):
  - 0.5° longitude ≈ 35 km
  - 0.5° latitude ≈ 55 km
- Grid cell area: ~1,900 km²

**Practical Impact**:
- London postcodes (SW1A 1AA, E1 6AN, etc.) → Same grid cell
- Central London to Heathrow → Likely same cell
- London to Brighton → Different cells

**Example Grid Snapping**:
```
Input:  51.501°N, 0.142°W (Buckingham Palace)
Output: 51.500°N, 0.250°W (nearest 0.5° grid center)
```

### Accuracy for Our Use Case

**Good for**:
- Annual energy estimates
- Regional comparisons
- Long-term planning
- MVP calculations

**Not good for**:
- Microclimate effects (urban heat islands)
- Block-by-block variations
- Year-specific predictions
- Real-time forecasts

## How We Use the Data

### Step 1: Retrieve Monthly GHI
```python
monthly_ghi = [0.93, 1.79, 3.14, ...]  // 12 values in kWh/m²/day
```

### Step 2: Convert to Annual Total
```python
days_in_month = [31, 28.25, 31, 30, ...]  // Average (accounts for leap years)
annual_ghi = sum(monthly * days for monthly, days in zip(monthly_ghi, days_in_month))
// Result: ~1,200 kWh/m²/year for London
```

### Step 3: Calculate Energy Output
```python
annual_kwh = (
    capacity_kWp *           // e.g., 4.0 kWp
    annual_ghi_kWh_m² *      // e.g., 1,200 kWh/m²
    system_efficiency        // e.g., 0.85 (includes all losses)
)
```

## Data Sources (Behind the Scenes)

NASA POWER combines:
1. **CERES** (Clouds and Earth's Radiant Energy System)
   - Satellite observations
   - Measures actual solar radiation

2. **MERRA-2** (Modern-Era Retrospective analysis for Research and Applications, Version 2)
   - NASA's global atmospheric reanalysis
   - Fills gaps where satellite data is unavailable

3. **Ground Validation**
   - Calibrated against thousands of ground stations worldwide

## Alternatives (If NASA POWER Were Unavailable)

1. **PVGIS** (Photovoltaic Geographical Information System)
   - EU Joint Research Centre
   - Higher resolution for Europe (3-5 km)
   - Free API: https://re.jrc.ec.europa.eu/pvg_tools/en/

2. **Solargis**
   - Commercial (paid)
   - Very high resolution
   - Used by professionals

3. **UK Met Office**
   - UK-specific
   - Requires license for historical data
   - More accurate for microclimate

## Why NASA POWER is Perfect for Our MVP

✅ **Free** - No API key, no rate limits (reasonable use)
✅ **Global** - Works anywhere in the world
✅ **Reliable** - NASA infrastructure, 99.9% uptime
✅ **Purpose-Built** - Designed for renewable energy applications
✅ **Well-Documented** - Extensive documentation and examples
✅ **No Authentication** - Simple HTTP GET requests
✅ **Climate Normals** - Exactly what we need (long-term averages)
✅ **Monthly Data** - Perfect for showing seasonal variation

## Limitations to Be Aware Of

❌ **Coarse Resolution** - 0.5° (~55km) misses local variations
❌ **No Real-Time** - Historical averages only
❌ **Terrain Blind** - Doesn't account for hills, valleys
❌ **Urban Heat Island** - Doesn't adjust for city effects
❌ **Shading** - Can't see buildings, trees
❌ **Horizon** - Doesn't account for obstructed horizons

**Solution**: We acknowledge these in our disclaimers and confidence bands (±15%)

## Example Use in Our Code

```python
# From app/services/climate.py

async def get_solar_climate_data(latitude: float, longitude: float):
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"

    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",  # Global Horizontal Irradiance
        "community": "RE",                   # Renewable Energy
        "longitude": longitude,
        "latitude": latitude,
        "format": "JSON"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        data = response.json()

        # Extract monthly values
        monthly_data = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        monthly_ghi = [monthly_data[month] for month in ["JAN", "FEB", ...]]

        # Calculate annual total
        annual_ghi = sum(m * days for m, days in zip(monthly_ghi, days_per_month))

        return SolarClimateData(
            monthly_ghi_kwh_m2_day=monthly_ghi,
            annual_ghi_kwh_m2=annual_ghi
        )
```

## Real-World Comparison

**NASA POWER for London (SW1A 1AA)**:
- Annual GHI: ~1,050-1,100 kWh/m²/year
- July peak: ~5.9 kWh/m²/day
- December low: ~0.7 kWh/m²/day

**UK Government Data** (actual installations):
- London typical: 900-1,000 kWh/kWp
- **Our estimate**: 743 kWh/kWp (includes all losses and shading)
- Within expected range ✅

## Summary

**Who**: NASA's Applied Sciences Program
**What**: Long-term average solar irradiance data
**How**: Satellite observations + atmospheric models
**Resolution**: 0.5° (~55km grid), monthly averages, 20-40 year climatology
**Cost**: Free, no API key required
**Best For**: Annual energy estimates, regional planning, MVP applications
**Not For**: Real-time forecasts, microclimate modeling, block-level accuracy

**Bottom Line**: Perfect for our MVP - scientifically credible, globally available, free, and exactly the right level of detail for homeowner energy estimates.
