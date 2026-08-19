import hashlib
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from intertext_ingest.normalized import AcquiredSource, SourceMetadata
from intertext_ingest.sources.base import read_metadata, write_metadata


class CommandRunner(Protocol):
    def __call__(
        self, command: list[str], *, cwd: Path | None = None, text: bool = True
    ) -> subprocess.CompletedProcess: ...


def run_command(
    command: list[str], *, cwd: Path | None = None, text: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=text,
    )


class GitRepositorySource:
    def __init__(
        self,
        *,
        identifier: str,
        provider: str,
        repository_url: str,
        license: str,
        content_subpath: str,
        revision: str | None = None,
        textual_version: str | None = None,
        textual_version_resolver: Callable[[Path], str | None] | None = None,
        runner: CommandRunner = run_command,
    ) -> None:
        self.identifier = identifier
        self.provider = provider
        self.repository_url = repository_url
        self.license = license
        self.content_subpath = content_subpath
        self.revision = revision
        self.textual_version = textual_version
        self.textual_version_resolver = textual_version_resolver
        self.runner = runner

    def acquire(self, raw_root: Path, *, refresh: bool = False) -> AcquiredSource:
        raw_root = raw_root.resolve()
        raw_root.mkdir(parents=True, exist_ok=True)
        repository_path = raw_root / self.provider / self.identifier
        metadata_path = raw_root / self.provider / f"{self.identifier}.source.json"
        repository_path.parent.mkdir(parents=True, exist_ok=True)

        if not (repository_path / ".git").exists():
            self.runner(
                ["git", "clone", "--no-tags", self.repository_url, str(repository_path)]
            )
        elif refresh:
            self.runner(["git", "fetch", "--prune", "origin"], cwd=repository_path)

        if self.revision is not None:
            target = self.revision
        elif refresh:
            target = "origin/HEAD"
        else:
            target = "HEAD"
        if target != "HEAD":
            self.runner(["git", "checkout", "--detach", target], cwd=repository_path)

        commit = self.runner(
            ["git", "rev-parse", "HEAD"], cwd=repository_path
        ).stdout.strip()
        archive = self.runner(
            ["git", "archive", "--format=tar", commit],
            cwd=repository_path,
            text=False,
        ).stdout
        checksum = hashlib.sha256(archive).hexdigest()

        if metadata_path.exists() and not refresh:
            cached_metadata = read_metadata(metadata_path)
            if (
                cached_metadata.source_revision == commit
                and cached_metadata.sha256 == checksum
            ):
                return AcquiredSource(
                    content_path=repository_path / self.content_subpath,
                    metadata=cached_metadata,
                )

        content_path = repository_path / self.content_subpath
        if not content_path.is_dir():
            raise FileNotFoundError(
                f"Git content path does not exist at commit {commit}: {content_path}"
            )
        detected_textual_version = (
            self.textual_version_resolver(repository_path)
            if self.textual_version_resolver is not None
            else None
        )
        metadata = SourceMetadata(
            provider=self.provider,
            source_locator=self.repository_url,
            source_revision=commit,
            retrieved_at=datetime.now(UTC),
            sha256=checksum,
            license=self.license,
            raw_artifact_path=str(repository_path),
            textual_version=detected_textual_version or self.textual_version,
            attributes={
                "artifact_type": "git_repository",
                "content_subpath": self.content_subpath,
            },
        )
        write_metadata(metadata_path, metadata)
        return AcquiredSource(content_path=content_path, metadata=metadata)
