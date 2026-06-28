"""Audit log schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: int
    account_id: uuid.UUID | None
    patient_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    payload: dict
    prev_hash: str
    record_hash: str
    created_at: datetime


class AuditVerifyResponse(BaseModel):
    patient_id: uuid.UUID | None
    entries_checked: int
    chain_valid: bool
