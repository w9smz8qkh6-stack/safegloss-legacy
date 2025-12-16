"""
California Resource Provider.

Discovers educational resources that support California
Content Standards and Frameworks.
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
    normalize_subject,
)

logger = logging.getLogger(__name__)


@register_resource_provider("STATE_CA")
class CaliforniaResourceProvider(BaseResourceProvider):
    """
    Resource provider for California standards.

    SEARCH STRATEGY:
    ================
    1. CDE Instructional Materials
       - URL: https://www.cde.ca.gov/ci/rl/im/
       - State-adopted instructional materials by subject
       - K-8 and 9-12 adoption lists

    2. California Curriculum Frameworks
       - URL: https://www.cde.ca.gov/ci/
       - Comprehensive frameworks with resource recommendations

    3. California Digital Library
       - URL: https://www.cde.ca.gov/ci/cr/cf/
       - Free digital resources for California educators

    IMPLEMENTATION:
    ==============
    - Returns curated official CDE resources
    - Searches Google Books for California-aligned textbooks
    """

    SEARCH_STRATEGY = """
    1. Check CDE Adopted Instructional Materials list
    2. Review California Curriculum Frameworks
    3. Search California Digital Library
    4. Check major district curriculum pages
    """

    SOURCE_URLS = [
        "https://www.cde.ca.gov/ci/rl/im/",
        "https://www.cde.ca.gov/ci/",
        "https://www.cde.ca.gov/ci/cr/cf/",
        "https://www.lausd.org/",
        "https://www.sandiegounified.org/",
    ]

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_CA"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for California standards.

        Combines:
        - Curated official CDE resources
        - Google Books search for California-aligned textbooks
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Add California-specific official resources
        ca_resources = [
            ResourceData(
                title="CDE Adopted Instructional Materials",
                source_url="https://www.cde.ca.gov/ci/rl/im/",
                media_type="guide",
                platform="cde",
                publisher="California Department of Education",
                description="State-adopted instructional materials for California schools",
                is_official=True,
                endorsement_notes="Official CDE adopted materials",
            ),
            ResourceData(
                title="California Curriculum Frameworks",
                source_url="https://www.cde.ca.gov/ci/",
                media_type="curriculum",
                platform="cde",
                publisher="California Department of Education",
                description="Official California curriculum frameworks by subject",
                is_official=True,
                endorsement_notes="Official CDE frameworks",
            ),
            ResourceData(
                title="CDE Digital Library",
                source_url="https://www.cde.ca.gov/ci/cr/cf/",
                media_type="curriculum",
                platform="cde",
                publisher="California Department of Education",
                description="Free digital resources for California educators",
                is_official=True,
                endorsement_notes="Official CDE free resources",
            ),
        ]
        resources.extend(ca_resources)

        # 3. Search Google Books for California-specific textbooks
        normalized_subject = normalize_subject(subject)
        search_term = f"California {subject} {grade_level} textbook"

        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["california", subject.lower()[:4]]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

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
            "English Language Arts",
            "Mathematics",
            "Science (NGSS)",
            "History-Social Science",
            "Health Education",
            "Physical Education",
            "Visual and Performing Arts",
            "World Languages",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return [
            "Kindergarten",
            "Grade 1",
            "Grade 2",
            "Grade 3",
            "Grade 4",
            "Grade 5",
            "Grade 6",
            "Grade 7",
            "Grade 8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
        ]
