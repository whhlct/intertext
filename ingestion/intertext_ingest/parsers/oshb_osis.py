from dataclasses import replace
from pathlib import Path

from defusedxml import ElementTree

from intertext_ingest.normalized import (
    AcquiredSource,
    NormalizedToken,
    ParsedSegment,
    ParsedSource,
    SourceReference,
)

_OSIS_NAMESPACE = "http://www.bibletechnologies.net/2003/OSIS/namespace"
_OSIS = f"{{{_OSIS_NAMESPACE}}}"
_TEXTUAL_SEGMENTS = {
    "x-maqqef",
    "x-paseq",
    "x-pe",
    "x-reversednun",
    "x-samekh",
    "x-sof-pasuq",
}


class OshbOsisParser:
    """Parse OSHB OSIS XML while retaining source-native Hebrew annotations."""

    PARSER_VERSION = "oshb-osis-1"

    def parse(self, source: AcquiredSource) -> ParsedSource:
        segments: list[ParsedSegment] = []
        for path in sorted(source.content_path.glob("*.xml")):
            root = ElementTree.parse(path).getroot()
            book = root.find(f".//{_OSIS}div[@type='book']")
            if book is None:
                continue
            segments.extend(self._parse_book(path, book))
        if not segments:
            raise ValueError(f"No OSHB OSIS book XML files found in {source.content_path}")
        ordered_segments = tuple(
            replace(segment, sequence=index)
            for index, segment in enumerate(segments, start=1)
        )
        return ParsedSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            segments=ordered_segments,
        )

    def _parse_book(self, path: Path, book) -> list[ParsedSegment]:
        segments: list[ParsedSegment] = []
        for verse in book.iter(f"{_OSIS}verse"):
            osis_id = verse.attrib.get("osisID")
            if not osis_id:
                raise ValueError(f"OSHB verse lacks an osisID in {path}")
            reference = self._source_reference(osis_id)
            tokens: list[NormalizedToken] = []
            elements: list[dict] = []
            for element in verse:
                name = self._local_name(element.tag)
                if name == "w":
                    word = self._word(element)
                    elements.append(word)
                    tokens.append(
                        NormalizedToken(
                            surface=word["surface"],
                            index=len(tokens),
                            metadata={
                                "source_id": word["id"],
                                "lemma": word["lemma"],
                                "morphology": word["morphology"],
                                "cantillation_hierarchy": word.get(
                                    "cantillation_hierarchy"
                                ),
                                "osis_attributes": word["attributes"],
                            },
                        )
                    )
                elif name == "seg":
                    segment_type = element.attrib.get("type")
                    if segment_type not in _TEXTUAL_SEGMENTS:
                        raise ValueError(
                            f"Unsupported OSHB segment type in {path}: {segment_type}"
                        )
                    elements.append(
                        {
                            "type": "segment",
                            "segment_type": segment_type,
                            "text": element.text or "",
                            "attributes": dict(element.attrib),
                        }
                    )
                elif name == "note":
                    elements.append(self._structured_element(element))
                else:
                    raise ValueError(f"Unsupported OSHB verse element in {path}: {name}")
            text = self._render_text(elements)
            if not text:
                raise ValueError(f"OSHB verse rendered to empty text: {osis_id}")
            segments.append(
                ParsedSegment(
                    sequence=0,
                    text=text,
                    source_reference=reference,
                    content_markup={
                        "source_format": "osis",
                        "source_profile": "oshb",
                        "elements": elements,
                        "unicode_normalization": "none",
                        "morpheme_delimiter": "/",
                    },
                    metadata={"source_file": path.name, "osis_id": osis_id},
                    tokens=tuple(tokens),
                )
            )
        return segments

    @staticmethod
    def _source_reference(osis_id: str) -> SourceReference:
        parts = osis_id.split(".")
        if len(parts) != 3:
            raise ValueError(f"Unsupported OSHB OSIS verse identifier: {osis_id}")
        book, chapter_text, verse_text = parts
        try:
            chapter = int(chapter_text)
            verse = int(verse_text)
        except ValueError as error:
            raise ValueError(f"Invalid OSHB OSIS verse identifier: {osis_id}") from error
        if chapter < 1 or verse < 1:
            raise ValueError(f"Invalid OSHB OSIS verse identifier: {osis_id}")
        return SourceReference(
            scheme="oshb_osis",
            label=osis_id,
            components={"book_id": book, "chapter": chapter, "verse": verse},
        )

    @staticmethod
    def _word(element) -> dict:
        required = ("id", "lemma", "morph")
        missing = [name for name in required if not element.attrib.get(name)]
        if missing:
            raise ValueError("OSHB word lacks attributes: " + ", ".join(missing))
        surface = element.text or ""
        if not surface:
            raise ValueError(f"OSHB word has no surface text: {element.attrib['id']}")
        word = {
            "type": "word",
            "surface": surface,
            "id": element.attrib["id"],
            "lemma": element.attrib["lemma"],
            "morphology": element.attrib["morph"],
            "attributes": dict(element.attrib),
        }
        if "n" in element.attrib:
            word["cantillation_hierarchy"] = element.attrib["n"]
        return word

    @classmethod
    def _structured_element(cls, element) -> dict:
        return {
            "type": cls._local_name(element.tag),
            "text": element.text or "",
            "attributes": dict(element.attrib),
            "children": [cls._structured_element(child) for child in element],
        }

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _render_text(elements: list[dict]) -> str:
        parts: list[str] = []
        previous_segment: str | None = None
        for element in elements:
            element_type = element["type"]
            if element_type == "note":
                continue
            if element_type == "word":
                # Slash is OSHB morpheme markup, not a character in the WLC text.
                surface = element["surface"].replace("/", "")
                if parts and previous_segment != "x-maqqef":
                    parts.append(" ")
                parts.append(surface)
                previous_segment = None
                continue
            segment_type = element["segment_type"]
            value = element["text"]
            if segment_type in {"x-maqqef", "x-sof-pasuq"}:
                parts.append(value)
            else:
                if parts and parts[-1] != " ":
                    parts.append(" ")
                parts.append(value)
            previous_segment = segment_type
        return "".join(parts).strip()
