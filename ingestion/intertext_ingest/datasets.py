import re
from dataclasses import dataclass
from pathlib import Path

from intertext_ingest.corpora.base import CorpusMapper, CorpusValidator
from intertext_ingest.corpora.bible import PROTESTANT_66_CANON, BibleMapper
from intertext_ingest.corpora.bible.validation import BibleVersionValidator
from intertext_ingest.corpora.quran import QuranMapper, QuranVersionValidator
from intertext_ingest.normalized import VersionDefinition
from intertext_ingest.parsers.base import SourceParser
from intertext_ingest.parsers.quran_pipe_text import QuranPipeTextParser
from intertext_ingest.parsers.quran_xml import QuranXmlParser
from intertext_ingest.parsers.sblgnt_xml import SblgntXmlParser
from intertext_ingest.parsers.usfm import UsfmParser
from intertext_ingest.sources.base import SourceAdapter
from intertext_ingest.sources.git import GitRepositorySource
from intertext_ingest.sources.http import HttpFileSource, HttpZipSource


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

TANZIL_QURAN_SIMPLE_URL = (
    "https://tanzil.net/pub/download/index.php?marks=true&sajdah=true&"
    "tatweel=true&quranType=simple&outType=xml&agree=true"
)
TANZIL_SAHEEH_INTERNATIONAL_URL = (
    "https://tanzil.net/trans/?transID=en.sahih&type=txt-2"
)


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
    if name == "quran":
        return DatasetDefinition(
            name="quran",
            source=HttpFileSource(
                identifier="quran-simple",
                provider="tanzil",
                url=TANZIL_QURAN_SIMPLE_URL,
                file_suffix=".xml",
                textual_version="1.1",
                license=(
                    "Creative Commons Attribution 3.0; Tanzil terms require "
                    "verbatim text, attribution, and a link to tanzil.net"
                ),
            ),
            parser=QuranXmlParser(),
            version=VersionDefinition(
                slug="tanzil-simple",
                title="Tanzil Quran Text (Simple)",
                abbreviation="Tanzil Simple",
                language_iso="ar",
                language_name="Arabic",
                language_native_name="العربية",
                script="Arab",
                direction="rtl",
                version_type="digital_edition",
                publisher="Tanzil Project",
                rights_statement=(
                    "Tanzil Quran Text (Simple), Version 1.1. Copyright "
                    "2007-2026 Tanzil Project; Creative Commons Attribution "
                    "3.0. Tanzil requires the Quran text to remain verbatim, "
                    "clear attribution to Tanzil Project, a link to tanzil.net, "
                    "and reproduction of its copyright notice in derived files "
                    "containing a substantial portion of the text."
                ),
            ),
            corpus_mapper=QuranMapper(),
            corpus_validator=QuranVersionValidator(),
            preferred_role="default_source",
        )
    if name == "quran-saheeh-international":
        return DatasetDefinition(
            name="quran-saheeh-international",
            source=HttpFileSource(
                identifier="en-sahih",
                provider="tanzil",
                url=TANZIL_SAHEEH_INTERNATIONAL_URL,
                file_suffix=".txt",
                textual_version="2011-04-24",
                license=(
                    "Non-commercial use only via Tanzil; other use requires "
                    "permission from the translator or publisher"
                ),
            ),
            parser=QuranPipeTextParser(),
            version=VersionDefinition(
                slug="saheeh-international",
                title="Saheeh International",
                abbreviation="Saheeh",
                language_iso="en",
                language_name="English",
                language_native_name="English",
                script="Latn",
                direction="ltr",
                version_type="translation",
                publisher="Saheeh International",
                rights_statement=(
                    "Saheeh International English Quran translation, Tanzil ID "
                    "en.sahih, last updated April 24, 2011. Tanzil provides this "
                    "translation for non-commercial purposes only; other use "
                    "requires necessary permission from the translator or "
                    "publisher."
                ),
            ),
            corpus_mapper=QuranMapper(),
            corpus_validator=QuranVersionValidator(),
        )
    raise ValueError(
        f"Unsupported dataset '{name}'. Expected one of: kjv, quran, "
        "quran-saheeh-international, sblgnt"
    )
