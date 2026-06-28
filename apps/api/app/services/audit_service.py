"""Immutable, hash-chained audit log service (P1-09).

Every clinical action is appended here. Writes are append-only: the service exposes no
update or delete. Each row chains to the previous via SHA-256 so tampering is detectable
(see app.core.audit_hash). A Postgres transaction-level advisory lock serializes appends so
the chain stays linear under concurrency; on SQLite (tests) execution is already serial.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_hash import (
    GENESIS_HASH,
    canonical_payload,
    compute_record_hash,
    verify_chain,
)
from app.models.audit_log import AuditLog

# Arbitrary fixed key for the append advisory lock.
_AUDIT_LOCK_KEY = 4823701


def _iso_utc(dt: datetime) -> str:
    """Stable UTC ISO timestamp. SQLite drops tzinfo on round-trip; PG keeps it. Coercing
    naive values to UTC makes the hashed representation identical at write and verify time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _lock(self) -> None:
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            await self.db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _AUDIT_LOCK_KEY})

    async def _latest(self) -> AuditLog | None:
        result = await self.db.execute(select(AuditLog).order_by(AuditLog.sequence.desc()).limit(1))
        return result.scalar_one_or_none()

    async def record(
        self,
        *,
        action: str,
        account_id: uuid.UUID | None = None,
        patient_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> AuditLog:
        """Append one immutable, hash-chained audit entry. Does not commit."""
        await self._lock()
        latest = await self._latest()
        sequence = (latest.sequence + 1) if latest else 1
        prev_hash = latest.record_hash if latest else GENESIS_HASH
        created_at = datetime.now(UTC)
        payload = payload or {}

        canonical = canonical_payload(
            sequence=sequence,
            action=action,
            account_id=str(account_id) if account_id else None,
            patient_id=str(patient_id) if patient_id else None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            payload=payload,
            created_at=_iso_utc(created_at),
        )
        record_hash = compute_record_hash(prev_hash, canonical)

        entry = AuditLog(
            sequence=sequence,
            account_id=account_id,
            patient_id=patient_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            prev_hash=prev_hash,
            record_hash=record_hash,
            created_at=created_at,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_for_patient(
        self,
        patient_id: uuid.UUID,
        *,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        from sqlalchemy import func

        base = select(AuditLog).where(AuditLog.patient_id == patient_id)
        if action:
            base = base.where(AuditLog.action == action)

        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(AuditLog.sequence.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def verify_patient_chain(self, patient_id: uuid.UUID) -> tuple[int, bool]:
        """Recompute the hash chain for a patient's entries in global sequence order."""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.patient_id == patient_id)
            .order_by(AuditLog.sequence.asc())
        )
        rows = list(result.scalars().all())
        entries = [
            {
                "sequence": r.sequence,
                "action": r.action,
                "account_id": str(r.account_id) if r.account_id else None,
                "patient_id": str(r.patient_id) if r.patient_id else None,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "payload": r.payload,
                "created_at": _iso_utc(r.created_at),
                "prev_hash": r.prev_hash,
                "record_hash": r.record_hash,
            }
            for r in rows
        ]
        # Per-patient slice: validate each record's own hash recomputes; chain linkage is
        # validated globally. Here we recompute each record's hash from its stored prev_hash.
        valid = all(
            compute_record_hash(
                e["prev_hash"],
                canonical_payload(
                    sequence=e["sequence"],
                    action=e["action"],
                    account_id=e["account_id"],
                    patient_id=e["patient_id"],
                    entity_type=e["entity_type"],
                    entity_id=e["entity_id"],
                    payload=e["payload"],
                    created_at=e["created_at"],
                ),
            )
            == e["record_hash"]
            for e in entries
        )
        return len(entries), valid

    async def verify_full_chain(self) -> tuple[int, bool]:
        """Verify the entire global chain is unbroken (genesis -> latest)."""
        result = await self.db.execute(select(AuditLog).order_by(AuditLog.sequence.asc()))
        rows = list(result.scalars().all())
        entries = [
            {
                "sequence": r.sequence,
                "action": r.action,
                "account_id": str(r.account_id) if r.account_id else None,
                "patient_id": str(r.patient_id) if r.patient_id else None,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "payload": r.payload,
                "created_at": _iso_utc(r.created_at),
                "prev_hash": r.prev_hash,
                "record_hash": r.record_hash,
            }
            for r in rows
        ]
        return len(entries), verify_chain(entries)
