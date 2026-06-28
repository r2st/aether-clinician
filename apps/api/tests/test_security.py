"""Unit tests for password hashing and JWT helpers."""

from __future__ import annotations

import uuid

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.exceptions import TokenError


def test_password_round_trip():
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_access_token_round_trip():
    aid = uuid.uuid4()
    token = create_access_token(aid)
    payload = decode_token(token)
    assert payload["sub"] == str(aid)
    assert payload["type"] == "access"


def test_decode_rejects_garbage():
    with pytest.raises(TokenError):
        decode_token("not-a-jwt")


def test_refresh_token_hash_is_stable_and_opaque():
    raw = generate_refresh_token()
    assert len(raw) >= 32
    assert hash_token(raw) == hash_token(raw)
    assert hash_token(raw) != raw
