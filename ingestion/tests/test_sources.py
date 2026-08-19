import hashlib
import io
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import httpx
from conftest import FIXTURES
from intertext_ingest.datasets import detect_sblgnt_version
from intertext_ingest.sources.git import GitRepositorySource
from intertext_ingest.sources.http import HttpFileSource, HttpZipSource
from intertext_ingest.sources.local import LocalSource


def test_http_zip_source_downloads_extracts_and_reuses_checksum_cache(
    tmp_path: Path,
) -> None:
    archive_buffer = io.BytesIO()
    with ZipFile(archive_buffer, "w") as archive:
        archive.write(
            FIXTURES / "kjv" / "71-MRKeng-kjv2006.usfm",
            "71-MRKeng-kjv2006.usfm",
        )
    request_count = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            content=archive_buffer.getvalue(),
            headers={"ETag": '"fixture-etag"'},
            request=request,
        )

    source = HttpZipSource(
        identifier="kjv-fixture",
        provider="ebible",
        url="https://example.test/kjv.zip",
        license="Public Domain",
        transport=httpx.MockTransport(respond),
    )
    first = source.acquire(tmp_path)
    second = source.acquire(tmp_path)

    assert request_count == 1
    assert (first.content_path / "71-MRKeng-kjv2006.usfm").is_file()
    assert first.metadata.source_revision == "fixture-etag"
    assert (
        first.metadata.sha256 == hashlib.sha256(archive_buffer.getvalue()).hexdigest()
    )
    assert second.metadata == first.metadata


def test_http_file_source_downloads_and_reuses_checksum_cache(
    tmp_path: Path,
) -> None:
    content = (FIXTURES / "quran" / "quran-simple.xml").read_bytes()
    request_count = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            content=content,
            headers={
                "Content-Type": "application/octet-stream; charset=utf-8",
                "Content-Disposition": "attachment; filename=quran-simple.xml",
            },
            request=request,
        )

    source = HttpFileSource(
        identifier="quran-simple-fixture",
        provider="tanzil",
        url="https://example.test/quran.xml",
        license="CC BY 3.0",
        file_suffix=".xml",
        textual_version="1.1",
        transport=httpx.MockTransport(respond),
    )
    first = source.acquire(tmp_path)
    second = source.acquire(tmp_path)

    assert request_count == 1
    assert first.content_path.read_bytes() == content
    assert first.metadata.sha256 == hashlib.sha256(content).hexdigest()
    assert first.metadata.source_revision == first.metadata.sha256
    assert first.metadata.attributes["artifact_type"] == "file"
    assert second.metadata == first.metadata


def test_git_source_records_commit_and_archive_checksum(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    xml_path = origin / "data" / "sblgnt" / "xml"
    xml_path.mkdir(parents=True)
    shutil.copy(FIXTURES / "sblgnt" / "xml" / "Mark.xml", xml_path)
    shutil.copy(FIXTURES / "sblgnt" / "README.md", origin)
    shutil.copy(FIXTURES / "sblgnt" / "LICENSE", origin)
    subprocess.run(["git", "init", "-q", str(origin)], check=True)
    subprocess.run(["git", "-C", str(origin), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(origin),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(origin), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    source = GitRepositorySource(
        identifier="sblgnt-fixture",
        provider="faithlife",
        repository_url=str(origin),
        license="CC BY 4.0",
        content_subpath="data/sblgnt/xml",
        textual_version_resolver=detect_sblgnt_version,
    )
    acquired = source.acquire(tmp_path / "raw")
    cached = source.acquire(tmp_path / "raw")

    assert acquired.metadata.source_revision == commit
    assert len(acquired.metadata.sha256) == 64
    assert acquired.metadata.textual_version == "1.2"
    assert acquired.content_path.joinpath("Mark.xml").is_file()
    assert cached.metadata == acquired.metadata


def test_local_source_copies_artifact_and_records_provenance(tmp_path: Path) -> None:
    local_path = FIXTURES / "kjv"
    source = LocalSource(
        identifier="local-usfm",
        provider="local-fixture",
        path=local_path,
        license="fixture license",
        source_revision="fixture-revision",
    )

    acquired = source.acquire(tmp_path / "raw")

    assert acquired.content_path != local_path
    assert acquired.content_path.joinpath("71-MRKeng-kjv2006.usfm").is_file()
    assert acquired.metadata.source_locator == local_path.resolve().as_uri()
    assert acquired.metadata.source_revision == "fixture-revision"
    assert len(acquired.metadata.sha256) == 64
