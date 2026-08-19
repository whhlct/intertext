import re
import unicodedata
from dataclasses import dataclass

from intertext_ingest.normalized import NormalizedReference


@dataclass(frozen=True)
class BibleBook:
    order: int
    code: str
    name: str
    testament: str


_BOOK_DATA = (
    ("GEN", "Genesis"),
    ("EXO", "Exodus"),
    ("LEV", "Leviticus"),
    ("NUM", "Numbers"),
    ("DEU", "Deuteronomy"),
    ("JOS", "Joshua"),
    ("JDG", "Judges"),
    ("RUT", "Ruth"),
    ("1SA", "1 Samuel"),
    ("2SA", "2 Samuel"),
    ("1KI", "1 Kings"),
    ("2KI", "2 Kings"),
    ("1CH", "1 Chronicles"),
    ("2CH", "2 Chronicles"),
    ("EZR", "Ezra"),
    ("NEH", "Nehemiah"),
    ("EST", "Esther"),
    ("JOB", "Job"),
    ("PSA", "Psalms"),
    ("PRO", "Proverbs"),
    ("ECC", "Ecclesiastes"),
    ("SNG", "Song of Solomon"),
    ("ISA", "Isaiah"),
    ("JER", "Jeremiah"),
    ("LAM", "Lamentations"),
    ("EZK", "Ezekiel"),
    ("DAN", "Daniel"),
    ("HOS", "Hosea"),
    ("JOL", "Joel"),
    ("AMO", "Amos"),
    ("OBA", "Obadiah"),
    ("JON", "Jonah"),
    ("MIC", "Micah"),
    ("NAM", "Nahum"),
    ("HAB", "Habakkuk"),
    ("ZEP", "Zephaniah"),
    ("HAG", "Haggai"),
    ("ZEC", "Zechariah"),
    ("MAL", "Malachi"),
    ("MAT", "Matthew"),
    ("MRK", "Mark"),
    ("LUK", "Luke"),
    ("JHN", "John"),
    ("ACT", "Acts"),
    ("ROM", "Romans"),
    ("1CO", "1 Corinthians"),
    ("2CO", "2 Corinthians"),
    ("GAL", "Galatians"),
    ("EPH", "Ephesians"),
    ("PHP", "Philippians"),
    ("COL", "Colossians"),
    ("1TH", "1 Thessalonians"),
    ("2TH", "2 Thessalonians"),
    ("1TI", "1 Timothy"),
    ("2TI", "2 Timothy"),
    ("TIT", "Titus"),
    ("PHM", "Philemon"),
    ("HEB", "Hebrews"),
    ("JAS", "James"),
    ("1PE", "1 Peter"),
    ("2PE", "2 Peter"),
    ("1JN", "1 John"),
    ("2JN", "2 John"),
    ("3JN", "3 John"),
    ("JUD", "Jude"),
    ("REV", "Revelation"),
)

BIBLE_BOOKS = tuple(
    BibleBook(
        order=index + 1,
        code=code,
        name=name,
        testament="old" if index < 39 else "new",
    )
    for index, (code, name) in enumerate(_BOOK_DATA)
)
BOOK_BY_CODE = {book.code: book for book in BIBLE_BOOKS}


def normalize_reference_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


BOOK_BY_NAME = {normalize_reference_label(book.name): book for book in BIBLE_BOOKS}
BOOK_BY_NAME.update(
    {
        "song of songs": BOOK_BY_CODE["SNG"],
        "psalm": BOOK_BY_CODE["PSA"],
        "revelation of john": BOOK_BY_CODE["REV"],
    }
)


def book_from_name(name: str) -> BibleBook:
    try:
        return BOOK_BY_NAME[normalize_reference_label(name)]
    except KeyError as error:
        raise ValueError(f"Unknown Bible book name: {name}") from error


def bible_reference(book_code: str, chapter: int, verse: int) -> NormalizedReference:
    try:
        book = BOOK_BY_CODE[book_code]
    except KeyError as error:
        raise ValueError(f"Unsupported Bible book code: {book_code}") from error
    if chapter < 1 or verse < 1:
        raise ValueError(f"Invalid Bible reference: {book.name} {chapter}:{verse}")
    return NormalizedReference(
        scheme="bible.usfm",
        key=f"bible.{book.code.lower()}.{chapter}.{verse}",
        label=f"{book.name} {chapter}:{verse}",
        components={
            "book_code": book.code,
            "book_name": book.name,
            "book_order": book.order,
            "testament": book.testament,
            "chapter": chapter,
            "verse": verse,
        },
    )


_BIBLE_LABEL = re.compile(r"^(.+?)\s+(\d+):(\d+)$")


def bible_reference_from_label(label: str) -> NormalizedReference:
    match = _BIBLE_LABEL.fullmatch(label.strip())
    if match is None:
        raise ValueError(f"Invalid Bible reference label: {label}")
    book = book_from_name(match.group(1))
    return bible_reference(book.code, int(match.group(2)), int(match.group(3)))


def bible_reference_sort_key(reference: NormalizedReference) -> tuple[int, int, int]:
    components = reference.components
    return (
        int(components["book_order"]),
        int(components["chapter"]),
        int(components["verse"]),
    )
