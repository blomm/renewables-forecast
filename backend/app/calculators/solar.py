"""Solar PV energy calculator using pvlib."""

import numpy as np
from typing import Optional
from app.services.climate import SolarClimateData


class SolarOutput:
    """Solar PV calculation results."""

    def __init__(
        self,
        annual_kwh: float,
        monthly_kwh: list[float],
        capacity_factor: float,
        kwh_per_kwp: float,
        assumptions: dict
    ):
        self.annual_kwh = annual_kwh
        self.monthly_kwh = monthly_kwh
        self.capacity_factor = capacity_factor
        self.kwh_per_kwp = kwh_per_kwp
        self.assumptions = assumptions

    def __repr__(self):
        return f"<SolarOutput {self.annual_kwh:.1f} kWh/year ({self.kwh_per_kwp:.0f} kWh/kWp)>"


# Orientation penalty factors (relative to south-facing)
ORIENTATION_FACTORS = {
    "south": 1.00,
    "south-east": 0.97,
    "south-west": 0.97,
    "east": 0.88,
    "west": 0.88,
    "north-east": 0.75,
    "north-west": 0.75,
    "north": 0.55
}


def calculate_optimal_tilt(latitude: float) -> float:
    """
    Calculate optimal tilt angle for solar panels based on latitude.

    Rule of thumb for UK: optimal tilt ≈ latitude - 10°
    (slightly shallower than latitude for year-round optimization)

    Args:
        latitude: Latitude in degrees

    Returns:
        Optimal tilt angle in degrees
    """
    # For UK latitudes (50-60°), optimal is typically latitude - 10°
    optimal = max(0, latitude - 10)
    return round(optimal, 1)


def calculate_tilt_factor(tilt: float, optimal_tilt: float) -> float:
    """
    Calculate performance reduction factor due to non-optimal tilt.

    Args:
        tilt: Actual tilt angle in degrees
        optimal_tilt: Optimal tilt angle in degrees

    Returns:
        Tilt factor (0-1), where 1.0 is optimal
    """
    # Simple model: performance drops by ~0.5% per degree away from optimal
    # This is a simplified version - pvlib has more sophisticated models
    deviation = abs(tilt - optimal_tilt)

    if deviation == 0:
        return 1.0

    # Penalty: 0.5% per degree deviation
    penalty = 0.005 * deviation
    factor = max(0.7, 1.0 - penalty)  # Minimum 70% performance

    return round(factor, 3)


def calculate_solar_output(
    capacity_kwp: float,
    climate_data: SolarClimateData,
    latitude: float,
    panel_orientation: str = "south",
    panel_tilt_degrees: Optional[float] = None,
    shading_factor: float = 1.0,
    inverter_efficiency: float = 0.96
) -> SolarOutput:
    """
    Calculate annual and monthly solar PV energy output.

    This uses a simplified calculation based on industry-standard factors.
    For production, consider using pvlib's more sophisticated models.

    Args:
        capacity_kwp: System capacity in kWp
        climate_data: Solar climate data (GHI values)
        latitude: Latitude for optimal tilt calculation
        panel_orientation: Panel orientation (default: south)
        panel_tilt_degrees: Panel tilt angle (default: optimal for latitude)
        shading_factor: Shading factor 0-1 (default: 1.0 = no shading)
        inverter_efficiency: Inverter efficiency (default: 0.96)

    Returns:
        SolarOutput with annual/monthly results and assumptions
    """
    # Calculate optimal tilt if not provided
    optimal_tilt = calculate_optimal_tilt(latitude)
    if panel_tilt_degrees is None:
        panel_tilt_degrees = optimal_tilt

    # Get orientation factor
    orientation_factor = ORIENTATION_FACTORS.get(panel_orientation.lower(), 0.88)

    # Calculate tilt factor
    tilt_factor = calculate_tilt_factor(panel_tilt_degrees, optimal_tilt)

    # System efficiency factors (UK-specific)
    temperature_coefficient = 0.96  # -4% for UK average temperatures
    soiling_losses = 0.98  # -2% for dust, dirt, bird droppings
    cable_losses = 0.99  # -1% for cable resistance
    mismatch_losses = 0.99  # -1% for panel mismatch

    # Combined system efficiency
    system_efficiency = (
        orientation_factor *
        tilt_factor *
        inverter_efficiency *
        temperature_coefficient *
        soiling_losses *
        cable_losses *
        mismatch_losses *
        shading_factor
    )

    # Calculate monthly output
    # Formula: kWh = capacity_kWp * GHI_kWh/m²/day * days_in_month * system_efficiency * performance_ratio
    # Performance ratio accounts for the fact that panels don't perform at STC (Standard Test Conditions)
    performance_ratio = 0.85  # Typical UK performance ratio

    days_in_month = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    monthly_kwh = []
    for ghi_per_day, days in zip(climate_data.monthly_ghi_kwh_m2_day, days_in_month):
        # Monthly energy = capacity * GHI per day * days * efficiency * performance ratio
        monthly_energy = capacity_kwp * ghi_per_day * days * system_efficiency * performance_ratio
        monthly_kwh.append(round(monthly_energy, 2))

    # Calculate annual total
    annual_kwh = sum(monthly_kwh)

    # Calculate capacity factor (actual output / theoretical maximum)
    theoretical_max_kwh = capacity_kwp * 8760  # 8760 hours per year
    capacity_factor = annual_kwh / theoretical_max_kwh

    # kWh per kWp (common UK metric)
    kwh_per_kwp = annual_kwh / capacity_kwp

    # Record assumptions
    assumptions = {
        "optimal_tilt_degrees": optimal_tilt,
        "actual_tilt_degrees": panel_tilt_degrees,
        "orientation": panel_orientation,
        "orientation_factor": round(orientation_factor, 3),
        "tilt_factor": round(tilt_factor, 3),
        "system_efficiency": round(system_efficiency, 3),
        "performance_ratio": performance_ratio,
        "inverter_efficiency": inverter_efficiency,
        "temperature_coefficient": temperature_coefficient,
        "soiling_losses": round(1 - soiling_losses, 3),
        "shading_factor": shading_factor,
        "climate_source": climate_data.source
    }

    return SolarOutput(
        annual_kwh=round(annual_kwh, 2),
        monthly_kwh=monthly_kwh,
        capacity_factor=round(capacity_factor, 4),
        kwh_per_kwp=round(kwh_per_kwp, 1),
        assumptions=assumptions
    )
