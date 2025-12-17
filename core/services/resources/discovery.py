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


def enrich_with_google_books(resource: ResourceData) -> ResourceData:
    """
    Enrich a resource with metadata from Google Books API.

    This function is for METADATA ENRICHMENT ONLY - not for discovering
    new resources. Use it to add ISBNs, covers, and descriptions to
    resources that were discovered through authoritative sources.

    Args:
        resource: ResourceData to enrich (must have title and optionally author/isbn)

    Returns:
        Enriched ResourceData (same object, modified in place)
    """
    # Build search query from available identifiers
    if resource.isbn_13:
        query = f"isbn:{resource.isbn_13}"
    elif resource.isbn_10:
        query = f"isbn:{resource.isbn_10}"
    else:
        # Search by title and author
        query = resource.title
        if resource.author:
            query += f" {resource.author.split(',')[0]}"  # First author

    api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"

    result = fetch_url(api_url)
    if not result.is_success:
        logger.warning(f"Google Books enrichment failed: {result.error}")
        return resource

    try:
        data = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Google Books response")
        return resource

    items = data.get("items", [])
    if not items:
        return resource

    volume_info = items[0].get("volumeInfo", {})

    # Enrich ISBNs if not present
    if not resource.isbn_10 or not resource.isbn_13:
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_10" and not resource.isbn_10:
                resource.isbn_10 = identifier.get("identifier", "")
            elif identifier.get("type") == "ISBN_13" and not resource.isbn_13:
                resource.isbn_13 = identifier.get("identifier", "")

    # Enrich cover image if not present
    if not resource.cover_image_url:
        image_links = volume_info.get("imageLinks", {})
        cover_url = image_links.get("thumbnail", image_links.get("smallThumbnail", ""))
        if cover_url:
            resource.cover_image_url = cover_url.replace("http://", "https://")

    # Enrich description if not present
    if not resource.description:
        desc = volume_info.get("description", "")
        if desc:
            resource.description = desc[:500]

    # Enrich publisher if not present
    if not resource.publisher:
        resource.publisher = volume_info.get("publisher", "")

    # Store metadata and publisher URL/info link
    resource.metadata = resource.metadata or {}
    resource.metadata["google_books"] = volume_info
    info_link = volume_info.get("infoLink", "")
    if info_link and not resource.publisher_url:
        resource.publisher_url = info_link
    if info_link and not resource.source_url:
        resource.source_url = info_link

    return resource


