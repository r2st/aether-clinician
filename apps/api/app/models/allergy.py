"""Allergy model — critical for drug-safety hard blocks."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID, JSONBType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Allergy(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A patient allergy. Drug allergies link to drug_vocabulary for deterministic checks.

    Allergy conflicts produce HARD BLOCKS — the system may never override them.
    """

    __tablename__ = "allergies"
    __table_args__ = (
        CheckConstraint(
            "allergen_type IN ('drug', 'food', 'environmental', 'other')",
            name="ck_allergies_allergen_type",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN "
            "('mild', 'moderate', 'severe', 'life_threatening', 'unknown')",
            name="ck_allergies_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved', 'refuted', 'unknown')",
            name="ck_allergies_status",
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
    allergen_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    allergen_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="drug", server_default="drug"
    )
    reaction_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", server_default="active"
    )
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    drug_vocabulary_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("drug_vocabulary.id"), nullable=True, index=True
    )
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
