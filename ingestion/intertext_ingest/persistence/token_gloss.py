import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.models import (
    EnrichmentImport,
    Language,
    Lexeme,
    TextVersion,
    Token,
    TokenGloss,
    VersionRelease,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from intertext_ingest.corpora.bible.tagnt_alignment import (
    SblgntTargetToken,
    TagntAlignmentResult,
)
from intertext_ingest.normalized import SourceMetadata


@dataclass(frozen=True)
class TokenEnrichmentResult:
    dataset: str
    created: bool
    enrichment_import_id: str
    target_release_id: str
    source_sha256: str
    token_count: int
    gloss_count: int
    skipped_verse_count: int


class TokenGlossPersistence:
    def existing_result(
        self,
        session: Session,
        *,
        dataset: str,
        enrichment_type: str,
        target_release: VersionRelease,
        source_sha256: str,
    ) -> TokenEnrichmentResult | None:
        imported = session.scalar(
            select(EnrichmentImport).where(
                EnrichmentImport.target_version_release_id == target_release.id,
                EnrichmentImport.enrichment_type == enrichment_type,
                EnrichmentImport.source_sha256 == source_sha256,
            )
        )
        if imported is None:
            return None
        gloss_count = session.scalar(
            select(func.count(TokenGloss.id)).where(
                TokenGloss.enrichment_import_id == imported.id
            )
        ) or 0
        token_count = session.scalar(
            select(func.count(func.distinct(Token.id)))
            .join(
                TokenGloss,
                TokenGloss.token_id == Token.id,
            )
            .where(TokenGloss.enrichment_import_id == imported.id)
        ) or 0
        issues = imported.metadata_.get("alignment_issues", [])
        return TokenEnrichmentResult(
            dataset=dataset,
            created=False,
            enrichment_import_id=str(imported.id),
            target_release_id=str(target_release.id),
            source_sha256=source_sha256,
            token_count=token_count,
            gloss_count=gloss_count,
            skipped_verse_count=len(issues),
        )

    def persist(
        self,
        session: Session,
        *,
        dataset: str,
        enrichment_type: str,
        source_label: str,
        alignment_edition: str,
        target_version: TextVersion,
        target_release: VersionRelease,
        source: SourceMetadata,
        parser_version: str,
        target_tokens: tuple[SblgntTargetToken, ...],
        alignment: TagntAlignmentResult,
    ) -> TokenEnrichmentResult:
        english = session.scalar(select(Language).where(Language.iso_code == "en"))
        if english is None:
            english = Language(
                iso_code="en",
                name="English",
                native_name="English",
                script="Latn",
                direction="ltr",
            )
            session.add(english)
            session.flush()

        imported = EnrichmentImport(
            target_version_release_id=target_release.id,
            enrichment_type=enrichment_type,
            source=source_label,
            source_revision=source.source_revision,
            source_sha256=source.sha256,
            parser_version=parser_version,
            metadata_={
                "source": source.as_dict(),
                "target_version_slug": target_version.slug,
                "alignment_edition": alignment_edition,
                "alignment_issues": [
                    {
                        "reference": issue.reference_label,
                        "reason": issue.reason,
                    }
                    for issue in alignment.issues
                ],
            },
        )
        session.add(imported)
        session.flush()

        tokens_by_key: dict[tuple[uuid.UUID, int], Token] = {}
        for target in target_tokens:
            token = (
                session.get(Token, target.existing_token_id)
                if target.existing_token_id is not None
                else None
            )
            if token is None:
                token = session.scalar(
                    select(Token).where(
                        Token.segment_id == target.segment_id,
                        Token.token_index == target.token_index,
                    )
                )
            if token is None:
                token = Token(
                    segment_id=target.segment_id,
                    token_index=target.token_index,
                    surface=target.surface,
                    normalized=target.normalized,
                    char_start=target.char_start,
                    char_end=target.char_end,
                    language_id=target.language_id,
                    is_word=True,
                    is_punctuation=False,
                    metadata_={
                        "tokenization_source": "SBLGNT XML",
                        "target_release_id": str(target_release.id),
                    },
                )
                session.add(token)
            tokens_by_key[(target.segment_id, target.token_index)] = token
        session.flush()

        lexemes: dict[str, Lexeme] = {
            lexeme.lemma: lexeme
            for lexeme in session.scalars(
                select(Lexeme).where(
                    Lexeme.language_id == target_version.default_language_id
                )
            )
        }
        for aligned in alignment.aligned:
            entry = aligned.candidate.entry
            reading = aligned.candidate.reading
            token = tokens_by_key[
                (aligned.target.segment_id, aligned.target.token_index)
            ]
            lexeme = None
            if entry.lemma:
                lexeme = lexemes.get(entry.lemma)
                if lexeme is None:
                    grammar = (reading.analysis or "").partition("=")[2]
                    lexeme = Lexeme(
                        language_id=target_version.default_language_id,
                        lemma=entry.lemma,
                        normalized_lemma=entry.normalized_lemma,
                        part_of_speech=grammar.partition("-")[0] or None,
                        metadata_={
                            "dictionary_gloss": entry.dictionary_gloss,
                            "source": source_label,
                        },
                    )
                    session.add(lexeme)
                    lexemes[entry.lemma] = lexeme
                token.lexeme = lexeme
            enrichment_metadata = {
                "source_identifier": entry.source_identifier,
                "source_file": entry.metadata["source_file"],
                "source_line": entry.metadata["source_line"],
                "source_surface": reading.surface,
                "normalized_surface": reading.normalized,
                "lemma": entry.lemma,
                "normalized_lemma": entry.normalized_lemma,
                "dictionary_gloss": entry.dictionary_gloss,
                "edition_membership": list(reading.editions),
                "edition_markers": list(reading.edition_markers),
                "reading_type": reading.reading_type,
                "analysis": reading.analysis,
                "source_sha256": source.sha256,
            }
            token.metadata_ = {
                **token.metadata_,
                source_label.lower(): enrichment_metadata,
            }
            session.add(
                TokenGloss(
                    token_id=token.id,
                    target_language_id=english.id,
                    enrichment_import_id=imported.id,
                    gloss=reading.contextual_gloss,
                    gloss_type="contextual",
                    source=source_label,
                    confidence=Decimal("1.0000"),
                    metadata_=enrichment_metadata,
                )
            )
        session.flush()
        return TokenEnrichmentResult(
            dataset=dataset,
            created=True,
            enrichment_import_id=str(imported.id),
            target_release_id=str(target_release.id),
            source_sha256=source.sha256,
            token_count=len(alignment.aligned),
            gloss_count=len(alignment.aligned),
            skipped_verse_count=len(alignment.issues),
        )
