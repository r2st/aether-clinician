"""Resolve raw drug names to DrugVocabulary entries (brand -> generic -> reference_id).

Never matches by string equality alone (CLAUDE.md pitfall #4): resolution goes through the
vocabulary, with exact brand/generic match first, then trigram/Levenshtein fuzzy matching
for OCR misspellings (e.g. "Crocin" -> Paracetamol, "Glycomet" -> Metformin).
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug_vocabulary import DrugVocabulary

# Minimum fuzzy score (0-100) to accept a non-exact match.
FUZZY_THRESHOLD = 86.0


@dataclass(frozen=True)
class ResolvedDrug:
    vocabulary_id: object
    reference_id: str
    generic_name: str
    brand_name: str | None
    drug_class: str | None
    match_type: str  # exact_brand | exact_generic | exact_reference | fuzzy
    score: float


class DrugResolver:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._cache: list[DrugVocabulary] | None = None

    async def _all(self) -> list[DrugVocabulary]:
        if self._cache is None:
            result = await self.db.execute(
                select(DrugVocabulary).where(DrugVocabulary.is_active.is_(True))
            )
            self._cache = list(result.scalars().all())
        return self._cache

    async def resolve(self, name: str | None) -> ResolvedDrug | None:
        if not name or not name.strip():
            return None
        query = name.strip().lower()
        rows = await self._all()
        if not rows:
            return None

        # 1) Exact matches (reference_id, brand, generic).
        for row in rows:
            if row.reference_id.lower() == query:
                return self._make(row, "exact_reference", 100.0)
        for row in rows:
            if row.brand_name and row.brand_name.lower() == query:
                return self._make(row, "exact_brand", 100.0)
        for row in rows:
            if row.generic_name.lower() == query:
                return self._make(row, "exact_generic", 100.0)

        # 2) Fuzzy match against brand and generic names.
        candidates: dict[str, DrugVocabulary] = {}
        for row in rows:
            if row.brand_name:
                candidates.setdefault(row.brand_name.lower(), row)
            candidates.setdefault(row.generic_name.lower(), row)

        best = process.extractOne(query, list(candidates.keys()), scorer=fuzz.WRatio)
        if best and best[1] >= FUZZY_THRESHOLD:
            return self._make(candidates[best[0]], "fuzzy", float(best[1]))
        return None

    async def resolve_reference_id(self, reference_id: str) -> DrugVocabulary | None:
        for row in await self._all():
            if row.reference_id == reference_id:
                return row
        return None

    @staticmethod
    def _make(row: DrugVocabulary, match_type: str, score: float) -> ResolvedDrug:
        return ResolvedDrug(
            vocabulary_id=row.id,
            reference_id=row.reference_id,
            generic_name=row.generic_name,
            brand_name=row.brand_name,
            drug_class=row.drug_class,
            match_type=match_type,
            score=score,
        )
