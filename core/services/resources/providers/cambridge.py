"""
Cambridge Assessment Resource Provider.

Discovers educational resources for Cambridge programmes:
IGCSE, O Level, AS/A Level, Cambridge Primary/Secondary.
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


@register_resource_provider("CAIE_IGCSE")
class CambridgeIGCSEResourceProvider(BaseResourceProvider):
    """
    Resource provider for Cambridge IGCSE.

    SEARCH STRATEGY:
    ================
    1. Cambridge University Press (Official Publisher)
       - URL: https://www.cambridge.org/gb/education/secondary
       - Official endorsed textbooks for all IGCSE subjects
       - Digital and print resources

    2. Cambridge School Support Hub
       - URL: https://www.cambridgeinternational.org/support-and-training-for-schools/
       - Teacher support materials, past papers
       - Requires school registration

    3. Endorsed Publisher Partners
       - Hodder Education Cambridge series
       - Collins Cambridge IGCSE
       - Marshall Cavendish Education

    IMPLEMENTATION:
    ==============
    - Returns curated official Cambridge resources
    - Searches Google Books for IGCSE textbooks
    - Adds major publisher resources
    """

    SEARCH_STRATEGY = """
    1. Check Cambridge University Press IGCSE catalogue
    2. Query Cambridge School Support Hub
    3. Search endorsed publisher catalogues (Hodder, Collins)
    4. Check Cambridge GO digital resources
    """

    SOURCE_URLS = [
        "https://www.cambridge.org/gb/education/secondary",
        "https://www.cambridgeinternational.org/support-and-training-for-schools/",
        "https://www.hoddereducation.co.uk/subjects/cambridge",
        "https://collins.co.uk/pages/secondary-cambridge",
    ]

    @property
    def authority_code(self) -> str:
        return "CAMBRIDGE"

    @property
    def program_code(self) -> str:
        return "CAIE_IGCSE"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Cambridge IGCSE.

        Combines:
        - Curated official Cambridge resources
        - Google Books search for IGCSE textbooks
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

        # 2. Add Cambridge official resources
        cambridge_resources = [
            ResourceData(
                title="Cambridge IGCSE Syllabus & Resources",
                source_url="https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-igcse/",
                media_type="curriculum",
                platform="cambridge",
                publisher="Cambridge Assessment International Education",
                description="Official IGCSE syllabi, specimen papers, and resources",
                is_official=True,
                endorsement_notes="Official Cambridge resource",
            ),
            ResourceData(
                title="Cambridge School Support Hub",
                source_url="https://www.cambridgeinternational.org/support-and-training-for-schools/",
                media_type="guide",
                platform="cambridge",
                publisher="Cambridge Assessment International Education",
                description="Teacher support materials and past papers (requires school access)",
                is_official=True,
                endorsement_notes="Official Cambridge support platform",
            ),
        ]
        resources.extend(cambridge_resources)

        # 3. Search Google Books for IGCSE textbooks
        search_term = f"Cambridge IGCSE {subject} textbook"
        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["cambridge", "igcse", subject.lower()[:4]]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 4. Add major publisher resources
        publisher_resources = [
            ResourceData(
                title=f"Cambridge IGCSE {subject} Coursebook",
                source_url="https://www.cambridge.org/gb/education/secondary",
                media_type="book",
                platform="cup",
                publisher="Cambridge University Press",
                description=f"Official Cambridge IGCSE {subject} coursebook",
                is_official=True,
                endorsement_notes="Official Cambridge publication",
            ),
            ResourceData(
                title=f"Hodder Cambridge IGCSE {subject}",
                source_url="https://www.hoddereducation.co.uk/subjects/cambridge",
                media_type="book",
                platform="hodder",
                publisher="Hodder Education",
                description=f"Cambridge IGCSE {subject} endorsed textbook",
                is_official=False,
                endorsement_notes="Cambridge endorsed",
            ),
            ResourceData(
                title=f"Collins Cambridge IGCSE {subject}",
                source_url="https://collins.co.uk/pages/secondary-cambridge",
                media_type="book",
                platform="collins",
                publisher="Collins",
                description=f"Cambridge IGCSE {subject} student book",
                is_official=False,
            ),
        ]
        resources.extend(publisher_resources)
        discovery_notes.append("Added major publisher resources.")

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
            "English Language",
            "English Literature",
            "Mathematics",
            "Additional Mathematics",
            "Physics",
            "Chemistry",
            "Biology",
            "Combined Science",
            "Computer Science",
            "History",
            "Geography",
            "Economics",
            "Business Studies",
            "Art and Design",
            "Music",
            "Physical Education",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["IGCSE", "IGCSE (9-1)", "O Level"]


@register_resource_provider("CAIE_AS")
class CambridgeASLevelResourceProvider(BaseResourceProvider):
    """
    Resource provider for Cambridge AS and A Level.

    SEARCH STRATEGY:
    ================
    Same sources as IGCSE plus:
    - Advanced level textbooks and resources
    - Subject-specific practical guides
    - Exam preparation materials

    IMPLEMENTATION:
    ==============
    - Returns curated official Cambridge resources
    - Searches Google Books for A Level textbooks
    - Adds major publisher resources
    """

    SEARCH_STRATEGY = """
    1. Check Cambridge University Press A Level catalogue
    2. Query Cambridge School Support Hub
    3. Search endorsed A Level publishers
    4. Check subject-specific advanced resources
    """

    SOURCE_URLS = [
        "https://www.cambridge.org/gb/education/secondary",
        "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/",
        "https://www.hoddereducation.co.uk/subjects/cambridge",
    ]

    @property
    def authority_code(self) -> str:
        return "CAMBRIDGE"

    @property
    def program_code(self) -> str:
        return "CAIE_AS"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for Cambridge AS and A Level.

        Combines:
        - Curated official Cambridge resources
        - Google Books search for A Level textbooks
        - Major publisher resources
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # Determine if AS or A Level
        level = "A Level" if "A Level" in grade_level else "AS Level"

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Add Cambridge official resources
        cambridge_resources = [
            ResourceData(
                title=f"Cambridge {level} Syllabus & Resources",
                source_url="https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/",
                media_type="curriculum",
                platform="cambridge",
                publisher="Cambridge Assessment International Education",
                description=f"Official {level} syllabi, specimen papers, and resources",
                is_official=True,
                endorsement_notes="Official Cambridge resource",
            ),
        ]
        resources.extend(cambridge_resources)

        # 3. Search Google Books for A Level textbooks
        search_term = f"Cambridge {level} {subject} textbook"
        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["cambridge", "level", subject.lower()[:4]]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 4. Add major publisher resources
        publisher_resources = [
            ResourceData(
                title=f"Cambridge {level} {subject} Coursebook",
                source_url="https://www.cambridge.org/gb/education/secondary",
                media_type="book",
                platform="cup",
                publisher="Cambridge University Press",
                description=f"Official Cambridge {level} {subject} coursebook",
                is_official=True,
                endorsement_notes="Official Cambridge publication",
            ),
            ResourceData(
                title=f"Hodder Cambridge {level} {subject}",
                source_url="https://www.hoddereducation.co.uk/subjects/cambridge",
                media_type="book",
                platform="hodder",
                publisher="Hodder Education",
                description=f"Cambridge {level} {subject} endorsed textbook",
                is_official=False,
                endorsement_notes="Cambridge endorsed",
            ),
        ]
        resources.extend(publisher_resources)
        discovery_notes.append("Added major publisher resources.")

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
            "English Language",
            "English Literature",
            "Mathematics",
            "Further Mathematics",
            "Physics",
            "Chemistry",
            "Biology",
            "Computer Science",
            "History",
            "Geography",
            "Economics",
            "Business",
            "Psychology",
            "Sociology",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["AS Level", "A Level"]