def search_google_books(
    query: str,
    max_results: int = 10,
) -> list[ResourceData]:
    """
    Search Google Books API for educational resources.

    NOTE: This function should primarily be used for metadata enrichment
    or as a fallback. Official resources should be discovered from
    authority websites, not from Google Books.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of ResourceData objects (marked as commonly_used tier)
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

        # Build resource - NOTE: marked as commonly_used, not official
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
            recommendation_tier="commonly_used",  # NOT official - discovered via search
            publisher_url=volume_info.get("infoLink", ""),
            metadata={"google_books": volume_info},
            retrieved_from="google_books",
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

    NOTE: Like Google Books, this is primarily for metadata enrichment.
    Resources discovered here are marked as commonly_used.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of ResourceData objects (marked as commonly_used tier)
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
            platform="other",
            author=", ".join(doc.get("author_name", [])[:3]),
            publisher=", ".join(doc.get("publisher", [])[:1]) if doc.get("publisher") else "",
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            cover_image_url=cover_url,
            recommendation_tier="commonly_used",  # NOT official - discovered via search
        )

        if resource.title:
            resources.append(resource)

    return resources


# Well-known educational resources by subject/authority
# Uses recommendation_tier: "official", "recommended", "commonly_used"
CURATED_RESOURCES = {
    "CCSS_ELA": {
        "default": [
            ResourceData(
                title="EngageNY ELA Curriculum",
                source_url="https://www.engageny.org/english-language-arts",
                media_type="curriculum",
                platform="authority",
                publisher="New York State Education Department",
                description="Free, open-source ELA curriculum aligned to Common Core",
                recommendation_tier="official",
                endorsement_notes="Official NY State curriculum, CCSS-aligned",
                recommending_organization="New York State Education Department",
            ),
            ResourceData(
                title="Achieve the Core - ELA/Literacy",
                source_url="https://achievethecore.org/category/411/ela-literacy",
                media_type="guide",
                platform="authority",
                publisher="Student Achievement Partners",
                description="Free resources for implementing Common Core ELA standards",
                recommendation_tier="official",
                endorsement_notes="Created by lead writers of Common Core",
                recommending_organization="Student Achievement Partners",
            ),
            ResourceData(
                title="ReadWorks",
                source_url="https://www.readworks.org/",
                media_type="curriculum",
                platform="publisher",
                publisher="ReadWorks, Inc.",
                description="Free reading comprehension resources for K-12",
                recommendation_tier="recommended",
                recommending_organization="EdReports",
            ),
            ResourceData(
                title="CommonLit",
                source_url="https://www.commonlit.org/",
                media_type="curriculum",
                platform="publisher",
                publisher="CommonLit, Inc.",
                description="Free reading passages and literacy resources for grades 3-12",
                recommendation_tier="commonly_used",
            ),
        ],
    },
    "CCSS_MATH": {
        "default": [
            ResourceData(
                title="EngageNY Mathematics",
                source_url="https://www.engageny.org/mathematics",
                media_type="curriculum",
                platform="authority",
                publisher="New York State Education Department",
                description="Free, open-source math curriculum aligned to Common Core",
                recommendation_tier="official",
                endorsement_notes="Official NY State curriculum, CCSS-aligned",
                recommending_organization="New York State Education Department",
            ),
            ResourceData(
                title="Achieve the Core - Mathematics",
                source_url="https://achievethecore.org/category/412/mathematics",
                media_type="guide",
                platform="authority",
                publisher="Student Achievement Partners",
                description="Free resources for implementing Common Core Math standards",
                recommendation_tier="official",
                endorsement_notes="Created by lead writers of Common Core",
                recommending_organization="Student Achievement Partners",
            ),
            ResourceData(
                title="Illustrative Mathematics",
                source_url="https://illustrativemathematics.org/",
                media_type="curriculum",
                platform="publisher",
                publisher="Illustrative Mathematics",
                description="Problem-based K-12 mathematics curriculum",
                recommendation_tier="recommended",
                endorsement_notes="Created by lead CCSS writer William McCallum",
                recommending_organization="EdReports (Green Rating)",
            ),
            ResourceData(
                title="Khan Academy - Math",
                source_url="https://www.khanacademy.org/math",
                media_type="video_series",
                platform="khan_academy",
                publisher="Khan Academy",
                description="Free online math courses and practice",
                recommendation_tier="commonly_used",
            ),
        ],
    },
    "CB_AP": {
        "default": [
            ResourceData(
                title="AP Classroom",
                source_url="https://apcentral.collegeboard.org/instructional-resources/ap-classroom",
                media_type="course",
                platform="authority",
                publisher="College Board",
                description="Official AP course materials and resources",
                recommendation_tier="official",
                endorsement_notes="Official College Board resource",
                recommending_organization="College Board",
            ),
            ResourceData(
                title="AP Daily Videos",
                source_url="https://apcentral.collegeboard.org/courses/ap-daily",
                media_type="video_series",
                platform="authority",
                publisher="College Board",
                description="Short, searchable video lessons for each AP course",
                recommendation_tier="official",
                endorsement_notes="Official College Board resource",
                recommending_organization="College Board",
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
                recommendation_tier="official",
                endorsement_notes="Official College Board partnership",
                recommending_organization="College Board",
            ),
            ResourceData(
                title="College Board SAT Practice",
                source_url="https://satsuite.collegeboard.org/sat/practice-preparation",
                media_type="practice_tests",
                platform="authority",
                publisher="College Board",
                description="Official SAT practice tests and questions",
                recommendation_tier="official",
                endorsement_notes="Official College Board resource",
                recommending_organization="College Board",
            ),
            ResourceData(
                title="Bluebook - Digital SAT Practice",
                source_url="https://bluebook.collegeboard.org/",
                media_type="practice_tests",
                platform="authority",
                publisher="College Board",
                description="Official digital SAT practice app",
                recommendation_tier="official",
                endorsement_notes="Official College Board digital practice",
                recommending_organization="College Board",
            ),
        ],
    },
    "ACT_PREP": {
        "default": [
            ResourceData(
                title="ACT Academy",
                source_url="https://academy.act.org/",
                media_type="practice_tests",
                platform="authority",
                publisher="ACT, Inc.",
                description="Free ACT test prep and practice",
                recommendation_tier="official",
                endorsement_notes="Official ACT resource",
                recommending_organization="ACT, Inc.",
            ),
            ResourceData(
                title="The Official ACT Prep Guide",
                source_url="https://www.act.org/content/act/en/products-and-services/the-act/test-preparation.html",
                media_type="book",
                platform="print",
                publisher="ACT, Inc.",
                description="Official ACT preparation book with practice tests",
                recommendation_tier="official",
                endorsement_notes="Official ACT publication",
                recommending_organization="ACT, Inc.",
            ),
        ],
    },
    "STATE_TX": {
        "default": [
            ResourceData(
                title="TEA Instructional Materials",
                source_url="https://tea.texas.gov/academics/instructional-materials",
                media_type="guide",
                platform="authority",
                publisher="Texas Education Agency",
                description="State-adopted instructional materials for Texas",
                recommendation_tier="official",
                endorsement_notes="Official TEA adopted materials",
                recommending_organization="Texas Education Agency",
            ),
            ResourceData(
                title="Texas Resource Review",
                source_url="https://texasresourcereview.org/",
                media_type="guide",
                platform="authority",
                publisher="Texas Education Agency",
                description="TEKS-aligned instructional materials reviews",
                recommendation_tier="official",
                endorsement_notes="Official TEA alignment reviews",
                recommending_organization="Texas Education Agency",
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


# =============================================================================
# AI-Assisted Resource Discovery
# =============================================================================

@dataclass
class ExtractedResource:
    """A resource extracted from a web page by AI."""
    title: str
    url: str = ""
    author: str = ""
    publisher: str = ""
    description: str = ""
    media_type: str = "book"  # book, curriculum, guide, etc.
    isbn: str = ""
    confidence: float = 0.0  # 0-1 confidence score


def extract_resources_with_ai(
    page_content: str,
    page_url: str,
    subject: str = "",
    grade_level: str = "",
    context: str = "",
) -> list[ExtractedResource]:
    """
    Use AI to extract educational resources from web page content.

    This function uses an LLM to parse web pages (authority websites,
    district curriculum pages, etc.) and extract structured resource
    information.

    Args:
        page_content: HTML or text content of the page
        page_url: URL the content was fetched from
        subject: Subject area to focus on (optional)
        grade_level: Grade level to focus on (optional)
        context: Additional context (e.g., "Texas adopted textbooks")

    Returns:
        List of ExtractedResource objects
    """
    from django.conf import settings
    from openai import OpenAI

    # Check if API key is configured (prefer OpenRouter)
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not configured, skipping AI extraction")
        return []

    # Parse HTML to text if needed
    if "<html" in page_content.lower() or "<body" in page_content.lower():
        soup = BeautifulSoup(page_content, "html.parser")
        # Remove scripts and styles
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text_content = soup.get_text(separator="\n", strip=True)
    else:
        text_content = page_content

    # Truncate if too long (keep first 15000 chars)
    if len(text_content) > 15000:
        text_content = text_content[:15000] + "\n...[truncated]"

    # Build prompt
    prompt = f"""Analyze this web page and extract educational resources (textbooks, curricula, workbooks, guides, online courses, etc.).

