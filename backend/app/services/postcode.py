"""Postcode lookup service using Postcodes.io API."""

import httpx
from typing import Optional
from functools import lru_cache
from app.core.config import get_settings

settings = get_settings()


class PostcodeNotFoundError(Exception):
    """Raised when postcode is not found."""
    pass


class PostcodeAPIError(Exception):
    """Raised when postcode API fails."""
    pass


class Location:
    """Location data from postcode lookup."""

    def __init__(self, postcode: str, latitude: float, longitude: float, region: str):
        self.postcode = postcode
        self.latitude = latitude
        self.longitude = longitude
        self.region = region

    def __repr__(self):
        return f"<Location {self.postcode} ({self.latitude}, {self.longitude})>"


# Simple in-memory cache for development (replace with Redis in production)
_postcode_cache: dict[str, Location] = {}


async def lookup_postcode(postcode: str) -> Location:
    """
    Look up a UK postcode and return location data.

    Args:
        postcode: UK postcode (e.g., "SW1A 1AA")

    Returns:
        Location object with lat/lon and region

    Raises:
        PostcodeNotFoundError: If postcode is invalid or not found
        PostcodeAPIError: If API call fails
    """
    # Normalize postcode
    normalized = postcode.replace(" ", "").upper()

    # Check cache first
    if normalized in _postcode_cache:
        return _postcode_cache[normalized]

    # Call Postcodes.io API
    url = f"{settings.postcodes_io_base_url}/postcodes/{normalized}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code == 404:
                raise PostcodeNotFoundError(f"Postcode '{postcode}' not found")

            if response.status_code != 200:
                raise PostcodeAPIError(f"Postcodes.io API returned status {response.status_code}")

            data = response.json()

            if data.get("status") != 200:
                raise PostcodeNotFoundError(f"Postcode '{postcode}' not found")

            result = data.get("result", {})

            location = Location(
                postcode=result.get("postcode", postcode),
                latitude=result.get("latitude"),
                longitude=result.get("longitude"),
                region=result.get("region") or result.get("admin_district") or "Unknown"
            )

            # Cache the result
            _postcode_cache[normalized] = location

            return location

    except httpx.TimeoutException:
        raise PostcodeAPIError("Postcode lookup timed out")
    except httpx.RequestError as e:
        raise PostcodeAPIError(f"Postcode lookup failed: {str(e)}")
