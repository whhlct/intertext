import hashlib
from dataclasses import replace
from pathlib import Path

from app import models  # noqa: F401
from app.db.base import Base
from app.models import (
    CanonicalUnit,
    EnrichmentImport,
    Lexeme,
    PreferredVersion,
    ReferenceLabel,
    SegmentUnitMapping,
    StructureNode,
    Text,
    TextVersion,
    Token,
    TokenGloss,
    VersionRelease,
    VersionSegment,
)
from intertext_ingest.corpora.quran.validation import QuranVersionValidator
from intertext_ingest.datasets import get_dataset
from intertext_ingest.enrichment_pipeline import TokenEnrichmentPipeline
from intertext_ingest.enrichments import get_token_enrichment
from intertext_ingest.normalized import AcquiredSource
from intertext_ingest.pipeline import IngestionPipeline
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class FixtureSource:
    def __init__(self, acquired: AcquiredSource) -> None:
        self.acquired = acquired

    def acquire(self, raw_root: Path, *, refresh: bool = False) -> AcquiredSource:
        return self.acquired


def test_pipeline_maps_persists_and_is_idempotent(
    tmp_path: Path,
    kjv_source: AcquiredSource,
    sblgnt_source: AcquiredSource,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    pipeline = IngestionPipeline(sessions)
    kjv = replace(get_dataset("kjv"), source=FixtureSource(kjv_source))
    sblgnt = replace(get_dataset("sblgnt"), source=FixtureSource(sblgnt_source))

    first_kjv = pipeline.run(kjv, raw_root=tmp_path)
    first_sblgnt = pipeline.run(sblgnt, raw_root=tmp_path)
    second_kjv = pipeline.run(kjv, raw_root=tmp_path)
    second_sblgnt = pipeline.run(sblgnt, raw_root=tmp_path)
    updated_kjv_source = AcquiredSource(
        kjv_source.content_path,
        replace(
            kjv_source.metadata,
            source_revision="fixture-2",
            sha256=hashlib.sha256(b"fixture-2").hexdigest(),
        ),
    )
    updated_kjv = replace(kjv, source=FixtureSource(updated_kjv_source))
    updated_kjv_result = pipeline.run(updated_kjv, raw_root=tmp_path)

    assert first_kjv.created is True
    assert first_sblgnt.created is True
    assert second_kjv.created is False
    assert second_sblgnt.created is False
    assert updated_kjv_result.created is True
    with sessions() as session:
        assert session.scalar(select(func.count(TextVersion.id))) == 2
        assert session.scalar(select(func.count(VersionRelease.id))) == 3
        assert session.scalar(select(func.count(VersionSegment.id))) == 9
        assert session.scalar(select(func.count(SegmentUnitMapping.id))) == 9
        canonical_keys = set(session.scalars(select(CanonicalUnit.internal_key)))
        assert canonical_keys == {
            "bible.mark.1.1",
            "bible.mark.1.2",
            "bible.mark.1.3",
        }
        assert set(session.scalars(select(StructureNode.path))) == {
            "bible.mark",
            "bible.mark.1",
        }
        source_identifiers = set(
            session.scalars(select(VersionSegment.source_identifier))
        )
        assert source_identifiers == {"Mark 1:1", "Mark 1:2", "Mark 1:3"}
        assert all(
            "book_code" not in unit.metadata_
            for unit in session.scalars(select(CanonicalUnit))
        )
        kjv_version_id = session.scalar(
            select(TextVersion.id).where(TextVersion.slug == "kjv")
        )
        assert (
            session.scalar(
                select(func.count(VersionRelease.id)).where(
                    VersionRelease.version_id == kjv_version_id,
                    VersionRelease.is_current.is_(True),
                )
            )
            == 1
        )
        preferred = session.scalar(select(PreferredVersion))
        assert preferred is not None
        version = session.get(TextVersion, preferred.version_id)
        assert version is not None
        assert version.slug == "sblgnt"
        assert preferred.role == "default_source"

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_oshb_pipeline_aligns_genesis_and_sets_old_testament_source(
    tmp_path: Path,
    oshb_source: AcquiredSource,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    pipeline = IngestionPipeline(sessions)
    oshb = replace(get_dataset("oshb"), source=FixtureSource(oshb_source))

    first = pipeline.run(oshb, raw_root=tmp_path)
    second = pipeline.run(oshb, raw_root=tmp_path)

    assert first.created is True
    assert second.created is False
    assert first.segment_count == 3
    assert first.mapping_count == 3
    with sessions() as session:
        assert set(session.scalars(select(CanonicalUnit.internal_key))) == {
            "bible.genesis.1.1",
            "bible.genesis.1.2",
            "bible.genesis.1.3",
        }
        segments = list(
            session.scalars(select(VersionSegment).order_by(VersionSegment.sequence))
        )
        assert [segment.source_identifier for segment in segments] == [
            "Genesis 1:1",
            "Genesis 1:2",
            "Genesis 1:3",
        ]
        assert segments[0].text_plain.startswith("בְּרֵאשִׁ֖ית בָּרָ֣א")
        first_word = segments[0].content_markup["elements"][0]
        assert first_word["id"] == "01xeN"
        assert first_word["lemma"] == "b/7225"
        assert first_word["morphology"] == "HR/Ncfsa"
        assert first_word["cantillation_hierarchy"] == "1.0"
        preferred = session.scalar(select(PreferredVersion))
        assert preferred is not None
        assert preferred.role == "default_source"
        version = session.get(TextVersion, preferred.version_id)
        assert version is not None
        assert version.slug == "oshb"
        first_mapping = session.scalar(
            select(SegmentUnitMapping).where(
                SegmentUnitMapping.segment_id == segments[0].id
            )
        )
        assert first_mapping is not None
        assert preferred.start_unit_id == first_mapping.canonical_unit_id

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_tagnt_enrichment_populates_sblgnt_tokens_glosses_and_is_idempotent(
    tmp_path: Path,
    sblgnt_source: AcquiredSource,
    tagnt_source: AcquiredSource,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    sblgnt = replace(
        get_dataset("sblgnt"), source=FixtureSource(sblgnt_source)
    )
    IngestionPipeline(sessions).run(sblgnt, raw_root=tmp_path)
    enrichment = replace(
        get_token_enrichment("tagnt-sblgnt"),
        source=FixtureSource(tagnt_source),
    )
    pipeline = TokenEnrichmentPipeline(sessions)

    first = pipeline.run(enrichment, raw_root=tmp_path)
    second = pipeline.run(enrichment, raw_root=tmp_path)

    assert first.created is True
    assert second.created is False
    assert first.token_count == 15
    assert first.gloss_count == 15
    assert first.skipped_verse_count == 0
    assert second.enrichment_import_id == first.enrichment_import_id
    with sessions() as session:
        assert session.scalar(select(func.count(VersionRelease.id))) == 1
        assert session.scalar(select(func.count(EnrichmentImport.id))) == 1
        assert session.scalar(select(func.count(Token.id))) == 15
        assert session.scalar(select(func.count(TokenGloss.id))) == 15
        assert session.scalar(select(func.count(Lexeme.id))) > 0
        first_token = session.scalar(
            select(Token)
            .join(VersionSegment, VersionSegment.id == Token.segment_id)
            .where(VersionSegment.source_identifier == "Mark 1:1")
            .order_by(Token.token_index)
        )
        assert first_token is not None
        assert first_token.surface == "Ἀρχὴ"
        assert first_token.normalized == "αρχη"
        assert first_token.metadata_["tagnt"]["source_identifier"] == (
            "Mrk.1.1#01=NKO"
        )
        gloss = session.scalar(
            select(TokenGloss).where(TokenGloss.token_id == first_token.id)
        )
        assert gloss is not None
        assert gloss.gloss == "[The] beginning"
        assert gloss.gloss_type == "contextual"
        assert gloss.source == "TAGNT"
        assert gloss.metadata_["source_file"] == "TAGNT Mark - fixture.txt"
        mark_three = list(
            session.execute(
                select(Token.surface, TokenGloss.gloss)
                .join(TokenGloss, TokenGloss.token_id == Token.id)
                .join(VersionSegment, VersionSegment.id == Token.segment_id)
                .where(VersionSegment.source_identifier == "Mark 1:3")
                .order_by(Token.token_index)
            )
        )
        assert mark_three[:3] == [
            ("φωνὴ", "[The] voice"),
            ("βοῶντος", "of one crying"),
            ("ἐν", "in"),
        ]
        imported = session.scalar(select(EnrichmentImport))
        assert imported is not None
        assert imported.source_revision == "tagnt-fixture-commit"
        assert imported.metadata_["source"]["license"] == "CC BY 4.0"

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_quran_pipeline_maps_persists_and_is_idempotent(
    tmp_path: Path,
    quran_source: AcquiredSource,
    quran_saheeh_source: AcquiredSource,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    pipeline = IngestionPipeline(sessions)
    quran = replace(
        get_dataset("quran"),
        source=FixtureSource(quran_source),
        corpus_validator=QuranVersionValidator(
            expected_surah_count=2,
            expected_ayah_count=4,
            required_canonical_keys=("quran.1.1", "quran.2.2"),
        ),
    )
    saheeh = replace(
        get_dataset("quran-saheeh-international"),
        source=FixtureSource(quran_saheeh_source),
        corpus_validator=QuranVersionValidator(
            expected_surah_count=2,
            expected_ayah_count=4,
            required_canonical_keys=("quran.1.1", "quran.2.2"),
        ),
    )

    first_saheeh = pipeline.run(saheeh, raw_root=tmp_path)
    second_saheeh = pipeline.run(saheeh, raw_root=tmp_path)
    first = pipeline.run(quran, raw_root=tmp_path)
    second = pipeline.run(quran, raw_root=tmp_path)

    assert first.created is True
    assert second.created is False
    assert first.segment_count == 4
    assert first.mapping_count == 4
    assert first_saheeh.created is True
    assert second_saheeh.created is False
    assert first_saheeh.segment_count == 4
    assert first_saheeh.mapping_count == 4
    with sessions() as session:
        text = session.scalar(select(Text).where(Text.slug == "quran"))
        assert text is not None
        assert text.title == "Quran"
        assert set(session.scalars(select(CanonicalUnit.internal_key))) == {
            "quran.1.1",
            "quran.1.2",
            "quran.2.1",
            "quran.2.2",
        }
        assert set(session.scalars(select(StructureNode.path))) == {
            "quran.1",
            "quran.2",
        }
        assert set(session.scalars(select(VersionSegment.source_identifier))) == {
            "1:1",
            "1:2",
            "2:1",
            "2:2",
        }
        assert session.scalar(select(func.count(TextVersion.id))) == 2
        assert session.scalar(select(func.count(VersionRelease.id))) == 2
        assert session.scalar(select(func.count(VersionSegment.id))) == 8
        assert session.scalar(select(func.count(SegmentUnitMapping.id))) == 8
        labels = set(session.scalars(select(ReferenceLabel.normalized_label)))
        assert {"1:1", "surah 1", "الفاتحة"}.issubset(labels)
        first_segment = session.scalar(
            select(VersionSegment)
            .join(
                VersionRelease,
                VersionRelease.id == VersionSegment.version_release_id,
            )
            .join(TextVersion, TextVersion.id == VersionRelease.version_id)
            .where(TextVersion.slug == "tanzil-simple")
            .order_by(VersionSegment.sequence)
        )
        assert first_segment is not None
        assert first_segment.text_plain == (
            "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"
        )
        translated_segment = session.scalar(
            select(VersionSegment)
            .join(
                VersionRelease,
                VersionRelease.id == VersionSegment.version_release_id,
            )
            .join(TextVersion, TextVersion.id == VersionRelease.version_id)
            .where(
                TextVersion.slug == "saheeh-international",
                VersionSegment.source_identifier == "2:2",
            )
        )
        assert translated_segment is not None
        assert translated_segment.text_plain == (
            "This is the Book | about which there is no doubt."
        )
        preferred = session.scalar(select(PreferredVersion))
        assert preferred is not None
        version = session.get(TextVersion, preferred.version_id)
        assert version is not None
        assert version.slug == "tanzil-simple"
        assert preferred.role == "default_source"

    Base.metadata.drop_all(engine)
    engine.dispose()
