"""Document extraction pipeline (Phase 1).

Production path: Claude vision multimodal extraction. Fallbacks: Tesseract OCR (when the
binary is available) and a deterministic heuristic text parser used offline / in tests /
when no ANTHROPIC_API_KEY is configured. All paths converge on the same ExtractionResult
schema with per-field confidence scoring.
"""

from app.services.extraction.pipeline import ExtractionPipeline

__all__ = ["ExtractionPipeline"]
