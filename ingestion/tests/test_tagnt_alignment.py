import uuid
from dataclasses import replace

import pytest
from intertext_ingest.corpora.bible import PROTESTANT_66_CANON
from intertext_ingest.corpora.bible.tagnt_alignment import (
    SblgntTargetToken,
    SblgntTargetVerse,
    TagntAlignmentError,
    TagntSblgntAligner,
)
from intertext_ingest.normalized import AcquiredSource
from intertext_ingest.normalizers.greek import normalize_greek_token
from intertext_ingest.parsers.tagnt import TagntParser


def _target(surface: str) -> SblgntTargetVerse:
    return SblgntTargetVerse(
        reference_label="Mark 1:1",
        tokens=(
            SblgntTargetToken(
                segment_id=uuid.uuid4(),
                token_index=0,
                surface=surface,
                normalized=normalize_greek_token(surface),
                language_id=uuid.uuid4(),
                char_start=0,
                char_end=len(surface),
            ),
        ),
    )


def test_tagnt_alignment_rejects_mismatched_tokens(
    tagnt_source: AcquiredSource,
) -> None:
    parsed = TagntParser().parse(tagnt_source)
    aligner = TagntSblgntAligner(PROTESTANT_66_CANON)

    with pytest.raises(TagntAlignmentError, match="no complete normalized-token"):
        aligner.align(parsed, (_target("ἀσύμφωνον"),))


def test_tagnt_alignment_rejects_ambiguous_context(
    tagnt_source: AcquiredSource,
) -> None:
    parsed = TagntParser().parse(tagnt_source)
    source = next(
        entry
        for entry in parsed.entries
        if entry.source_identifier == "Mrk.1.1#02=NKO"
    )
    duplicate = replace(
        source,
        source_identifier="Mrk.1.1#99=NKO",
        source_word_number=99,
    )
    ambiguous = replace(parsed, entries=(*parsed.entries, duplicate))
    aligner = TagntSblgntAligner(PROTESTANT_66_CANON)

    with pytest.raises(TagntAlignmentError, match="more than one alignment"):
        aligner.align(ambiguous, (_target("τοῦ"),))
