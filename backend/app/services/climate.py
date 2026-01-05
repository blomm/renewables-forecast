"""Climate data service using NASA POWER API."""

import httpx
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


class ClimateAPIError(Exception):
    """Raised when climate API fails."""
    pass


class SolarClimateData:
    """Solar climate data from NASA POWER."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        monthly_ghi_kwh_m2_day: list[float],
        annual_ghi_kwh_m2: float,
        source: str = "NASA_POWER"
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.monthly_ghi_kwh_m2_day = monthly_ghi_kwh_m2_day
        self.annual_ghi_kwh_m2 = annual_ghi_kwh_m2
        self.source = source

    def __repr__(self):
        return f"<SolarClimateData ({self.latitude}, {self.longitude}) - {self.annual_ghi_kwh_m2:.1f} kWh/m²/year>"


# Simple in-memory cache (replace with Redis in production)
_climate_cache: dict[str, SolarClimateData] = {}


async def get_solar_climate_data(latitude: float, longitude: float) -> SolarClimateData:
    """
    Get solar irradiance climate data from NASA POWER API.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        SolarClimateData object with monthly and annual GHI values

    Raises:
        ClimateAPIError: If API call fails
    """
    # Create cache key (rounded to 2 decimal places to increase hit rate)
    cache_key = f"{latitude:.2f},{longitude:.2f}"

    # Check cache first
    if cache_key in _climate_cache:
        return _climate_cache[cache_key]

    # NASA POWER API endpoint for climatology (long-term averages)
    url = f"{settings.nasa_power_base_url}/temporal/climatology/point"

    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",  # Global Horizontal Irradiance
        "community": "RE",  # Renewable Energy
        "longitude": longitude,
        "latitude": latitude,
        "format": "JSON"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise ClimateAPIError(f"NASA POWER API returned status {response.status_code}")

            data = response.json()

            # Extract monthly GHI values
            parameters = data.get("properties", {}).get("parameter", {})
            monthly_data = parameters.get("ALLSKY_SFC_SW_DWN", {})

            if not monthly_data:
                raise ClimateAPIError("No GHI data returned from NASA POWER")

            # Convert monthly averages (kWh/m²/day) to list
            # NASA POWER returns data as: {"JAN": 1.2, "FEB": 2.1, ...}
            month_order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

            monthly_ghi = [monthly_data.get(month, 0.0) for month in month_order]

            # Calculate annual total (monthly average * days in each month)
            days_in_month = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # .25 for leap year avg
            annual_ghi = sum(m * d for m, d in zip(monthly_ghi, days_in_month))

            climate_data = SolarClimateData(
                latitude=latitude,
                longitude=longitude,
                monthly_ghi_kwh_m2_day=monthly_ghi,
                annual_ghi_kwh_m2=annual_ghi,
                source="NASA_POWER"
            )

            # Cache the result
            _climate_cache[cache_key] = climate_data

            return climate_data

    except httpx.TimeoutException:
        raise ClimateAPIError("NASA POWER API request timed out")
    except httpx.RequestError as e:
        raise ClimateAPIError(f"NASA POWER API request failed: {str(e)}")
    except (KeyError, ValueError) as e:
        raise ClimateAPIError(f"Failed to parse NASA POWER response: {str(e)}")
