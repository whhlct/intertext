import hashlib
import json
from pathlib import Path
from typing import Protocol

from intertext_ingest.normalized import AcquiredSource, SourceMetadata


class SourceAdapter(Protocol):
    def acquire(self, raw_root: Path, *, refresh: bool = False) -> AcquiredSource: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    digest = hashlib.sha256()
    for child in sorted(
        candidate for candidate in path.rglob("*") if candidate.is_file()
    ):
        relative_path = child.relative_to(path).as_posix().encode()
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        with child.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def write_metadata(path: Path, metadata: SourceMetadata) -> None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(metadata.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def read_metadata(path: Path) -> SourceMetadata:
    return SourceMetadata.from_dict(json.loads(path.read_text(encoding="utf-8")))
