"""Unit tests for the audit hash-chain primitives."""

from __future__ import annotations

from app.core.audit_hash import (
    GENESIS_HASH,
    canonical_payload,
    compute_record_hash,
    verify_chain,
)


def _entry(seq, prev_hash, action="patient_created", payload=None):
    payload = payload or {"k": seq}
    canonical = canonical_payload(
        sequence=seq,
        action=action,
        account_id="acct",
        patient_id="pat",
        entity_type="patient",
        entity_id="ent",
        payload=payload,
        created_at=f"2026-06-27T00:00:0{seq}+00:00",
    )
    record_hash = compute_record_hash(prev_hash, canonical)
    return {
        "sequence": seq,
        "action": action,
        "account_id": "acct",
        "patient_id": "pat",
        "entity_type": "patient",
        "entity_id": "ent",
        "payload": payload,
        "created_at": f"2026-06-27T00:00:0{seq}+00:00",
        "prev_hash": prev_hash,
        "record_hash": record_hash,
    }


def _build_chain(n):
    entries = []
    prev = GENESIS_HASH
    for i in range(1, n + 1):
        e = _entry(i, prev)
        entries.append(e)
        prev = e["record_hash"]
    return entries


def test_valid_chain_verifies():
    assert verify_chain(_build_chain(5)) is True


def test_genesis_links_to_zero_hash():
    chain = _build_chain(1)
    assert chain[0]["prev_hash"] == GENESIS_HASH


def test_tampered_payload_breaks_chain():
    chain = _build_chain(4)
    # Tamper with a middle record's payload without recomputing hashes downstream.
    chain[1]["payload"] = {"k": 999}
    assert verify_chain(chain) is False


def test_broken_link_breaks_chain():
    chain = _build_chain(3)
    chain[2]["prev_hash"] = "f" * 64  # wrong linkage
    assert verify_chain(chain) is False


def test_record_hash_is_deterministic():
    c = canonical_payload(
        sequence=1,
        action="a",
        account_id=None,
        patient_id=None,
        entity_type=None,
        entity_id=None,
        payload={"x": 1},
        created_at="t",
    )
    assert compute_record_hash(GENESIS_HASH, c) == compute_record_hash(GENESIS_HASH, c)
