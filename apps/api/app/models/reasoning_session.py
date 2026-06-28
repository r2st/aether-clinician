"""ReasoningSession model — one run of the 8-agent diagnostic reasoning engine (P2-01).

A session is created from a presenting complaint, passes through an adaptive intake loop,
then the multi-agent pipeline. The final ``case_state`` snapshot captures the complete
CaseState for reproducibility/audit (architecture-design §6.2). Sessions are mutable while
running; the ClinicalSuggestion records they emit are immutable.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID, JSONBType
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

_STATUSES = (
    "created",
    "intake",
    "intake_complete",
    "reasoning",
    "awaiting_review",
    "completed",
    "failed",
    "offline_paused",
)


class ReasoningSession(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A diagnostic reasoning session over a patient's longitudinal record."""

    __tablename__ = "reasoning_sessions"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _STATUSES)})",
            name="ck_reasoning_sessions_status",
        ),
        CheckConstraint(
            "autonomy_tier IS NULL OR autonomy_tier IN "
            "('informational', 'suggestive', 'flag_for_review')",
            name="ck_reasoning_sessions_tier",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("patients.id"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("accounts.id"), nullable=False, index=True
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("encounters.id"), nullable=True
    )
    presenting_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="created", server_default="created", index=True
    )
    autonomy_tier: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Highest-information-gain remaining, set by the triage agent each intake round.
    info_gain_score: Mapped[float | None] = mapped_column(nullable=True)
    intake_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    online: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Full CaseState snapshot (hypotheses, traces, verdicts) at completion — reproducibility.
    case_state: Mapped[dict] = mapped_column(
        JSONBType, nullable=False, default=dict, server_default="{}"
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
