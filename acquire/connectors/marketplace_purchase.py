"""
Commercial marketplace connector for purchase-only links with price capture.

Uses Google Books saleInfo as a lightweight purchase signal (no scraping).
"""

from typing import Any, Dict, List, Optional

import httpx

from acquire.models import AcquisitionCandidate, TextSource
from acquire.services import matching

from .base import TextSourceConnector

GOOGLE_BOOKS_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"


class MarketplacePurchaseConnector(TextSourceConnector):
    source_name = "Marketplace Purchase"
    capabilities = {"search_catalog"}

    def __init__(self) -> None:
        self._text_source: Optional[TextSource] = None

    def search(self, text: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        if sale.get("saleability") != "FOR_SALE" or not sale.get("retailPrice"):
            return None

        identifiers = {}
        for ident in volume.get("industryIdentifiers", []):
            t = ident.get("type")
            if t == "ISBN_13":
                identifiers["isbn13"] = ident.get("identifier")
            if t == "ISBN_10":
                identifiers["isbn10"] = ident.get("identifier")

        url = sale.get("buyLink") or volume.get("canonicalVolumeLink") or volume.get("infoLink")
        if not url:
            return None

        match_signals = matching.default_match_signals(
            text,
            {"identifiers": identifiers},
        )
        match_score = 1.0 if match_signals.get("isbn_exact") else 0.7

        price = sale.get("retailPrice", {})
        return {
            "text_source": self._text_source,
            "url": url,
            "access_type": AcquisitionCandidate.PURCHASE_ONLY,
            "match_score": match_score,
            "match_signals": match_signals,
            "availability_snapshot": {
                "saleability": sale.get("saleability"),
            },
            "price_amount": price.get("amount"),
            "price_currency": price.get("currencyCode", ""),
        }

    def check_availability(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        return candidate.get("availability_snapshot", {})

    def open_reader_url(self, candidate: Dict[str, Any]) -> str:
        return candidate.get("url", "")
