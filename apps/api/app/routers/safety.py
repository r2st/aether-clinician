"""Drug-safety check routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.safety import has_hard_block
from app.db.session import get_db
from app.dependencies import get_current_account
from app.models.user import Account
from app.schemas.safety import (
    ActiveFlagsResponse,
    SafetyCheckRequest,
    SafetyCheckResponse,
    SafetyFlagResponse,
)
from app.services.safety_service import SafetyService

router = APIRouter(prefix="/patients/{patient_id}/drug-safety", tags=["drug-safety"])


def _flag_to_response(flag) -> SafetyFlagResponse:
    return SafetyFlagResponse(
        check_type=flag.check_type,
        severity=flag.severity,
        is_hard_block=flag.is_hard_block,
        summary=flag.summary,
        details=flag.details,
        drug_interaction_id=_uuid(flag.drug_interaction_id),
        contraindication_id=_uuid(flag.contraindication_id),
        allergy_id=_uuid(flag.allergy_id),
    )


def _uuid(value):
    try:
        return uuid.UUID(str(value)) if value else None
    except (ValueError, TypeError):
        return None


@router.post("/check", response_model=SafetyCheckResponse)
async def check_medication(
    patient_id: uuid.UUID,
    body: SafetyCheckRequest,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> SafetyCheckResponse:
    vocab, ctx, flags = await SafetyService(db).check_medication(
        account_id=account.id,
        patient_id=patient_id,
        drug_reference_id=body.drug_reference_id,
        drug_name=body.drug_name,
    )
    blocked = has_hard_block(flags)
    return SafetyCheckResponse(
        patient_id=patient_id,
        proposed_drug_reference_id=vocab.reference_id,
        proposed_drug_name=vocab.generic_name,
        is_blocked=blocked,
        is_hard_block=blocked,
        checked_against={
            "current_medications": len(ctx.current_meds),
            "allergies": len(ctx.allergies),
            "conditions": len(ctx.conditions),
            "egfr_available": ctx.egfr is not None,
        },
        flags=[_flag_to_response(f) for f in flags],
    )


@router.get("/flags", response_model=ActiveFlagsResponse)
async def active_flags(
    patient_id: uuid.UUID,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> ActiveFlagsResponse:
    results = await SafetyService(db).active_flags(account_id=account.id, patient_id=patient_id)
    flags: list[SafetyFlagResponse] = []
    for _vocab, flag_list in results:
        flags.extend(_flag_to_response(f) for f in flag_list)
    return ActiveFlagsResponse(patient_id=patient_id, flags=flags)
