from dataclasses import replace
from pathlib import Path

from defusedxml import ElementTree

from intertext_ingest.normalized import (
    AcquiredSource,
    NormalizedSegment,
    NormalizedVersion,
)
from intertext_ingest.normalizers.references import (
    bible_reference_from_label,
    bible_reference_sort_key,
)
from intertext_ingest.normalizers.text import normalize_plain_text


class SblgntXmlParser:
    PARSER_VERSION = "sblgnt-xml-1"

    def parse(self, source: AcquiredSource) -> NormalizedVersion:
        segments: list[NormalizedSegment] = []
        for path in source.content_path.glob("*.xml"):
            root = ElementTree.parse(path).getroot()
            if root.tag != "book":
                continue
            segments.extend(self._parse_book(path, root))
        if not segments:
            raise ValueError(f"No SBLGNT book XML files found in {source.content_path}")
        segments.sort(key=lambda segment: bible_reference_sort_key(segment.reference))
        ordered_segments = tuple(
            replace(segment, sequence=index)
            for index, segment in enumerate(segments, start=1)
        )
        return NormalizedVersion(
            slug="sblgnt",
            title="SBL Greek New Testament",
            abbreviation="SBLGNT",
            language_iso="grc",
            language_name="Ancient Greek",
            language_native_name="Ἑλληνική",
            script="Grek",
            direction="ltr",
            version_type="critical_edition",
            source=source.metadata,
            segments=ordered_segments,
            publisher="Society of Biblical Literature and Logos Bible Software",
            rights_statement=(
                "Copyright 2010 Society of Biblical Literature and Logos Bible "
                "Software; licensed CC BY 4.0."
            ),
        )

    def _parse_book(self, path: Path, root) -> list[NormalizedSegment]:
        segments: list[NormalizedSegment] = []
        current_label: str | None = None
        elements: list[dict[str, str]] = []

        def flush() -> None:
            nonlocal current_label, elements
            if current_label is None:
                return
            reference = bible_reference_from_label(current_label)
            text = self._render_elements(elements)
            if not text:
                raise ValueError(
                    f"SBLGNT verse normalized to empty text: {current_label}"
                )
            segments.append(
                NormalizedSegment(
                    sequence=0,
                    language_iso="grc",
                    text=text,
                    source_reference=current_label,
                    reference=reference,
                    content_markup={
                        "source_format": "sblgnt_xml",
                        "elements": list(elements),
                    },
                    metadata={
                        "source_file": path.name,
                        "parser_version": self.PARSER_VERSION,
                    },
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
