"""Longitudinal patient-record assembly (P1-06c)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy
from app.models.condition import Condition
from app.models.derived_marker import DerivedMarker
from app.models.lab_result import LabResult
from app.models.medication_event import MedicationEvent
from app.schemas.record import (
    AllergyItem,
    ConditionItem,
    DerivedMarkerItem,
    LabItem,
    LongitudinalRecord,
    MedicationItem,
)


class RecordService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def assemble(self, patient_id: uuid.UUID) -> LongitudinalRecord:
        meds = await self.db.execute(
            select(MedicationEvent)
            .where(
                MedicationEvent.patient_id == patient_id,
                MedicationEvent.is_deleted.is_(False),
            )
            .order_by(MedicationEvent.is_current.desc(), MedicationEvent.event_date.desc())
        )
        labs = await self.db.execute(
            select(LabResult)
            .where(LabResult.patient_id == patient_id, LabResult.is_deleted.is_(False))
            .order_by(LabResult.sample_date.desc().nullslast(), LabResult.marker_name)
        )
        conditions = await self.db.execute(
            select(Condition)
            .where(Condition.patient_id == patient_id, Condition.is_deleted.is_(False))
            .order_by(Condition.status, Condition.condition_name)
        )
        allergies = await self.db.execute(
            select(Allergy)
            .where(Allergy.patient_id == patient_id, Allergy.is_deleted.is_(False))
            .order_by(Allergy.allergen_name)
        )
        markers = await self.db.execute(
            select(DerivedMarker)
            .where(DerivedMarker.patient_id == patient_id, DerivedMarker.is_deleted.is_(False))
            .order_by(DerivedMarker.computed_at.desc())
        )

        return LongitudinalRecord(
            patient_id=patient_id,
            medications=[MedicationItem.model_validate(m) for m in meds.scalars().all()],
            lab_results=[LabItem.model_validate(lab) for lab in labs.scalars().all()],
            conditions=[ConditionItem.model_validate(c) for c in conditions.scalars().all()],
            allergies=[AllergyItem.model_validate(a) for a in allergies.scalars().all()],
            derived_markers=[DerivedMarkerItem.model_validate(d) for d in markers.scalars().all()],
        )
