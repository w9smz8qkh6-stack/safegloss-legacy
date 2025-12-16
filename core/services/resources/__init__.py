"""
Resource Discovery Service.

Provides functionality for discovering educational resources
(textbooks, courses, videos) that support learning objectives
from various standards authorities.

Each authority has its own provider that knows where to search
for official and recommended resources.

Discovery Pipeline:
1. Official resources - from authority websites (TEA, FLDOE, etc.)
2. Recommended resources - from professional organizations (NCTM, NCTE)
3. Commonly used - from school district websites
4. Metadata enrichment - Google Books for ISBNs, covers, descriptions
"""

from .base import (
    BaseResourceProvider,
    ResourceData,
    DiscoveryResult,
    ResourceProviderError,
    register_resource_provider,
    get_resource_provider,
    list_registered_resource_providers,
    create_resource_provider,
)

from .discovery import (
    # Core discovery functions
    discover_from_authority_website,
    discover_from_district_website,
    discover_from_professional_org,
    # Metadata enrichment
    enrich_with_google_books,
    enrich_resources_batch,
    # AI extraction
    extract_resources_with_ai,
    ExtractedResource,
    # Curated resources
    get_curated_resources,
    CURATED_RESOURCES,
    # Resource pages for automated discovery
    AUTHORITY_RESOURCE_PAGES,
    PROFESSIONAL_ORG_PAGES,
    DISTRICT_CURRICULUM_PAGES,
)

__all__ = [
    # Base classes
    "BaseResourceProvider",
    "ResourceData",
    "DiscoveryResult",
    "ResourceProviderError",
    # Registry
    "register_resource_provider",
    "get_resource_provider",
    "list_registered_resource_providers",
    "create_resource_provider",
    # Discovery functions
    "discover_from_authority_website",
    "discover_from_district_website",
    "discover_from_professional_org",
    # Enrichment
    "enrich_with_google_books",
    "enrich_resources_batch",
    # AI extraction
    "extract_resources_with_ai",
    "ExtractedResource",
    # Curated resources
    "get_curated_resources",
    "CURATED_RESOURCES",
    # Known resource pages
    "AUTHORITY_RESOURCE_PAGES",
    "PROFESSIONAL_ORG_PAGES",
    "DISTRICT_CURRICULUM_PAGES",
]

# Import provider implementations to trigger registration
from . import providers as _providers_module  # noqa: F401
