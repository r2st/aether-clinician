"""Shared schemas: enums, pagination, error envelope.

Enums here must stay in sync with packages/shared-types/src/enums.ts.
"""

from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class AutonomyTier(str, Enum):
    informational = "informational"
    suggestive = "suggestive"
    flag_for_review = "flag_for_review"


class ProbabilityBand(str, Enum):
    high = "high"
    moderate = "moderate"
    low = "low"
    very_low = "very_low"
    insufficient_data = "insufficient_data"


class ExtractionConfidence(str, Enum):
    high = "high"  # >= 0.85
    medium = "medium"  # 0.50 - 0.84
    low = "low"  # < 0.50


class SafetySeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"
    hard_block = "hard_block"


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class ErrorResponse(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code")
    message: str
    detail: dict | None = None


class MessageResponse(BaseModel):
    message: str
