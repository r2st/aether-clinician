#!/usr/bin/env python
"""Guideline corpus ingestion CLI (Phase 3).

Thin wrapper over ``app.services.guideline_ingest`` so the corpus can be (re)built from the
command line. Chunks the curated guidelines in ``data/guidelines/``, stores them in the
``guideline_chunks`` table (lexical-retrieval source of truth), and — when
``sentence-transformers`` and ``qdrant-client`` are installed — embeds and indexes them in
Qdrant for dense retrieval.

Usage:
    python services/rag/ingest.py            # ingest into DB (+ Qdrant if available)
    python -m app.services.guideline_ingest  # equivalent, from apps/api
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the FastAPI app package importable when run from the repo root.
_API = Path(__file__).resolve().parents[2] / "apps" / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))


async def _run() -> None:
    from app.config import settings
    from app.db.session import get_sessionmaker
    from app.services.guideline_ingest import ingest

    sm = get_sessionmaker()
    async with sm() as db:
        added = await ingest(db, push_qdrant=True)
        await db.commit()
    print(f"Ingested {added} guideline chunks (corpus {settings.guideline_corpus_version}).")


if __name__ == "__main__":
    asyncio.run(_run())
