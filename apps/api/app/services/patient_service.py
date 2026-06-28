"""Patient CRUD, search, and consent-gated creation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConsentRequiredError, PatientNotFoundError
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit_service import AuditService


class PatientService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def create(self, account_id: uuid.UUID, data: PatientCreate) -> Patient:
        if not data.consent_given:
            raise ConsentRequiredError()
        patient = Patient(
            account_id=account_id,
            full_name=data.full_name,
            date_of_birth=data.date_of_birth,
            sex=data.sex,
            phone=data.phone,
            address_text=data.address_text,
            notes=data.notes,
            consent_given=True,
            consent_given_at=datetime.now(UTC),
        )
        self.db.add(patient)
        await self.db.flush()
        await self.audit.record(
            action="patient_created",
            account_id=account_id,
            patient_id=patient.id,
            entity_type="patient",
            entity_id=patient.id,
            payload={"full_name": patient.full_name, "consent_given": True},
        )
        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def get(self, account_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
        result = await self.db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.account_id == account_id,
                Patient.is_deleted.is_(False),
            )
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise PatientNotFoundError()
        return patient

    async def list(
        self,
        account_id: uuid.UUID,
        *,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Patient], int]:
        conditions = [
            Patient.account_id == account_id,
            Patient.is_deleted.is_(False),
        ]
        if search:
            like = f"%{search.strip()}%"
            conditions.append(or_(Patient.full_name.ilike(like), Patient.phone.ilike(like)))

        base = select(Patient).where(*conditions)
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(Patient.updated_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def update(
        self, account_id: uuid.UUID, patient_id: uuid.UUID, data: PatientUpdate
    ) -> Patient:
        patient = await self.get(account_id, patient_id)
        changed: dict = {}
        for field_name, value in data.model_dump(exclude_unset=True).items():
            if field_name == "consent_given":
                if value and not patient.consent_given:
                    patient.consent_given_at = datetime.now(UTC)
                patient.consent_given = bool(value)
                changed["consent_given"] = bool(value)
                continue
            setattr(patient, field_name, value)
            changed[field_name] = value
        await self.db.flush()
        await self.audit.record(
            action="patient_updated",
            account_id=account_id,
            patient_id=patient.id,
            entity_type="patient",
            entity_id=patient.id,
            payload={"changed_fields": sorted(changed.keys())},
        )
        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def soft_delete(self, account_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        patient = await self.get(account_id, patient_id)
        patient.is_deleted = True
        patient.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self.audit.record(
            action="patient_deleted",
            account_id=account_id,
            patient_id=patient.id,
            entity_type="patient",
            entity_id=patient.id,
            payload={"soft_delete": True},
        )
        await self.db.commit()
