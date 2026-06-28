# services/reasoning/ — Multi-Agent Diagnostic Reasoning Engine (Phase 2)

The 8-agent reasoning pipeline (Triage/Intake, Hypothesis Panel, Can't-Miss Sentinel,
Devil's-Advocate, Investigation Strategist, Guideline-RAG, Verifier, Synthesis/Orchestrator).

**Implemented.** The engine lives in `apps/api/app/agents/` (co-located with the FastAPI app so
it shares the patient graph, deterministic safety engine, and immutable audit log):

| File | Role |
| --- | --- |
| `state.py` | `CaseState` shared object + dataclasses (Hypothesis, Evidence, VerifierVerdict, …) |
| `graph.py` | LangGraph-style `StateGraph` orchestrator: nodes, edges, conditional verifier gate |
| `context.py` | `ReasoningContext` (LLM clients, guideline retriever, safety evaluator, SSE emitter) |
| `llm.py` | Claude client (lazy import); deterministic fallback when offline |
| `triage_intake.py` … `synthesis.py` | the eight agent nodes |
| `cant_miss.py` | deterministic can't-miss rule table (offline-capable safety floor) |
| `prompts.py` | per-agent system prompts (prescriber-framed, hedged, evidence-for/against) |

Driven by `app/services/reasoning_service.py` and exposed via `app/routers/reasoning.py`
(sessions, adaptive intake, blocking run, **SSE Reasoning Theatre stream**, immutable
`ClinicalSuggestion` persistence, clinician decisions).

**Non-negotiable safety properties (enforced & tested):**
- The Verifier node sits on every path to synthesis — it cannot be bypassed.
- Conservative output wins on disagreement (tier escalation, band downgrade).
- Allergy/contraindication hard blocks are deterministic and surfaced; overriding requires
  documented reasoning.
- Can't-miss diagnoses are append-only and force flag-for-review.
- Offline → deterministic degraded mode with an explicit `degraded` signal, never silent.

`langgraph` is an optional dependency: the orchestrator runs the same node functions as a
self-contained async state machine without it.
