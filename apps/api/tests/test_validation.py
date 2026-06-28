"""Phase 4 — clinical validation, metrics, CDSCO dossier, safety reporting, pilot mode."""

from __future__ import annotations

import pytest

from tests.conftest import create_patient


@pytest.mark.asyncio
async def test_validation_run_computes_metrics(auth_client):
    resp = await auth_client.post("/api/v1/validation/run")
    assert resp.status_code == 201, resp.text
    run = resp.json()
    m = run["metrics"]
    assert run["vignette_count"] >= 5
    # Harness scored every dimension.
    for key in (
        "diagnostic_top1_accuracy",
        "diagnostic_top3_accuracy",
        "cant_miss_recall",
        "hard_block_accuracy",
        "autonomy_tier_distribution",
        "degraded_rate",
    ):
        assert key in m
    # The deterministic vignettes are designed so can't-miss recall and hard-block accuracy
    # are perfect (these are the safety-critical metrics).
    assert m["cant_miss_recall"] == 1.0
    assert m["hard_block_accuracy"] == 1.0
    assert m["diagnostic_top3_accuracy"] >= 0.8


@pytest.mark.asyncio
async def test_validation_run_listed_and_fetchable(auth_client):
    resp = await auth_client.post("/api/v1/validation/run")
    run_id = resp.json()["id"]
    resp = await auth_client.get("/api/v1/validation/runs")
    assert resp.status_code == 200
    assert any(r["id"] == run_id for r in resp.json())
    resp = await auth_client.get(f"/api/v1/validation/runs/{run_id}")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) >= 5


@pytest.mark.asyncio
async def test_performance_metrics(auth_client):
    await auth_client.post("/api/v1/validation/run")
    resp = await auth_client.get("/api/v1/metrics/performance")
    assert resp.status_code == 200
    m = resp.json()
    assert m["total_sessions"] >= 5
    assert "autonomy_tier_distribution" in m
    assert m["citation_faithfulness_target"] == 0.95


@pytest.mark.asyncio
async def test_samd_dossier_json_and_markdown(auth_client):
    await auth_client.post("/api/v1/validation/run")
    resp = await auth_client.get("/api/v1/regulatory/samd-dossier")
    assert resp.status_code == 200
    d = resp.json()
    assert d["audit_integrity"]["chain_valid"] is True
    assert len(d["risk_management"]["controls"]) == 8
    assert d["clinical_validation"]["metrics"] is not None

    resp = await auth_client.get("/api/v1/regulatory/samd-dossier?format=markdown")
    assert resp.status_code == 200
    assert "CDSCO SaMD Technical Dossier" in resp.text
    assert "Risk Management Controls" in resp.text


@pytest.mark.asyncio
async def test_safety_report_filing(auth_client):
    patient = await create_patient(auth_client)
    resp = await auth_client.post(
        "/api/v1/safety-reports",
        json={
            "category": "incorrect_suggestion",
            "severity": "near_miss",
            "description": "Suggestion ranked a benign cause above a can't-miss diagnosis.",
            "patient_id": patient["id"],
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "open"

    resp = await auth_client.get("/api/v1/safety-reports")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Open report shows up in performance metrics.
    resp = await auth_client.get("/api/v1/metrics/performance")
    assert resp.json()["open_safety_reports"] == 1


@pytest.mark.asyncio
async def test_safety_report_rejects_bad_severity(auth_client):
    resp = await auth_client.post(
        "/api/v1/safety-reports",
        json={"category": "x", "severity": "catastrophic", "description": "bad severity"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pilot_status(auth_client):
    resp = await auth_client.get("/api/v1/pilot/status")
    assert resp.status_code == 200
    assert "pilot_mode" in resp.json()
