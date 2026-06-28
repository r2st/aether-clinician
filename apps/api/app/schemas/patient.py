"""Patient request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Sex = Literal["male", "female", "other", "unknown"]


class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=500)
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone: str | None = Field(default=None, max_length=20)
    address_text: str | None = None
    notes: str | None = None
    consent_given: bool = Field(
        ..., description="Must be true before clinical data is stored (DPDP Act)."
    )


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=500)
    date_of_birth: date | None = None
    sex: Sex | None = None
    phone: str | None = Field(default=None, max_length=20)
    address_text: str | None = None
    notes: str | None = None
    consent_given: bool | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    address_text: str | None
    notes: str | None
    consent_given: bool
    consent_given_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    consent_given: bool
    updated_at: datetime
