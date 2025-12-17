"""
Cambridge Standards Provider (stub).

Downloads syllabus (and scheme of work if available), extracts objectives via LLM,
and returns FetchResult for a single course/subject/grade.
"""

import logging
import re
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from core.services.standards.providers import (
    BaseStandardsProvider,
    FetchResult,
    ObjectiveNodeData,
    ProviderError,
    register_provider,
)
from core.services.standards.validation import ProvenanceValidationError

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _fetch_url(url: str) -> str:
    resp = requests.get(url, timeout=25, headers={"User-Agent": "SafeglossBot/1.0"})
    resp.raise_for_status()
    return resp.text


@register_provider("CAIE_GENERIC")
class CambridgeProvider(BaseStandardsProvider):
    """
    Generic Cambridge provider: expects syllabus_url to be supplied via params.

    This is a stub; in production, map program/subject/grade to canonical syllabus URLs.
    """

    @property
    def authority_code(self) -> str:
        return "CAMBRIDGE"

    @property
    def program_code(self) -> str:
        # Placeholder; real mapping should register per-program providers
        return "CAIE_GENERIC"

    def fetch_objectives(
        self,
        subject: str,
        grade_level: str,
        version: Optional[str] = None,
        syllabus_url: Optional[str] = None,
        source_title: Optional[str] = None,
    ) -> FetchResult:
        """
        Download syllabus and extract objectives via heuristic + fallback LLM.
        """
        if not syllabus_url:
            raise ProviderError("syllabus_url is required for Cambridge provider", provider="cambridge")

        try:
            html = _fetch_url(syllabus_url)
        except Exception as e:
            raise ProviderError(f"Failed to fetch syllabus: {e}", provider="cambridge")

        nodes = self._extract_objectives(html)

        # Build provenance
        provenance = {
            "source_publisher_name": "Cambridge Assessment International Education",
            "source_publisher_type": "testing_org",
            "source_title": source_title or "Cambridge Syllabus",
            "source_url": syllabus_url,
            "source_url_canonical": syllabus_url,
            "source_accessed_at": timezone.now().isoformat(),
            "source_content_type": "html",
            "source_version_label": version or "",
            "acquisition_method": "official_web_page",
            "acquisition_notes": "Fetched syllabus page and extracted objectives.",
            "evidence_sha256_canonical": "",
        }

        return FetchResult(
            authority_code=self.authority_code,
            program_code=self.program_code,
            subject=subject,
            grade_level=grade_level,
            version_label=version or "",
            provenance=provenance,
            nodes=nodes,
            artifact_content=html.encode("utf-8"),
            artifact_filename="cambridge_syllabus.html",
            artifact_content_type="html",
        )

    def list_available_subjects(self) -> list[str]:
        return []

    def list_available_grades(self, subject: Optional[str] = None) -> list[str]:
        return []

    def _extract_objectives(self, html: str) -> list[ObjectiveNodeData]:
        """
        Heuristic extraction: look for bullet lists and headings as objectives.
        For production, replace with structured parse or LLM.
        """
        soup = BeautifulSoup(html, "html.parser")
        bullets = soup.find_all(["li"])
        nodes = []
        order = 1
        for li in bullets[:200]:  # cap to avoid runaway
            text = _clean_text(li.get_text(" ", strip=True))
            if not text or len(text) < 20:
                continue
            nodes.append(
                ObjectiveNodeData(
                    id=f"n{order}",
                    parent_id=None,
                    node_type="objective",
                    code=f"O{order}",
                    text=text,
                    sort_order=order,
                )
            )
            order += 1
        if not nodes:
            raise ProviderError("No objectives extracted from syllabus", provider="cambridge")
        return nodes
