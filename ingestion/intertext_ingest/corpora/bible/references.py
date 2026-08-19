import re
import unicodedata

from intertext_ingest.corpora.bible.canon import PROTESTANT_66_CANON, BibleCanon
from intertext_ingest.normalized import CanonicalReference, SourceReference

_USFM_CODES = (
    "GEN",
    "EXO",
    "LEV",
    "NUM",
    "DEU",
    "JOS",
    "JDG",
    "RUT",
    "1SA",
    "2SA",
    "1KI",
    "2KI",
    "1CH",
    "2CH",
    "EZR",
    "NEH",
    "EST",
    "JOB",
    "PSA",
    "PRO",
    "ECC",
    "SNG",
    "ISA",
    "JER",
    "LAM",
    "EZK",
    "DAN",
    "HOS",
    "JOL",
    "AMO",
    "OBA",
    "JON",
    "MIC",
    "NAM",
    "HAB",
    "ZEP",
    "HAG",
    "ZEC",
    "MAL",
    "MAT",
    "MRK",
    "LUK",
    "JHN",
    "ACT",
    "ROM",
    "1CO",
    "2CO",
    "GAL",
    "EPH",
    "PHP",
    "COL",
    "1TH",
    "2TH",
    "1TI",
    "2TI",
    "TIT",
    "PHM",
    "HEB",
    "JAS",
    "1PE",
    "2PE",
    "1JN",
    "2JN",
    "3JN",
    "JUD",
    "REV",
)
_USFM_SLUG_BY_CODE = {
    code: book.slug for code, book in zip(_USFM_CODES, PROTESTANT_66_CANON.books)
}
_OSIS_SLUG_BY_ID = {
    "Gen": "genesis",
    "Exod": "exodus",
    "Lev": "leviticus",
    "Num": "numbers",
    "Deut": "deuteronomy",
    "Josh": "joshua",
    "Judg": "judges",
    "Ruth": "ruth",
    "1Sam": "1-samuel",
    "2Sam": "2-samuel",
    "1Kgs": "1-kings",
    "2Kgs": "2-kings",
    "1Chr": "1-chronicles",
    "2Chr": "2-chronicles",
    "Ezra": "ezra",
    "Neh": "nehemiah",
    "Esth": "esther",
    "Job": "job",
    "Ps": "psalms",
    "Prov": "proverbs",
    "Eccl": "ecclesiastes",
    "Song": "song-of-solomon",
    "Isa": "isaiah",
    "Jer": "jeremiah",
    "Lam": "lamentations",
    "Ezek": "ezekiel",
    "Dan": "daniel",
    "Hos": "hosea",
    "Joel": "joel",
    "Amos": "amos",
    "Obad": "obadiah",
    "Jonah": "jonah",
    "Mic": "micah",
    "Nah": "nahum",
    "Hab": "habakkuk",
    "Zeph": "zephaniah",
    "Hag": "haggai",
    "Zech": "zechariah",
    "Mal": "malachi",
}
_BIBLE_LABEL = re.compile(r"^(.+?)\s+(\d+):(\d+)$")


def normalize_reference_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def book_from_name(name: str, canon: BibleCanon):
    normalized_name = normalize_reference_label(name)
    for book in canon.books:
        names = (book.name, *book.aliases)
        if normalized_name in {normalize_reference_label(value) for value in names}:
            return book
    raise ValueError(f"Bible book is not in {canon.name}: {name}")


def _book_from_source(reference: SourceReference, canon: BibleCanon):
    if reference.scheme == "usfm":
        code = str(reference.components.get("book_code", ""))
        try:
            slug = _USFM_SLUG_BY_CODE[code]
            return canon.books_by_slug[slug]
        except KeyError as error:
            raise ValueError(f"USFM book is not in {canon.name}: {code}") from error
    if reference.scheme == "sblgnt":
        return book_from_name(str(reference.components.get("book_name", "")), canon)
    if reference.scheme == "oshb_osis":
        book_id = str(reference.components.get("book_id", ""))
        try:
            return canon.books_by_slug[_OSIS_SLUG_BY_ID[book_id]]
        except KeyError as error:
            raise ValueError(f"OSIS book is not in {canon.name}: {book_id}") from error
    raise ValueError(f"Bible mapper cannot resolve source scheme: {reference.scheme}")


def bible_reference(
    book_slug: str, chapter: int, verse: int, canon: BibleCanon
) -> CanonicalReference:
    try:
        book = canon.books_by_slug[book_slug]
    except KeyError as error:
        raise ValueError(f"Bible book is not in {canon.name}: {book_slug}") from error
    if chapter < 1 or verse < 1:
        raise ValueError(f"Invalid Bible reference: {book.name} {chapter}:{verse}")
    order = canon.order_by_slug[book.slug]
    return CanonicalReference(
        scheme=f"bible.{canon.identifier}",
        key=f"bible.{book.slug}.{chapter}.{verse}",
        label=f"{book.name} {chapter}:{verse}",
        components={
            "book_slug": book.slug,
            "book_name": book.name,
            "book_order": order,
            "testament": book.testament,
            "chapter": chapter,
            "verse": verse,
        },
    )


def bible_reference_from_label(label: str, canon: BibleCanon) -> CanonicalReference:
    match = _BIBLE_LABEL.fullmatch(label.strip())
    if match is None:
        raise ValueError(f"Invalid Bible reference label: {label}")
    book = book_from_name(match.group(1), canon)
    return bible_reference(book.slug, int(match.group(2)), int(match.group(3)), canon)


def resolve_bible_reference(
    reference: SourceReference, canon: BibleCanon
) -> CanonicalReference:
    book = _book_from_source(reference, canon)
    return bible_reference(
        book.slug,
        int(reference.components.get("chapter", 0)),
        int(reference.components.get("verse", 0)),
        canon,
    )


def bible_reference_sort_key(reference: CanonicalReference) -> tuple[int, int, int]:
    return (
        int(reference.components["book_order"]),
        int(reference.components["chapter"]),
        int(reference.components["verse"]),
    )