Page URL: {page_url}
{f"Subject focus: {subject}" if subject else ""}
{f"Grade level focus: {grade_level}" if grade_level else ""}
{f"Context: {context}" if context else ""}

PAGE CONTENT:
{text_content}

For each educational resource found, extract:
- title: The full title of the resource
- url: Direct URL to the resource if available (leave empty if not found)
- author: Author name(s) if mentioned
- publisher: Publisher name if mentioned
- description: Brief description (1-2 sentences)
- media_type: One of: book, curriculum, guide, workbook, video_series, course, practice_tests, website
- isbn: ISBN if mentioned
- confidence: How confident you are this is a valid educational resource (0.0-1.0)

Return a JSON array of objects. Only include actual educational resources, not navigation links, advertisements, or general website content. If no resources are found, return an empty array [].

JSON:"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        response_text = response.choices[0].message.content.strip()

        # Try to extract JSON from response
        if response_text.startswith("["):
            json_str = response_text
        else:
            # Look for JSON array in response
            match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if match:
                json_str = match.group()
            else:
                logger.warning("No JSON array found in AI response")
                return []

        data = json.loads(json_str)

        resources = []
        for item in data:
            if not item.get("title"):
                continue

            resource = ExtractedResource(
                title=item.get("title", ""),
                url=item.get("url", ""),
                author=item.get("author", ""),
                publisher=item.get("publisher", ""),
                description=item.get("description", ""),
                media_type=item.get("media_type", "book"),
                isbn=item.get("isbn", ""),
                confidence=float(item.get("confidence", 0.5)),
            )
            resources.append(resource)

        logger.info(f"AI extracted {len(resources)} resources from {page_url}")
        return resources

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return []


