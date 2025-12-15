"""Open Library API service."""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

from .base import ExternalBookService, BookSearchResult, BookText


logger = logging.getLogger(__name__)


class OpenLibraryService(ExternalBookService):
    """
    Service for searching and retrieving books from Open Library.

    API Documentation: https://openlibrary.org/developers/api

    Note: Full text is available through Internet Archive links.
    """

    BASE_URL = "https://openlibrary.org"
    COVERS_URL = "https://covers.openlibrary.org/b"
    USER_AGENT = "SafeglossLiteracyGenerator/1.0 (contact@safegloss.com)"
    TIMEOUT = 30

    @property
    def source_name(self) -> str:
        return "openlibrary"

    def _make_request(self, url: str) -> Optional[dict]:
        """Make an HTTP GET request and return JSON response."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error(f"Open Library API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Open Library response: {e}")
            return None

    def _get_cover_url(self, cover_id: Optional[int], size: str = "M") -> str:
        """Get cover image URL from cover ID."""
        if not cover_id:
            return ""
        return f"{self.COVERS_URL}/id/{cover_id}-{size}.jpg"

    def _parse_search_doc(self, doc: dict) -> BookSearchResult:
        """Parse Open Library search document into BookSearchResult."""
        # Extract author names
        authors = doc.get("author_name", [])
        author_str = ", ".join(authors[:3]) if authors else "Unknown Author"

        # Get cover
        cover_id = doc.get("cover_i")
        cover_url = self._get_cover_url(cover_id)

        # Get subjects
        subjects = doc.get("subject", [])[:5]

        # Check for full text availability
        has_full_text = doc.get("has_fulltext", False)

        # Get language
        languages = doc.get("language", ["eng"])
        language = languages[0] if languages else "eng"
        # Convert 3-letter to 2-letter code
        lang_map = {"eng": "en", "spa": "es", "fre": "fr", "ger": "de"}
        language = lang_map.get(language, language[:2] if len(language) > 2 else language)

        return BookSearchResult(
            source="openlibrary",
            external_id=doc.get("key", "").replace("/works/", ""),
            title=doc.get("title", "Unknown Title"),
            author=author_str,
            cover_url=cover_url,
            language=language,
            subjects=subjects,
            first_publish_year=doc.get("first_publish_year"),
            has_full_text=has_full_text,
            raw_metadata=doc,
        )

    def search(
        self,
        query: str,
        page: int = 1,
        language: str = "en",
    ) -> tuple[list[BookSearchResult], int]:
        """
        Search Open Library.

        Args:
            query: Search terms
            page: Page number (1-indexed)
            language: Language code (e.g., 'en', 'es')

        Returns:
            Tuple of (list of BookSearchResult, total count)
        """
        # Convert 2-letter to 3-letter language code for OL
        lang_map = {"en": "eng", "es": "spa", "fr": "fre", "de": "ger"}
        ol_lang = lang_map.get(language, language)

        params = {
            "q": query,
            "language": ol_lang,
            "page": page,
            "limit": 20,
            "has_fulltext": "true",
        }
        url = f"{self.BASE_URL}/search.json?{urllib.parse.urlencode(params)}"

        data = self._make_request(url)
        if not data:
            return [], 0

        results = [self._parse_search_doc(doc) for doc in data.get("docs", [])]
        total = data.get("numFound", 0)

        return results, total

    def get_book_details(self, external_id: str) -> Optional[BookSearchResult]:
        """
        Get detailed information about a specific work.

        Args:
            external_id: Open Library work key (without /works/ prefix)

        Returns:
            BookSearchResult or None
        """
        # Search for the specific work
        url = f"{self.BASE_URL}/search.json?q=key:/works/{external_id}&limit=1"
        data = self._make_request(url)

        if not data or not data.get("docs"):
            return None

        return self._parse_search_doc(data["docs"][0])

    def get_full_text(self, external_id: str) -> Optional[BookText]:
        """
        Retrieve full text from Internet Archive.

        Args:
            external_id: Open Library work key

        Returns:
            BookText or None

        Note: Open Library texts are hosted on Internet Archive.
        This requires additional API calls to IA.
        """
        # Get work details to find IA identifier
        url = f"{self.BASE_URL}/works/{external_id}.json"
        work_data = self._make_request(url)

        if not work_data:
            return None

        # Look for Internet Archive ID in the work's editions
        # This is complex - OL works have multiple editions, each may have different IA IDs
        # For now, return None and implement full IA integration later
        logger.info(
            f"Full text retrieval for Open Library works requires Internet Archive integration. "
            f"Work: {external_id}"
        )

        # TODO: Implement Internet Archive text retrieval
        # 1. Get editions for this work
        # 2. Find edition with IA identifier
        # 3. Fetch text from IA

        return None
