"""Drug-safety check schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SafetyCheckRequest(BaseModel):
    """Check a proposed medication against the patient's record."""

    drug_reference_id: str | None = Field(
        default=None, description="Canonical drug_vocabulary.reference_id"
    )
    drug_name: str | None = Field(
        default=None, description="Brand or generic name; resolved via DrugVocabulary"
    )


class SafetyFlagResponse(BaseModel):
    check_type: str
    severity: str
    is_hard_block: bool
    summary: str
    details: dict
    drug_interaction_id: uuid.UUID | None = None
    contraindication_id: uuid.UUID | None = None
    allergy_id: uuid.UUID | None = None


class SafetyCheckResponse(BaseModel):
    patient_id: uuid.UUID
    proposed_drug_reference_id: str
    proposed_drug_name: str
    is_blocked: bool = Field(..., description="True if any hard block is present")
    is_hard_block: bool = Field(..., description="Hard blocks cannot be dismissed")
    checked_against: dict = Field(
        ..., description="Counts of meds/allergies/conditions the check ran against"
    )
    flags: list[SafetyFlagResponse]
    offline_capable: bool = True


class ActiveFlagsResponse(BaseModel):
    patient_id: uuid.UUID
    flags: list[SafetyFlagResponse]
