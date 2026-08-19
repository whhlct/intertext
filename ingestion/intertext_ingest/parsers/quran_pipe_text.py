from intertext_ingest.normalized import (
    AcquiredSource,
    ParsedSegment,
    ParsedSource,
    SourceReference,
)


class QuranPipeTextParser:
    """Parse surah|ayah|text records while ignoring blank and comment lines."""

    PARSER_VERSION = "quran-pipe-text-1"

    def parse(self, source: AcquiredSource) -> ParsedSource:
        if not source.content_path.is_file():
            raise ValueError(
                f"Quran pipe-text source is not a file: {source.content_path}"
            )

        segments: list[ParsedSegment] = []
        previous_reference: tuple[int, int] | None = None
        with source.content_path.open(encoding="utf-8-sig") as source_file:
            for line_number, raw_line in enumerate(source_file, start=1):
                line = raw_line.rstrip("\r\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split("|", 2)
                if len(parts) != 3:
                    raise ValueError(
                        f"Invalid Quran pipe-text record at line {line_number}"
                    )
                surah = self._positive_integer(parts[0], line_number, "surah")
                ayah = self._positive_integer(parts[1], line_number, "ayah")
                text = parts[2]
                if not text.strip():
                    raise ValueError(
                        f"Quran pipe-text record has no text at line {line_number}"
                    )
                self._validate_order(previous_reference, (surah, ayah), line_number)
                segments.append(
                    ParsedSegment(
                        sequence=len(segments) + 1,
                        text=text,
                        source_reference=SourceReference(
                            scheme="quran_pipe_text",
                            label=f"{surah}:{ayah}",
                            components={"surah": surah, "ayah": ayah},
                        ),
                        content_markup={"source_format": "quran_pipe_text"},
                        metadata={"source_line": line_number},
                    )
                )
                previous_reference = (surah, ayah)

        if not segments:
            raise ValueError(
                f"Quran pipe-text source contains no records: {source.content_path}"
            )
        return ParsedSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            segments=tuple(segments),
        )

    @staticmethod
    def _positive_integer(value: str, line_number: int, field: str) -> int:
        try:
            parsed = int(value)
        except ValueError as error:
            raise ValueError(
                f"Invalid Quran pipe-text {field} at line {line_number}: {value}"
            ) from error
        if parsed < 1:
            raise ValueError(
                f"Invalid Quran pipe-text {field} at line {line_number}: {value}"
            )
        return parsed

    @staticmethod
    def _validate_order(
        previous: tuple[int, int] | None,
        current: tuple[int, int],
        line_number: int,
    ) -> None:
        if previous is None:
            if current != (1, 1):
                raise ValueError("Quran pipe-text records must begin with 1:1")
            return
        previous_surah, previous_ayah = previous
        surah, ayah = current
        valid = (surah == previous_surah and ayah == previous_ayah + 1) or (
            surah == previous_surah + 1 and ayah == 1
        )
        if not valid:
            raise ValueError(
                f"Non-contiguous Quran pipe-text ordering at line {line_number}: "
                f"{previous_surah}:{previous_ayah} followed by {surah}:{ayah}"
            )
