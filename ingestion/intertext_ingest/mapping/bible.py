import uuid
from collections import defaultdict

from app.models import (
    CanonicalUnit,
    ReferenceLabel,
    ReferenceScheme,
    StructureNode,
    Text,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from intertext_ingest.mapping.base import CanonicalMappingResult
from intertext_ingest.normalized import NormalizedReference, NormalizedSegment
from intertext_ingest.normalizers.references import (
    BOOK_BY_CODE,
    normalize_reference_label,
)


class BibleCanonicalMapper:
    SCHEME_NAME = "Intertext Bible"

    def map_segments(
        self, session: Session, segments: tuple[NormalizedSegment, ...]
    ) -> CanonicalMappingResult:
        references = {segment.reference.key: segment.reference for segment in segments}
        for reference in references.values():
            if reference.scheme != "bible.usfm":
                raise ValueError(
                    f"Bible mapper cannot resolve scheme '{reference.scheme}'"
                )

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
                description="Intertext's normalized Bible alignment reference scheme.",
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
            unit_ids_by_reference={
                key: (existing_units[key].id,) for key in references
            },
        )

    @staticmethod
    def _ordinal(reference: NormalizedReference) -> int:
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
                (str(unit.metadata_["book_code"]), int(unit.metadata_["chapter"]))
            ].append(unit)

        existing_nodes = list(
            session.scalars(
                select(StructureNode).where(StructureNode.text_id == text_id)
            )
        )
        books = {
            str(node.metadata_.get("book_code")): node
            for node in existing_nodes
            if node.node_type == "book"
        }
        chapters = {
            (
                str(node.metadata_.get("book_code")),
                int(node.metadata_.get("chapter", 0)),
            ): node
            for node in existing_nodes
            if node.node_type == "chapter"
        }

        for (book_code, chapter), chapter_units in sorted(
            units_by_chapter.items(),
            key=lambda item: (BOOK_BY_CODE[item[0][0]].order, item[0][1]),
        ):
            book = BOOK_BY_CODE[book_code]
            book_node = books.get(book_code)
            if book_node is None:
                book_node = StructureNode(
                    text_id=text_id,
                    parent_id=None,
                    node_type="book",
                    title=book.name,
                    short_title=book.name,
                    ordinal=book.order,
                    path=f"bible.{book.code.lower()}",
                    depth=0,
                    metadata_={"book_code": book.code, "testament": book.testament},
                )
                session.add(book_node)
                session.flush()
                books[book_code] = book_node
            first_ordinal = min(unit.ordinal for unit in chapter_units)
            last_ordinal = max(unit.ordinal for unit in chapter_units)
            chapter_node = chapters.get((book_code, chapter))
            if chapter_node is None:
                chapter_node = StructureNode(
                    text_id=text_id,
                    parent_id=book_node.id,
                    node_type="chapter",
                    title=f"{book.name} {chapter}",
                    short_title=str(chapter),
                    ordinal=chapter,
                    path=f"bible.{book.code.lower()}.{chapter}",
                    depth=1,
                    start_unit_ordinal=first_ordinal,
                    end_unit_ordinal=last_ordinal,
                    metadata_={"book_code": book.code, "chapter": chapter},
                )
                session.add(chapter_node)
                chapters[(book_code, chapter)] = chapter_node
            else:
                chapter_node.start_unit_ordinal = first_ordinal
                chapter_node.end_unit_ordinal = last_ordinal

        for book_code, book_node in books.items():
            book_units = [
                unit
                for (code, _chapter), values in units_by_chapter.items()
                if code == book_code
                for unit in values
            ]
            if book_units:
                book_node.start_unit_ordinal = min(unit.ordinal for unit in book_units)
                book_node.end_unit_ordinal = max(unit.ordinal for unit in book_units)

    def _ensure_labels(
        self,
        session: Session,
        scheme_id: uuid.UUID,
        units,
    ) -> None:
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
            book_code = str(unit.metadata_["book_code"])
            chapter = int(unit.metadata_["chapter"])
            units_by_chapter[(book_code, chapter)].append(unit)
            label_text = (
                f"{BOOK_BY_CODE[book_code].name} {chapter}:{unit.metadata_['verse']}"
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

        for (book_code, chapter), chapter_units in units_by_chapter.items():
            first_unit = min(chapter_units, key=lambda unit: unit.ordinal)
            last_unit = max(chapter_units, key=lambda unit: unit.ordinal)
            label_text = f"{BOOK_BY_CODE[book_code].name} {chapter}"
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
