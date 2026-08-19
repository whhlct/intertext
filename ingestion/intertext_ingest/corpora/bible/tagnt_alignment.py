import uuid
from dataclasses import dataclass
from functools import lru_cache

from intertext_ingest.corpora.bible.canon import BibleCanon
from intertext_ingest.corpora.bible.references import (
    bible_reference_from_label,
    resolve_bible_reference,
)
from intertext_ingest.normalizers.greek import greek_alignment_forms
from intertext_ingest.parsers.tagnt import (
    ParsedTagntSource,
    TagntEntry,
    TagntReading,
)


class TagntAlignmentError(ValueError):
    pass


@dataclass(frozen=True)
class SblgntTargetToken:
    segment_id: uuid.UUID
    token_index: int
    surface: str
    normalized: str
    language_id: uuid.UUID
    char_start: int | None
    char_end: int | None
    existing_token_id: uuid.UUID | None = None


@dataclass(frozen=True)
class SblgntTargetVerse:
    reference_label: str
    tokens: tuple[SblgntTargetToken, ...]


@dataclass(frozen=True)
class TagntCandidate:
    entry: TagntEntry
    reading: TagntReading
    surface: str
    reading_part: int


@dataclass(frozen=True)
class AlignedTagntToken:
    target: SblgntTargetToken
    candidate: TagntCandidate


@dataclass(frozen=True)
class TagntAlignmentIssue:
    reference_label: str
    reason: str


@dataclass(frozen=True)
class TagntAlignmentResult:
    aligned: tuple[AlignedTagntToken, ...]
    issues: tuple[TagntAlignmentIssue, ...]


