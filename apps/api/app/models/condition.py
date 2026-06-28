"""Condition model — diagnosed conditions / problems, source-linked."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID, JSONBType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Condition(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A diagnosed condition or problem."""

    __tablename__ = "conditions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'resolved', 'inactive', 'recurrence', 'unknown')",
            name="ck_conditions_status",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN ('mild', 'moderate', 'severe', 'unknown')",
            name="ck_conditions_severity",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("patients.id"), nullable=False, index=True
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("encounters.id"), nullable=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("documents.id"), nullable=True
    )
    condition_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    icd10_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", server_default="active"
    )
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_region: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    extraction_confidence: Mapped[dict] = mapped_column(
        JSONBType, nullable=False, default=dict, server_default="{}"
    )
    clinician_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    clinician_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