def discover_from_authority_website(
    authority_url: str,
    authority_name: str,
    subject: str = "",
    grade_level: str = "",
) -> list[ResourceData]:
    """
    Discover official resources from a standards authority website.

    Fetches the authority's resource/materials page and uses AI to
    extract official resources.

    Args:
        authority_url: URL of the authority's resources page
        authority_name: Name of the authority (e.g., "Texas Education Agency")
        subject: Subject to focus on
        grade_level: Grade level to focus on

    Returns:
        List of ResourceData marked as "official" tier
    """
    result = fetch_url(authority_url)
    if not result.is_success:
        logger.warning(f"Failed to fetch authority page: {authority_url}")
        return []

    extracted = extract_resources_with_ai(
        page_content=result.content,
        page_url=authority_url,
        subject=subject,
        grade_level=grade_level,
        context=f"Official resources from {authority_name}",
    )

    resources = []
    for item in extracted:
        if item.confidence < 0.5:
            continue

        # Parse ISBN
        isbn_10, isbn_13 = "", ""
        if item.isbn:
            if len(item.isbn.replace("-", "")) == 13:
                isbn_13 = item.isbn.replace("-", "")
            elif len(item.isbn.replace("-", "")) == 10:
                isbn_10 = item.isbn.replace("-", "")

        resource = ResourceData(
            title=item.title,
            source_url=item.url or authority_url,
            media_type=item.media_type,
            platform="authority",
            author=item.author,
            publisher=item.publisher or authority_name,
            description=item.description,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            recommendation_tier="official",
            discovered_from_url=authority_url,
            recommending_organization=authority_name,
            endorsement_notes=f"Listed on official {authority_name} website",
        )
        resources.append(resource)

    return resources


def discover_from_district_website(
    district_url: str,
    district_name: str,
    subject: str = "",
    grade_level: str = "",
) -> list[ResourceData]:
    """
    Discover commonly used resources from a school district website.

    Fetches district curriculum pages and uses AI to extract
    resources that are commonly used.

    Args:
        district_url: URL of the district's curriculum page
        district_name: Name of the district (e.g., "Houston ISD")
        subject: Subject to focus on
        grade_level: Grade level to focus on

    Returns:
        List of ResourceData marked as "commonly_used" tier
    """
    result = fetch_url(district_url)
    if not result.is_success:
        logger.warning(f"Failed to fetch district page: {district_url}")
        return []

    extracted = extract_resources_with_ai(
        page_content=result.content,
        page_url=district_url,
        subject=subject,
        grade_level=grade_level,
        context=f"Curriculum resources used by {district_name}",
    )

    resources = []
    for item in extracted:
        if item.confidence < 0.4:  # Lower threshold for district discovery
            continue

        # Parse ISBN
        isbn_10, isbn_13 = "", ""
        if item.isbn:
            if len(item.isbn.replace("-", "")) == 13:
                isbn_13 = item.isbn.replace("-", "")
            elif len(item.isbn.replace("-", "")) == 10:
                isbn_10 = item.isbn.replace("-", "")

        resource = ResourceData(
            title=item.title,
            source_url=item.url or district_url,
            media_type=item.media_type,
            platform="district",
            author=item.author,
            publisher=item.publisher,
            description=item.description,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            recommendation_tier="commonly_used",
            discovered_from_url=district_url,
            recommending_organization=district_name,
            endorsement_notes=f"Used by {district_name}",
        )
        resources.append(resource)

    return resources


