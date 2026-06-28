"""Pydantic schemas for Phase 4: validation runs, safety reports, metrics."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ValidationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vignette_count: int
    corpus_version: str | None
    metrics: dict
    results: list
    notes: str | None
    created_at: datetime


class ValidationRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vignette_count: int
    metrics: dict
    created_at: datetime


class SafetyReportIn(BaseModel):
    category: str = Field(..., min_length=2, max_length=60)
    severity: str = Field(..., pattern="^(near_miss|non_serious|serious|sentinel_event)$")
    description: str = Field(..., min_length=3, max_length=4000)
    patient_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    detail: dict | None = None


class SafetyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    severity: str
    status: str
    description: str
    patient_id: uuid.UUID | None
    session_id: uuid.UUID | None
    detail: dict
    created_at: datetime
