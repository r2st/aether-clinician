"""Portable SQLAlchemy column types.

Production runs on PostgreSQL 16 (UUID, JSONB, INET). Tests run on SQLite for
speed and isolation. These type decorators emit the native PostgreSQL type when
bound to a PG dialect and a portable fallback (CHAR/JSON/VARCHAR) on SQLite, so
the same ORM models serve both targets.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import CHAR, String
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import JSON, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's native UUID, otherwise stores as a 32-char hex string.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(str(value)).hex

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# JSONB on PostgreSQL, generic JSON elsewhere.
JSONBType = JSON().with_variant(JSONB(), "postgresql")


class INETType(TypeDecorator):
    """INET on PostgreSQL, plain VARCHAR on SQLite."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(INET())
        return dialect.type_descriptor(String(64))


def dumps(value: Any) -> str:
    return json.dumps(value, default=str)
