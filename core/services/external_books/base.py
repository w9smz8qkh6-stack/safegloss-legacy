"""Base classes and data structures for external book services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BookSearchResult:
    """Standardized search result from any external book source."""
    source: str  # "openlibrary" or "gutenberg"
    external_id: str  # Unique ID within the source
    title: str
    author: str
    cover_url: str = ""
    language: str = "en"
    subjects: list = field(default_factory=list)
    first_publish_year: Optional[int] = None
    has_full_text: bool = False
    raw_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "author": self.author,
            "cover_url": self.cover_url,
            "language": self.language,
            "subjects": self.subjects,
            "first_publish_year": self.first_publish_year,
            "has_full_text": self.has_full_text,
        }


@dataclass
class BookText:
    """Retrieved full text content from an external source."""
    text: str
    format: str  # "plain" or "html"
    word_count: int
    source_url: str = ""

    @classmethod
    def from_plain_text(cls, text: str, source_url: str = "") -> "BookText":
        """Create BookText from plain text."""
        word_count = len(text.split())
        return cls(
            text=text,
            format="plain",
            word_count=word_count,
            source_url=source_url,
        )


@dataclass
class ChapterInfo:
    """Information about a detected chapter in a book."""
    number: int
    title: str
    start_pos: int
    end_pos: int
    word_count: int


class ExternalBookService(ABC):
    """Abstract base class for external book API services."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier (e.g., 'gutenberg', 'openlibrary')."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        page: int = 1,
        language: str = "en",
    ) -> tuple[list[BookSearchResult], int]:
        """
        Search for books matching the query.

        Args:
            query: Search terms (title, author, etc.)
            page: Page number (1-indexed)
            language: Language code filter

        Returns:
            Tuple of (list of results, total count)
        """
        pass

    @abstractmethod
    def get_book_details(self, external_id: str) -> Optional[BookSearchResult]:
        """
        Get detailed information about a specific book.

        Args:
            external_id: The book's ID in this source

        Returns:
            BookSearchResult with full details, or None if not found
        """
        pass

    @abstractmethod
    def get_full_text(self, external_id: str) -> Optional[BookText]:
        """
        Retrieve the full text content of a book.

        Args:
            external_id: The book's ID in this source

        Returns:
            BookText with the content, or None if unavailable
        """
        pass
