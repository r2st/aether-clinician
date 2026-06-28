"""Shared execution context passed to every agent node.

Carries the LLM clients (a separate one for the independent Verifier), a guideline retriever
callable (injected by the ReasoningService; Phase 3 wires the real Qdrant/lexical retriever),
a deterministic drug-safety evaluator, and an async event emitter used to stream the Reasoning
Theatre over SSE.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.agents.llm import LLMClient

# (query, k) -> list of guideline-chunk dicts with keys:
#   section_id, source, document_title, heading, content, score, corpus_version, page_range
Retriever = Callable[[str, int], list[dict[str, Any]]]
# proposed-drug name -> list of safety-flag dicts (deterministic engine output)
SafetyEvaluator = Callable[[str], list[dict[str, Any]]]
EventEmitter = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _noop_emit(event: str, data: dict[str, Any]) -> None:  # pragma: no cover
    return None


def _empty_retriever(query: str, k: int) -> list[dict[str, Any]]:
    return []


def _empty_safety(drug: str) -> list[dict[str, Any]]:
    return []


@dataclass
class ReasoningContext:
    llm: LLMClient = field(default_factory=LLMClient)
    verifier_llm: LLMClient = field(default_factory=LLMClient)
    retrieve: Retriever = _empty_retriever
    evaluate_safety: SafetyEvaluator = _empty_safety
    emit: EventEmitter = _noop_emit
    # Tuning knobs (architecture §3.2).
    info_gain_threshold: float = 0.35
    question_cap: int = 6
    retrieval_threshold: float = 0.75

    def llm_available(self) -> bool:
        return self.llm.available()
