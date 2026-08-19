import shutil
from datetime import UTC, datetime
from pathlib import Path

from intertext_ingest.normalized import AcquiredSource, SourceMetadata
from intertext_ingest.sources.base import sha256_path, write_metadata


class LocalSource:
    """Acquire a local file or directory into the raw artifact store."""

    def __init__(
        self,
        *,
        identifier: str,
        provider: str,
        path: Path,
        license: str,
        source_revision: str | None = None,
        textual_version: str | None = None,
    ) -> None:
        self.identifier = identifier
        self.provider = provider
        self.path = path
        self.license = license
        self.source_revision = source_revision
        self.textual_version = textual_version

    def acquire(self, raw_root: Path, *, refresh: bool = False) -> AcquiredSource:
        source_path = self.path.resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Local source does not exist: {source_path}")
        checksum = sha256_path(source_path)
        artifact_root = (
            raw_root / self.provider / self.identifier / checksum
        ).resolve()
        if artifact_root.is_relative_to(source_path):
            raise ValueError(
                "Local raw artifact store cannot be inside the source path"
            )
        artifact_path = artifact_root / source_path.name
        if refresh or not artifact_path.exists():
            artifact_root.mkdir(parents=True, exist_ok=True)
            if source_path.is_dir():
                if artifact_path.exists():
                    shutil.rmtree(artifact_path)
                shutil.copytree(source_path, artifact_path)
            else:
                shutil.copy2(source_path, artifact_path)
        if sha256_path(artifact_path) != checksum:
            raise ValueError(f"Local artifact checksum mismatch: {artifact_path}")

        metadata = SourceMetadata(
            provider=self.provider,
            source_locator=source_path.as_uri(),
            source_revision=self.source_revision or checksum,
            retrieved_at=datetime.now(UTC),
            sha256=checksum,
            license=self.license,
            raw_artifact_path=str(artifact_path),
            textual_version=self.textual_version,
            attributes={
                "artifact_type": "local_directory"
                if source_path.is_dir()
                else "local_file"
            },
        )
        write_metadata(artifact_root / "source.json", metadata)
        return AcquiredSource(content_path=artifact_path, metadata=metadata)
