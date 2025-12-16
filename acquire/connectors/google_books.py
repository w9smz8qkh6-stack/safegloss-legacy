"""
Google Books connector (metadata + preview/purchase links).
"""

from typing import Any, Dict, List, Optional

import httpx

from acquire.models import AcquisitionCandidate, TextSource
from acquire.services import matching

from .base import TextSourceConnector

GOOGLE_BOOKS_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksConnector(TextSourceConnector):
    source_name = "Google Books"
    capabilities = {"search_catalog"}

    def __init__(self) -> None:
        self._text_source: Optional[TextSource] = None

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Ensure TextSource exists
        if self._text_source is None:
            self._text_source = TextSource.objects.filter(name=self.source_name).first()
        if not self._text_source:
            return []

        queries = []
        if text.get("isbn13"):
            queries.append(f"isbn:{matching.normalize_isbn(text['isbn13'])}")
        if text.get("isbn10"):
            queries.append(f"isbn:{matching.normalize_isbn(text['isbn10'])}")
        if text.get("title"):
            title = text["title"]
            author = (text.get("authors") or [""])[0] if isinstance(text.get("authors"), list) else text.get("authors") or ""
            queries.append(f'intitle:"{title}" inauthor:"{author}"')

        seen_ids = set()
        candidates: List[Dict[str, Any]] = []
        with httpx.Client(timeout=10.0) as client:
            for q in queries:
                try:
                    resp = client.get(GOOGLE_BOOKS_ENDPOINT, params={"q": q, "maxResults": 5})
                    resp.raise_for_status()
                except Exception:
                    continue
                data = resp.json()
                for item in data.get("items", []):
                    vid = item.get("id")
                    if vid in seen_ids:
                        continue
                    seen_ids.add(vid)
                    parsed = self._parse_item(item, text)
                    if parsed:
                        candidates.append(parsed)
        return candidates

    def _parse_item(self, item: Dict[str, Any], text: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        volume = item.get("volumeInfo", {})
        sale = item.get("saleInfo", {})
        identifiers = {}
        for ident in volume.get("industryIdentifiers", []):
            t = ident.get("type")
            if t == "ISBN_13":
                identifiers["isbn13"] = ident.get("identifier")
            if t == "ISBN_10":
                identifiers["isbn10"] = ident.get("identifier")
        url = volume.get("canonicalVolumeLink") or volume.get("infoLink") or ""
        if not url:
            return None

        match_signals = matching.default_match_signals(
            text,
            {"identifiers": identifiers},
        )
        # Simple heuristic: exact ISBN gets higher score.
        match_score = 0.5
        if match_signals.get("isbn_exact"):
            match_score = 1.0

        access_type = AcquisitionCandidate.READ_ONLINE
        price_amount = None
        price_currency = ""
        if sale.get("saleability") == "FOR_SALE" and sale.get("retailPrice"):
            access_type = AcquisitionCandidate.PURCHASE_ONLY
            price_amount = sale["retailPrice"].get("amount")
            price_currency = sale["retailPrice"].get("currencyCode", "")

        return {
            "text_source": self._text_source,
            "url": url,
            "access_type": access_type,
            "match_score": match_score,
            "match_signals": match_signals,
            "availability_snapshot": {
                "saleability": sale.get("saleability"),
                "isEbook": sale.get("isEbook"),
            },
            "price_amount": price_amount,
            "price_currency": price_currency,
        }

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        # No authenticated availability for Google Books metadata; no-op.
        return {}

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        return candidate.get("url", "")
