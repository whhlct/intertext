import re

from intertext_ingest.normalizers.unicode import normalize_unicode

_WHITESPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?·])")


def normalize_plain_text(value: str) -> str:
    normalized = normalize_unicode(value)
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    return _SPACE_BEFORE_PUNCTUATION.sub(r"\1", normalized)
