"""Magic-byte file-type detection. Never trust the client-supplied Content-Type alone."""

from __future__ import annotations

# Maps detected type -> our documents.file_type enum value.
SUPPORTED = ("pdf", "image/jpeg", "image/png", "image/webp", "image/heic")


def sniff_file_type(data: bytes) -> str | None:
    """Return the canonical file_type from magic bytes, or None if unsupported."""
    if len(data) < 12:
        return None
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    # HEIC/HEIF: 'ftyp' box with heic/heif/heix/mif1 brand.
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heif", b"heix", b"mif1"):
        return "image/heic"
    return None
