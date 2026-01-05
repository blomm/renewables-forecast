"""Feedback model - stores user-submitted actual performance data."""

from sqlalchemy import Column, String, Numeric, DateTime, Integer, Boolean, Text, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.session import Base


class Feedback(Base):
    """User-submitted actual performance feedback."""

    __tablename__ = "feedback"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Link to original calculation
    calculation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calculations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Actual performance
    actual_annual_kwh = Column(Numeric(10, 2), nullable=False)
    installation_date = Column(Date, nullable=True)
    performance_period_months = Column(Integer, nullable=True)

    # Deviation analysis
    predicted_annual_kwh = Column(Numeric(10, 2), nullable=True)
    deviation_percent = Column(Numeric(6, 2), nullable=True)

    # Context
    notes = Column(Text, nullable=True)
    user_email = Column(String(255), nullable=True)

    # Quality flags
    validated = Column(Boolean, default=False)
    validation_notes = Column(Text, nullable=True)

    # Relationship
    calculation = relationship("Calculation", backref="feedback_submissions")

    def __repr__(self):
        return f"<Feedback {self.id} - {self.actual_annual_kwh} kWh/year ({self.deviation_percent:+.1f}%)>"
