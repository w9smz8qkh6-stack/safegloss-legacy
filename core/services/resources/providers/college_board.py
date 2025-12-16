"""
College Board Resource Provider.

Discovers educational resources for College Board programmes:
AP (Advanced Placement), SAT, PSAT.
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


@register_resource_provider("CB_AP")
class CollegeBoardAPResourceProvider(BaseResourceProvider):
    """
    Resource provider for AP (Advanced Placement) courses.

    SEARCH STRATEGY:
    ================
    1. College Board AP Central
       - URL: https://apcentral.collegeboard.org/
       - Official course descriptions, exam info
       - AP Classroom resources (requires access)

    2. College Board Store
       - URL: https://store.collegeboard.org/
       - Official AP prep books and materials

    3. AP Classroom
       - URL: https://apclassroom.collegeboard.org/
       - Practice questions, progress checks
       - Requires AP teacher/student account

    4. Publisher AP Resources
       - Barron's AP Prep
       - Princeton Review AP
       - Kaplan AP
       - REA AP Test Prep

    5. Khan Academy AP Courses
       - URL: https://www.khanacademy.org/
       - Free AP course preparation

    IMPLEMENTATION:
    ==============
    - Returns curated official College Board resources
    - Searches Google Books for AP prep books by subject
    """

    SEARCH_STRATEGY = """
    1. Check College Board AP Central for official resources
    2. Query College Board Store for prep materials
    3. Search publisher AP prep catalogues (Barron's, Princeton Review)
    4. Check Khan Academy AP content
    """

    SOURCE_URLS = [
        "https://apcentral.collegeboard.org/",
        "https://store.collegeboard.org/",
        "https://apclassroom.collegeboard.org/",
        "https://www.khanacademy.org/",
        "https://www.barronseduc.com/",
        "https://www.princetonreview.com/college/ap-test-prep",
    ]

    @property
    def authority_code(self) -> str:
        return "COLLEGE_BOARD"

    @property
    def program_code(self) -> str:
        return "CB_AP"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for AP courses.

        Combines:
        - Curated official College Board resources
        - Google Books search for AP prep books
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for AP prep books
        # Clean up subject for search (remove "AP " prefix if present)
        clean_subject = subject.replace("AP ", "") if subject.startswith("AP ") else subject
        search_term = f"AP {clean_subject} prep book"

        try:
            book_results = search_google_books(search_term, max_results=8)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                # Filter to AP prep books
                if "ap" in title_lower or clean_subject.lower()[:5] in title_lower:
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 3. Add well-known AP prep publishers
        ap_publishers = [
            ResourceData(
                title=f"Barron's AP {clean_subject}",
                source_url=f"https://www.barronseduc.com/search?q=AP+{clean_subject.replace(' ', '+')}",
                media_type="book",
                platform="barrons",
                publisher="Barron's Educational Series",
                description=f"Comprehensive AP {clean_subject} review and practice tests",
                is_official=False,
            ),
            ResourceData(
                title=f"Princeton Review AP {clean_subject}",
                source_url=f"https://www.princetonreview.com/college/ap-test-prep",
                media_type="book",
                platform="princeton_review",
                publisher="The Princeton Review",
                description=f"AP {clean_subject} prep with strategies and practice",
                is_official=False,
            ),
        ]
        resources.extend(ap_publishers)
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
            # Arts
            "AP Art History",
            "AP Music Theory",
            "AP 2-D Art and Design",
            "AP 3-D Art and Design",
            "AP Drawing",
            # English
            "AP English Language and Composition",
            "AP English Literature and Composition",
            # History & Social Science
            "AP Comparative Government and Politics",
            "AP European History",
            "AP Human Geography",
            "AP Macroeconomics",
            "AP Microeconomics",
            "AP Psychology",
            "AP United States Government and Politics",
            "AP United States History",
            "AP World History: Modern",
            # Math & Computer Science
            "AP Calculus AB",
            "AP Calculus BC",
            "AP Computer Science A",
            "AP Computer Science Principles",
            "AP Statistics",
            "AP Precalculus",
            # Sciences
            "AP Biology",
            "AP Chemistry",
            "AP Environmental Science",
            "AP Physics 1",
            "AP Physics 2",
            "AP Physics C: Electricity and Magnetism",
            "AP Physics C: Mechanics",
            # World Languages
            "AP Chinese Language and Culture",
            "AP French Language and Culture",
            "AP German Language and Culture",
            "AP Italian Language and Culture",
            "AP Japanese Language and Culture",
            "AP Latin",
            "AP Spanish Language and Culture",
            "AP Spanish Literature and Culture",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["AP", "Grades 10-12"]


@register_resource_provider("CB_SAT")
class CollegeBoardSATResourceProvider(BaseResourceProvider):
    """
    Resource provider for SAT preparation.

    SEARCH STRATEGY:
    ================
    1. College Board Official SAT Practice
       - URL: https://www.collegeboard.org/sat
       - Free practice on Khan Academy partnership

    2. Khan Academy SAT Prep
       - URL: https://www.khanacademy.org/sat
       - Official free prep partner

    3. Publisher SAT Prep
       - College Board's Official SAT Study Guide
       - Barron's, Princeton Review, Kaplan

    IMPLEMENTATION:
    ==============
    - Returns curated official resources (Khan Academy partnership, Bluebook)
    - Searches Google Books for SAT prep books
    """

    SEARCH_STRATEGY = """
    1. Check College Board official SAT practice
    2. Khan Academy SAT prep (official partner)
    3. Search publisher SAT prep catalogues
    """

    SOURCE_URLS = [
        "https://www.collegeboard.org/sat",
        "https://www.khanacademy.org/sat",
        "https://store.collegeboard.org/",
    ]

    @property
    def authority_code(self) -> str:
        return "COLLEGE_BOARD"

    @property
    def program_code(self) -> str:
        return "CB_SAT"

    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for SAT preparation.

        Combines:
        - Curated official resources (Khan Academy, Bluebook)
        - Google Books search for SAT prep books
        """
        resources = []
        sources_checked = list(self.SOURCE_URLS)
        discovery_notes = []

        # 1. Get curated resources (includes Khan Academy official partnership)
        curated = get_curated_resources(self.program_code, subject)
        resources.extend(curated)
        if curated:
            discovery_notes.append(f"Found {len(curated)} curated official resources.")

        # 2. Search Google Books for SAT prep
        search_term = f"SAT prep {subject}" if subject else "SAT prep book"
        try:
            book_results = search_google_books(search_term, max_results=8)
            sources_checked.append("https://www.googleapis.com/books/v1/volumes")

            for book in book_results:
                title_lower = book.title.lower()
                if "sat" in title_lower:
                    resources.append(book)

            if book_results:
                discovery_notes.append(f"Searched Google Books: found {len(book_results)} results.")
        except Exception as e:
            logger.warning(f"Google Books search failed: {e}")
            discovery_notes.append(f"Google Books search failed: {e}")

        # 3. Add official College Board guide
        resources.append(ResourceData(
            title="The Official SAT Study Guide",
            source_url="https://store.collegeboard.org/",
            media_type="book",
            platform="college_board",
            publisher="College Board",
            description="Official SAT practice tests and strategies from the test maker",
            is_official=True,
            endorsement_notes="Official College Board publication",
        ))

        # 4. Add well-known SAT prep publishers
        sat_publishers = [
            ResourceData(
                title="Barron's SAT Study Guide",
                source_url="https://www.barronseduc.com/search?q=SAT",
                media_type="book",
                platform="barrons",
                publisher="Barron's Educational Series",
                description="Comprehensive SAT review with practice tests",
                is_official=False,
            ),
            ResourceData(
                title="Princeton Review SAT Premium Prep",
                source_url="https://www.princetonreview.com/college/sat-test-prep",
                media_type="book",
                platform="princeton_review",
                publisher="The Princeton Review",
                description="SAT prep with strategies, practice tests, and online resources",
                is_official=False,
            ),
        ]
        resources.extend(sat_publishers)
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
            "SAT Reading",
            "SAT Writing and Language",
            "SAT Math",
            "SAT Essay (discontinued)",
        ]

    def list_available_grades(self, subject: str = None) -> list[str]:
        return ["SAT", "PSAT/NMSQT", "PSAT 10", "PSAT 8/9"]
