"""
Standards Discovery Module.

Uses web fetching and AI extraction to discover learning objectives
from authority websites. This is the core discovery mechanism that
powers the "Refresh Objectives" functionality.

Discovery Pipeline:
1. Search for official standards pages (or use known URLs)
2. Fetch page content
3. Use AI to extract structured objectives
4. Parse into ObjectiveNodeData format for import
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache

from .providers import ObjectiveNodeData, FetchResult

logger = logging.getLogger(__name__)

# Cache timeout for discovery results (1 hour)
DISCOVERY_CACHE_TIMEOUT = 3600


@dataclass
class ExtractedObjective:
    """A learning objective extracted from a web page by AI."""
    code: str
    text: str
    node_type: str = "objective"  # strand, substrand, objective, note
    parent_code: str = ""
    sort_order: int = 0
    confidence: float = 0.0


@dataclass
class DiscoveredStandards:
    """Result of discovering standards from a web page."""
    source_url: str
    source_title: str
    subject: str
    grade_level: str
    version_label: str
    objectives: list[ExtractedObjective]
    discovery_notes: str = ""
    raw_content: str = ""
    content_hash: str = ""


def fetch_page(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
    use_cache: bool = True,
) -> tuple[str, str, Optional[str]]:
    """
    Fetch a web page with caching support.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        headers: Optional HTTP headers
        use_cache: Whether to use cache

    Returns:
        Tuple of (content, content_type, error)
    """
    cache_key = f"standards:fetch:{hashlib.md5(url.encode()).hexdigest()}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {url}")
            return cached["content"], cached["content_type"], None

    default_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SafeglossBot/1.0; +https://safegloss.com/bot)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if headers:
        default_headers.update(headers)

    try:
        response = requests.get(url, timeout=timeout, headers=default_headers)
        response.raise_for_status()
        content = response.text
        content_type = response.headers.get("Content-Type", "text/html")

        if use_cache:
            cache.set(cache_key, {
                "content": content,
                "content_type": content_type,
            }, DISCOVERY_CACHE_TIMEOUT)

        return content, content_type, None

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return "", "", str(e)


def extract_standards_with_ai(
    page_content: str,
    page_url: str,
    subject: str = "",
    grade_level: str = "",
    authority_name: str = "",
) -> list[ExtractedObjective]:
    """
    Use AI to extract learning objectives from web page content.

    This function uses an LLM (via OpenRouter) to parse official standards pages
    and extract structured objective information.

    Args:
        page_content: HTML or text content of the page
        page_url: URL the content was fetched from
        subject: Subject area to focus on
        grade_level: Grade level to focus on
        authority_name: Name of the standards authority

    Returns:
        List of ExtractedObjective objects
    """
    from django.conf import settings
    from openai import OpenAI

    # Check if API key is configured (prefer OpenRouter, fallback to Anthropic)
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not api_key:
        api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
        if api_key:
            # Use Anthropic directly
            base_url = "https://api.anthropic.com/v1"
            model = "claude-3-haiku-20240307"
        else:
            logger.warning("No API key configured (OPENROUTER_API_KEY or ANTHROPIC_API_KEY), skipping AI extraction")
            return []
    else:
        # Use OpenRouter
        base_url = "https://openrouter.ai/api/v1"
        model = "openai/gpt-4o-mini"  # Fast and efficient via OpenRouter

    # Parse HTML to text if needed
    if "<html" in page_content.lower() or "<body" in page_content.lower():
        soup = BeautifulSoup(page_content, "html.parser")
        # Remove scripts, styles, and navigation
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        text_content = soup.get_text(separator="\n", strip=True)
    else:
        text_content = page_content

    # Truncate if too long (keep first 20000 chars for standards - they can be detailed)
    if len(text_content) > 20000:
        text_content = text_content[:20000] + "\n...[truncated]"

    # Build prompt
    prompt = f"""Analyze this official standards document and extract the learning objectives/standards.

Page URL: {page_url}
{f"Standards Authority: {authority_name}" if authority_name else ""}
{f"Subject: {subject}" if subject else ""}
{f"Grade Level: {grade_level}" if grade_level else ""}

DOCUMENT CONTENT:
{text_content}

