import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from intertext_ingest.normalized import (
    AcquiredSource,
    NormalizedSegment,
    NormalizedVersion,
)
from intertext_ingest.normalizers.references import (
    BOOK_BY_CODE,
    bible_reference,
    bible_reference_sort_key,
)
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
    PARSER_VERSION = "usfm-kjv-1"

    def __init__(
        self,
        *,
        slug: str,
        title: str,
        abbreviation: str,
        language_iso: str,
        language_name: str,
        version_type: str,
        rights_statement: str | None = None,
    ) -> None:
        self.slug = slug
        self.title = title
        self.abbreviation = abbreviation
        self.language_iso = language_iso
        self.language_name = language_name
        self.version_type = version_type
        self.rights_statement = rights_statement

    def parse(self, source: AcquiredSource) -> NormalizedVersion:
        paths = list(source.content_path.glob("*.usfm"))
        if not paths:
            raise FileNotFoundError(f"No USFM files found in {source.content_path}")
        paths.sort(key=self._file_order)

        segments: list[NormalizedSegment] = []
        for path in paths:
            segments.extend(self._parse_file(path))
        segments.sort(key=lambda segment: bible_reference_sort_key(segment.reference))
        ordered_segments = tuple(
            replace(segment, sequence=index)
            for index, segment in enumerate(segments, start=1)
        )
        return NormalizedVersion(
            slug=self.slug,
            title=self.title,
            abbreviation=self.abbreviation,
            language_iso=self.language_iso,
            language_name=self.language_name,
            language_native_name="English",
            script="Latn",
            direction="ltr",
            version_type=self.version_type,
            source=source.metadata,
            segments=ordered_segments,
            rights_statement=self.rights_statement,
        )

    @staticmethod
    def _file_order(path: Path) -> int:
        match = re.search(r"(?:^|-)\d*-?([0-9A-Z]{3})", path.name.upper())
        if match is None or match.group(1) not in BOOK_BY_CODE:
            raise ValueError(f"Cannot determine Bible book from USFM filename: {path}")
        return BOOK_BY_CODE[match.group(1)].order

    def _parse_file(self, path: Path) -> list[NormalizedSegment]:
        book_code: str | None = None
        chapter: int | None = None
        pending: _PendingVerse | None = None
        paragraph_start = False
        segments: list[NormalizedSegment] = []

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
                if book_code not in BOOK_BY_CODE:
                    raise ValueError(
                        f"Unsupported USFM book code in {path}: {book_code}"
                    )
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
    ) -> NormalizedSegment:
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
        reference = bible_reference(pending.book_code, pending.chapter, pending.verse)
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
        return NormalizedSegment(
            sequence=0,
            language_iso=self.language_iso,
            text=text,
            source_reference=reference.label,
            reference=reference,
            content_markup=markup,
            metadata={
                "source_file": source_path.name,
                "parser_version": self.PARSER_VERSION,
            },
        )
