"""Patient model."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Core patient record. One account manages many patients."""

    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("sex IN ('male', 'female', 'other', 'unknown')", name="ck_patients_sex"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.id"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_given: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
