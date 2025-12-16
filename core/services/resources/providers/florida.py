"""
Florida Resource Provider.

Discovers educational resources that support Florida B.E.S.T.
(Benchmarks for Excellent Student Thinking) standards.
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


@register_resource_provider("STATE_FL")
class FloridaResourceProvider(BaseResourceProvider):
    """
    Resource provider for Florida B.E.S.T. standards.

    SEARCH STRATEGY:
    ================
    1. FLDOE Instructional Materials
       - URL: https://www.fldoe.org/academics/standards/instructional-materials/
       - State-adopted instructional materials list
       - Updated after adoption cycles

    2. CPALMS (Collaborate, Plan, Align, Learn, Motivate, Share)
       - URL: https://www.cpalms.org/
       - Florida's official standards and resources portal
       - Contains lesson plans, assessments, and resource links

    3. Florida Virtual School (FLVS)
       - URL: https://www.flvs.net/
       - Free online courses aligned to Florida standards

    IMPLEMENTATION:
    ==============
    - Returns curated official FLDOE resources
    - Searches Google Books for aligned textbooks
    """

    SEARCH_STRATEGY = """
    1. Check FLDOE Instructional Materials adoption list
    2. Search CPALMS for aligned resources
    3. Check FLVS course catalog
    4. Search major district curriculum pages
    """

    SOURCE_URLS = [
        "https://www.fldoe.org/academics/standards/instructional-materials/",
        "https://www.cpalms.org/",
        "https://www.flvs.net/",
        "https://www.dadeschools.net/",
        "https://www.browardschools.com/",
    ]

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_FL"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Florida B.E.S.T. standards.

        Combines:
        - Curated official FLDOE resources
        - Google Books search for Florida-aligned textbooks
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Add Florida-specific official resources
        florida_resources = [
            ResourceData(
                title="CPALMS - Florida's Standards Portal",
                source_url="https://www.cpalms.org/",
                media_type="curriculum",
                platform="cpalms",
                publisher="Florida Department of Education",
                description="Official Florida B.E.S.T. standards, lesson plans, and resources",
                is_official=True,
                endorsement_notes="Official FLDOE resource platform",
            ),
            ResourceData(
                title="Florida Virtual School (FLVS)",
                source_url="https://www.flvs.net/",
                media_type="course",
                platform="flvs",
                publisher="Florida Virtual School",
                description="Free online courses aligned to Florida standards",
                is_official=True,
                endorsement_notes="Florida's official virtual school",
            ),
        ]
        resources.extend(florida_resources)

        # 3. Search Google Books for Florida-specific textbooks
        normalized_subject = normalize_subject(subject)
        search_term = f"Florida B.E.S.T. {subject} {grade_level} textbook"

        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["florida", "best", subject.lower()[:4]]):
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
            "Science",
            "Social Studies",
            "Health Education",
            "Physical Education",
            "Fine Arts",
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
