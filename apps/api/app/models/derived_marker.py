"""DerivedMarker model — computed clinical values (e.g. eGFR), fully reproducible."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID, JSONBType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DerivedMarker(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A computed clinical value. Reproducible via formula_name + version + input_values."""

    __tablename__ = "derived_markers"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("patients.id"), nullable=False, index=True
    )
    source_lab_result_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("lab_results.id"), nullable=True
    )
    marker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    marker_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value_numeric: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    formula_name: Mapped[str] = mapped_column(String(100), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(20), nullable=False)
    input_values: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    reference_range_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reference_range_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    is_abnormal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
