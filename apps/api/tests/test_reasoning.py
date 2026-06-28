"""Phase 2 — multi-agent reasoning engine: intake loop, pipeline, safety, immutability."""

from __future__ import annotations

import uuid

import pytest

from app.models.allergy import Allergy
from app.models.medication_event import MedicationEvent
from tests.conftest import create_patient


async def _start(client, patient_id: str, complaint: str) -> dict:
    resp = await client.post(
        f"/api/v1/patients/{patient_id}/reasoning",
        json={"presenting_complaint": complaint},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _complete_intake(client, session_id: str) -> dict:
    """Answer all pending questions until intake is complete."""
    state = None
    for _ in range(4):
        resp = await client.get(f"/api/v1/reasoning/{session_id}/intake")
        pending = resp.json()
        if not pending:
            break
        answers = [{"question_id": q["id"], "answer_text": "no"} for q in pending]
        resp = await client.post(
            f"/api/v1/reasoning/{session_id}/intake/answers", json={"answers": answers}
        )
        assert resp.status_code == 200, resp.text
        state = resp.json()
        if state["intake_complete"]:
            break
    return state or {}


@pytest.mark.asyncio
async def test_start_generates_intake_questions(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever and cough for three days")
    assert state["session"]["status"] in ("intake", "intake_complete")
    assert len(state["pending_questions"]) >= 1
    # Triage must include at least one red-flag screen.
    assert any(q["question_type"] == "red_flag" for q in state["pending_questions"])


@pytest.mark.asyncio
async def test_intake_loop_then_run_produces_verified_suggestions(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever and cough for three days")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)

    resp = await auth_client.post(f"/api/v1/reasoning/{session_id}/run")
    assert resp.status_code == 200, resp.text
    result = resp.json()

    suggestions = result["suggestions"]
    assert suggestions, "expected clinical suggestions"
    # Every clinical suggestion carries an autonomy tier and a verifier verdict (Rule #1).
    tiers = ("informational", "suggestive", "flag_for_review")
    assert all(s["autonomy_tier"] in tiers for s in suggestions)
    diffs = [s for s in suggestions if s["output_type"] in ("differential", "cant_miss")]
    assert diffs
    for s in diffs:
        # Evidence-before-conclusion: evidence payload present and structured.
        assert "evidence_for" in s["evidence"]
    # Verifier ran: case state records a verifier status + autonomy tier.
    assert result["case_state"]["verifier_status"] in (
        "agree",
        "partial_disagreement",
        "major_disagreement",
    )
    assert result["session"]["autonomy_tier"] is not None


@pytest.mark.asyncio
async def test_cant_miss_forced_for_chest_pain(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(
        auth_client, patient["id"], "central chest pain radiating to the left arm with sweating"
    )
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    resp = await auth_client.post(f"/api/v1/reasoning/{session_id}/run")
    result = resp.json()

    cant_miss = [s for s in result["suggestions"] if s["cant_miss_flag"]]
    assert cant_miss, "chest pain must force can't-miss diagnoses onto the differential"
    names = " ".join(s["title"].lower() for s in cant_miss)
    assert "coronary" in names or "pulmonary embolism" in names
    # A can't-miss flag forces the case to flag-for-review (conservative wins).
    assert result["session"]["autonomy_tier"] == "flag_for_review"


@pytest.mark.asyncio
async def test_devils_advocate_always_present_on_leader(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever and cough")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    resp = await auth_client.post(f"/api/v1/reasoning/{session_id}/run")
    result = resp.json()
    leaders = [
        s for s in result["suggestions"] if s["output_type"] in ("differential", "cant_miss")
    ]
    assert any(s["devils_advocate"] for s in leaders), "devil's-advocate critique must be shown"


@pytest.mark.asyncio
async def test_hard_block_surfaced_and_override_requires_reason(auth_client, db):
    patient = await create_patient(auth_client)
    pid = uuid.UUID(patient["id"])
    # Patient is on Aspirin AND documented allergic to Aspirin -> deterministic hard block.
    db.add(
        MedicationEvent(
            patient_id=pid,
            generic_name="Aspirin",
            dose="75",
            event_type="continue",
            is_current=True,
            clinician_confirmed=True,
        )
    )
    db.add(
        Allergy(
            patient_id=pid,
            allergen_name="Aspirin",
            allergen_type="drug",
            status="active",
            clinician_confirmed=True,
        )
    )
    await db.commit()

    state = await _start(auth_client, patient["id"], "chest discomfort")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    resp = await auth_client.post(f"/api/v1/reasoning/{session_id}/run")
    result = resp.json()

    blocks = [s for s in result["suggestions"] if s["is_hard_block"]]
    assert blocks, "documented allergy to a current med must surface a hard block"
    assert result["session"]["autonomy_tier"] == "flag_for_review"

    block = blocks[0]
    # Overriding a hard block without documented reasoning is rejected (Safety Rule #3).
    resp = await auth_client.post(
        f"/api/v1/reasoning/{session_id}/suggestions/{block['id']}/decision",
        json={"decision": "overridden"},
    )
    assert resp.status_code == 422
    # With a reason, the decision is recorded as a separate immutable record.
    resp = await auth_client.post(
        f"/api/v1/reasoning/{session_id}/suggestions/{block['id']}/decision",
        json={"decision": "overridden", "reason": "Benefit outweighs risk; discussed w/ patient."},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["decision"] == "overridden"


@pytest.mark.asyncio
async def test_suggestions_listed_and_session_fetchable(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "headache")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    await auth_client.post(f"/api/v1/reasoning/{session_id}/run")

    resp = await auth_client.get(f"/api/v1/reasoning/{session_id}/suggestions")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await auth_client.get(f"/api/v1/reasoning/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("completed", "awaiting_review")


@pytest.mark.asyncio
async def test_cross_account_session_isolation(auth_client, client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever")
    session_id = state["session"]["id"]

    # A different account cannot read the session.
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "other@example.com", "password": "password123"},
    )
    other_token = resp.json()["access_token"]
    resp = await client.get(
        f"/api/v1/reasoning/{session_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sse_stream_emits_reasoning_events(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever and cough")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)

    token = auth_client.headers["Authorization"].split(" ", 1)[1]
    async with auth_client.stream(
        "GET", f"/api/v1/reasoning/{session_id}/stream?token={token}"
    ) as resp:
        assert resp.status_code == 200
        body = ""
        async for chunk in resp.aiter_text():
            body += chunk
            if "reasoning_complete" in body or "event: done" in body:
                break
    assert "event: reasoning_start" in body
    assert "event: verifier" in body
    assert "event: reasoning_complete" in body or "event: done" in body
