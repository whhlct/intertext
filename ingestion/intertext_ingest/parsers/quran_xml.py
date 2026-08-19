from defusedxml import ElementTree

from intertext_ingest.normalized import (
    AcquiredSource,
    ParsedSegment,
    ParsedSource,
    SourceReference,
)


class QuranXmlParser:
    """Parse the sura/aya XML format without assigning canonical identities."""

    PARSER_VERSION = "quran-xml-1"

    def parse(self, source: AcquiredSource) -> ParsedSource:
        if not source.content_path.is_file():
            raise ValueError(f"Quran XML source is not a file: {source.content_path}")
        root = ElementTree.parse(source.content_path).getroot()
        if root.tag != "quran":
            raise ValueError(f"Expected Quran XML root 'quran', found: {root.tag}")

        segments: list[ParsedSegment] = []
        expected_surah = 1
        for surah_element in root:
            if surah_element.tag != "sura":
                raise ValueError(
                    f"Unsupported Quran XML element under quran: {surah_element.tag}"
                )
            surah = self._positive_integer(surah_element.attrib.get("index"), "sura")
            if surah != expected_surah:
                raise ValueError(
                    f"Non-contiguous Quran XML sura ordering: expected "
                    f"{expected_surah}, found {surah}"
                )
            surah_name = surah_element.attrib.get("name", "").strip()
            if not surah_name:
                raise ValueError(f"Quran XML sura {surah} has no name")

            expected_ayah = 1
            for ayah_element in surah_element:
                if ayah_element.tag != "aya":
                    raise ValueError(
                        f"Unsupported Quran XML element in sura {surah}: "
                        f"{ayah_element.tag}"
                    )
                ayah = self._positive_integer(
                    ayah_element.attrib.get("index"),
                    f"aya in sura {surah}",
                )
                if ayah != expected_ayah:
                    raise ValueError(
                        f"Non-contiguous Quran XML aya ordering in sura {surah}: "
                        f"expected {expected_ayah}, found {ayah}"
                    )
                text = ayah_element.attrib.get("text")
                if text is None or not text.strip():
                    raise ValueError(f"Quran XML aya {surah}:{ayah} has no text")
                source_attributes = {
                    key: value
                    for key, value in ayah_element.attrib.items()
                    if key not in {"index", "text"}
                }
                segments.append(
                    ParsedSegment(
                        sequence=len(segments) + 1,
                        text=text,
                        source_reference=SourceReference(
                            scheme="quran_xml",
                            label=f"{surah}:{ayah}",
                            components={
                                "surah": surah,
                                "ayah": ayah,
                                "surah_name": surah_name,
                            },
                        ),
                        content_markup={
                            "source_format": "quran_xml",
                            "surah": {"index": surah, "name": surah_name},
                            "attributes": source_attributes,
                        },
                        metadata={"source_surah": surah, "source_ayah": ayah},
                    )
                )
                expected_ayah += 1
            if expected_ayah == 1:
                raise ValueError(f"Quran XML sura {surah} contains no ayat")
            expected_surah += 1

        if not segments:
            raise ValueError(f"Quran XML contains no ayat: {source.content_path}")
        return ParsedSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            segments=tuple(segments),
        )

    @staticmethod
    def _positive_integer(value: str | None, field: str) -> int:
        try:
            parsed = int(value or "")
        except ValueError as error:
            raise ValueError(f"Invalid Quran XML {field} index: {value}") from error
        if parsed < 1:
            raise ValueError(f"Invalid Quran XML {field} index: {value}")
        return parsed
