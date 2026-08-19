import re
from dataclasses import dataclass
from pathlib import Path

from intertext_ingest.corpora.base import CorpusMapper, CorpusValidator
from intertext_ingest.corpora.bible import PROTESTANT_66_CANON, BibleMapper
from intertext_ingest.corpora.bible.validation import BibleVersionValidator
from intertext_ingest.normalized import VersionDefinition
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
    version: VersionDefinition
    corpus_mapper: CorpusMapper
    corpus_validator: CorpusValidator
    preferred_role: str | None = None


MARK_ONE_REQUIRED = (
    "bible.mark.1.1",
    "bible.mark.1.2",
    "bible.mark.1.3",
)

_SBLGNT_VERSION = re.compile(r"<tr><td>v(\d+(?:\.\d+)+)</td>", re.IGNORECASE)


def detect_sblgnt_version(repository_path: Path) -> str | None:
    readme_path = repository_path / "README.md"
    if not readme_path.is_file():
        return None
    match = _SBLGNT_VERSION.search(readme_path.read_text(encoding="utf-8"))
    return match.group(1) if match is not None else None


def _bible_mapper() -> BibleMapper:
    return BibleMapper(PROTESTANT_66_CANON)


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
            parser=UsfmParser(),
            version=VersionDefinition(
                slug="kjv",
                title="King James Version",
                abbreviation="KJV",
                language_iso="en",
                language_name="English",
                language_native_name="English",
                script="Latn",
                direction="ltr",
                version_type="translation",
                rights_statement=(
                    "Standardized 1769 KJV, protocanon only. Public Domain outside "
                    "the United Kingdom; UK Crown printing restrictions apply."
                ),
            ),
            corpus_mapper=_bible_mapper(),
            corpus_validator=BibleVersionValidator(
                required_canonical_keys=MARK_ONE_REQUIRED
            ),
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
            version=VersionDefinition(
                slug="sblgnt",
                title="SBL Greek New Testament",
                abbreviation="SBLGNT",
                language_iso="grc",
                language_name="Ancient Greek",
                language_native_name="Ἑλληνική",
                script="Grek",
                direction="ltr",
                version_type="critical_edition",
                publisher="Society of Biblical Literature and Logos Bible Software",
                rights_statement=(
                    "Copyright 2010 Society of Biblical Literature and Logos Bible "
                    "Software; licensed CC BY 4.0."
                ),
            ),
            corpus_mapper=_bible_mapper(),
            corpus_validator=BibleVersionValidator(
                required_canonical_keys=MARK_ONE_REQUIRED,
                expected_testament="new",
            ),
            preferred_role="default_source",
        )
    raise ValueError(f"Unsupported dataset '{name}'. Expected one of: kjv, sblgnt")
