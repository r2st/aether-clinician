"""Safety-reporting register (Phase 4) — append-only adverse-event capture for the pilot."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation import SafetyReport
from app.services.audit_service import AuditService


class SafetyReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def file_report(
        self,
        *,
        account_id: uuid.UUID,
        category: str,
        severity: str,
        description: str,
        patient_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        detail: dict | None = None,
    ) -> SafetyReport:
        report = SafetyReport(
            account_id=account_id,
            patient_id=patient_id,
            session_id=session_id,
            category=category,
            severity=severity,
            status="open",
            description=description,
            detail=detail or {},
        )
        self.db.add(report)
        await self.db.flush()
        await self.audit.record(
            action="safety_report_filed",
            account_id=account_id,
            patient_id=patient_id,
            entity_type="safety_report",
            entity_id=report.id,
            payload={"category": category, "severity": severity},
        )
        await self.db.commit()
        return report

    async def list_reports(self, account_id: uuid.UUID) -> list[SafetyReport]:
        result = await self.db.execute(
            select(SafetyReport)
            .where(SafetyReport.account_id == account_id)
            .order_by(SafetyReport.created_at.desc())
        )
        return list(result.scalars().all())
