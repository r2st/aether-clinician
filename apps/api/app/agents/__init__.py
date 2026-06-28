"""Multi-agent diagnostic reasoning engine (Phase 2).

A LangGraph-style ``StateGraph`` of eight agents that debate and cross-check before any
clinical output reaches the clinician. The orchestrator (``graph.py``) is a self-contained
async state machine mirroring the LangGraph node/edge model from architecture-design §3.4, so
the pipeline runs and is fully testable without the optional ``langgraph`` runtime. When
``langgraph`` is installed it can drive the same node functions; offline (no ANTHROPIC_API_KEY)
the agents fall back to deterministic reasoning and the pipeline signals degraded mode.
"""
