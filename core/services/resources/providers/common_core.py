"""
Common Core Resource Provider.

Discovers educational resources aligned to Common Core
State Standards (CCSS) for ELA and Mathematics.
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
    search_open_library,
    normalize_subject,
)

logger = logging.getLogger(__name__)


@register_resource_provider("CCSS_ELA")
class CommonCoreELAResourceProvider(BaseResourceProvider):
    """
    Resource provider for Common Core ELA standards.

    SEARCH STRATEGY:
    ================
    1. Achieve the Core
       - URL: https://achievethecore.org/
       - Free lessons and assessments aligned to CCSS
       - Created by Student Achievement Partners

    2. UnboundEd (formerly EngageNY)
       - URL: https://www.unbounded.org/
       - Complete curriculum modules aligned to CCSS
       - Free and openly licensed

    3. ReadWorks
       - URL: https://www.readworks.org/
       - Free reading passages and comprehension resources

    4. CommonLit
       - URL: https://www.commonlit.org/
       - Free reading resources and assessments

    IMPLEMENTATION:
    ==============
    - Returns curated official CCSS resources
    - Searches book APIs for aligned materials
    """

    SEARCH_STRATEGY = """
    1. Search Achieve the Core for aligned resources
    2. Check UnboundEd curriculum modules
    3. Search ReadWorks and CommonLit
    4. Check publisher CCSS alignment documents
    """

    SOURCE_URLS = [
        "https://achievethecore.org/",
        "https://www.unbounded.org/",
        "https://www.readworks.org/",
        "https://www.commonlit.org/",
        "http://www.corestandards.org/",
    ]

    @property
    def authority_code(self) -> str:
        return "CCSS"

    @property
    def program_code(self) -> str:
        return "CCSS_ELA"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Common Core ELA.

        Combines:
        - Curated official resources (EngageNY, Achieve the Core, etc.)
        - Book API searches for aligned textbooks
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for ELA resources
        search_term = f"Common Core ELA {grade_level} curriculum"
        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["common core", "ela", "reading", "language arts", "literacy"]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 3. Search Open Library for additional resources
        try:
            ol_results = search_open_library(f"Common Core English Language Arts {grade_level}", max_results=3)
            sources_checked.append("https://openlibrary.org/search.json")

            for book in ol_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["common core", "ela", "reading", "english"]):
                    resources.append(book)

            if ol_results:
                discovery_notes.append(f"Searched Open Library: found {len(ol_results)} results.")
        except Exception as e:
            logger.warning(f"Open Library search failed: {e}")

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
            "Reading: Literature",
            "Reading: Informational Text",
            "Writing",
            "Speaking and Listening",
            "Language",
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
            "Grades 9-10",
            "Grades 11-12",
        ]


@register_resource_provider("CCSS_MATH")
class CommonCoreMathResourceProvider(BaseResourceProvider):
    """
    Resource provider for Common Core Math standards.

    SEARCH STRATEGY:
    ================
    1. Illustrative Mathematics
       - URL: https://illustrativemathematics.org/
       - High-quality math curriculum aligned to CCSS
       - Free and openly licensed

    2. Khan Academy
       - URL: https://www.khanacademy.org/
       - Free video lessons and practice aligned to CCSS Math

    3. Achieve the Core
       - URL: https://achievethecore.org/
       - Math-specific resources and coherence maps

    4. Desmos
       - URL: https://www.desmos.com/
       - Interactive math tools and activities

    IMPLEMENTATION:
    ==============
    - Returns curated official resources
    - Searches book APIs for aligned materials
    """

    SEARCH_STRATEGY = """
    1. Check Illustrative Mathematics curriculum
    2. Search Khan Academy CCSS-aligned content
    3. Check Achieve the Core math resources
    4. Search Desmos activities
    """

    SOURCE_URLS = [
        "https://illustrativemathematics.org/",
        "https://www.khanacademy.org/",
        "https://achievethecore.org/",
        "https://www.desmos.com/",
    ]

    @property
    def authority_code(self) -> str:
        return "CCSS"

    @property
    def program_code(self) -> str:
        return "CCSS_MATH"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Common Core Math.

        Combines:
        - Curated official resources (Illustrative Math, Khan Academy)
        - Book API searches for aligned textbooks
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for math resources
        search_term = f"Common Core Math {grade_level} curriculum"
        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["common core", "math", "algebra", "geometry", "calculus"]):
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
            "Mathematics",
            "Counting and Cardinality",
            "Operations and Algebraic Thinking",
            "Number and Operations",
            "Geometry",
            "Measurement and Data",
            "Statistics and Probability",
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
            "High School",
        ]
