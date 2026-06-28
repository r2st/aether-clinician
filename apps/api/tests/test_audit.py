"""Immutable audit-log integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import create_patient
from tests.test_documents import PRESCRIPTION


@pytest.mark.asyncio
async def test_actions_are_logged_and_chain_is_valid(auth_client):
    patient = await create_patient(auth_client)
    doc = (
        await auth_client.post(
            f"/api/v1/patients/{patient['id']}/documents",
            files={"file": ("rx.pdf", PRESCRIPTION, "application/pdf")},
        )
    ).json()
    await auth_client.post(
        f"/api/v1/patients/{patient['id']}/documents/{doc['id']}/approve",
        json={"corrections": [], "rejected_entity_indexes": []},
    )

    audit = (await auth_client.get(f"/api/v1/patients/{patient['id']}/audit")).json()
    actions = {entry["action"] for entry in audit["items"]}
    assert "patient_created" in actions
    assert "document_uploaded" in actions
    assert "extraction_completed" in actions
    assert "extraction_approved" in actions
    assert "graph_merged" in actions

    # Every entry carries a hash and links to the previous one.
    for entry in audit["items"]:
        assert len(entry["record_hash"]) == 64
        assert len(entry["prev_hash"]) == 64

    verify = (await auth_client.get(f"/api/v1/patients/{patient['id']}/audit/verify")).json()
    assert verify["chain_valid"] is True
    assert verify["entries_checked"] >= 4


@pytest.mark.asyncio
async def test_audit_filter_by_action(auth_client):
    patient = await create_patient(auth_client)
    resp = await auth_client.get(
        f"/api/v1/patients/{patient['id']}/audit", params={"action": "patient_created"}
    )
    items = resp.json()["items"]
    assert items and all(i["action"] == "patient_created" for i in items)


@pytest.mark.asyncio
async def test_audit_log_model_is_append_only_shape(db):
    """Structural immutability: the audit table has no updated_at / is_deleted columns."""
    from app.models.audit_log import AuditLog

    columns = set(AuditLog.__table__.columns.keys())
    assert "updated_at" not in columns
    assert "is_deleted" not in columns
    assert {"sequence", "prev_hash", "record_hash"} <= columns


@pytest.mark.asyncio
async def test_tampering_detected_by_verifier(db, auth_client):
    """Mutating a stored payload makes the recomputed chain invalid."""
    patient = await create_patient(auth_client)
    # Tamper directly at the SQL layer (simulating a breach), then re-verify.
    await db.execute(
        text("UPDATE audit_logs SET payload = :p WHERE action = 'patient_created'"),
        {"p": '{"full_name": "TAMPERED"}'},
    )
    await db.commit()

    from app.services.audit_service import AuditService

    _count, valid = await AuditService(db).verify_patient_chain(patient["id"])
    assert valid is False
