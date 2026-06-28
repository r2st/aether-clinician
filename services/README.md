# services/

Standalone Python services in the Aether Clinician monorepo.

| Directory | Phase | Status |
|---|---|---|
| `reasoning/` | Phase 2 | Planned — LangGraph 8-agent diagnostic reasoning engine |
| `rag/` | Phase 3 | Planned — Guideline corpus embedding + retrieval (Qdrant) |

**Note on extraction:** The document extraction pipeline (Claude vision + Tesseract OCR
fallback + deterministic text parser + normalization) is implemented for Phase 1 inside
`apps/api/app/services/extraction/`, where it shares the API's database session, drug
vocabulary, and patient-graph models. It will be promoted to a standalone
`services/extraction/` worker when Phase 2 introduces the async Redis-Stream job queue.
