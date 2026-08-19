import re
from dataclasses import replace
from pathlib import Path

from defusedxml import ElementTree

from intertext_ingest.normalized import (
    AcquiredSource,
    ParsedSegment,
    ParsedSource,
    SourceReference,
)
from intertext_ingest.normalizers.text import normalize_plain_text

_VERSE_LABEL = re.compile(r"^(.+?)\s+(\d+):(\d+)$")


class SblgntXmlParser:
    """Parse SBLGNT XML without assigning canonical Bible identities."""

    PARSER_VERSION = "sblgnt-xml-1"

    def parse(self, source: AcquiredSource) -> ParsedSource:
        segments: list[ParsedSegment] = []
        for path in sorted(source.content_path.glob("*.xml")):
            root = ElementTree.parse(path).getroot()
            if root.tag != "book":
                continue
            segments.extend(self._parse_book(path, root))
        if not segments:
            raise ValueError(f"No SBLGNT book XML files found in {source.content_path}")
        ordered_segments = tuple(
            replace(segment, sequence=index)
            for index, segment in enumerate(segments, start=1)
        )
        return ParsedSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            segments=ordered_segments,
        )

    def _parse_book(self, path: Path, root) -> list[ParsedSegment]:
        segments: list[ParsedSegment] = []
        current_label: str | None = None
        elements: list[dict[str, str]] = []

        def flush() -> None:
            nonlocal current_label, elements
            if current_label is None:
                return
            source_reference = self._source_reference(current_label)
            text = self._render_elements(elements)
            if not text:
                raise ValueError(
                    f"SBLGNT verse normalized to empty text: {current_label}"
                )
            segments.append(
                ParsedSegment(
                    sequence=0,
                    text=text,
                    source_reference=source_reference,
                    content_markup={
                        "source_format": "sblgnt_xml",
                        "elements": list(elements),
                    },
                    metadata={"source_file": path.name},
                )
            )
            current_label = None
            elements = []

        for paragraph in root.findall("p"):
            for element in paragraph:
                if element.tag == "verse-number":
                    flush()
                    current_label = element.attrib.get("id")
                    if not current_label:
                        raise ValueError(f"SBLGNT verse lacks an id in {path}")
                elif element.tag in {"prefix", "w", "suffix"}:
                    if current_label is None:
                        raise ValueError(
                            f"SBLGNT text appears before a verse number in {path}"
                        )
                    elements.append({"type": element.tag, "text": element.text or ""})
                else:
                    raise ValueError(
                        f"Unsupported SBLGNT XML element in {path}: {element.tag}"
                    )
        flush()
        return segments

    @staticmethod
    def _source_reference(label: str) -> SourceReference:
        match = _VERSE_LABEL.fullmatch(label.strip())
        if match is None:
            raise ValueError(f"Invalid SBLGNT verse identifier: {label}")
        return SourceReference(
            scheme="sblgnt",
            label=label,
            components={
                "book_name": match.group(1),
                "chapter": int(match.group(2)),
                "verse": int(match.group(3)),
            },
        )

    @staticmethod
    def _render_elements(elements: list[dict[str, str]]) -> str:
        parts: list[str] = []
        previous_type: str | None = None
        for element in elements:
            element_type = element["type"]
            value = element["text"]
            if element_type == "w":
                if (
                    parts
                    and previous_type != "prefix"
                    and not parts[-1].endswith((" ", "\n", "\t"))
                ):
                    parts.append(" ")
                parts.append(value)
            else:
                parts.append(value)
            previous_type = element_type
        return normalize_plain_text("".join(parts))
