"""Calculate energy generation endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import hashlib

from app.db.session import get_db
from app.models.calculation import Calculation
from app.schemas.calculation import (
    CalculationRequest,
    CalculationResponse,
    LocationResponse,
    ResultsResponse,
    SolarSpecs
)
from app.services.postcode import lookup_postcode, PostcodeNotFoundError, PostcodeAPIError
from app.services.climate import get_solar_climate_data, ClimateAPIError
from app.calculators.solar import calculate_solar_output

router = APIRouter()


@router.post("", response_model=CalculationResponse, status_code=status.HTTP_200_OK)
async def calculate_energy(
    request: CalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate renewable energy generation potential.

    This endpoint:
    1. Looks up the postcode to get lat/lon
    2. Retrieves climate data (NASA POWER)
    3. Calculates energy output using industry-standard formulas
    4. Saves the calculation to the database
    5. Returns the results with explanation

    Currently supports:
    - Solar PV systems (wind coming soon)
    """
    try:
        # Step 1: Look up postcode
        try:
            location = await lookup_postcode(request.postcode)
        except PostcodeNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "INVALID_POSTCODE",
                    "message": str(e),
                    "field": "postcode"
                }
            )
        except PostcodeAPIError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "POSTCODE_SERVICE_ERROR",
                    "message": str(e)
                }
            )

        # Step 2: Get climate data
        try:
            climate_data = await get_solar_climate_data(location.latitude, location.longitude)
        except ClimateAPIError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "CLIMATE_API_ERROR",
                    "message": str(e)
                }
            )

        # Step 3: Calculate energy output based on system type
        if request.system_type == "solar":
            if not isinstance(request.system_specs, SolarSpecs):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solar system requires SolarSpecs"
                )

            solar_output = calculate_solar_output(
                capacity_kwp=request.system_specs.capacity_kwp,
                climate_data=climate_data,
                latitude=location.latitude,
                panel_orientation=request.system_specs.panel_orientation,
                panel_tilt_degrees=request.system_specs.panel_tilt_degrees,
                shading_factor=request.system_specs.shading_factor,
                inverter_efficiency=request.system_specs.inverter_efficiency
            )

            annual_energy_kwh = solar_output.annual_kwh
            monthly_energy_kwh = solar_output.monthly_kwh
            assumptions = solar_output.assumptions

        elif request.system_type == "wind":
            # Wind calculation not implemented yet
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={
                    "error": "NOT_IMPLEMENTED",
                    "message": "Wind turbine calculations coming soon!"
                }
            )

        # Step 4: Save to database
        # Hash postcode for privacy (GDPR compliance)
        postcode_hash = hashlib.sha256(request.postcode.encode()).hexdigest()

        calculation = Calculation(
            postcode_hash=postcode_hash,
            latitude=location.latitude,
            longitude=location.longitude,
            region=location.region,
            system_type=request.system_type,
            system_specs=request.system_specs.model_dump(),
            climate_data={
                "monthly_ghi_kwh_m2_day": climate_data.monthly_ghi_kwh_m2_day,
                "annual_ghi_kwh_m2": climate_data.annual_ghi_kwh_m2,
                "source": climate_data.source
            },
            climate_source=climate_data.source,
            annual_energy_kwh=annual_energy_kwh,
            monthly_energy_kwh=monthly_energy_kwh,
            confidence_band_percent=15.0,  # Default UK confidence band
            assumptions=assumptions,
            calculation_version="1.0.0"
        )

        db.add(calculation)
        await db.commit()
        await db.refresh(calculation)

        # Step 5: Build response
        response = CalculationResponse(
            calculation_id=calculation.id,
            created_at=calculation.created_at,
            location=LocationResponse(
                postcode=request.postcode,
                latitude=location.latitude,
                longitude=location.longitude,
                region=location.region
            ),
            system={
                "type": request.system_type,
                "specs": request.system_specs.model_dump()
            },
            results=ResultsResponse(
                annual_energy_kwh=annual_energy_kwh,
                monthly_energy_kwh=monthly_energy_kwh,
                confidence_band_percent=15.0,
                breakdown={
                    "capacity_factor": solar_output.capacity_factor if request.system_type == "solar" else None,
                    "kwh_per_kwp": solar_output.kwh_per_kwp if request.system_type == "solar" else None,
                    "assumptions": assumptions
                }
            ),
            explanation={
                "summary": f"Your {request.system_specs.capacity_kwp if request.system_type == 'solar' else 0} kWp "
                          f"{request.system_type} system in {location.region} is estimated to generate "
                          f"{annual_energy_kwh:,.0f} kWh per year.",
                "assumptions": [
                    f"{request.system_specs.panel_orientation.title()}-facing panels" if request.system_type == "solar" else "",
                    f"{assumptions.get('actual_tilt_degrees')}° tilt angle" if request.system_type == "solar" else "",
                    f"{int(request.system_specs.shading_factor * 100)}% unshaded" if request.system_type == "solar" else "",
                    "Climate data from NASA POWER (20-year average)",
                    "Industry-standard efficiency factors applied"
                ],
                "regional_context": f"Typical {request.system_type} systems in {location.region} generate "
                                   f"{850 if location.region == 'London' else 900}-{950 if location.region == 'London' else 1000} kWh/kWp annually. "
                                   f"Your system is expected to perform at {solar_output.kwh_per_kwp if request.system_type == 'solar' else 0:.0f} kWh/kWp.",
                "caveats": [
                    "Actual output varies ±15% year-to-year due to weather",
                    "Micro-shading from nearby objects not accounted for",
                    "System performance degrades ~0.5% per year",
                    "Professional site survey recommended for accurate assessment"
                ]
            }
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error in calculate_energy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again."
            }
        )
