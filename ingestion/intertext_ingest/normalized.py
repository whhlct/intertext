from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceMetadata:
    provider: str
    source_locator: str
    source_revision: str
    retrieved_at: datetime
    sha256: str
    license: str
    raw_artifact_path: str
    textual_version: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_locator": self.source_locator,
            "source_revision": self.source_revision,
            "retrieved_at": self.retrieved_at.isoformat(),
            "sha256": self.sha256,
            "license": self.license,
            "raw_artifact_path": self.raw_artifact_path,
            "textual_version": self.textual_version,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceMetadata":
        return cls(
            provider=value["provider"],
            source_locator=value["source_locator"],
            source_revision=value["source_revision"],
            retrieved_at=datetime.fromisoformat(value["retrieved_at"]),
            sha256=value["sha256"],
            license=value["license"],
            raw_artifact_path=value["raw_artifact_path"],
            textual_version=value.get("textual_version"),
            attributes=value.get("attributes", {}),
        )


@dataclass(frozen=True)
class AcquiredSource:
    content_path: Path
    metadata: SourceMetadata


@dataclass(frozen=True)
class NormalizedReference:
    scheme: str
    key: str
    label: str
    components: dict[str, str | int] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedToken:
    surface: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSegment:
    sequence: int
    language_iso: str
    text: str
    source_reference: str
    reference: NormalizedReference
    content_markup: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens: tuple[NormalizedToken, ...] = ()


@dataclass(frozen=True)
class NormalizedVersion:
    slug: str
    title: str
    abbreviation: str
    language_iso: str
    language_name: str
    language_native_name: str | None
    script: str | None
    direction: str
    version_type: str
    source: SourceMetadata
    segments: tuple[NormalizedSegment, ...]
    description: str | None = None
    publisher: str | None = None
    rights_statement: str | None = None


@dataclass(frozen=True)
class ImportResult:
    dataset: str
    created: bool
    release_id: str
    source_sha256: str
    segment_count: int
    mapping_count: int
