"""External book services for importing from Open Library, Project Gutenberg, and Open Textbook Library."""

from .base import BookSearchResult, BookText, ExternalBookService
from .gutenberg import GutendexService
from .openlibrary import OpenLibraryService
from .opentextbook import OpenTextbookService
from .text_processor import TextProcessor


def get_service(source: str) -> ExternalBookService:
    """Factory function to get the appropriate service for a source."""
    if source == "gutenberg":
        return GutendexService()
    elif source == "openlibrary":
        return OpenLibraryService()
    elif source == "opentextbook":
        return OpenTextbookService()
    else:
        raise ValueError(f"Unknown source: {source}")


__all__ = [
    "BookSearchResult",
    "BookText",
    "ExternalBookService",
    "GutendexService",
    "OpenLibraryService",
    "OpenTextbookService",
    "TextProcessor",
    "get_service",
]
