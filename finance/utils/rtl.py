"""Qt-free right-to-left text helpers (safe to import from models)."""

from __future__ import annotations

_RLE = "‫"
_PDF = "‬"


def wrap_hebrew_rtl(text: str) -> str:
    if not text:
        return text
    if any("֐" <= char <= "׿" for char in text):
        return _RLE + text + _PDF
    return text


def unwrap_rtl(text: str) -> str:
    if not text:
        return text
    if text.startswith(_RLE) and text.endswith(_PDF):
        return text[1:-1]
    return text
