import unicodedata

from intertext_ingest.normalized import CanonicalReference, SourceReference


def normalize_quran_reference_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def quran_reference(
    surah: int,
    ayah: int,
    surah_name: str | None = None,
) -> CanonicalReference:
    if surah < 1 or ayah < 1:
        raise ValueError(f"Invalid Quran reference: {surah}:{ayah}")
    components: dict[str, str | int] = {"surah": surah, "ayah": ayah}
    if surah_name and surah_name.strip():
        components["surah_name"] = surah_name
    return CanonicalReference(
        scheme="quran.intertext",
        key=f"quran.{surah}.{ayah}",
        label=f"{surah}:{ayah}",
        components=components,
    )


def resolve_quran_reference(reference: SourceReference) -> CanonicalReference:
    if reference.scheme not in {"quran_pipe_text", "quran_xml"}:
        raise ValueError(
            f"Quran mapper cannot resolve source scheme: {reference.scheme}"
        )
    return quran_reference(
        int(reference.components.get("surah", 0)),
        int(reference.components.get("ayah", 0)),
        str(reference.components.get("surah_name", "")) or None,
    )


def quran_reference_sort_key(reference: CanonicalReference) -> tuple[int, int]:
    return (
        int(reference.components["surah"]),
        int(reference.components["ayah"]),
    )
