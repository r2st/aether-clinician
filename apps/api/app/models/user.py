"""Account and Session models (auth domain)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.types import GUID, INETType
from app.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Account(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Clinician/user account. Demo mode: no clinician-credential gate."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("email", name="uq_accounts_email"),)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sessions: Mapped[list[Session]] = relationship(back_populates="account")


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Refresh-token session tracking. Raw tokens are never stored, only SHA-256 hashes."""

    __tablename__ = "sessions"

    account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INETType(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    account: Mapped[Account] = relationship(back_populates="sessions")
