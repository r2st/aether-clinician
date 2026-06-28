"""Longitudinal patient record route."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_account
from app.models.user import Account
from app.schemas.record import LongitudinalRecord
from app.services.patient_service import PatientService
from app.services.record_service import RecordService

router = APIRouter(prefix="/patients/{patient_id}/record", tags=["records"])


@router.get("", response_model=LongitudinalRecord)
async def get_record(
    patient_id: uuid.UUID,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_db),
) -> LongitudinalRecord:
    # Ownership check (raises if not found / not owned).
    await PatientService(db).get(account.id, patient_id)
    return await RecordService(db).assemble(patient_id)
