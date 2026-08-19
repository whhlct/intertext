import hashlib
from dataclasses import replace
from pathlib import Path

from app import models  # noqa: F401
from app.db.base import Base
from app.models import (
    CanonicalUnit,
    PreferredVersion,
    SegmentUnitMapping,
    StructureNode,
    TextVersion,
    VersionRelease,
    VersionSegment,
)
from intertext_ingest.datasets import get_dataset
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
