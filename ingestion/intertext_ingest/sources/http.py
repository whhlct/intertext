import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import httpx

from intertext_ingest.normalized import AcquiredSource, SourceMetadata
from intertext_ingest.sources.base import (
    read_metadata,
    sha256_file,
    write_metadata,
)


class HttpZipSource:
    def __init__(
        self,
        *,
        identifier: str,
        provider: str,
        url: str,
        license: str,
        textual_version: str | None = None,
        source_revision: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.identifier = identifier
        self.provider = provider
        self.url = url
        self.license = license
        self.textual_version = textual_version
        self.source_revision = source_revision
        self.transport = transport

    def acquire(self, raw_root: Path, *, refresh: bool = False) -> AcquiredSource:
        source_root = (raw_root / self.provider / self.identifier).resolve()
        source_root.mkdir(parents=True, exist_ok=True)
        metadata_path = source_root / "source.json"

        if metadata_path.exists() and not refresh:
            metadata = read_metadata(metadata_path)
            archive_path = Path(metadata.raw_artifact_path)
            if not archive_path.exists():
                raise FileNotFoundError(f"Cached artifact is missing: {archive_path}")
            if sha256_file(archive_path) != metadata.sha256:
                raise ValueError(f"Cached artifact checksum mismatch: {archive_path}")
            return AcquiredSource(
                content_path=self._extract(archive_path, source_root, metadata.sha256),
                metadata=metadata,
            )

        temporary_path = source_root / f"{self.identifier}.zip.part"
        headers: dict[str, str]
        with (
            httpx.Client(
                follow_redirects=True,
                timeout=httpx.Timeout(120.0),
                transport=self.transport,
            ) as client,
            client.stream("GET", self.url) as response,
        ):
            response.raise_for_status()
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower() in {"etag", "last-modified", "content-type"}
            }
            with temporary_path.open("wb") as archive_file:
                for chunk in response.iter_bytes():
                    archive_file.write(chunk)
        checksum = sha256_file(temporary_path)
        archive_path = source_root / "archives" / f"{checksum}.zip"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        if archive_path.exists():
            temporary_path.unlink()
        else:
            temporary_path.replace(archive_path)
        revision = (
            self.source_revision
            or headers.get("etag", "").strip('"')
            or headers.get("last-modified")
            or checksum
        )
        metadata = SourceMetadata(
            provider=self.provider,
            source_locator=self.url,
            source_revision=revision,
            retrieved_at=datetime.now(UTC),
            sha256=checksum,
            license=self.license,
            raw_artifact_path=str(archive_path),
            textual_version=self.textual_version,
            attributes={"http_headers": headers, "artifact_type": "zip"},
        )
        write_metadata(metadata_path, metadata)
        return AcquiredSource(
            content_path=self._extract(archive_path, source_root, checksum),
            metadata=metadata,
        )

    @staticmethod
    def _extract(archive_path: Path, source_root: Path, checksum: str) -> Path:
        extraction_path = source_root / "extracted" / checksum
        completion_marker = extraction_path / ".complete"
        if completion_marker.is_file():
            return extraction_path
        with ZipFile(archive_path) as archive:
            for member in archive.infolist():
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError(
                        f"Unsafe ZIP member in {archive_path}: {member.filename}"
                    )
            if extraction_path.exists():
                shutil.rmtree(extraction_path)
            extraction_path.mkdir(parents=True, exist_ok=False)
            try:
                archive.extractall(extraction_path)
                completion_marker.write_text(checksum + "\n", encoding="utf-8")
            except Exception:
                shutil.rmtree(extraction_path)
                raise
        return extraction_path
