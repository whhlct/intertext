from intertext_ingest.normalized import AcquiredSource
from intertext_ingest.parsers.sblgnt_xml import SblgntXmlParser
from intertext_ingest.parsers.usfm import UsfmParser


def make_kjv_parser() -> UsfmParser:
    return UsfmParser(
        slug="kjv",
        title="King James Version",
        abbreviation="KJV",
        language_iso="en",
        language_name="English",
        version_type="translation",
    )


def test_usfm_parser_normalizes_text_and_preserves_strongs(
    kjv_source: AcquiredSource,
) -> None:
    version = make_kjv_parser().parse(kjv_source)

    assert len(version.segments) == 3
    first = version.segments[0]
    assert first.reference.key == "bible.mrk.1.1"
    assert first.text == (
        "The beginning of the gospel of Jesus Christ, the Son of God;"
    )
    assert first.content_markup["strongs"][0] == {
        "surface": "beginning",
        "strong": "G0746",
    }
    assert "\\w" not in first.text
    assert "strong=" not in first.text
    assert version.segments[1].content_markup["character_styles"] == ["wj"]
    assert version.segments[2].content_markup["omitted_footnote_count"] == 1


def test_sblgnt_xml_parser_emits_the_same_normalized_shape(
    sblgnt_source: AcquiredSource,
) -> None:
    version = SblgntXmlParser().parse(sblgnt_source)

    assert len(version.segments) == 3
    first = version.segments[0]
    assert first.reference.key == "bible.mrk.1.1"
    assert first.text == "Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ ⸀χριστοῦ."
    assert first.content_markup["source_format"] == "sblgnt_xml"
    assert {element["type"] for element in first.content_markup["elements"]} == {
        "prefix",
        "suffix",
        "w",
    }