def discover_from_professional_org(
    org_url: str,
    org_name: str,
    subject: str = "",
    grade_level: str = "",
) -> list[ResourceData]:
    """
    Discover recommended resources from a professional organization.

    Fetches resource pages from organizations like NCTM, NCTE, etc.
    and uses AI to extract recommended resources.

    Args:
        org_url: URL of the organization's recommendations page
        org_name: Name of the organization (e.g., "NCTM")
        subject: Subject to focus on
        grade_level: Grade level to focus on

    Returns:
        List of ResourceData marked as "recommended" tier
    """
    result = fetch_url(org_url)
    if not result.is_success:
        logger.warning(f"Failed to fetch organization page: {org_url}")
        return []

    extracted = extract_resources_with_ai(
        page_content=result.content,
        page_url=org_url,
        subject=subject,
        grade_level=grade_level,
        context=f"Resources recommended by {org_name}",
    )

    resources = []
    for item in extracted:
        if item.confidence < 0.5:
            continue

        # Parse ISBN
        isbn_10, isbn_13 = "", ""
        if item.isbn:
            if len(item.isbn.replace("-", "")) == 13:
                isbn_13 = item.isbn.replace("-", "")
            elif len(item.isbn.replace("-", "")) == 10:
                isbn_10 = item.isbn.replace("-", "")

        resource = ResourceData(
            title=item.title,
            source_url=item.url or org_url,
            media_type=item.media_type,
            platform="publisher",
            author=item.author,
            publisher=item.publisher,
            description=item.description,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            recommendation_tier="recommended",
            discovered_from_url=org_url,
            recommending_organization=org_name,
            endorsement_notes=f"Recommended by {org_name}",
        )
        resources.append(resource)

    return resources


def enrich_resources_batch(
    resources: list[ResourceData],
    skip_if_has_isbn: bool = True,
) -> list[ResourceData]:
    """
    Enrich a batch of resources with metadata from Google Books.

    Args:
        resources: List of ResourceData to enrich
        skip_if_has_isbn: Skip enrichment if resource already has ISBN

    Returns:
        Same list of resources with metadata enriched
    """
    for resource in resources:
        # Skip if already has good metadata
        if skip_if_has_isbn and (resource.isbn_10 or resource.isbn_13):
            if resource.cover_image_url and resource.description:
                continue

        try:
            enrich_with_google_books(resource)
        except Exception as e:
            logger.warning(f"Failed to enrich '{resource.title}': {e}")

    return resources


# Known authority resource pages for automated discovery
AUTHORITY_RESOURCE_PAGES = {
    "STATE_TX": {
        "name": "Texas Education Agency",
        "official_pages": [
            "https://tea.texas.gov/academics/instructional-materials",
            "https://texasresourcereview.org/",
        ],
    },
    "STATE_FL": {
        "name": "Florida Department of Education",
        "official_pages": [
            "https://www.fldoe.org/academics/standards/instructional-materials/",
        ],
    },
    "STATE_CA": {
        "name": "California Department of Education",
        "official_pages": [
            "https://www.cde.ca.gov/ci/rl/im/",
        ],
    },
    "CCSS_ELA": {
        "name": "Common Core State Standards Initiative",
        "official_pages": [
            "http://www.corestandards.org/ELA-Literacy/",
        ],
    },
    "CCSS_MATH": {
        "name": "Common Core State Standards Initiative",
        "official_pages": [
            "http://www.corestandards.org/Math/",
        ],
    },
}

# Known professional organizations for recommendations
PROFESSIONAL_ORG_PAGES = {
    "mathematics": [
        {
            "name": "National Council of Teachers of Mathematics (NCTM)",
            "url": "https://www.nctm.org/Resources/",
        },
    ],
    "ela": [
        {
            "name": "National Council of Teachers of English (NCTE)",
            "url": "https://ncte.org/resources/",
        },
        {
            "name": "International Literacy Association (ILA)",
            "url": "https://www.literacyworldwide.org/resources",
        },
    ],
    "science": [
        {
            "name": "National Science Teaching Association (NSTA)",
            "url": "https://www.nsta.org/resources",
        },
    ],
}

# Known large district curriculum pages for commonly-used discovery
DISTRICT_CURRICULUM_PAGES = {
    "STATE_TX": [
        {"name": "Houston ISD", "url": "https://www.houstonisd.org/Page/33421"},
        {"name": "Dallas ISD", "url": "https://www.dallasisd.org/Page/36987"},
        {"name": "Austin ISD", "url": "https://www.austinisd.org/academics/curriculum"},
    ],
    "STATE_FL": [
        {"name": "Miami-Dade County Public Schools", "url": "https://curriculum.dadeschools.net/"},
        {"name": "Broward County Public Schools", "url": "https://www.browardschools.com/Page/30706"},
    ],
    "STATE_CA": [
        {"name": "Los Angeles USD", "url": "https://achieve.lausd.net/curriculum"},
        {"name": "San Diego USD", "url": "https://www.sandiegounified.org/departments/curriculum-instruction"},
    ],
}
