# data/guidelines/ — Clinical Guideline Corpus (Phase 3)

Source documents for the guideline RAG corpus, organized by issuing organization:

- `icmr/` — ICMR Standard Treatment Workflows (primary spine)
- `who/` — WHO guidelines (supplementary)
- `nice/` — NICE guidelines (supplementary)

Each subdirectory carries a `manifest.yaml` describing its documents (title, edition,
publication date, specialty tags, corpus version). Ingestion is wired in Phase 3 via
`services/rag/ingest.py`. Corpus document metadata is seeded in the database in Phase 3.
