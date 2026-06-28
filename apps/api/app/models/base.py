"""Declarative base and shared column mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import GUID


class Base(DeclarativeBase):
    """Project-wide declarative base."""


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreatedAtMixin:
    """For append-only tables: created_at only, no updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