Extract each learning standard/objective with:
- code: The official code/identifier (e.g., "1.1", "CCSS.ELA-LITERACY.RL.6.1", "(1)(A)")
- text: The full text of the standard/objective
- node_type: One of: "strand" (major category), "substrand" (subcategory), "objective" (specific skill), "note" (explanatory text)
- parent_code: The code of the parent strand/substrand (empty string if top-level)
- sort_order: Numeric order within parent (1, 2, 3, etc.)
- confidence: How confident you are this is a valid learning objective (0.0-1.0)

IMPORTANT:
- Preserve the EXACT official code/identifier from the document
- Preserve the EXACT wording of each objective - do not paraphrase
- Include the hierarchical structure (strands contain objectives)
- Only extract actual learning objectives, not navigation text or page metadata

Return a JSON array of objects. If no standards are found, return an empty array [].

JSON:"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=4000,
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

        objectives = []
        for item in data:
            if not item.get("code") or not item.get("text"):
                continue

            obj = ExtractedObjective(
                code=item.get("code", ""),
                text=item.get("text", ""),
                node_type=item.get("node_type", "objective"),
                parent_code=item.get("parent_code", ""),
                sort_order=int(item.get("sort_order", 0)),
                confidence=float(item.get("confidence", 0.5)),
            )
            objectives.append(obj)

        logger.info(f"AI extracted {len(objectives)} objectives from {page_url}")
        return objectives

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return []


def discover_standards_from_url(
    url: str,
    authority_name: str,
    subject: str = "",
    grade_level: str = "",
    version_label: str = "",
) -> DiscoveredStandards:
    """
    Discover learning standards from an authority website URL.

    Fetches the page and uses AI to extract structured objectives.

    Args:
        url: URL of the standards page
        authority_name: Name of the standards authority
        subject: Subject to focus on
        grade_level: Grade level to focus on
        version_label: Version/year of the standards

    Returns:
        DiscoveredStandards with extracted objectives
    """
    content, content_type, error = fetch_page(url)

    if error:
        logger.warning(f"Failed to fetch standards page: {url} - {error}")
        return DiscoveredStandards(
            source_url=url,
            source_title="",
            subject=subject,
            grade_level=grade_level,
            version_label=version_label,
            objectives=[],
            discovery_notes=f"Fetch failed: {error}",
        )

    # Extract page title
    title = ""
    if "html" in content_type.lower():
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

    # Compute content hash for provenance
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Extract objectives using AI
    objectives = extract_standards_with_ai(
        page_content=content,
        page_url=url,
        subject=subject,
        grade_level=grade_level,
        authority_name=authority_name,
    )

    # Filter low-confidence objectives
    high_confidence = [obj for obj in objectives if obj.confidence >= 0.5]

    return DiscoveredStandards(
        source_url=url,
        source_title=title,
        subject=subject,
        grade_level=grade_level,
        version_label=version_label,
        objectives=high_confidence,
        discovery_notes=f"Extracted {len(high_confidence)} objectives (filtered {len(objectives) - len(high_confidence)} low-confidence)",
        raw_content=content,
        content_hash=content_hash,
    )


def convert_to_fetch_result(
    discovered: DiscoveredStandards,
    authority_code: str,
    program_code: str,
) -> FetchResult:
    """
    Convert DiscoveredStandards to FetchResult for import.

    Args:
        discovered: DiscoveredStandards from discovery
        authority_code: Authority code (e.g., "US_STATES")
        program_code: Program code (e.g., "STATE_TX")

    Returns:
        FetchResult ready for import
    """
    # Build node tree from extracted objectives
    nodes = []
    code_to_id = {}
    node_id = 0

    # First pass: create all nodes and map codes to IDs
    for obj in discovered.objectives:
        node_id += 1
        node_id_str = str(node_id)
        code_to_id[obj.code] = node_id_str

        nodes.append(ObjectiveNodeData(
            id=node_id_str,
            parent_id=None,  # Will be filled in second pass
            node_type=obj.node_type,
            code=obj.code,
            text=obj.text,
            sort_order=obj.sort_order or node_id,
        ))

    # Second pass: link parents
    for i, obj in enumerate(discovered.objectives):
        if obj.parent_code and obj.parent_code in code_to_id:
            nodes[i].parent_id = code_to_id[obj.parent_code]

    # Build provenance
    provenance = {
        "source_publisher_name": "",  # Will be filled from authority
        "source_publisher_type": "government",
        "source_title": discovered.source_title,
        "source_url": discovered.source_url,
        "source_url_canonical": discovered.source_url,
        "source_accessed_at": datetime.utcnow().isoformat() + "Z",
        "source_content_type": "html",
        "source_version_label": discovered.version_label or "Current",
        "acquisition_method": "web_scrape_ai",
        "acquisition_notes": discovered.discovery_notes,
        "evidence_sha256_raw": discovered.content_hash,
        "evidence_sha256_canonical": "",
    }

    return FetchResult(
        authority_code=authority_code,
        program_code=program_code,
        subject=discovered.subject,
        grade_level=discovered.grade_level,
        version_label=discovered.version_label or "Current",
        provenance=provenance,
        nodes=nodes,
    )


