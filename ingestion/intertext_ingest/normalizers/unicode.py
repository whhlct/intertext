import unicodedata


def normalize_unicode(value: str, form: str = "NFC") -> str:
    return unicodedata.normalize(form, value)
