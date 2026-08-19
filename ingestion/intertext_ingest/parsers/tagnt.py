import re
from dataclasses import dataclass, field
from pathlib import Path

from intertext_ingest.normalized import AcquiredSource, SourceMetadata, SourceReference
from intertext_ingest.normalizers.greek import normalize_greek_token

_ROW_IDENTIFIER = re.compile(
    r"^(?P<reference>[A-Za-z0-9]{3}\.\d+\.\d+)"
    r"(?P<reference_variants>(?:\[\d+\.\d+\]|\(\d+\.\d+\)|\{\d+\.\d+\})*)"
    r"#(?P<word>\d+)=(?P<word_type>.+)$"
)
_REFERENCE = re.compile(
    r"^(?P<book>[A-Za-z0-9]{3})\.(?P<chapter>\d+)\.(?P<verse>\d+)$"
)
_SURFACE_TRANSLITERATION = re.compile(r"^(?P<surface>.*?) \((?P<transliteration>.*)\)$")
_EDITION_MARKER = re.compile(r"^(?P<edition>[A-Za-z0-9]+)(?P<move>[«»]\d+)?$")
_MEANING_READING = re.compile(
    r"^(?P<surface>.+?) \([^)]*=.*?\) (?P<gloss>.+?)\s+-\s+"
    r"(?P<analysis>.+?) in: (?P<editions>.+)$"
)
_SPELLING_READING = re.compile(
    r"(?:^|;\s*)\+?(?P<editions>[A-Za-z0-9+«»]+):\s*(?P<surface>[^;]+)"
)

_FIELD_NAMES = (
    "word_and_type",
    "greek",
    "english_translation",
    "strongs_grammar",
    "dictionary_form_gloss",
    "editions",
    "meaning_variants",
    "spelling_variants",
    "spanish_translation",
    "sub_meaning",
    "conjoin_word",
    "simple_strongs_instance",
    "alternate_strongs",
    "variant_notes",
    "field_14",
    "field_15",
    "field_16",
)


@dataclass(frozen=True)
class TagntReading:
    surface: str
    normalized: str
    contextual_gloss: str
    editions: tuple[str, ...]
    edition_markers: tuple[str, ...]
    displacement: int = 0
    reading_type: str = "primary"
    analysis: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TagntEntry:
    sequence: int
    source_identifier: str
    source_reference: SourceReference
    source_word_number: int
    word_type: str
    lemma: str | None
    normalized_lemma: str | None
    dictionary_gloss: str | None
    readings: tuple[TagntReading, ...]
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedTagntSource:
    source: SourceMetadata
    parser_version: str
    entries: tuple[TagntEntry, ...]