# Known standards pages for automated discovery
AUTHORITY_STANDARDS_PAGES = {
    "STATE_TX": {
        "name": "Texas Education Agency",
        "authority_code": "US_STATES",
        "base_url": "https://tea.texas.gov",
        "standards_pages": {
            "Technology Applications": {
                "default": "https://tea.texas.gov/academics/subject-areas/technology-applications",
            },
            "English Language Arts": {
                "default": "https://tea.texas.gov/academics/subject-areas/english-language-arts-and-reading",
            },
            "Mathematics": {
                "default": "https://tea.texas.gov/academics/subject-areas/mathematics",
            },
            "Science": {
                "default": "https://tea.texas.gov/academics/subject-areas/science",
            },
        },
        # The official TEKS definitions are at teksguide.org
        "teks_guide_url": "https://teksguide.org/",
    },
    "STATE_FL": {
        "name": "Florida Department of Education",
        "authority_code": "US_STATES",
        "base_url": "https://www.fldoe.org",
        "standards_pages": {
            "English Language Arts": {
                "default": "https://www.fldoe.org/academics/standards/subject-areas/english-language-arts/",
            },
            "Mathematics": {
                "default": "https://www.fldoe.org/academics/standards/subject-areas/mathematics/",
            },
            "Science": {
                "default": "https://www.fldoe.org/academics/standards/subject-areas/science/",
            },
        },
    },
    "STATE_CA": {
        "name": "California Department of Education",
        "authority_code": "US_STATES",
        "base_url": "https://www.cde.ca.gov",
        "standards_pages": {
            "English Language Arts": {
                "default": "https://www.cde.ca.gov/be/st/ss/elacontentstnds.asp",
            },
            "Mathematics": {
                "default": "https://www.cde.ca.gov/be/st/ss/mathcontentstnds.asp",
            },
            "Science": {
                "default": "https://www.cde.ca.gov/pd/ca/sc/ngssstandards.asp",
            },
        },
    },
    "CCSS_ELA": {
        "name": "Common Core State Standards Initiative",
        "authority_code": "CCSS",
        "base_url": "http://www.corestandards.org",
        "standards_pages": {
            "English Language Arts": {
                "default": "http://www.corestandards.org/ELA-Literacy/",
            },
        },
    },
    "CCSS_MATH": {
        "name": "Common Core State Standards Initiative",
        "authority_code": "CCSS",
        "base_url": "http://www.corestandards.org",
        "standards_pages": {
            "Mathematics": {
                "default": "http://www.corestandards.org/Math/",
            },
        },
    },
    "CAMBRIDGE": {
        "name": "Cambridge Assessment International Education",
        "authority_code": "CAMBRIDGE",
        "base_url": "https://www.cambridgeinternational.org",
        "standards_pages": {
            "default": {
                "IGCSE": "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-upper-secondary/cambridge-igcse/subjects/",
                "AS & A Level": "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/cambridge-international-as-and-a-levels/subjects/",
            },
        },
    },
}


def get_standards_url_for_program(
    program_code: str,
    subject: str,
    grade_level: str = "",
) -> Optional[str]:
    """
    Get the official standards URL for a program/subject/grade combination.

    Args:
        program_code: Program code (e.g., "STATE_TX")
        subject: Subject name
        grade_level: Grade level (optional)

    Returns:
        URL string or None if not found
    """
    program_info = AUTHORITY_STANDARDS_PAGES.get(program_code)
    if not program_info:
        return None

    subject_pages = program_info.get("standards_pages", {}).get(subject, {})

    if grade_level and grade_level in subject_pages:
        return subject_pages[grade_level]

    return subject_pages.get("default")
