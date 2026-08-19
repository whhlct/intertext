import re
from dataclasses import dataclass
from pathlib import Path

from intertext_ingest.parsers.base import SourceParser
from intertext_ingest.parsers.sblgnt_xml import SblgntXmlParser
from intertext_ingest.parsers.usfm import UsfmParser
from intertext_ingest.sources.base import SourceAdapter
from intertext_ingest.sources.git import GitRepositorySource
from intertext_ingest.sources.http import HttpZipSource


@dataclass(frozen=True)
class DatasetDefinition:
    name: str
    source: SourceAdapter
    parser: SourceParser
    required_reference_keys: tuple[str, ...]
    require_unique_references: bool = True
    preferred_role: str | None = None


MARK_ONE_REQUIRED = (
    "bible.mrk.1.1",
    "bible.mrk.1.2",
    "bible.mrk.1.3",
)

_SBLGNT_VERSION = re.compile(r"<tr><td>v(\d+(?:\.\d+)+)</td>", re.IGNORECASE)


def detect_sblgnt_version(repository_path: Path) -> str | None:
    readme_path = repository_path / "README.md"
    if not readme_path.is_file():
        return None
    match = _SBLGNT_VERSION.search(readme_path.read_text(encoding="utf-8"))
    return match.group(1) if match is not None else None


def get_dataset(name: str) -> DatasetDefinition:
    if name == "kjv":
        return DatasetDefinition(
            name="kjv",
            source=HttpZipSource(
                identifier="eng-kjv2006",
                provider="ebible",
                url="https://ebible.org/Scriptures/eng-kjv2006_usfm.zip",
                textual_version="Standardized 1769 KJV (eng-kjv2006)",
                license=(
                    "Public Domain outside the United Kingdom; UK Crown printing "
                    "restrictions apply"
                ),
            ),
            parser=UsfmParser(
                slug="kjv",
                title="King James Version",
                abbreviation="KJV",
                language_iso="en",
                language_name="English",
                version_type="translation",
                rights_statement=(
                    "Standardized 1769 KJV, protocanon only. Public Domain outside "
                    "the United Kingdom; UK Crown printing restrictions apply."
                ),
            ),
            required_reference_keys=MARK_ONE_REQUIRED,
        )
    if name == "sblgnt":
        return DatasetDefinition(
            name="sblgnt",
            source=GitRepositorySource(
                identifier="sblgnt",
                provider="faithlife",
                repository_url="https://github.com/Faithlife/SBLGNT.git",
                license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
                content_subpath="data/sblgnt/xml",
                textual_version="1.2",
                textual_version_resolver=detect_sblgnt_version,
            ),
            parser=SblgntXmlParser(),
            required_reference_keys=MARK_ONE_REQUIRED,
            preferred_role="default_source",
        )
    raise ValueError(f"Unsupported dataset '{name}'. Expected one of: kjv, sblgnt")
