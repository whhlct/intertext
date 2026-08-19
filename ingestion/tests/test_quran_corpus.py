from intertext_ingest.corpora.quran.references import resolve_quran_reference
from intertext_ingest.normalized import SourceReference


def test_quran_corpus_maps_quran_xml_reference() -> None:
    source = SourceReference(
        scheme="quran_xml",
        label="2:255",
        components={"surah": 2, "ayah": 255, "surah_name": "البقرة"},
    )

    reference = resolve_quran_reference(source)

    assert reference.key == "quran.2.255"
    assert reference.label == "2:255"
    assert reference.components["surah_name"] == "البقرة"
