"""Pydantic schemas for calculation endpoints."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class SolarSpecs(BaseModel):
    """Solar PV system specifications."""

    capacity_kwp: float = Field(..., ge=0.5, le=50, description="System capacity in kWp")
    panel_orientation: Optional[Literal["north", "south", "east", "west", "south-east", "south-west", "north-east", "north-west"]] = Field(
        default="south", description="Panel orientation"
    )
    panel_tilt_degrees: Optional[float] = Field(
        default=None, ge=0, le=90, description="Panel tilt angle in degrees (defaults to optimal for latitude)"
    )
    shading_factor: Optional[float] = Field(
        default=1.0, ge=0, le=1.0, description="Shading factor: 1.0 = no shading, 0.0 = completely shaded"
    )
    inverter_efficiency: Optional[float] = Field(
        default=0.96, ge=0.9, le=0.99, description="Inverter efficiency (typically 0.96)"
    )


class WindSpecs(BaseModel):
    """Wind turbine system specifications."""

    rated_power_kw: float = Field(..., ge=0.5, le=20, description="Rated power in kW")
    hub_height_m: float = Field(..., ge=5, le=30, description="Hub height in meters")
    turbine_model: Optional[str] = Field(default=None, description="Turbine model name")


class CalculationRequest(BaseModel):
    """Request to calculate energy generation."""

    postcode: str = Field(..., min_length=5, max_length=8, description="UK postcode")
    system_type: Literal["solar", "wind"] = Field(..., description="Type of renewable energy system")
    system_specs: SolarSpecs | WindSpecs = Field(..., description="System specifications")

    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, v: str) -> str:
        """Normalize postcode format."""
        # Remove spaces and convert to uppercase
        normalized = v.replace(" ", "").upper()
        # Add space before last 3 characters (UK postcode format)
        if len(normalized) >= 5:
            normalized = f"{normalized[:-3]} {normalized[-3:]}"
        return normalized


class LocationResponse(BaseModel):
    """Location information."""

    postcode: str
    latitude: float
    longitude: float
    region: str


class ResultsResponse(BaseModel):
    """Calculation results."""

    annual_energy_kwh: float = Field(..., description="Estimated annual energy generation in kWh")
    monthly_energy_kwh: list[float] = Field(..., description="Monthly energy generation breakdown (12 values)")
    confidence_band_percent: float = Field(..., description="Confidence interval (±%)")

    breakdown: Optional[dict] = Field(
        default=None,
        description="Optional detailed breakdown of calculation factors"
    )


class CalculationResponse(BaseModel):
    """Response from energy calculation."""

    calculation_id: UUID
    created_at: datetime

    location: LocationResponse

    system: dict = Field(..., description="System specifications used")

    results: ResultsResponse

    explanation: Optional[dict] = Field(
        default=None,
        description="AI-generated explanation (requires OpenAI key)"
    )

    disclaimer: str = Field(
        default="This is an estimate based on long-term climate averages. Actual performance may vary.",
        description="Legal disclaimer"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
                        "panel_tilt_degrees": 35
                    }
                },
                "results": {
                    "annual_energy_kwh": 3456.78,
                    "monthly_energy_kwh": [120.5, 180.2, 290.8, 380.5, 450.2, 480.9, 470.3, 420.6, 340.7, 250.4, 140.8, 110.2],
                    "confidence_band_percent": 15.0
                }
            }
        }
