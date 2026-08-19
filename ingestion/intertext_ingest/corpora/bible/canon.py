from dataclasses import dataclass

from intertext_ingest.corpora.bible.books import PROTESTANT_66_BOOKS, BibleBook


@dataclass(frozen=True)
class BibleCanon:
    identifier: str
    name: str
    books: tuple[BibleBook, ...]

    def __post_init__(self) -> None:
        if len({book.slug for book in self.books}) != len(self.books):
            raise ValueError(f"Duplicate book in Bible canon: {self.identifier}")

    @property
    def order_by_slug(self) -> dict[str, int]:
        return {book.slug: order for order, book in enumerate(self.books, start=1)}

    @property
    def books_by_slug(self) -> dict[str, BibleBook]:
        return {book.slug: book for book in self.books}


PROTESTANT_66_CANON = BibleCanon(
    identifier="protestant-66",
    name="Protestant 66-book canon",
    books=PROTESTANT_66_BOOKS,
)
