from collections.abc import Generator

import pytest
from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import (
    CanonicalUnit,
    EnrichmentImport,
    Language,
    PreferredVersion,
    ReferenceLabel,
    ReferenceScheme,
    SegmentUnitMapping,
    StructureNode,
    Text,
    TextVersion,
    Token,
    TokenGloss,
    VersionRelease,
    VersionSegment,
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with test_session_factory() as session:
        app.dependency_overrides[get_db_session] = lambda: session
        yield session
        app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def canonical_fixture(database_session: Session) -> None:
    text = Text(slug="bible", title="Bible")
    english = Language(iso_code="en", name="English", direction="ltr")
    greek = Language(
        iso_code="grc",
        name="Ancient Greek",
        native_name="Ἑλληνική",
        script="Grek",
        direction="ltr",
    )
    database_session.add_all([text, english, greek])
    database_session.flush()

    unit_one = CanonicalUnit(
        text_id=text.id,
        ordinal=1,
        internal_key="bible.mark.1.1",
        unit_type="verse",
        metadata_={"label": "1"},
    )
    unit_two = CanonicalUnit(
        text_id=text.id,
        ordinal=2,
        internal_key="bible.mark.1.2",
        unit_type="verse",
        metadata_={"label": "2"},
    )
    scheme = ReferenceScheme(text_id=text.id, name="Default")
    database_session.add_all([unit_one, unit_two, scheme])
    database_session.flush()
    text.default_reference_scheme_id = scheme.id
    book = StructureNode(
        text_id=text.id,
        node_type="book",
        title="Mark",
        short_title="Mark",
        ordinal=41,
        path="bible.mark",
        depth=0,
        start_unit_ordinal=unit_one.ordinal,
        end_unit_ordinal=unit_two.ordinal,
    )
    database_session.add(book)
    database_session.flush()
    database_session.add(
        StructureNode(
            text_id=text.id,
            parent_id=book.id,
            node_type="chapter",
            title="Mark 1",
            short_title="1",
            ordinal=1,
            path="bible.mark.1",
            depth=1,
            start_unit_ordinal=unit_one.ordinal,
            end_unit_ordinal=unit_two.ordinal,
        )
    )
    database_session.add(
        ReferenceLabel(
            reference_scheme_id=scheme.id,
            start_unit_id=unit_one.id,
            end_unit_id=unit_two.id,
            label="Mark 1",
            normalized_label="mark 1",
            sort_order=1,
        )
    )

    greek_version = TextVersion(
        text_id=text.id,
        slug="greek",
        title="Greek Test Version",
        abbreviation="GTV",
        default_language_id=greek.id,
        reference_scheme_id=scheme.id,
        version_type="critical_edition",
    )
    english_version = TextVersion(
        text_id=text.id,
        slug="english",
        title="English Test Version",
        abbreviation="ETV",
        default_language_id=english.id,
        reference_scheme_id=scheme.id,
        version_type="translation",
    )
    database_session.add_all([greek_version, english_version])
    database_session.flush()

    greek_release = VersionRelease(
        version_id=greek_version.id,
        version_label="test-1",
        source_sha256="a" * 64,
        is_current=True,
    )
    english_release = VersionRelease(
        version_id=english_version.id,
        version_label="test-1",
        source_sha256="b" * 64,
        is_current=True,
    )
    database_session.add_all([greek_release, english_release])
    database_session.flush()

    greek_segment = VersionSegment(
        version_release_id=greek_release.id,
        language_id=greek.id,
        sequence=1,
        text_plain="Ἀρχὴ τοῦ εὐαγγελίου",
    )
    english_one = VersionSegment(
        version_release_id=english_release.id,
        language_id=english.id,
        sequence=1,
        text_plain="The beginning of the gospel",
    )
    english_two = VersionSegment(
        version_release_id=english_release.id,
        language_id=english.id,
        sequence=2,
        text_plain="As it is written",
    )
    database_session.add_all([greek_segment, english_one, english_two])
    database_session.flush()
    enrichment_import = EnrichmentImport(
        target_version_release_id=greek_release.id,
        enrichment_type="token_gloss",
        source="TAGNT",
        source_revision="fixture-commit",
        source_sha256="c" * 64,
        parser_version="tagnt-tsv-1",
    )
    database_session.add(enrichment_import)
    database_session.flush()
    greek_tokens = [
        Token(
            segment_id=greek_segment.id,
            token_index=index,
            surface=surface,
            normalized=normalized,
            language_id=greek.id,
        )
        for index, (surface, normalized) in enumerate(
            [
                ("Ἀρχὴ", "αρχη"),
                ("τοῦ", "του"),
                ("εὐαγγελίου", "ευαγγελιου"),
            ]
        )
    ]
    database_session.add_all(greek_tokens)
    database_session.flush()
    for token, gloss in zip(
        greek_tokens,
        ["[The] beginning", "of the", "gospel"],
        strict=True,
    ):
        database_session.add(
            TokenGloss(
                token_id=token.id,
                target_language_id=english.id,
                enrichment_import_id=enrichment_import.id,
                gloss=gloss,
                gloss_type="contextual",
                source="TAGNT",
                confidence=1,
            )
        )
    database_session.add_all(
        [
            SegmentUnitMapping(
                segment_id=greek_segment.id,
                canonical_unit_id=unit_one.id,
                sequence=0,
                mapping_type="spans",
            ),
            SegmentUnitMapping(
                segment_id=greek_segment.id,
                canonical_unit_id=unit_two.id,
                sequence=1,
                mapping_type="spans",
            ),
            SegmentUnitMapping(
                segment_id=english_one.id,
                canonical_unit_id=unit_one.id,
                sequence=0,
                mapping_type="direct",
            ),
            SegmentUnitMapping(
                segment_id=english_two.id,
                canonical_unit_id=unit_two.id,
                sequence=0,
                mapping_type="direct",
            ),
            PreferredVersion(
                text_id=text.id,
                start_unit_id=unit_one.id,
                end_unit_id=unit_two.id,
                version_id=greek_version.id,
                role="default_source",
                priority=0,
            ),
        ]
    )
    database_session.commit()
