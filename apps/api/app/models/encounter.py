"""Encounter model — clinical visits, source-linked to documents."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID, JSONBType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Encounter(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Clinical encounter/visit."""

    __tablename__ = "encounters"
    __table_args__ = (
        CheckConstraint(
            "encounter_type IS NULL OR encounter_type IN "
            "('outpatient', 'inpatient', 'emergency', 'teleconsultation', 'follow_up', 'other')",
            name="ck_encounters_type",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("patients.id"), nullable=False, index=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("documents.id"), nullable=True
    )
    encounter_date: Mapped[date] = mapped_column(Date, nullable=False)
    encounter_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    presenting_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinician_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_region: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    extraction_confidence: Mapped[dict] = mapped_column(
        JSONBType, nullable=False, default=dict, server_default="{}"
    )
