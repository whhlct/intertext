from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from app.models import Text, TextVersion, Token, VersionRelease, VersionSegment
from sqlalchemy import select
from sqlalchemy.orm import Session

from intertext_ingest.corpora.bible.tagnt_alignment import (
    SblgntTargetToken,
    SblgntTargetVerse,
)
from intertext_ingest.enrichments import TokenEnrichmentDefinition
from intertext_ingest.normalizers.greek import normalize_greek_token
from intertext_ingest.persistence.token_gloss import (
    TokenEnrichmentResult,
    TokenGlossPersistence,
)


class TokenEnrichmentPipeline:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory
        self.persistence = TokenGlossPersistence()

    def run(
        self,
        enrichment: TokenEnrichmentDefinition,
        *,
        raw_root: Path,
        refresh: bool = False,
        allow_partial: bool = False,
    ) -> TokenEnrichmentResult:
        acquired = enrichment.source.acquire(raw_root, refresh=refresh)
        with self.session_factory() as session:
            try:
                target_version, target_release = self._target_release(
                    session,
                    enrichment.target_text_slug,
                    enrichment.target_version_slug,
                )
                existing = self.persistence.existing_result(
                    session,
                    dataset=enrichment.name,
                    enrichment_type=enrichment.enrichment_type,
                    target_release=target_release,
                    source_sha256=acquired.metadata.sha256,
                )
                if existing is not None:
                    return existing
                parsed = enrichment.parser.parse(acquired)
                target_verses, target_tokens = self._target_tokens(
                    session, target_release
                )
                alignment = enrichment.aligner.align(
                    parsed,
                    target_verses,
                    allow_partial=allow_partial,
                )
                result = self.persistence.persist(
                    session,
                    dataset=enrichment.name,
                    enrichment_type=enrichment.enrichment_type,
                    source_label=enrichment.source_label,
                    alignment_edition=enrichment.alignment_edition,
                    target_version=target_version,
                    target_release=target_release,
                    source=parsed.source,
                    parser_version=parsed.parser_version,
                    target_tokens=target_tokens,
                    alignment=alignment,
                )
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _target_release(
        session: Session, text_slug: str, version_slug: str
    ) -> tuple[TextVersion, VersionRelease]:
        version = session.scalar(
            select(TextVersion)
            .join(Text, Text.id == TextVersion.text_id)
            .where(Text.slug == text_slug, TextVersion.slug == version_slug)
        )
        if version is None:
            raise ValueError(
                f"Target version is not imported: {text_slug}/{version_slug}"
            )
        release = session.scalar(
            select(VersionRelease).where(
                VersionRelease.version_id == version.id,
                VersionRelease.is_current.is_(True),
            )
        )
        if release is None:
            raise ValueError(f"Target version has no current release: {version_slug}")
        return version, release

    @staticmethod
    def _target_tokens(
        session: Session, release: VersionRelease
    ) -> tuple[tuple[SblgntTargetVerse, ...], tuple[SblgntTargetToken, ...]]:
        segments = list(
            session.scalars(
                select(VersionSegment)
                .where(VersionSegment.version_release_id == release.id)
                .order_by(VersionSegment.sequence)
            )
        )
        if not segments:
            raise ValueError("SBLGNT target release has no segments")
        segment_ids = [segment.id for segment in segments]
        stored_by_segment: dict = defaultdict(list)
        for token in session.scalars(
            select(Token)
            .where(Token.segment_id.in_(segment_ids))
            .order_by(Token.segment_id, Token.token_index)
        ):
            stored_by_segment[token.segment_id].append(token)

        verses: list[SblgntTargetVerse] = []
        all_tokens: list[SblgntTargetToken] = []
        for segment in segments:
            if not segment.source_identifier:
                raise ValueError(f"SBLGNT segment lacks a reference: {segment.id}")
            stored = stored_by_segment.get(segment.id, [])
            if stored:
                word_tokens = [token for token in stored if token.is_word]
                if not word_tokens:
                    raise ValueError(
                        f"Existing token stream has no word tokens: "
                        f"{segment.source_identifier}"
                    )
                targets = tuple(
                    SblgntTargetToken(
                        segment_id=segment.id,
                        token_index=token.token_index,
                        surface=token.surface,
                        normalized=token.normalized
                        or normalize_greek_token(token.surface),
                        language_id=token.language_id,
                        char_start=token.char_start,
                        char_end=token.char_end,
                        existing_token_id=token.id,
                    )
                    for token in word_tokens
                )
            else:
                words = [
                    element["text"]
                    for element in segment.content_markup.get("elements", [])
                    if element.get("type") == "w"
                ]
                if not words:
                    raise ValueError(
                        f"SBLGNT segment has no XML word elements: "
                        f"{segment.source_identifier}"
                    )
                cursor = 0
                derived = []
                for index, surface in enumerate(words):
                    char_start = segment.text_plain.find(surface, cursor)
                    char_end = char_start + len(surface) if char_start >= 0 else None
                    derived.append(
                        SblgntTargetToken(
                            segment_id=segment.id,
                            token_index=index,
                            surface=surface,
                            normalized=normalize_greek_token(surface),
                            language_id=segment.language_id,
                            char_start=char_start if char_start >= 0 else None,
                            char_end=char_end,
                        )
                    )
                    if char_end is not None:
                        cursor = char_end
                targets = tuple(derived)
            verses.append(SblgntTargetVerse(segment.source_identifier, targets))
            all_tokens.extend(targets)
        return tuple(verses), tuple(all_tokens)
