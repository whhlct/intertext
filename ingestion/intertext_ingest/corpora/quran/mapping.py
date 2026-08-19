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
from intertext_ingest.corpora.quran.references import (
    normalize_quran_reference_label,
    quran_reference_sort_key,
    resolve_quran_reference,
)
from intertext_ingest.normalized import (
    CanonicalReference,
    NormalizedVersion,
    ResolvedSegment,
    ResolvedVersion,
)


class QuranMapper:
    """Interpret Quran source references and materialize Quran canonical units."""

    SCHEME_NAME = "Intertext Quran"

    def resolve(self, version: NormalizedVersion) -> ResolvedVersion:
        resolved: list[ResolvedSegment] = []
        for segment in version.segments:
            reference = resolve_quran_reference(segment.source_reference)
            resolved.append(
                ResolvedSegment(
                    segment=segment,
                    canonical_targets=(reference,),
                    identifier=reference.label,
                )
            )
        resolved.sort(
            key=lambda item: quran_reference_sort_key(item.canonical_targets[0])
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
        self,
        session: Session,
        version: ResolvedVersion,
    ) -> CanonicalMappingResult:
        references = {
            target.key: target
            for segment in version.segments
            for target in segment.canonical_targets
        }
        text = session.scalar(select(Text).where(Text.slug == "quran"))
        if text is None:
            text = Text(
                slug="quran",
                title="Quran",
                description=(
                    "The conceptual Quran corpus and its canonical reference "
                    "structure."
                ),
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
                description="Intertext's normalized surah and ayah reference scheme.",
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
            unit = existing_units.get(reference.key)
            if unit is None:
                unit = CanonicalUnit(
                    text_id=text.id,
                    ordinal=self._ordinal(reference),
                    internal_key=reference.key,
                    unit_type="ayah",
                    metadata_={"label": str(reference.components["ayah"])},
                )
                session.add(unit)
                existing_units[reference.key] = unit
            unit.metadata_ = {
                "label": str(reference.components["ayah"]),
                **reference.components,
            }
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
            int(reference.components["surah"]) * 1_000
            + int(reference.components["ayah"])
        )

    def _ensure_structure(
        self,
        session: Session,
        text_id: uuid.UUID,
        units,
    ) -> None:
        units_by_surah: dict[int, list[CanonicalUnit]] = defaultdict(list)
        for unit in units:
            units_by_surah[int(unit.metadata_["surah"])].append(unit)
        existing_nodes = {
            int(node.metadata_.get("surah", 0)): node
            for node in session.scalars(
                select(StructureNode).where(
                    StructureNode.text_id == text_id,
                    StructureNode.node_type == "surah",
                )
            )
        }
        for surah, surah_units in sorted(units_by_surah.items()):
            first = min(surah_units, key=lambda unit: unit.ordinal)
            last = max(surah_units, key=lambda unit: unit.ordinal)
            name = str(first.metadata_["surah_name"])
            node = existing_nodes.get(surah)
            if node is None:
                node = StructureNode(
                    text_id=text_id,
                    parent_id=None,
                    node_type="surah",
                    title=name,
                    short_title=str(surah),
                    ordinal=surah,
                    path=f"quran.{surah}",
                    depth=0,
                    metadata_={"surah": surah, "name": name},
                )
                session.add(node)
            node.title = name
            node.short_title = str(surah)
            node.start_unit_ordinal = first.ordinal
            node.end_unit_ordinal = last.ordinal
            node.metadata_ = {"surah": surah, "name": name}

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
        units_by_surah: dict[int, list[CanonicalUnit]] = defaultdict(list)
        for unit in units:
            surah = int(unit.metadata_["surah"])
            ayah = int(unit.metadata_["ayah"])
            name = str(unit.metadata_["surah_name"])
            units_by_surah[surah].append(unit)
            for label_text in (f"{surah}:{ayah}", f"Surah {surah}:{ayah}"):
                self._upsert_label(
                    session,
                    existing_labels,
                    scheme_id,
                    label_text,
                    unit,
                    unit,
                )
            self._upsert_label(
                session,
                existing_labels,
                scheme_id,
                f"{name} {ayah}",
                unit,
                unit,
            )

        for surah, surah_units in units_by_surah.items():
            first = min(surah_units, key=lambda unit: unit.ordinal)
            last = max(surah_units, key=lambda unit: unit.ordinal)
            name = str(first.metadata_["surah_name"])
            for label_text in (str(surah), f"Surah {surah}", name):
                self._upsert_label(
                    session,
                    existing_labels,
                    scheme_id,
                    label_text,
                    first,
                    last,
                )

    @staticmethod
    def _upsert_label(
        session: Session,
        existing: dict[str, ReferenceLabel],
        scheme_id: uuid.UUID,
        label_text: str,
        start: CanonicalUnit,
        end: CanonicalUnit,
    ) -> None:
        normalized = normalize_quran_reference_label(label_text)
        label = existing.get(normalized)
        if label is None:
            label = ReferenceLabel(
                reference_scheme_id=scheme_id,
                start_unit_id=start.id,
                end_unit_id=end.id,
                label=label_text,
                normalized_label=normalized,
                sort_order=start.ordinal,
            )
            session.add(label)
            existing[normalized] = label
        else:
            label.start_unit_id = start.id
            label.end_unit_id = end.id
            label.label = label_text
            label.sort_order = start.ordinal