class TagntSblgntAligner:
    """Align SBL-specific TAGNT readings to SBLGNT words, verse by verse."""

    EDITION = "SBL"

    def __init__(self, canon: BibleCanon) -> None:
        self.canon = canon

    def align(
        self,
        parsed: ParsedTagntSource,
        target_verses: tuple[SblgntTargetVerse, ...],
        *,
        allow_partial: bool = False,
    ) -> TagntAlignmentResult:
        entries_by_key: dict[str, list[TagntEntry]] = {}
        for entry in parsed.entries:
            reference = resolve_bible_reference(entry.source_reference, self.canon)
            entries_by_key.setdefault(reference.key, []).append(entry)

        aligned: list[AlignedTagntToken] = []
        issues: list[TagntAlignmentIssue] = []
        for target_verse in target_verses:
            reference = bible_reference_from_label(
                target_verse.reference_label, self.canon
            )
            try:
                candidate_orders = self._candidate_orders(
                    entries_by_key.get(reference.key, [])
                )
                aligned.extend(
                    self._align_candidate_orders(target_verse, candidate_orders)
                )
            except TagntAlignmentError as error:
                issue = TagntAlignmentIssue(target_verse.reference_label, str(error))
                if not allow_partial:
                    raise TagntAlignmentError(
                        f"TAGNT alignment failed for {target_verse.reference_label}: "
                        f"{error}"
                    ) from error
                issues.append(issue)
        return TagntAlignmentResult(tuple(aligned), tuple(issues))

    def _candidate_orders(
        self, entries: list[TagntEntry]
    ) -> tuple[tuple[TagntCandidate, ...], ...]:
        candidates: list[tuple[int, TagntCandidate]] = []
        for entry in entries:
            readings = self._sbl_readings(entry)
            for reading in readings:
                surfaces = reading.surface.split()
                if len(surfaces) != 1:
                    raise TagntAlignmentError(
                        f"multi-token SBL reading cannot receive one word gloss at "
                        f"{entry.source_identifier}: {reading.surface!r}"
                    )
                for part, surface in enumerate(surfaces):
                    candidates.append(
                        (
                            part,
                            TagntCandidate(entry, reading, surface, part),
                        )
                    )
        source_order = tuple(
            item[1]
            for item in sorted(
                candidates,
                key=lambda item: (item[1].entry.source_word_number, item[0]),
            )
        )
        # TAGNT normally presents a common base order and annotates editions that
        # differ from it. In a few records the displayed order already matches
        # SBLGNT despite an SBL displacement marker, so both documented order
        # interpretations are validated against the complete verse context.
        displaced_order = tuple(
            item[1]
            for item in sorted(
                candidates,
                key=lambda item: (
                    item[1].entry.source_word_number
                    + item[1].reading.displacement,
                    1 if item[1].reading.displacement else 0,
                    item[0],
                ),
            )
        )
        orders = [source_order]
        if displaced_order != source_order:
            orders.append(displaced_order)
        return tuple(orders)

    @classmethod
    def _align_candidate_orders(
        cls,
        target_verse: SblgntTargetVerse,
        candidate_orders: tuple[tuple[TagntCandidate, ...], ...],
    ) -> tuple[AlignedTagntToken, ...]:
        successful: dict[tuple[str, ...], tuple[AlignedTagntToken, ...]] = {}
        first_error: TagntAlignmentError | None = None
        for candidates in candidate_orders:
            try:
                alignment = cls._align_verse(target_verse, candidates)
            except TagntAlignmentError as error:
                first_error = first_error or error
                continue
            signature = tuple(
                aligned.candidate.entry.source_identifier for aligned in alignment
            )
            successful[signature] = alignment
        if not successful:
            if first_error is not None:
                raise first_error
            raise TagntAlignmentError("no TAGNT rows marked for the SBL edition")
        if len(successful) > 1:
            raise TagntAlignmentError(
                "ambiguous normalized-token/context match across TAGNT edition "
                "order interpretations"
            )
        return next(iter(successful.values()))

    def _sbl_readings(self, entry: TagntEntry) -> tuple[TagntReading, ...]:
        selected = [
            reading for reading in entry.readings if self.EDITION in reading.editions
        ]
        if not selected:
            return ()
        meaning = [
            reading for reading in selected if reading.reading_type == "meaning_variant"
        ]
        spelling = [
            reading for reading in selected if reading.reading_type == "spelling_variant"
        ]
        preferred = meaning or spelling or [
            reading for reading in selected if reading.reading_type == "primary"
        ]
        unique = {
            (reading.normalized, reading.contextual_gloss, reading.displacement): reading
            for reading in preferred
        }
        if len(unique) > 1:
            descriptions = ", ".join(
                f"{reading.surface!r}/{reading.contextual_gloss!r}"
                for reading in unique.values()
            )
            raise TagntAlignmentError(
                f"ambiguous SBL readings for {entry.source_identifier}: {descriptions}"
            )
        return tuple(unique.values())

    @staticmethod
    def _align_verse(
        target_verse: SblgntTargetVerse,
        candidates: tuple[TagntCandidate, ...],
    ) -> tuple[AlignedTagntToken, ...]:
        if not candidates:
            raise TagntAlignmentError("no TAGNT rows marked for the SBL edition")
        targets = target_verse.tokens

        def matches(target_index: int, candidate_index: int) -> bool:
            return bool(
                greek_alignment_forms(targets[target_index].surface)
                & greek_alignment_forms(candidates[candidate_index].surface)
            )

        @lru_cache(maxsize=None)
        def paths(target_index: int, candidate_start: int) -> tuple[tuple[int, ...], ...]:
            if target_index == len(targets):
                return ((),)
            solutions: list[tuple[int, ...]] = []
            remaining_targets = len(targets) - target_index
            last_start = len(candidates) - remaining_targets
            for candidate_index in range(candidate_start, last_start + 1):
                if not matches(target_index, candidate_index):
                    continue
                for tail in paths(target_index + 1, candidate_index + 1):
                    solutions.append((candidate_index, *tail))
                    if len(solutions) > 1:
                        return tuple(solutions)
            return tuple(solutions)

        solutions = paths(0, 0)
        if not solutions:
            target_text = " ".join(token.surface for token in targets)
            candidate_text = " ".join(candidate.surface for candidate in candidates)
            raise TagntAlignmentError(
                "no complete normalized-token/context match; "
                f"SBLGNT={target_text!r}; TAGNT-SBL={candidate_text!r}"
            )
        if len(solutions) > 1:
            raise TagntAlignmentError(
                "ambiguous normalized-token/context match; more than one alignment exists"
            )
        return tuple(
            AlignedTagntToken(target, candidates[candidate_index])
            for target, candidate_index in zip(targets, solutions[0])
        )
