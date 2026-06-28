"""Pure helpers for the immutable, hash-chained audit log (P1-09).

The genesis ``prev_hash`` and the record-hash construction live here so they can be
unit-tested and reused by an offline integrity verifier without touching the database.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Hash that the very first audit row chains from.
GENESIS_HASH = "0" * 64


def canonical_payload(
    *,
    sequence: int,
    action: str,
    account_id: str | None,
    patient_id: str | None,
    entity_type: str | None,
    entity_id: str | None,
    payload: dict[str, Any],
    created_at: str,
) -> str:
    """Deterministic JSON serialization of the hashed fields (sorted keys, no whitespace)."""
    body = {
        "sequence": sequence,
        "action": action,
        "account_id": account_id,
        "patient_id": patient_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload,
        "created_at": created_at,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def compute_record_hash(prev_hash: str, canonical: str) -> str:
    """record_hash = sha256(prev_hash || canonical_payload)."""
    digest = hashlib.sha256()
    digest.update(prev_hash.encode("utf-8"))
    digest.update(canonical.encode("utf-8"))
    return digest.hexdigest()


def verify_chain(entries: list[dict[str, Any]]) -> bool:
    """Verify an ordered list of audit entries forms an unbroken hash chain.

    Each entry must provide the same fields passed to :func:`canonical_payload` plus
    ``prev_hash`` and ``record_hash``. Returns True only if every link recomputes correctly
    and each ``prev_hash`` matches the prior row's ``record_hash``.
    """
    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry["prev_hash"] != expected_prev:
            return False
        canonical = canonical_payload(
            sequence=entry["sequence"],
            action=entry["action"],
            account_id=entry.get("account_id"),
            patient_id=entry.get("patient_id"),
            entity_type=entry.get("entity_type"),
            entity_id=entry.get("entity_id"),
            payload=entry.get("payload", {}),
            created_at=entry["created_at"],
        )
        if compute_record_hash(entry["prev_hash"], canonical) != entry["record_hash"]:
            return False
        expected_prev = entry["record_hash"]
    return True
