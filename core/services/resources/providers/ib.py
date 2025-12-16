"""
International Baccalaureate Resource Provider.

Discovers educational resources for IB programmes:
PYP, MYP, DP, and CP.
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


@register_resource_provider("IB_MYP")
class IBMYPResourceProvider(BaseResourceProvider):
    """
    Resource provider for IB Middle Years Programme.

    SEARCH STRATEGY:
    ================
    1. IB Store (Official Publications)
       - URL: https://www.ibo.org/programmes/middle-years-programme/
       - Official IB guides, teacher support materials
       - Requires IB World School access for some materials

    2. IB Resource Centre (My IB)
       - URL: https://resources.ibo.org/
       - Curriculum documents, sample assessments
       - Requires school subscription

    3. Publisher Partnerships
       - Oxford University Press IB resources
       - Cambridge University Press (for some subjects)
       - Hodder Education IB series

    NOTE: Many IB resources are behind paywalls or require
    IB World School credentials.

    IMPLEMENTATION:
    ==============
    - Returns curated official IB resources
    - Searches Google Books for IB MYP textbooks
    - Adds major publisher resources
    """

    SEARCH_STRATEGY = """
    1. Check IB official publications and store
    2. Query IB Resource Centre (requires credentials)
    3. Search publisher IB catalogues (OUP, Cambridge, Hodder)
    4. Check Follett Titlewave IB section
    """

    SOURCE_URLS = [
        "https://www.ibo.org/programmes/middle-years-programme/",
        "https://resources.ibo.org/",
        "https://global.oup.com/education/secondary/ib/",
        "https://www.hoddereducation.com/subjects/international-baccalaureate",
    ]

    @property
    def authority_code(self) -> str:
        return "IB"

    @property
    def program_code(self) -> str:
        return "IB_MYP"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for IB MYP.

        Combines:
        - Curated official IB resources
        - Google Books search for IB textbooks
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

        # 2. Add IB official resources
        ib_resources = [
            ResourceData(
                title="IB Middle Years Programme Guide",
                source_url="https://www.ibo.org/programmes/middle-years-programme/",
                media_type="guide",
                platform="ibo",
                publisher="International Baccalaureate",
                description="Official MYP curriculum framework and subject guides",
                is_official=True,
                endorsement_notes="Official IB publication",
            ),
            ResourceData(
                title="IB Resource Centre (My IB)",
                source_url="https://resources.ibo.org/",
                media_type="curriculum",
                platform="ibo",
                publisher="International Baccalaureate",
                description="IB curriculum documents, sample assessments (requires school access)",
                is_official=True,
                endorsement_notes="Official IB resource platform",
            ),
        ]
        resources.extend(ib_resources)

        # 3. Search Google Books for IB MYP textbooks
        search_term = f"IB MYP {subject} textbook"
        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["ib", "myp", "international baccalaureate"]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 4. Add major publisher resources
        publisher_resources = [
            ResourceData(
                title=f"Oxford IB MYP {subject}",
                source_url="https://global.oup.com/education/secondary/ib/",
                media_type="book",
                platform="oup",
                publisher="Oxford University Press",
                description=f"IB MYP {subject} textbook and resources",
                is_official=False,
                endorsement_notes="IB-endorsed publisher",
            ),
            ResourceData(
                title=f"Hodder Education IB MYP {subject}",
                source_url="https://www.hoddereducation.com/subjects/international-baccalaureate",
                media_type="book",
                platform="hodder",
                publisher="Hodder Education",
                description=f"IB MYP {subject} course companion",
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
            "Language and Literature",
            "Language Acquisition",
            "Individuals and Societies",
            "Sciences",
            "Mathematics",
            "Arts",
            "Physical and Health Education",
            "Design",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return [
            "MYP Year 1",
            "MYP Year 2",
            "MYP Year 3",
            "MYP Year 4",
            "MYP Year 5",
        ]


@register_resource_provider("IB_DP")
class IBDPResourceProvider(BaseResourceProvider):
    """
    Resource provider for IB Diploma Programme.

    SEARCH STRATEGY:
    ================
    Same sources as MYP plus:
    - Subject-specific study guides
    - Past paper resources (questionbank)
    - Extended Essay resources

    IMPLEMENTATION:
    ==============
    - Returns curated official IB resources
    - Searches Google Books for IB DP textbooks
    - Adds major publisher resources
    """

    SEARCH_STRATEGY = """
    1. Check IB official publications and store
    2. Query IB Resource Centre and Questionbank
    3. Search publisher DP catalogues
    4. Check subject-specific study guide publishers
    """

    SOURCE_URLS = [
        "https://www.ibo.org/programmes/diploma-programme/",
        "https://resources.ibo.org/",
        "https://global.oup.com/education/secondary/ib/",
        "https://www.pearson.com/en-gb/schools/secondary/international-baccalaureate.html",
    ]

    @property
    def authority_code(self) -> str:
        return "IB"

    @property
    def program_code(self) -> str:
        return "IB_DP"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for IB Diploma Programme.

        Combines:
        - Curated official IB resources
        - Google Books search for IB DP textbooks
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

        # 2. Add IB DP official resources
        ib_resources = [
            ResourceData(
                title="IB Diploma Programme Guide",
                source_url="https://www.ibo.org/programmes/diploma-programme/",
                media_type="guide",
                platform="ibo",
                publisher="International Baccalaureate",
                description="Official DP curriculum framework and assessment information",
                is_official=True,
                endorsement_notes="Official IB publication",
            ),
            ResourceData(
                title="IB Questionbank",
                source_url="https://resources.ibo.org/",
                media_type="practice_tests",
                platform="ibo",
                publisher="International Baccalaureate",
                description="Official IB past papers and exam questions (requires school access)",
                is_official=True,
                endorsement_notes="Official IB exam preparation",
            ),
        ]
        resources.extend(ib_resources)

        # 3. Search Google Books for IB DP textbooks
        # Determine SL/HL from grade level
        level = "HL" if "HL" in grade_level else "SL" if "SL" in grade_level else ""
        search_term = f"IB Diploma {subject} {level} textbook".strip()

        try:
            book_results = search_google_books(search_term, max_results=5)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if any(term in title_lower for term in ["ib", "diploma", "international baccalaureate"]):
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 4. Add major publisher resources
        publisher_resources = [
            ResourceData(
                title=f"Oxford IB Study Guide: {subject}",
                source_url="https://global.oup.com/education/secondary/ib/",
                media_type="book",
                platform="oup",
                publisher="Oxford University Press",
                description=f"IB DP {subject} study guide and course companion",
                is_official=False,
                endorsement_notes="IB-endorsed publisher",
            ),
            ResourceData(
                title=f"Pearson Baccalaureate: {subject}",
                source_url="https://www.pearson.com/en-gb/schools/secondary/international-baccalaureate.html",
                media_type="book",
                platform="pearson",
                publisher="Pearson Education",
                description=f"IB DP {subject} textbook",
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
            "Studies in Language and Literature",
            "Language Acquisition",
            "Individuals and Societies",
            "Sciences",
            "Mathematics",
            "The Arts",
            "Theory of Knowledge",
            "Extended Essay",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["DP Year 1", "DP Year 2", "SL", "HL"]
