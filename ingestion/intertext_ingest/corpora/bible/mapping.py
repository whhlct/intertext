import uuid
from collections import defaultdict
from dataclasses import replace

from app.models import (
    CanonicalUnit,
    ReferenceLabel,
    ReferenceScheme,
    StructureNode,
    Text,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from intertext_ingest.corpora.base import CanonicalMappingResult
from intertext_ingest.corpora.bible.canon import BibleCanon
from intertext_ingest.corpora.bible.references import (
    bible_reference_sort_key,
    normalize_reference_label,
    resolve_bible_reference,
)
from intertext_ingest.normalized import (
    CanonicalReference,
    NormalizedVersion,
    ResolvedSegment,
    ResolvedVersion,
)


class BibleMapper:
    """Interpret source references and materialize one configured Bible canon."""

    SCHEME_NAME = "Intertext Bible"

    def __init__(self, canon: BibleCanon) -> None:
        self.canon = canon

    def resolve(self, version: NormalizedVersion) -> ResolvedVersion:
        resolved: list[ResolvedSegment] = []
        for segment in version.segments:
            reference = resolve_bible_reference(segment.source_reference, self.canon)
            resolved.append(
                ResolvedSegment(
                    segment=segment,
                    canonical_targets=(reference,),
                    identifier=reference.label,
                )
            )
        resolved.sort(
            key=lambda item: bible_reference_sort_key(item.canonical_targets[0])
        )
        resequenced = tuple(
            replace(item, segment=replace(item.segment, sequence=sequence))
            for sequence, item in enumerate(resolved, start=1)
        )
        return ResolvedVersion(
            version=replace(
                version,
                segments=tuple(item.segment for item in resequenced),
            ),
            segments=resequenced,
        )

    def materialize(
        self, session: Session, version: ResolvedVersion
    ) -> CanonicalMappingResult:
        references = {
            target.key: target
            for segment in version.segments
            for target in segment.canonical_targets
        }
        text = session.scalar(select(Text).where(Text.slug == "bible"))
        if text is None:
            text = Text(
                slug="bible",
                title="Bible",
                description="The conceptual Bible corpus and its canonical reference structure.",
            )
            session.add(text)
            session.flush()

        scheme = session.scalar(
            select(ReferenceScheme).where(
                ReferenceScheme.text_id == text.id,
                ReferenceScheme.name == self.SCHEME_NAME,
            )
        )
        if scheme is None:
            scheme = ReferenceScheme(
                text_id=text.id,
                name=self.SCHEME_NAME,
                description=(
                    "Intertext's normalized Bible alignment reference scheme "
                    f"using the {self.canon.name}."
                ),
            )
            session.add(scheme)
            session.flush()
        if text.default_reference_scheme_id is None:
            text.default_reference_scheme_id = scheme.id

        existing_units = {
            unit.internal_key: unit
            for unit in session.scalars(
                select(CanonicalUnit).where(CanonicalUnit.text_id == text.id)
            )
        }
        for reference in sorted(references.values(), key=self._ordinal):
            if reference.key not in existing_units:
                unit = CanonicalUnit(
                    text_id=text.id,
                    ordinal=self._ordinal(reference),
                    internal_key=reference.key,
                    unit_type="verse",
                    metadata_={
                        "label": str(reference.components["verse"]),
                        "canon": self.canon.identifier,
                        **reference.components,
                    },
                )
                session.add(unit)
                existing_units[reference.key] = unit
        session.flush()

        self._ensure_structure(session, text.id, existing_units.values())
        self._ensure_labels(session, scheme.id, existing_units.values())
        session.flush()
        return CanonicalMappingResult(
            text_id=text.id,
            unit_ids_by_segment={
                resolved.segment.sequence: tuple(
                    existing_units[target.key].id
                    for target in resolved.canonical_targets
                )
                for resolved in version.segments
            },
        )

    @staticmethod
    def _ordinal(reference: CanonicalReference) -> int:
        return (
            int(reference.components["book_order"]) * 1_000_000
            + int(reference.components["chapter"]) * 1_000
            + int(reference.components["verse"])
        )

    def _ensure_structure(
        self,
        session: Session,
        text_id: uuid.UUID,
        units,
    ) -> None:
        units_by_chapter: dict[tuple[str, int], list[CanonicalUnit]] = defaultdict(list)
        for unit in units:
            units_by_chapter[
                (str(unit.metadata_["book_slug"]), int(unit.metadata_["chapter"]))
            ].append(unit)

        existing_nodes = list(
            session.scalars(
                select(StructureNode).where(StructureNode.text_id == text_id)
            )
        )
        books = {
            str(node.metadata_.get("book_slug")): node
            for node in existing_nodes
            if node.node_type == "book"
        }
        chapters = {
            (
                str(node.metadata_.get("book_slug")),
                int(node.metadata_.get("chapter", 0)),
            ): node
            for node in existing_nodes
            if node.node_type == "chapter"
        }
        for (book_slug, chapter), chapter_units in sorted(
            units_by_chapter.items(),
            key=lambda item: (
                int(item[1][0].metadata_["book_order"]),
                item[0][1],
            ),
        ):
            first_unit = chapter_units[0]
            book_order = int(first_unit.metadata_["book_order"])
            book = self.canon.books_by_slug[book_slug]
            book_node = books.get(book_slug)
            if book_node is None:
                book_node = StructureNode(
                    text_id=text_id,
                    parent_id=None,
                    node_type="book",
                    title=book.name,
                    short_title=book.name,
                    ordinal=book_order,
                    path=f"bible.{book.slug}",
                    depth=0,
                    metadata_={
                        "book_slug": book.slug,
                        "testament": book.testament,
                        "canon": self.canon.identifier,
                    },
                )
                session.add(book_node)
                session.flush()
                books[book_slug] = book_node
            first_ordinal = min(unit.ordinal for unit in chapter_units)
            last_ordinal = max(unit.ordinal for unit in chapter_units)
            chapter_node = chapters.get((book_slug, chapter))
            if chapter_node is None:
                chapter_node = StructureNode(
                    text_id=text_id,
                    parent_id=book_node.id,
                    node_type="chapter",
                    title=f"{book.name} {chapter}",
                    short_title=str(chapter),
                    ordinal=chapter,
                    path=f"bible.{book.slug}.{chapter}",
                    depth=1,
                    start_unit_ordinal=first_ordinal,
                    end_unit_ordinal=last_ordinal,
                    metadata_={"book_slug": book.slug, "chapter": chapter},
                )
                session.add(chapter_node)
                chapters[(book_slug, chapter)] = chapter_node
            else:
                chapter_node.start_unit_ordinal = first_ordinal
                chapter_node.end_unit_ordinal = last_ordinal

        for book_slug, book_node in books.items():
            book_units = [
                unit
                for (code, _chapter), values in units_by_chapter.items()
                if code == book_slug
                for unit in values
            ]
            if book_units:
                book_node.start_unit_ordinal = min(unit.ordinal for unit in book_units)
                book_node.end_unit_ordinal = max(unit.ordinal for unit in book_units)

    def _ensure_labels(self, session: Session, scheme_id: uuid.UUID, units) -> None:
        existing_labels = {
            label.normalized_label: label
            for label in session.scalars(
                select(ReferenceLabel).where(
                    ReferenceLabel.reference_scheme_id == scheme_id
                )
            )
        }
        units_by_chapter: dict[tuple[str, int], list[CanonicalUnit]] = defaultdict(list)
        for unit in units:
            book_slug = str(unit.metadata_["book_slug"])
            chapter = int(unit.metadata_["chapter"])
            units_by_chapter[(book_slug, chapter)].append(unit)
            label_text = (
                f"{unit.metadata_['book_name']} {chapter}:{unit.metadata_['verse']}"
            )
            normalized = normalize_reference_label(label_text)
            if normalized not in existing_labels:
                label = ReferenceLabel(
                    reference_scheme_id=scheme_id,
                    start_unit_id=unit.id,
                    end_unit_id=unit.id,
                    label=label_text,
                    normalized_label=normalized,
                    sort_order=unit.ordinal,
                )
                session.add(label)
                existing_labels[normalized] = label

        for (_book_slug, chapter), chapter_units in units_by_chapter.items():
            first_unit = min(chapter_units, key=lambda unit: unit.ordinal)
            last_unit = max(chapter_units, key=lambda unit: unit.ordinal)
            label_text = f"{first_unit.metadata_['book_name']} {chapter}"
            normalized = normalize_reference_label(label_text)
            label = existing_labels.get(normalized)
            if label is None:
                label = ReferenceLabel(
                    reference_scheme_id=scheme_id,
                    start_unit_id=first_unit.id,
                    end_unit_id=last_unit.id,
                    label=label_text,
                    normalized_label=normalized,
                    sort_order=first_unit.ordinal,
                )
                session.add(label)
                existing_labels[normalized] = label
            else:
                label.start_unit_id = first_unit.id
                label.end_unit_id = last_unit.id
                label.sort_order = first_unit.ordinal
