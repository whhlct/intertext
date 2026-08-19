import unicodedata


def normalize_greek_token(value: str) -> str:
    """Return a comparison key without changing the stored source spelling."""

    decomposed = unicodedata.normalize("NFD", value).casefold().replace("ς", "σ")
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character).startswith("L")
        and "GREEK" in unicodedata.name(character, "")
    )


def greek_alignment_forms(value: str) -> frozenset[str]:
    normalized = normalize_greek_token(value)
    forms = {normalized}
    # TAGNT and SBLGNT occasionally differ only by a movable final nu.
    if normalized.endswith(("εν", "σιν", "στιν")):
        forms.add(normalized[:-1])
    return frozenset(forms)
