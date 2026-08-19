import unicodedata

from intertext_ingest.normalized import AcquiredSource
from intertext_ingest.parsers.oshb_osis import OshbOsisParser
from intertext_ingest.parsers.quran_pipe_text import QuranPipeTextParser
from intertext_ingest.parsers.quran_xml import QuranXmlParser
from intertext_ingest.parsers.sblgnt_xml import SblgntXmlParser
from intertext_ingest.parsers.usfm import UsfmParser


def test_usfm_parser_emits_source_references_and_preserves_strongs(
    kjv_source: AcquiredSource,
) -> None:
    parsed = UsfmParser().parse(kjv_source)

    assert len(parsed.segments) == 3
    first = parsed.segments[0]
    assert first.source_reference.scheme == "usfm"
    assert first.source_reference.components == {
        "book_code": "MRK",
        "chapter": 1,
        "verse": 1,
    }
    assert first.text == (
        "The beginning of the gospel of Jesus Christ, the Son of God;"
    )
    assert first.content_markup["strongs"][0] == {
        "surface": "beginning",
        "strong": "G0746",
    }
    assert "\\w" not in first.text
    assert "strong=" not in first.text
    assert parsed.segments[1].content_markup["character_styles"] == ["wj"]
    assert parsed.segments[2].content_markup["omitted_footnote_count"] == 1
    assert not hasattr(parsed, "language_iso")


def test_sblgnt_xml_parser_emits_source_references(
    sblgnt_source: AcquiredSource,
) -> None:
    parsed = SblgntXmlParser().parse(sblgnt_source)

    assert len(parsed.segments) == 3
    first = parsed.segments[0]
    assert first.source_reference.scheme == "sblgnt"
    assert first.source_reference.components == {
        "book_name": "Mark",
        "chapter": 1,
        "verse": 1,
    }
    assert first.text == "Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ ⸀χριστοῦ."
    assert first.content_markup["source_format"] == "sblgnt_xml"
    assert {element["type"] for element in first.content_markup["elements"]} == {
        "prefix",
        "suffix",
        "w",
    }
    assert not hasattr(parsed, "language_iso")


def test_oshb_osis_parser_preserves_hebrew_words_and_annotations(
    oshb_source: AcquiredSource,
) -> None:
    parsed = OshbOsisParser().parse(oshb_source)

    assert len(parsed.segments) == 3
    first = parsed.segments[0]
    assert first.source_reference.scheme == "oshb_osis"
    assert first.source_reference.components == {
        "book_id": "Gen",
        "chapter": 1,
        "verse": 1,
    }
    assert first.text == (
        "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃"
    )
    first_word = first.tokens[0]
    assert first_word.surface == "בְּ/רֵאשִׁ֖ית"
    assert unicodedata.normalize("NFC", first_word.surface) != first_word.surface
    assert first_word.metadata == {
        "source_id": "01xeN",
        "lemma": "b/7225",
        "morphology": "HR/Ncfsa",
        "cantillation_hierarchy": "1.0",
        "osis_attributes": {
            "lemma": "b/7225",
            "n": "1.0",
            "morph": "HR/Ncfsa",
            "id": "01xeN",
        },
    }
    assert first.content_markup["unicode_normalization"] == "none"
    assert parsed.segments[1].text.endswith("עַל־פְּנֵ֣י הַמָּֽיִם׃")
    assert "Fixture note" not in parsed.segments[1].text
    variant = parsed.segments[1].content_markup["elements"][-1]
    qere_word = variant["children"][1]["children"][0]
    assert qere_word["attributes"] == {
        "lemma": "4325",
        "n": "0",
        "morph": "HNcmpa",
        "id": "01QER",
    }


def test_quran_xml_parser_preserves_ayah_text_and_structured_attributes(
    quran_source: AcquiredSource,
) -> None:
    parsed = QuranXmlParser().parse(quran_source)

    assert len(parsed.segments) == 4
    first = parsed.segments[0]
    assert first.source_reference.scheme == "quran_xml"
    assert first.source_reference.components == {
        "surah": 1,
        "ayah": 1,
        "surah_name": "الفاتحة",
    }
    assert first.text == "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"
    third = parsed.segments[2]
    assert third.source_reference.label == "2:1"
    assert third.content_markup["attributes"]["bismillah"] == (
        "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"
    )
    assert third.text == "الم"


def test_quran_pipe_text_parser_ignores_comments_and_preserves_content(
    quran_saheeh_source: AcquiredSource,
) -> None:
    parsed = QuranPipeTextParser().parse(quran_saheeh_source)

    assert len(parsed.segments) == 4
    first = parsed.segments[0]
    assert first.source_reference.scheme == "quran_pipe_text"
    assert first.source_reference.components == {"surah": 1, "ayah": 1}
    assert first.text == (
        "In the name of Allah, the Entirely Merciful, the Especially Merciful."
    )
    assert parsed.segments[-1].text == (
        "This is the Book | about which there is no doubt."
    )
    assert parsed.segments[-1].metadata["source_line"] == 7
