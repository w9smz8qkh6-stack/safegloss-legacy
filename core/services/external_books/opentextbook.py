"""Open Textbook Library API service.

API Documentation: https://open.umn.edu/opentextbooks/api-docs
Base URL: https://open.umn.edu/opentextbooks

The Open Textbook Library provides free, peer-reviewed, openly-licensed textbooks.
"""

import logging
import requests
from typing import Optional

from .base import BookSearchResult, BookText, ExternalBookService

logger = logging.getLogger(__name__)

BASE_URL = "https://open.umn.edu/opentextbooks"
TIMEOUT = 15


class OpenTextbookService(ExternalBookService):
    """Service for searching and retrieving textbooks from Open Textbook Library."""

    @property
    def source_name(self) -> str:
        return "opentextbook"

    def search(
        self,
        query: str,
        page: int = 1,
        language: str = "en",
    ) -> tuple[list[BookSearchResult], int]:
        """
        Search Open Textbook Library for textbooks.

        Args:
            query: Search terms
            page: Page number (1-indexed)
            language: Language filter (uses ISO 639-2 codes like 'eng')

        Returns:
            Tuple of (list of BookSearchResult, total count estimate)
        """
        results = []

        # Convert language code to ISO 639-2 (3-letter)
        lang_map = {"en": "eng", "es": "spa", "fr": "fra", "de": "deu"}
        lang_code = lang_map.get(language, language)

        params = {
            "q": query,
            "page": page,
        }

        # Only add language filter if not English (most textbooks are English)
        if language and language != "en":
            params["language"] = lang_code

        try:
            response = requests.get(
                f"{BASE_URL}/textbooks.json",
                params=params,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Open Textbook Library search failed: {e}")
            return [], 0

        textbooks = data.get("data", [])

        for book in textbooks:
            # Get primary author
            contributors = book.get("contributors", [])
            primary_author = ""
            for contrib in contributors:
                if contrib.get("primary"):
                    first = contrib.get("first_name", "")
                    last = contrib.get("last_name", "")
                    primary_author = f"{first} {last}".strip()
                    break
            if not primary_author and contributors:
                first = contributors[0].get("first_name", "")
                last = contributors[0].get("last_name", "")
                primary_author = f"{first} {last}".strip()

            # Get subjects
            subjects = [s.get("name", "") for s in book.get("subjects", [])]

            # Check if full text is available (has PDF or online format)
            formats = book.get("formats", [])
            has_full_text = any(
                f.get("type") in ("PDF", "Online", "Web") and f.get("url")
                for f in formats
            )

            # Get cover URL if available (Open Textbook Library doesn't provide covers in API)
            cover_url = ""

            results.append(BookSearchResult(
                source=self.source_name,
                external_id=str(book.get("id", "")),
                title=book.get("title", "Unknown Title"),
                author=primary_author or "Unknown Author",
                cover_url=cover_url,
                language=book.get("language", "eng")[:2],  # Convert back to 2-letter
                subjects=subjects[:5],  # Limit subjects
                first_publish_year=book.get("copyright_year"),
                has_full_text=has_full_text,
                raw_metadata=book,
            ))

        # Open Textbook Library doesn't return total count in response
        # Estimate based on whether we got a full page
        total_estimate = len(results) + (20 * page) if len(results) >= 20 else len(results) + (20 * (page - 1))

        return results, total_estimate

    def get_book_details(self, external_id: str) -> Optional[BookSearchResult]:
        """
        Get detailed information about a specific textbook.

        Args:
            external_id: The textbook ID

        Returns:
            BookSearchResult with full details, or None if not found
        """
        try:
            response = requests.get(
                f"{BASE_URL}/textbooks/{external_id}.json",
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            book = response.json()
        except requests.RequestException as e:
            logger.error(f"Open Textbook Library details failed for {external_id}: {e}")
            return None

        # Get primary author
        contributors = book.get("contributors", [])
        primary_author = ""
        for contrib in contributors:
            if contrib.get("primary"):
                first = contrib.get("first_name", "")
                last = contrib.get("last_name", "")
                primary_author = f"{first} {last}".strip()
                break
        if not primary_author and contributors:
            first = contributors[0].get("first_name", "")
            last = contributors[0].get("last_name", "")
            primary_author = f"{first} {last}".strip()

        # Get subjects
        subjects = [s.get("name", "") for s in book.get("subjects", [])]

        # Check for full text availability
        formats = book.get("formats", [])
        has_full_text = any(
            f.get("type") in ("PDF", "Online", "Web") and f.get("url")
            for f in formats
        )

        return BookSearchResult(
            source=self.source_name,
            external_id=str(book.get("id", "")),
            title=book.get("title", "Unknown Title"),
            author=primary_author or "Unknown Author",
            cover_url="",
            language=book.get("language", "eng")[:2],
            subjects=subjects,
            first_publish_year=book.get("copyright_year"),
            has_full_text=has_full_text,
            raw_metadata=book,
        )

    def get_full_text(self, external_id: str) -> Optional[BookText]:
        """
        Retrieve the full text content of a textbook.

        Note: Open Textbook Library provides links to external PDFs/websites,
        not raw text. This method attempts to fetch text-based formats.

        Args:
            external_id: The textbook ID

        Returns:
            BookText with content, or None if unavailable
        """
        # First get the book details to find format URLs
        details = self.get_book_details(external_id)
        if not details:
            return None

        formats = details.raw_metadata.get("formats", [])

        # Prefer plain text or HTML formats
        preferred_types = ["Plain Text", "HTML", "Web", "Online"]
        text_url = None
        source_type = None

        for ptype in preferred_types:
            for fmt in formats:
                if fmt.get("type") == ptype and fmt.get("url"):
                    text_url = fmt["url"]
                    source_type = ptype
                    break
            if text_url:
                break

        # If no text format, try PDF (but we can't extract text from it)
        if not text_url:
            for fmt in formats:
                if fmt.get("type") == "PDF" and fmt.get("url"):
                    # Return a message indicating PDF-only
                    return BookText(
                        text=f"[This textbook is only available as PDF. Download it from: {fmt['url']}]",
                        format="plain",
                        word_count=0,
                        source_url=fmt["url"],
                    )

        if not text_url:
            return None

        # Try to fetch the content
        try:
            response = requests.get(text_url, timeout=30)
            response.raise_for_status()
            content = response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch textbook content from {text_url}: {e}")
            return None

        # Determine format
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type or source_type in ("HTML", "Web", "Online"):
            text_format = "html"
        else:
            text_format = "plain"

        word_count = len(content.split())

        return BookText(
            text=content,
            format=text_format,
            word_count=word_count,
            source_url=text_url,
        )

    def get_subjects(self) -> list[dict]:
        """
        Get all available subjects/categories.

        Returns:
            List of subject dictionaries with id, name, and textbook count
        """
        try:
            response = requests.get(
                f"{BASE_URL}/subjects.json",
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Failed to fetch subjects: {e}")
            return []
