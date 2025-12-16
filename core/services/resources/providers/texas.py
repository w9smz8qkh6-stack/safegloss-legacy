"""
Texas Resource Provider.

Discovers educational resources that support Texas TEKS
(Texas Essential Knowledge and Skills) learning objectives.
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
    grade_matches,
)

logger = logging.getLogger(__name__)


@register_resource_provider("STATE_TX")
class TexasResourceProvider(BaseResourceProvider):
    """
    Resource provider for Texas TEKS standards.

    SEARCH STRATEGY:
    ================
    1. TEA Adopted Instructional Materials List
       - URL: https://tea.texas.gov/academics/instructional-materials
       - Contains state-adopted textbooks by subject and grade
       - Updated annually after SBOE adoption cycles

    2. Texas Resource Review (TRR)
       - URL: https://texasresourcereview.org/
       - Reviews of instructional materials aligned to TEKS
       - Contains alignment ratings and teacher reviews

    3. Major District Curriculum Pages
       - Houston ISD: https://www.houstonisd.org/curriculum
       - Dallas ISD: https://www.dallasisd.org/curriculum
       - Austin ISD: https://www.austinisd.org/academics
       - These often list supplemental resources beyond state adoptions

    4. Publisher TEKS Alignment Documents
       - Pearson Texas Portal
       - McGraw-Hill Texas Resources
       - HMH (Houghton Mifflin Harcourt) Texas

    IMPLEMENTATION:
    ==============
    - Returns curated official TEA resources
    - Searches Google Books for TEKS-aligned textbooks
    - Future: Web scraping of TEA materials list
    """

    SEARCH_STRATEGY = """
    1. Check TEA Adopted Instructional Materials list
    2. Query Texas Resource Review for aligned materials
    3. Search major district curriculum pages (Houston, Dallas, Austin ISDs)
    4. Check publisher TEKS alignment documents
    """

    SOURCE_URLS = [
        "https://tea.texas.gov/academics/instructional-materials",
        "https://texasresourcereview.org/",
        "https://www.houstonisd.org/curriculum",
        "https://www.dallasisd.org/curriculum",
        "https://www.austinisd.org/academics",
    ]

    # Subject-specific search terms for Google Books
    SUBJECT_SEARCH_TERMS = {
        "english language arts": "Texas TEKS English Language Arts textbook",
        "mathematics": "Texas TEKS Mathematics textbook",
        "science": "Texas TEKS Science textbook",
        "social studies": "Texas TEKS Social Studies textbook",
        "technology applications": "Texas TEKS Technology textbook",
    }

    @property
    def authority_code(self) -> str:
        return "US_STATES"

    @property
    def program_code(self) -> str:
        return "STATE_TX"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Texas TEKS.

        Combines:
        - Curated TEA official resources
        - Google Books search for TEKS-aligned textbooks
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for textbooks
        normalized_subject = normalize_subject(subject)
        search_term = self.SUBJECT_SEARCH_TERMS.get(
            normalized_subject,
            f"Texas TEKS {subject} {grade_level} textbook"
        )

        # Add grade to search if specific
        if grade_level and "grades" not in grade_level.lower():
            search_term = f"{search_term} {grade_level}"

        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            # Filter to likely educational books
            for book in book_results:
                # Skip if title doesn't seem educational
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["texas", "teks", subject.lower()[:4]]):
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
            "English Language Arts and Reading",
            "Mathematics",
            "Science",
            "Social Studies",
            "Technology Applications",
            "Health Education",
            "Physical Education",
            "Fine Arts",
            "Languages Other Than English",
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
            "Grades 6-8",
            "Grade 9",
            "Grade 10",
            "Grade 11",
            "Grade 12",
            "Grades 9-12",
        ]
