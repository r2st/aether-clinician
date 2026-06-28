# services/rag/ — Guideline RAG Service (Phase 3)

Manages the curated clinical guideline corpus (ICMR Standard Treatment Workflows spine,
WHO Essential Medicines, NICE): chunking, embedding, Qdrant storage, retrieval with score
thresholding, and strict citation grounding.

**Implemented.**

- **Corpus**: `data/guidelines/icmr_stw.json` — versioned documents → citable sections
  (hypertension, T2DM, community-acquired pneumonia, dengue, ACS, malaria, gastroenteritis).
- **Ingestion**: `python services/rag/ingest.py` (or `python -m app.services.guideline_ingest`).
  Section-aware ~512-token chunking, retains citation metadata (source, section_id, page_range,
  corpus_version), upserts into `guideline_chunks`, and — when `sentence-transformers` +
  `qdrant-client` are installed — embeds and indexes into Qdrant. The seed loader also calls it
  so dev/test databases carry the corpus.
- **Retrieval**: `app/services/guideline_service.py`. Dense Qdrant search in production; a
  deterministic lexical retriever (keyword + body overlap, saturating 0..1 score, ≥0.75 to
  ground a citation) as an offline-capable fallback.
- **Agent**: `app/agents/guideline_rag.py` drafts management options strictly grounded in
  retrieved chunks, emits an explicit "insufficient guideline support" notice below threshold,
  and computes **citation faithfulness** (share of cited sections actually retrieved; target ≥95%).
- **API**: `GET /guidelines/search`, `GET /guidelines/corpus`,
  `GET /reasoning/{id}/management-options`. UI: `/guidelines` corpus search + inline citations on
  management suggestion cards.

See `docs/implementation-plan.md` §4.
