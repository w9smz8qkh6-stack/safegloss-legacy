"""
ACT Resource Provider.

Discovers educational resources for ACT test preparation.
"""

import logging

from core.services.resources import (
    BaseResourceProvider,
    DiscoveryResult,
    ResourceData,
    ResourceProviderError,
    register_resource_provider,
)
from core.services.resources.discovery import (
    get_curated_resources,
    search_google_books,
)

logger = logging.getLogger(__name__)


@register_resource_provider("ACT_PREP")
class ACTResourceProvider(BaseResourceProvider):
    """
    Resource provider for ACT preparation.

    SEARCH STRATEGY:
    ================
    1. ACT Official Resources
       - URL: https://www.act.org/
       - Official practice tests and prep materials
       - ACT Academy (free prep platform)

    2. ACT Academy
       - URL: https://academy.act.org/
       - Free personalized learning paths
       - Practice questions and games

    3. Publisher ACT Prep
       - Official ACT Prep Guide (by ACT)
       - Barron's ACT Prep
       - Princeton Review ACT
       - Kaplan ACT Prep

    IMPLEMENTATION:
    ==============
    - Returns curated official ACT resources
    - Searches Google Books for ACT prep books
    - Adds major publisher resources
    """

    SEARCH_STRATEGY = """
    1. Check ACT official prep resources
    2. ACT Academy free platform
    3. Search publisher ACT prep catalogues
    4. Check for free practice test resources
    """

    SOURCE_URLS = [
        "https://www.act.org/",
        "https://academy.act.org/",
        "https://www.act.org/content/act/en/products-and-services/the-act/test-preparation.html",
        "https://www.barronseduc.com/",
        "https://www.princetonreview.com/college/act-test-prep",
    ]

    @property
    def authority_code(self) -> str:
        return "ACT"

    @property
    def program_code(self) -> str:
        return "ACT_PREP"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for ACT preparation.

        Combines:
        - Curated official ACT resources
        - Google Books search for ACT prep books
        - Major publisher resources
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for ACT prep
        search_term = f"ACT {subject} prep" if subject and "ACT" not in subject else "ACT prep book"
        try:
            book_results = search_google_books(search_term, max_results=8)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if "act" in title_lower and "practice" not in title_lower.replace("act", ""):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 3. Add well-known ACT prep resources
        act_resources = [
            ResourceData(
                title="ACT Academy",
                source_url="https://academy.act.org/",
                media_type="practice_tests",
                platform="act",
                publisher="ACT, Inc.",
                description="Free ACT test prep and personalized learning paths",
                is_official=True,
                endorsement_notes="Official ACT free prep platform",
            ),
            ResourceData(
                title="The Official ACT Prep Guide",
                source_url="https://www.act.org/content/act/en/products-and-services/the-act/test-preparation.html",
                media_type="book",
                platform="act",
                publisher="ACT, Inc.",
                description="Official ACT preparation guide with real practice tests",
                is_official=True,
                endorsement_notes="Official ACT publication",
            ),
            ResourceData(
                title="Barron's ACT Premium Study Guide",
                source_url="https://www.barronseduc.com/search?q=ACT",
                media_type="book",
                platform="barrons",
                publisher="Barron's Educational Series",
                description="Comprehensive ACT review with practice tests",
                is_official=False,
            ),
            ResourceData(
                title="Princeton Review ACT Premium Prep",
                source_url="https://www.princetonreview.com/college/act-test-prep",
                media_type="book",
                platform="princeton_review",
                publisher="The Princeton Review",
                description="ACT prep with strategies, drills, and practice tests",
                is_official=False,
            ),
        ]
        resources.extend(act_resources)
        discovery_notes.append("Added official and major publisher resources.")

        return DiscoveryResult(
            authority_code=self.authority_code,
            program_code=self.program_code,
            subject=subject,
            grade_level=grade_level,
            resources=resources,
            sources_checked=sources_checked,
            discovery_notes=" ".join(discovery_notes) or "Discovery completed.",
        )

    def list_available_subjects(self) -> list[str]:
        return [
            "ACT English",
            "ACT Mathematics",
            "ACT Reading",
            "ACT Science",
            "ACT Writing (optional)",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["ACT", "PreACT", "Grades 9-12"]
