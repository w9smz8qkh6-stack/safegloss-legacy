"""
Matching utilities for acquisition candidates.

Placeholder implementations will be replaced with real ISBN normalization and
similarity scoring.
"""

from typing import Dict


def normalize_isbn(value: str) -> str:
    """Strip hyphens/spaces and uppercase the ISBN."""
    return (value or "").replace("-", "").replace(" ", "").upper()


def default_match_signals(text: Dict, candidate: Dict) -> Dict:
    """Compute placeholder match signals."""
    isbn_exact = False
    text_isbn = normalize_isbn(text.get("isbn13") or text.get("isbn10") or "")
    cand_isbn = normalize_isbn(candidate.get("identifiers", {}).get("isbn13") or candidate.get("identifiers", {}).get("isbn10") or "")
    if text_isbn and cand_isbn:
        isbn_exact = text_isbn == cand_isbn
    return {
        "isbn_exact": isbn_exact,
        "title_similarity": 0.0,
        "author_similarity": 0.0,
        "edition_match": False,
        "year_delta": None,
    }
