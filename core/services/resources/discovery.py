"""
Discovery Helper Utilities.

Provides utilities for fetching and parsing web content
to discover educational resources.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache

from .base import ResourceData

logger = logging.getLogger(__name__)

# Cache timeout for discovery results (1 hour)
DISCOVERY_CACHE_TIMEOUT = 3600


@dataclass
class FetchResult:
    """Result of fetching a URL."""
    url: str
    status_code: int
    content: str
    content_type: str
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status_code == 200 and not self.error

    @property
    def soup(self) -> Optional[BeautifulSoup]:
        if self.is_success and "html" in self.content_type:
            return BeautifulSoup(self.content, "html.parser")
        return None


def fetch_url(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
    use_cache: bool = True,
) -> FetchResult:
    """
    Fetch a URL with caching support.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        headers: Optional HTTP headers
        use_cache: Whether to use cache

    Returns:
        FetchResult with response data
    """
    cache_key = f"discovery:fetch:{hashlib.md5(url.encode()).hexdigest()}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {url}")
            return FetchResult(**cached)

    default_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SafeglossBot/1.0; +https://safegloss.com/bot)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if headers:
        default_headers.update(headers)

    try:
        response = requests.get(url, timeout=timeout, headers=default_headers)
        result = FetchResult(
            url=url,
            status_code=response.status_code,
            content=response.text,
            content_type=response.headers.get("Content-Type", ""),
        )
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        result = FetchResult(
            url=url,
            status_code=0,
            content="",
            content_type="",
            error=str(e),
        )

    if use_cache and result.is_success:
        cache.set(cache_key, {
            "url": result.url,
            "status_code": result.status_code,
            "content": result.content,
            "content_type": result.content_type,
            "error": result.error,
        }, DISCOVERY_CACHE_TIMEOUT)

    return result


def extract_isbn(text: str) -> tuple[str, str]:
    """
    Extract ISBN-10 and ISBN-13 from text.

    Returns:
        Tuple of (isbn_10, isbn_13)
    """
    isbn_13_match = re.search(r"(?:ISBN[:\s-]*)?(\d{13})", text)
    isbn_10_match = re.search(r"(?:ISBN[:\s-]*)?(\d{9}[\dXx])", text)

    isbn_13 = isbn_13_match.group(1) if isbn_13_match else ""
    isbn_10 = isbn_10_match.group(1) if isbn_10_match else ""

    return isbn_10, isbn_13


def normalize_subject(subject: str) -> str:
    """Normalize subject name for matching."""
    subject_lower = subject.lower().strip()

    # Common normalizations
    mappings = {
        "ela": "english language arts",
        "english": "english language arts",
        "reading": "english language arts",
        "math": "mathematics",
        "science": "science",
        "social studies": "history-social science",
        "history": "history-social science",
    }

    for key, value in mappings.items():
        if key in subject_lower:
            return value

    return subject_lower


def normalize_grade(grade: str) -> list[int]:
    """
    Convert grade level string to list of grade numbers.

    Examples:
        "Grade 6" -> [6]
        "Grades 6-8" -> [6, 7, 8]
        "K-2" -> [0, 1, 2]
        "High School" -> [9, 10, 11, 12]
    """
    grade_lower = grade.lower().strip()

    # Handle special cases
    if "kindergarten" in grade_lower or grade_lower == "k":
        return [0]
    if "high school" in grade_lower:
        return [9, 10, 11, 12]
    if "middle school" in grade_lower:
        return [6, 7, 8]
    if "elementary" in grade_lower:
        return [0, 1, 2, 3, 4, 5]

    # Extract numbers from grade string
    numbers = re.findall(r"\d+", grade_lower)
    if len(numbers) == 0:
        return []
    elif len(numbers) == 1:
        return [int(numbers[0])]
    else:
        # Range
        start, end = int(numbers[0]), int(numbers[1])
        return list(range(start, end + 1))


def grade_matches(grade_filter: str, resource_grades: str) -> bool:
    """
    Check if a resource's grade range matches a filter.

    Args:
        grade_filter: The filter grade (e.g., "Grade 6")
        resource_grades: The resource's grade range (e.g., "Grades 6-8")

    Returns:
        True if there's overlap
    """
    filter_grades = set(normalize_grade(grade_filter))
    resource_grade_set = set(normalize_grade(resource_grades))

    return bool(filter_grades & resource_grade_set)


def search_google_books(
    query: str,
    max_results: int = 10,
) -> list[ResourceData]:
    """
    Search Google Books API for educational resources.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of ResourceData objects
    """
    api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}"

    result = fetch_url(api_url)
    if not result.is_success:
        logger.warning(f"Google Books search failed: {result.error}")
        return []

    try:
        data = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Google Books response")
        return []

    resources = []
    for item in data.get("items", []):
        volume_info = item.get("volumeInfo", {})

        # Extract ISBNs
        isbn_10 = ""
        isbn_13 = ""
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_10":
                isbn_10 = identifier.get("identifier", "")
            elif identifier.get("type") == "ISBN_13":
                isbn_13 = identifier.get("identifier", "")

        # Get thumbnail
        image_links = volume_info.get("imageLinks", {})
        cover_url = image_links.get("thumbnail", image_links.get("smallThumbnail", ""))

        # Build resource
        resource = ResourceData(
            title=volume_info.get("title", ""),
            source_url=volume_info.get("infoLink", ""),
            media_type="book",
            platform="google_books",
            author=", ".join(volume_info.get("authors", [])),
            publisher=volume_info.get("publisher", ""),
            description=volume_info.get("description", "")[:500] if volume_info.get("description") else "",
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            cover_image_url=cover_url.replace("http://", "https://") if cover_url else "",
            is_official=False,
        )

        if resource.title:
            resources.append(resource)

    return resources


def search_open_library(
    query: str,
    max_results: int = 10,
) -> list[ResourceData]:
    """
    Search Open Library for educational resources.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of ResourceData objects
    """
    api_url = f"https://openlibrary.org/search.json?q={query}&limit={max_results}"

    result = fetch_url(api_url)
    if not result.is_success:
        logger.warning(f"Open Library search failed: {result.error}")
        return []

    try:
        data = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Open Library response")
        return []

    resources = []
    for doc in data.get("docs", []):
        # Get cover
        cover_id = doc.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""

        # Get ISBNs
        isbns = doc.get("isbn", [])
        isbn_10 = ""
        isbn_13 = ""
        for isbn in isbns:
            if len(isbn) == 10:
                isbn_10 = isbn
            elif len(isbn) == 13:
                isbn_13 = isbn

        resource = ResourceData(
            title=doc.get("title", ""),
            source_url=f"https://openlibrary.org{doc.get('key', '')}",
            media_type="book",
            platform="open_library",
            author=", ".join(doc.get("author_name", [])[:3]),
            publisher=", ".join(doc.get("publisher", [])[:1]) if doc.get("publisher") else "",
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            cover_image_url=cover_url,
            is_official=False,
        )

        if resource.title:
            resources.append(resource)

    return resources


# Well-known educational resources by subject/authority
CURATED_RESOURCES = {
    "CCSS_ELA": {
        "default": [
            ResourceData(
                title="EngageNY ELA Curriculum",
                source_url="https://www.engageny.org/english-language-arts",
                media_type="curriculum",
                platform="engageny",
                publisher="New York State Education Department",
                description="Free, open-source ELA curriculum aligned to Common Core",
                is_official=True,
                endorsement_notes="Official NY State curriculum, CCSS-aligned",
            ),
            ResourceData(
                title="Achieve the Core - ELA/Literacy",
                source_url="https://achievethecore.org/category/411/ela-literacy",
                media_type="guide",
                platform="achieve_the_core",
                publisher="Student Achievement Partners",
                description="Free resources for implementing Common Core ELA standards",
                is_official=True,
                endorsement_notes="Created by lead writers of Common Core",
            ),
            ResourceData(
                title="ReadWorks",
                source_url="https://www.readworks.org/",
                media_type="curriculum",
                platform="readworks",
                publisher="ReadWorks, Inc.",
                description="Free reading comprehension resources for K-12",
                is_official=False,
            ),
            ResourceData(
                title="CommonLit",
                source_url="https://www.commonlit.org/",
                media_type="curriculum",
                platform="commonlit",
                publisher="CommonLit, Inc.",
                description="Free reading passages and literacy resources for grades 3-12",
                is_official=False,
            ),
        ],
    },
    "CCSS_MATH": {
        "default": [
            ResourceData(
                title="EngageNY Mathematics",
                source_url="https://www.engageny.org/mathematics",
                media_type="curriculum",
                platform="engageny",
                publisher="New York State Education Department",
                description="Free, open-source math curriculum aligned to Common Core",
                is_official=True,
                endorsement_notes="Official NY State curriculum, CCSS-aligned",
            ),
            ResourceData(
                title="Achieve the Core - Mathematics",
                source_url="https://achievethecore.org/category/412/mathematics",
                media_type="guide",
                platform="achieve_the_core",
                publisher="Student Achievement Partners",
                description="Free resources for implementing Common Core Math standards",
                is_official=True,
                endorsement_notes="Created by lead writers of Common Core",
            ),
            ResourceData(
                title="Illustrative Mathematics",
                source_url="https://illustrativemathematics.org/",
                media_type="curriculum",
                platform="illustrative_math",
                publisher="Illustrative Mathematics",
                description="Problem-based K-12 mathematics curriculum",
                is_official=True,
                endorsement_notes="Created by lead CCSS writer William McCallum",
            ),
            ResourceData(
                title="Khan Academy - Math",
                source_url="https://www.khanacademy.org/math",
                media_type="video_series",
                platform="khan_academy",
                publisher="Khan Academy",
                description="Free online math courses and practice",
                is_official=False,
            ),
        ],
    },
    "CB_AP": {
        "default": [
            ResourceData(
                title="AP Classroom",
                source_url="https://apcentral.collegeboard.org/instructional-resources/ap-classroom",
                media_type="course",
                platform="college_board",
                publisher="College Board",
                description="Official AP course materials and resources",
                is_official=True,
                endorsement_notes="Official College Board resource",
            ),
            ResourceData(
                title="AP Daily Videos",
                source_url="https://apcentral.collegeboard.org/courses/ap-daily",
                media_type="video_series",
                platform="college_board",
                publisher="College Board",
                description="Short, searchable video lessons for each AP course",
                is_official=True,
                endorsement_notes="Official College Board resource",
            ),
        ],
    },
    "CB_SAT": {
        "default": [
            ResourceData(
                title="Khan Academy Official SAT Practice",
                source_url="https://www.khanacademy.org/sat",
                media_type="practice_tests",
                platform="khan_academy",
                publisher="Khan Academy / College Board",
                description="Free, personalized SAT practice from College Board",
                is_official=True,
                endorsement_notes="Official College Board partnership",
            ),
            ResourceData(
                title="College Board SAT Practice",
                source_url="https://satsuite.collegeboard.org/sat/practice-preparation",
                media_type="practice_tests",
                platform="college_board",
                publisher="College Board",
                description="Official SAT practice tests and questions",
                is_official=True,
                endorsement_notes="Official College Board resource",
            ),
            ResourceData(
                title="Bluebook - Digital SAT Practice",
                source_url="https://bluebook.collegeboard.org/",
                media_type="practice_tests",
                platform="college_board",
                publisher="College Board",
                description="Official digital SAT practice app",
                is_official=True,
                endorsement_notes="Official College Board digital practice",
            ),
        ],
    },
    "ACT_PREP": {
        "default": [
            ResourceData(
                title="ACT Academy",
                source_url="https://academy.act.org/",
                media_type="practice_tests",
                platform="act",
                publisher="ACT, Inc.",
                description="Free ACT test prep and practice",
                is_official=True,
                endorsement_notes="Official ACT resource",
            ),
            ResourceData(
                title="The Official ACT Prep Guide",
                source_url="https://www.act.org/content/act/en/products-and-services/the-act/test-preparation.html",
                media_type="book",
                platform="print",
                publisher="ACT, Inc.",
                description="Official ACT preparation book with practice tests",
                is_official=True,
                endorsement_notes="Official ACT publication",
            ),
        ],
    },
    "STATE_TX": {
        "default": [
            ResourceData(
                title="TEA Instructional Materials",
                source_url="https://tea.texas.gov/academics/instructional-materials",
                media_type="guide",
                platform="tea",
                publisher="Texas Education Agency",
                description="State-adopted instructional materials for Texas",
                is_official=True,
                endorsement_notes="Official TEA adopted materials",
            ),
            ResourceData(
                title="Texas Resource Review",
                source_url="https://texasresourcereview.org/",
                media_type="guide",
                platform="texas_resource_review",
                publisher="Texas Education Agency",
                description="TEKS-aligned instructional materials reviews",
                is_official=True,
                endorsement_notes="Official TEA alignment reviews",
            ),
        ],
    },
}


def get_curated_resources(program_code: str, subject: str = None) -> list[ResourceData]:
    """
    Get curated resources for a program.

    Args:
        program_code: The program code (e.g., "CCSS_ELA")
        subject: Optional subject filter

    Returns:
        List of curated ResourceData objects
    """
    program_resources = CURATED_RESOURCES.get(program_code, {})

    # Try subject-specific first, fall back to default
    if subject:
        subject_key = normalize_subject(subject)
        resources = program_resources.get(subject_key, [])
        if resources:
            return resources

    return program_resources.get("default", [])
