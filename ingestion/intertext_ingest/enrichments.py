from dataclasses import dataclass

from intertext_ingest.corpora.bible import PROTESTANT_66_CANON
from intertext_ingest.corpora.bible.tagnt_alignment import TagntSblgntAligner
from intertext_ingest.parsers.tagnt import TagntParser
from intertext_ingest.sources.base import SourceAdapter
from intertext_ingest.sources.git import GitRepositorySource


@dataclass(frozen=True)
class TokenEnrichmentDefinition:
    name: str
    enrichment_type: str
    source_label: str
    alignment_edition: str
    source: SourceAdapter
    parser: TagntParser
    aligner: TagntSblgntAligner
    target_text_slug: str
    target_version_slug: str


def get_token_enrichment(name: str) -> TokenEnrichmentDefinition:
    if name == "tagnt-sblgnt":
        return TokenEnrichmentDefinition(
            name=name,
            enrichment_type="token_gloss",
            source_label="TAGNT",
            alignment_edition="SBL",
            source=GitRepositorySource(
                identifier="stepbible-data",
                provider="stepbible",
                repository_url="https://github.com/STEPBible/STEPBible-Data.git",
                license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
                content_subpath="Translators Amalgamated OT+NT",
                textual_version="TAGNT",
            ),
            parser=TagntParser(),
            aligner=TagntSblgntAligner(PROTESTANT_66_CANON),
            target_text_slug="bible",
            target_version_slug="sblgnt",
        )
    raise ValueError(
        f"Unsupported token enrichment '{name}'. Expected: tagnt-sblgnt"
    )
