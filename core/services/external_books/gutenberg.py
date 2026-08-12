"""Gutendex API service for Project Gutenberg books."""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

import requests

from .base import ExternalBookService, BookSearchResult, BookText


logger = logging.getLogger(__name__)


class GutendexService(ExternalBookService):
    """
    Service for searching and retrieving books from Project Gutenberg via Gutendex API.

    API Documentation: https://gutendex.com/
    """

    BASE_URL = "https://gutendex.com"
    USER_AGENT = "SafeglossLiteracyGenerator/1.0"
    TIMEOUT = 30

    @property
    def source_name(self) -> str:
        return "gutenberg"

    def _make_request(self, url: str) -> Optional[dict]:
        """Make an HTTP GET request and return JSON response."""
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "gutendex.com":
            logger.error("Refusing non-Gutendex API URL")
            return None

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)

        try:
            # The scheme and host are allowlisted immediately above.
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:  # nosec B310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error(f"Gutendex API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gutendex response: {e}")
            return None

    def _fetch_text(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch plain text content from a URL using requests with retry logic."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/plain",
            "Accept-Encoding": "identity",  # Disable compression to avoid incomplete reads
        }

        for attempt in range(retries):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=180,
                    stream=True,
                )
                response.raise_for_status()

                # Use iter_content for more reliable large file downloads
                chunks = []
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        chunks.append(chunk)
                content = b"".join(chunks)
                return content.decode("utf-8", errors="replace")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed to fetch {url}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All {retries} attempts failed to fetch text from {url}")
                    return None

        return None

    def _parse_book(self, book_data: dict) -> BookSearchResult:
        """Parse Gutendex book data into BookSearchResult."""
        # Extract authors
        authors = book_data.get("authors", [])
        author_names = ", ".join(
            a.get("name", "Unknown") for a in authors
        ) if authors else "Unknown Author"

        # Get cover image URL
        cover_url = ""
        formats = book_data.get("formats", {})
        for fmt_key in ["image/jpeg", "image/png"]:
            if fmt_key in formats:
                cover_url = formats[fmt_key]
                break

        # Get subjects
        subjects = book_data.get("subjects", [])[:5]  # Limit to 5

        # Check if full text is available
        has_text = any(
            fmt in formats
            for fmt in ["text/plain", "text/plain; charset=utf-8", "text/html"]
        )

        # Get languages
        languages = book_data.get("languages", ["en"])
        language = languages[0] if languages else "en"

        return BookSearchResult(
            source="gutenberg",
            external_id=str(book_data.get("id", "")),
            title=book_data.get("title", "Unknown Title"),
            author=author_names,
            cover_url=cover_url,
            language=language,
            subjects=subjects,
            first_publish_year=None,  # Gutendex doesn't provide this
            has_full_text=has_text,
            raw_metadata=book_data,
        )

    def search(
        self,
        query: str,
        page: int = 1,
        language: str = "en",
    ) -> tuple[list[BookSearchResult], int]:
        """
        Search Project Gutenberg via Gutendex API.

        Args:
            query: Search terms
            page: Page number (1-indexed)
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            Tuple of (list of BookSearchResult, total count)
        """
        params = {
            "search": query,
            "languages": language,
            "page": page,
        }
        url = f"{self.BASE_URL}/books?{urllib.parse.urlencode(params)}"

        data = self._make_request(url)
        if not data:
            return [], 0

        results = [self._parse_book(book) for book in data.get("results", [])]
        total = data.get("count", 0)

        return results, total

    def get_book_details(self, external_id: str) -> Optional[BookSearchResult]:
        """
        Get detailed information about a specific Gutenberg book.

        Args:
            external_id: Gutenberg book ID

        Returns:
            BookSearchResult or None
        """
        url = f"{self.BASE_URL}/books/{external_id}"
        data = self._make_request(url)

        if not data:
            return None

        return self._parse_book(data)

    def get_full_text(self, external_id: str) -> Optional[BookText]:
        """
        Retrieve the full text of a Gutenberg book.

        Args:
            external_id: Gutenberg book ID

        Returns:
            BookText or None
        """
        # Try the cache URL first (more reliable than ebooks URL)
        cache_urls = [
            f"https://www.gutenberg.org/cache/epub/{external_id}/pg{external_id}.txt",
            f"https://www.gutenberg.org/files/{external_id}/{external_id}-0.txt",
        ]

        for cache_url in cache_urls:
            text = self._fetch_text(cache_url, retries=2)
            if text:
                return BookText.from_plain_text(text, source_url=cache_url)

        # Fallback: get URLs from book metadata
        url = f"{self.BASE_URL}/books/{external_id}"
        data = self._make_request(url)

        if not data:
            return None

        formats = data.get("formats", {})

        # Priority: plain text (UTF-8) > plain text > HTML
        text_url = None
        for fmt_key in [
            "text/plain; charset=utf-8",
            "text/plain",
            "text/plain; charset=us-ascii",
        ]:
            if fmt_key in formats:
                text_url = formats[fmt_key]
                break

        if not text_url:
            logger.warning(f"No plain text format found for Gutenberg book {external_id}")
            return None

        # Fetch the text
        text = self._fetch_text(text_url)
        if not text:
            return None

        return BookText.from_plain_text(text, source_url=text_url)
