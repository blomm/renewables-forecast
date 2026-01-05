"""Regional factors model - stores learned correction factors by region."""

from sqlalchemy import Column, String, Numeric, DateTime, Integer, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class RegionalFactor(Base):
    """Regional correction factors learned from feedback."""

    __tablename__ = "regional_factors"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Region and system type
    region = Column(String(50), nullable=False)
    system_type = Column(String(10), nullable=False)

    # Statistical factors
    correction_factor = Column(Numeric(6, 4), default=1.0, nullable=False)
    confidence_band_percent = Column(Numeric(5, 2), default=15.0, nullable=False)

    # Evidence
    sample_count = Column(Integer, default=0, nullable=False)
    mean_deviation = Column(Numeric(6, 4), nullable=True)
    std_deviation = Column(Numeric(6, 4), nullable=True)

    # Metadata
    last_recalculated_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("region", "system_type", name="uq_region_system_type"),
        CheckConstraint("system_type IN ('solar', 'wind')", name="check_system_type"),
    )

    def __repr__(self):
        return f"<RegionalFactor {self.region} - {self.system_type} - {self.correction_factor:.4f} (n={self.sample_count})>"
