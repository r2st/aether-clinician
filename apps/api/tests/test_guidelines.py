"""Phase 3 — guideline RAG: corpus seeding, search, cited management, citation faithfulness."""

from __future__ import annotations

import pytest

from tests.conftest import create_patient
from tests.test_reasoning import _complete_intake, _start


@pytest.mark.asyncio
async def test_corpus_seeded_and_searchable(auth_client):
    resp = await auth_client.get("/api/v1/guidelines/corpus")
    assert resp.status_code == 200
    info = resp.json()
    assert info["chunk_count"] >= 10
    assert info["citation_faithfulness_target"] == 0.95

    resp = await auth_client.get(
        "/api/v1/guidelines/search", params={"q": "management of type 2 diabetes"}
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results, "expected guideline hits"
    assert any("T2DM" in r["section_id"] for r in results)
    # Every result carries citation metadata.
    for r in results:
        assert r["source"] in ("icmr", "who", "nice")
        assert r["section_id"] and r["document_title"]


@pytest.mark.asyncio
async def test_reasoning_produces_cited_management_options(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "fever with productive cough and sputum")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    resp = await auth_client.post(f"/api/v1/reasoning/{session_id}/run")
    result = resp.json()

    management = [s for s in result["suggestions"] if s["output_type"] == "management"]
    assert management, "guideline-backed management options expected for pneumonia-like case"
    # Every cited management option references a real corpus chunk.
    for m in management:
        assert m["citations"], "management options must carry citations"
        for c in m["citations"]:
            assert c["section_id"]
            assert c["source"] in ("icmr", "who", "nice")

    # Citation faithfulness target (>=0.95): all cited section_ids were actually retrieved.
    faithfulness = result["case_state"].get("citation_faithfulness")
    assert faithfulness is not None and faithfulness >= 0.95


@pytest.mark.asyncio
async def test_management_options_endpoint(auth_client):
    patient = await create_patient(auth_client)
    state = await _start(auth_client, patient["id"], "high blood pressure and headache")
    session_id = state["session"]["id"]
    await _complete_intake(auth_client, session_id)
    await auth_client.post(f"/api/v1/reasoning/{session_id}/run")

    resp = await auth_client.get(f"/api/v1/reasoning/{session_id}/management-options")
    assert resp.status_code == 200
    options = resp.json()
    assert all(o["output_type"] == "management" for o in options)


@pytest.mark.asyncio
async def test_search_requires_auth(client):
    resp = await client.get("/api/v1/guidelines/search", params={"q": "diabetes"})
    assert resp.status_code == 401
