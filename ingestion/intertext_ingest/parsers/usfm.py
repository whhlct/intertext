import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from intertext_ingest.normalized import (
    AcquiredSource,
    ParsedSegment,
    ParsedSource,
    SourceReference,
)
from intertext_ingest.normalizers.markup import without_empty_values
from intertext_ingest.normalizers.text import normalize_plain_text

_ID_MARKER = re.compile(r"^\\id\s+([0-9A-Z]{3})\b")
_CHAPTER_MARKER = re.compile(r"^\\c\s+(\d+)\b")
_VERSE_MARKER = re.compile(r"^\\v\s+(\d+)(?:[a-z]|-\d+)?\s*(.*)$")
_NOTE = re.compile(r"\\(?:f|x)\b.*?\\(?:f|x)\*", re.DOTALL)
_WORD = re.compile(r"\\\+?w\s+(.+?)\|(.+?)\\\+?w\*", re.DOTALL)
_ATTRIBUTE = re.compile(r"([\w-]+)=\"([^\"]*)\"")
_STYLE = re.compile(r"\\\+?(add|wj|nd)\b")
_MARKER = re.compile(r"\\\+?[A-Za-z][A-Za-z0-9-]*\*?")
_PARAGRAPH_MARKER = re.compile(r"^\\(?:p|m|q\d*|pi\d*)\b\s*(.*)$")


@dataclass
class _PendingVerse:
    book_code: str
    chapter: int
    verse: int
    raw_parts: list[str]
    paragraph_start: bool


class UsfmParser:
    """Parse USFM syntax without assigning Intertext canonical identities."""

    PARSER_VERSION = "usfm-1"

    def parse(self, source: AcquiredSource) -> ParsedSource:
        paths = sorted(source.content_path.glob("*.usfm"))
        if not paths:
            raise FileNotFoundError(f"No USFM files found in {source.content_path}")

        segments: list[ParsedSegment] = []
        for path in paths:
            segments.extend(self._parse_file(path))
        ordered_segments = tuple(
            replace(segment, sequence=index)
            for index, segment in enumerate(segments, start=1)
        )
        return ParsedSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            segments=ordered_segments,
        )

    def _parse_file(self, path: Path) -> list[ParsedSegment]:
        book_code: str | None = None
        chapter: int | None = None
        pending: _PendingVerse | None = None
        paragraph_start = False
        segments: list[ParsedSegment] = []

        def flush() -> None:
            nonlocal pending
            if pending is None:
                return
            segments.append(self._normalize_pending(pending, path))
            pending = None

        for source_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = source_line.strip()
            if not line:
                continue
            if match := _ID_MARKER.match(line):
                book_code = match.group(1)
                continue
            if match := _CHAPTER_MARKER.match(line):
                flush()
                chapter = int(match.group(1))
                paragraph_start = False
                continue
            if match := _VERSE_MARKER.match(line):
                flush()
                if book_code is None or chapter is None:
                    raise ValueError(
                        f"Verse appears before book/chapter markers in {path}"
                    )
                raw_text = match.group(2)
                has_paragraph_symbol = raw_text.lstrip().startswith("¶")
                if has_paragraph_symbol:
                    raw_text = raw_text.lstrip().removeprefix("¶").lstrip()
                pending = _PendingVerse(
                    book_code=book_code,
                    chapter=chapter,
                    verse=int(match.group(1)),
                    raw_parts=[raw_text],
                    paragraph_start=paragraph_start or has_paragraph_symbol,
                )
                paragraph_start = False
                continue
            if match := _PARAGRAPH_MARKER.match(line):
                paragraph_start = True
                continuation = match.group(1)
                if continuation and pending is not None:
                    pending.raw_parts.append(continuation)
                continue
            if pending is not None and not line.startswith(("\\s", "\\r")):
                pending.raw_parts.append(line)
        flush()
        return segments

    def _normalize_pending(
        self, pending: _PendingVerse, source_path: Path
    ) -> ParsedSegment:
        raw_text = " ".join(pending.raw_parts)
        footnote_count = len(_NOTE.findall(raw_text))
        raw_text = _NOTE.sub(" ", raw_text)
        strongs: list[dict[str, str]] = []

        def replace_word(match: re.Match[str]) -> str:
            surface = normalize_plain_text(match.group(1))
            attributes = dict(_ATTRIBUTE.findall(match.group(2)))
            if strong := attributes.get("strong"):
                strongs.append({"surface": surface, "strong": strong})
            return surface

        raw_text = _WORD.sub(replace_word, raw_text)
        character_styles = sorted(set(_STYLE.findall(raw_text)))
        raw_text = _MARKER.sub("", raw_text)
        text = normalize_plain_text(raw_text)
        if not text:
            raise ValueError(
                f"USFM verse normalized to empty text: {source_path} "
                f"{pending.chapter}:{pending.verse}"
            )
        source_reference = SourceReference(
            scheme="usfm",
            label=f"{pending.book_code} {pending.chapter}:{pending.verse}",
            components={
                "book_code": pending.book_code,
                "chapter": pending.chapter,
                "verse": pending.verse,
            },
        )
        markup: dict[str, Any] = {
            "source_format": "usfm",
            "paragraph_start": pending.paragraph_start,
            "strongs": strongs,
            "strongs_policy": "preserved_as_segment_markup_not_tokens",
        }
        if character_styles:
            markup["character_styles"] = character_styles
        if footnote_count:
            markup["omitted_footnote_count"] = footnote_count
        return ParsedSegment(
            sequence=0,
            text=text,
            source_reference=source_reference,
            content_markup=without_empty_values(markup),
            metadata={"source_file": source_path.name},
        )
