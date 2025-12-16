"""
NYPL catalog connector (discovery + vendor detection).

For now, constructs deep links to the public catalog using ISBN/title.
"""

from typing import Any, Dict, List, Optional

from acquire.models import AcquisitionCandidate, TextSource
from acquire.services import matching

from .base import TextSourceConnector


class NYPLConnector(TextSourceConnector):
    source_name = "NYPL"
    capabilities = {"search_catalog"}

    def __init__(self) -> None:
        self._text_source: Optional[TextSource] = None
        self.base_search = "https://browse.nypl.org/iii/encore/search/C__S"

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._text_source is None:
            self._text_source = TextSource.objects.filter(name=self.source_name).first()
        if not self._text_source:
            return []

        isbn = matching.normalize_isbn(text.get("isbn13") or text.get("isbn10") or "")
        if isbn:
            url = f"{self.base_search}{isbn}__Orightresult__U?lang=eng&suite=def"
        elif text.get("title"):
            title = text["title"].replace(" ", "+")
            url = f"{self.base_search}{title}__Orightresult__U?lang=eng&suite=def"
        else:
            return []

        identifiers = {"isbn13": isbn} if len(isbn) == 13 else {"isbn10": isbn} if isbn else {}
        match_signals = matching.default_match_signals(text, {"identifiers": identifiers})
        match_score = 1.0 if match_signals.get("isbn_exact") else 0.5

        return [{
            "text_source": self._text_source,
            "url": url,
            "access_type": AcquisitionCandidate.LOGIN_REQUIRED,
            "match_score": match_score,
            "match_signals": match_signals,
            "availability_snapshot": {"note": "Login may be required for borrow/hold"},
        }]

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        # No programmatic availability check without vendor connector.
        return candidate.get("availability_snapshot", {})

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        return candidate.get("url", "")
