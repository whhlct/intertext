import pytest
from intertext_ingest.corpora.bible import PROTESTANT_66_CANON
from intertext_ingest.corpora.bible.references import (
    bible_reference_from_label,
    resolve_bible_reference,
)
from intertext_ingest.normalized import SourceReference


def test_bible_corpus_maps_distinct_source_schemes_to_one_canonical_reference() -> None:
    usfm = SourceReference(
        scheme="usfm",
        label="MRK 1:1",
        components={"book_code": "MRK", "chapter": 1, "verse": 1},
    )
    sblgnt = SourceReference(
        scheme="sblgnt",
        label="Mark 1:1",
        components={"book_name": "Mark", "chapter": 1, "verse": 1},
    )

    usfm_reference = resolve_bible_reference(usfm, PROTESTANT_66_CANON)
    sblgnt_reference = resolve_bible_reference(sblgnt, PROTESTANT_66_CANON)

    assert usfm_reference == sblgnt_reference
    assert usfm_reference.key == "bible.mark.1.1"
    assert usfm_reference.components["book_slug"] == "mark"
    assert "book_code" not in usfm_reference.components
    assert PROTESTANT_66_CANON.identifier == "protestant-66"


def test_bible_reference_aliases_belong_to_the_corpus_layer() -> None:
    reference = bible_reference_from_label("Song of Songs 1:1", PROTESTANT_66_CANON)

    assert reference.key == "bible.song-of-solomon.1.1"


def test_bible_corpus_rejects_an_unowned_source_scheme() -> None:
    reference = SourceReference(
        scheme="tanzil",
        label="1:1",
        components={"surah": 1, "ayah": 1},
    )

    with pytest.raises(ValueError, match="cannot resolve source scheme"):
        resolve_bible_reference(reference, PROTESTANT_66_CANON)
