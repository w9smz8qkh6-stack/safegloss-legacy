"""
Open Library connector (covers metadata and CDL links when present).
"""

from typing import Any, Dict, List, Optional

import httpx

from acquire.models import AcquisitionCandidate, TextSource
from acquire.services import matching

from .base import TextSourceConnector


class OpenLibraryConnector(TextSourceConnector):
    source_name = "Open Library"
    capabilities = {"search_catalog", "download_open"}

    def __init__(self) -> None:
        self._text_source: Optional[TextSource] = None

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._text_source is None:
            self._text_source = TextSource.objects.filter(name=self.source_name).first()
        if not self._text_source:
            return []

        isbn = text.get("isbn13") or text.get("isbn10")
        if not isbn:
            return []

        normalized = matching.normalize_isbn(isbn)
        url = f"https://openlibrary.org/api/books"
        params = {"bibkeys": f"ISBN:{normalized}", "format": "json", "jscmd": "data"}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except Exception:
            return []

        key = f"ISBN:{normalized}"
        data = payload.get(key)
        if not data:
            return []

        identifiers = {
            "isbn13": normalized if len(normalized) == 13 else "",
            "isbn10": normalized if len(normalized) == 10 else "",
        }
        ol_url = data.get("url") or data.get("key")
        if ol_url and ol_url.startswith("/"):
            ol_url = f"https://openlibrary.org{ol_url}"
        if not ol_url:
            return []

        ebooks = data.get("ebooks", [])
        access_type = AcquisitionCandidate.READ_ONLINE
        availability_snapshot = {}
        if ebooks:
            ebook = ebooks[0]
            if ebook.get("borrow_url"):
                access_type = AcquisitionCandidate.BORROW
                availability_snapshot["borrow_url"] = ebook.get("borrow_url")
            elif ebook.get("preview_url"):
                availability_snapshot["preview_url"] = ebook.get("preview_url")

        match_signals = matching.default_match_signals(
            text,
            {"identifiers": identifiers},
        )
        match_score = 1.0 if match_signals.get("isbn_exact") else 0.6

        return [{
            "text_source": self._text_source,
            "url": ol_url,
            "access_type": access_type,
            "match_score": match_score,
            "match_signals": match_signals,
            "availability_snapshot": availability_snapshot,
        }]

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        # Open Library availability is already captured in ebooks payload when present.
        return candidate.get("availability_snapshot", {})

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        return candidate.get("url", "")
