import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from intertext_ingest.normalized import AcquiredSource, SourceMetadata

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def source_metadata() -> SourceMetadata:
    return SourceMetadata(
        provider="fixture",
        source_locator="fixture://local",
        source_revision="fixture-1",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        sha256=hashlib.sha256(b"fixture-1").hexdigest(),
        license="fixture license",
        raw_artifact_path=str(FIXTURES),
        textual_version="fixture-1",
    )


@pytest.fixture
def kjv_source(source_metadata: SourceMetadata) -> AcquiredSource:
    return AcquiredSource(FIXTURES / "kjv", source_metadata)


@pytest.fixture
def sblgnt_source(source_metadata: SourceMetadata) -> AcquiredSource:
    metadata = replace(
        source_metadata,
        sha256=hashlib.sha256(b"fixture-sblgnt").hexdigest(),
    )
    return AcquiredSource(FIXTURES / "sblgnt" / "xml", metadata)
