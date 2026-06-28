"""Claude vision multimodal extraction client (production path).

Only used when ANTHROPIC_API_KEY is configured. Sends the document to Claude with a
structured-output instruction and parses the JSON response into ParsedEntity objects.
When no key is present, callers fall back to the deterministic text parser.
"""

from __future__ import annotations

import base64
import json

from app.config import settings
from app.services.extraction.text_parser import ParsedEntity, ParsedField

EXTRACTION_SYSTEM_PROMPT = """You are a clinical document extraction engine for an Indian \
primary-care CDSS. Extract structured data from the supplied medical document \
(prescription, lab report, or discharge summary).

Return ONLY a JSON object with this shape:
{
  "document_type": "prescription|lab_report|discharge_summary|other",
  "entities": [
    {"entity_type": "medication", "fields": {"brand_name_raw": str, "dose": str,
      "dose_unit": str, "frequency": str, "route": str, "event_type": "continue|start|stop"},
     "confidence": {"brand_name_raw": 0-1, "dose": 0-1, ...}},
    {"entity_type": "lab_result", "fields": {"marker_name": str, "value_numeric": number,
      "unit": str, "reference_range_low": number, "reference_range_high": number},
     "confidence": {...}},
    {"entity_type": "condition", "fields": {"condition_name": str, "status": str}, "confidence": {...}},
    {"entity_type": "allergy", "fields": {"allergen_name": str, "reaction_description": str},
     "confidence": {...}}
  ]
}
Per-field confidence in [0,1] reflects extraction certainty. Never invent data; if a field \
is illegible, omit it. Preserve original Indian brand names verbatim in brand_name_raw."""

_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}


def is_available() -> bool:
    return bool(settings.anthropic_api_key)


def _to_entities(payload: dict) -> tuple[list[ParsedEntity], str | None]:
    entities: list[ParsedEntity] = []
    for raw in payload.get("entities", []):
        etype = raw.get("entity_type")
        fields_map = raw.get("fields", {})
        conf_map = raw.get("confidence", {})
        fields = [
            ParsedField(name=k, value=v, confidence=float(conf_map.get(k, 0.7)))
            for k, v in fields_map.items()
            if v is not None
        ]
        if fields:
            entities.append(ParsedEntity(entity_type=etype, fields=fields))
    return entities, payload.get("document_type")


def extract(file_bytes: bytes, file_type: str) -> tuple[list[ParsedEntity], str | None]:
    """Call Claude vision/text and return (entities, document_type).

    Raises RuntimeError on any failure so the pipeline can fall back deterministically.
    """
    if not is_available():
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    content: list[dict] = [{"type": "text", "text": "Extract structured clinical data."}]
    if file_type in _MEDIA_TYPES:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _MEDIA_TYPES[file_type],
                    "data": base64.b64encode(file_bytes).decode("ascii"),
                },
            }
        )
    elif file_type == "pdf":
        content.append(
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.b64encode(file_bytes).decode("ascii"),
                },
            }
        )
    else:
        raise RuntimeError(f"Unsupported file type for vision extraction: {file_type}")

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("No JSON object in model response")
    payload = json.loads(text[start : end + 1])
    return _to_entities(payload)
