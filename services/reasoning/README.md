# services/reasoning/ — Multi-Agent Diagnostic Reasoning Engine (Phase 2)

LangGraph-based orchestration of the 8-agent reasoning pipeline (Triage/Intake,
Hypothesis Panel, Can't-Miss Sentinel, Devil's-Advocate, Investigation Strategist,
Guideline-RAG, Verifier, Synthesis/Orchestrator).

Not yet implemented — Phase 1 ships the foundation this engine builds on (patient graph,
deterministic drug-safety checks, immutable audit log). See `docs/implementation-plan.md`
§3 and `CLAUDE.md` for the agent specifications and non-negotiable safety rules (the
Verifier can never be bypassed; conservative output wins on disagreement).
