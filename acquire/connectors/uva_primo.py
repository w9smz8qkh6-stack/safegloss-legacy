"""
UVA connector (Primo search + OpenURL resolver fallback).

Uses resolver link construction when no API details are available.
"""

from typing import Any, Dict, List, Optional

from django.conf import settings

from acquire.models import AcquisitionCandidate, TextSource
from acquire.services import matching

from .base import TextSourceConnector


class UVAConnector(TextSourceConnector):
    source_name = "UVA Libraries"
    capabilities = {"search_catalog", "check_availability"}

    def __init__(self) -> None:
        self._text_source: Optional[TextSource] = None
        self.resolver_base = getattr(
            settings,
            "UVA_RESOLVER_BASE_URL",
            "https://search.lib.virginia.edu/discovery/openurl",
        )

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._text_source is None:
            self._text_source = TextSource.objects.filter(name=self.source_name).first()
        if not self._text_source:
            return []

        isbn = matching.normalize_isbn(text.get("isbn13") or text.get("isbn10") or "")
        title = text.get("title", "")
        if not isbn and not title:
            return []

        # Construct a resolver or catalog link using ISBN preference.
        if isbn:
            url = f"{self.resolver_base}?rft.isbn={isbn}"
        else:
            url = f"{self.resolver_base}?rft.title={title}"

        identifiers = {"isbn13": isbn} if len(isbn) == 13 else {"isbn10": isbn} if isbn else {}
        match_signals = matching.default_match_signals(
            text,
            {"identifiers": identifiers},
        )
        match_score = 1.0 if match_signals.get("isbn_exact") else 0.6

        return [{
            "text_source": self._text_source,
            "url": url,
            "access_type": AcquisitionCandidate.LOGIN_REQUIRED,
            "match_score": match_score,
            "match_signals": match_signals,
            "availability_snapshot": {"note": "Login required; resolver link"},
        }]

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        # Without API credentials, availability is not programmatically checked.
        return candidate.get("availability_snapshot", {})

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        return candidate.get("url", "")
