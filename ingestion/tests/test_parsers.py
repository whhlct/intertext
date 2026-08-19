from intertext_ingest.normalized import AcquiredSource
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
