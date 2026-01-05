"""Calculation model - stores energy generation calculations."""

from sqlalchemy import Column, String, Numeric, DateTime, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Calculation(Base):
    """Energy generation calculation record."""

    __tablename__ = "calculations"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Location (anonymized after 90 days)
    postcode_hash = Column(String(64), nullable=True)  # SHA256 hash
    latitude = Column(Numeric(9, 6), nullable=False)
    longitude = Column(Numeric(9, 6), nullable=False)
    region = Column(String(50), nullable=True)

    # System specification
    system_type = Column(String(10), nullable=False)
    system_specs = Column(JSONB, nullable=False)

    # Climate data used
    climate_data = Column(JSONB, nullable=False)
    climate_source = Column(String(50), nullable=True)

    # Calculation results
    annual_energy_kwh = Column(Numeric(10, 2), nullable=False)
    monthly_energy_kwh = Column(ARRAY(Numeric(10, 2)), nullable=True)
    confidence_band_percent = Column(Numeric(5, 2), nullable=True)

    # Calculation metadata
    assumptions = Column(JSONB, nullable=True)
    regional_factors_applied = Column(JSONB, nullable=True)
    calculation_version = Column(String(20), nullable=True)

    __table_args__ = (
        CheckConstraint("system_type IN ('solar', 'wind')", name="check_system_type"),
    )

    def __repr__(self):
        return f"<Calculation {self.id} - {self.system_type} - {self.annual_energy_kwh} kWh/year>"