class TagntParser:
    """Parse TAGNT tab records without choosing a Bible edition or target text."""

    PARSER_VERSION = "tagnt-tsv-1"

    def parse(self, source: AcquiredSource) -> ParsedTagntSource:
        entries: list[TagntEntry] = []
        for path in sorted(source.content_path.glob("TAGNT *.txt")):
            entries.extend(self._parse_file(path))
        if not entries:
            raise ValueError(f"No TAGNT data files found in {source.content_path}")
        # File-local line numbers remain in metadata, while sequence identifies a
        # stable position across the complete acquired artifact.
        entries = [
            TagntEntry(
                sequence=sequence,
                source_identifier=entry.source_identifier,
                source_reference=entry.source_reference,
                source_word_number=entry.source_word_number,
                word_type=entry.word_type,
                lemma=entry.lemma,
                normalized_lemma=entry.normalized_lemma,
                dictionary_gloss=entry.dictionary_gloss,
                readings=entry.readings,
                metadata=entry.metadata,
            )
            for sequence, entry in enumerate(entries, start=1)
        ]
        return ParsedTagntSource(
            source=source.metadata,
            parser_version=self.PARSER_VERSION,
            entries=tuple(entries),
        )

    def _parse_file(self, path: Path) -> list[TagntEntry]:
        entries: list[TagntEntry] = []
        with path.open(encoding="utf-8-sig", newline="") as source_file:
            for line_number, line in enumerate(source_file, start=1):
                fields = line.rstrip("\r\n").split("\t")
                match = _ROW_IDENTIFIER.fullmatch(fields[0]) if fields else None
                if match is None:
                    continue
                if len(fields) != len(_FIELD_NAMES):
                    raise ValueError(
                        f"TAGNT row has {len(fields)} fields instead of "
                        f"{len(_FIELD_NAMES)} at {path.name}:{line_number}"
                    )
                row = dict(zip(_FIELD_NAMES, fields))
                reference = self._source_reference(match.group("reference"))
                lemma, dictionary_gloss = self._dictionary(row["dictionary_form_gloss"])
                readings = self._readings(row)
                if not readings:
                    raise ValueError(
                        f"TAGNT row has no readings at {path.name}:{line_number}"
                    )
                entries.append(
                    TagntEntry(
                        sequence=len(entries) + 1,
                        source_identifier=fields[0],
                        source_reference=reference,
                        source_word_number=int(match.group("word")),
                        word_type=match.group("word_type"),
                        lemma=lemma,
                        normalized_lemma=(
                            normalize_greek_token(lemma) if lemma else None
                        ),
                        dictionary_gloss=dictionary_gloss,
                        readings=readings,
                        metadata={
                            "source_file": path.name,
                            "source_line": line_number,
                            "reference_variants": match.group(
                                "reference_variants"
                            ),
                            "fields": row,
                        },
                    )
                )
        return entries

    @classmethod
    def _readings(cls, row: dict[str, str]) -> tuple[TagntReading, ...]:
        surface, transliteration = cls._surface(row["greek"])
        editions, markers = cls._editions(row["editions"])
        readings = [
            TagntReading(
                surface=surface,
                normalized=normalize_greek_token(surface),
                contextual_gloss=row["english_translation"],
                editions=editions,
                edition_markers=markers,
                displacement=cls._displacement(markers, "SBL"),
                analysis=row["strongs_grammar"] or None,
                metadata={"transliteration": transliteration},
            )
        ]
        for variant in row["meaning_variants"].split(" ¦ "):
            match = _MEANING_READING.fullmatch(variant.strip())
            if match is None:
                continue
            variant_editions, variant_markers = cls._editions(match.group("editions"))
            readings.append(
                TagntReading(
                    surface=match.group("surface"),
                    normalized=normalize_greek_token(match.group("surface")),
                    contextual_gloss=match.group("gloss").strip(),
                    editions=variant_editions,
                    edition_markers=variant_markers,
                    displacement=cls._displacement(variant_markers, "SBL"),
                    reading_type="meaning_variant",
                    analysis=match.group("analysis").strip(),
                    metadata={"raw_variant": variant},
                )
            )
        for match in _SPELLING_READING.finditer(row["spelling_variants"]):
            variant_editions, variant_markers = cls._editions(match.group("editions"))
            variant_surface = match.group("surface").strip()
            readings.append(
                TagntReading(
                    surface=variant_surface,
                    normalized=normalize_greek_token(variant_surface),
                    contextual_gloss=row["english_translation"],
                    editions=variant_editions,
                    edition_markers=variant_markers,
                    displacement=cls._displacement(variant_markers, "SBL"),
                    reading_type="spelling_variant",
                    analysis=row["strongs_grammar"] or None,
                    metadata={"raw_variant": match.group(0)},
                )
            )
        return tuple(readings)

    @staticmethod
    def _surface(value: str) -> tuple[str, str | None]:
        match = _SURFACE_TRANSLITERATION.fullmatch(value)
        if match is None:
            return value, None
        return match.group("surface"), match.group("transliteration")

    @staticmethod
    def _dictionary(value: str) -> tuple[str | None, str | None]:
        if not value:
            return None, None
        lemma, separator, gloss = value.partition("=")
        return lemma.strip() or None, gloss.strip() if separator else None

    @staticmethod
    def _editions(value: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        markers = tuple(item.strip() for item in value.split("+") if item.strip())
        editions = []
        for marker in markers:
            match = _EDITION_MARKER.fullmatch(marker)
            if match is not None:
                editions.append(match.group("edition"))
        return tuple(editions), markers

    @staticmethod
    def _displacement(markers: tuple[str, ...], edition: str) -> int:
        for marker in markers:
            match = _EDITION_MARKER.fullmatch(marker)
            if match is None or match.group("edition") != edition:
                continue
            movement = match.group("move")
            if movement is None:
                return 0
            distance = int(movement[1:])
            return distance if movement[0] == "»" else -distance
        return 0

    @staticmethod
    def _source_reference(label: str) -> SourceReference:
        match = _REFERENCE.fullmatch(label)
        if match is None:
            raise ValueError(f"Invalid TAGNT reference: {label}")
        return SourceReference(
            scheme="tagnt",
            label=label,
            components={
                "book_code": match.group("book"),
                "chapter": int(match.group("chapter")),
                "verse": int(match.group("verse")),
            },
        )
