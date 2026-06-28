#!/usr/bin/env bash
# Seed drug vocabulary, interactions, and contraindications (idempotent).
set -euo pipefail
cd "$(dirname "$0")/../apps/api"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://aether:aether@localhost:5432/aether_clinician}"
PYTHONPATH=. ../../.venv/bin/python -m app.db.seed
