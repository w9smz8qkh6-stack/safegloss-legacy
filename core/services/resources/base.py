"""
Resource Provider Base Class and Registry.

Provides abstract interface for discovering educational resources
(textbooks, courses, videos) that support learning objectives.
Each authority gets its own provider implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResourceData:
    """Data class for a discovered resource."""
    title: str
    source_url: str
    media_type: str  # book, guide, curriculum, practice_tests, video_series, course, website
    platform: str  # print, authority, google_books, amazon, khan_academy, district, publisher, etc.

    # Optional metadata
    author: str = ""
    publisher: str = ""
    description: str = ""
    isbn_10: str = ""
    isbn_13: str = ""
    cover_image_url: str = ""

    # Recommendation tier: official, recommended, commonly_used
    recommendation_tier: str = "commonly_used"
    endorsement_notes: str = ""

    # Discovery provenance
    discovered_from_url: str = ""
    recommending_organization: str = ""

    # Legacy field for backwards compatibility
    is_official: bool = False

    # Features (JSON-compatible dict)
    features: dict = field(default_factory=dict)

    # Objective alignment (list of native codes)
    aligned_objective_codes: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Sync is_official with recommendation_tier for backwards compatibility."""
        if self.is_official and self.recommendation_tier == "commonly_used":
            self.recommendation_tier = "official"
        elif self.recommendation_tier == "official":
            self.is_official = True


@dataclass
class DiscoveryResult:
    """Result of a resource discovery operation."""
    authority_code: str
    program_code: str
    subject: str
    grade_level: str

    resources: list[ResourceData]

    # Discovery metadata
    sources_checked: list[str] = field(default_factory=list)
    discovery_notes: str = ""
    error: Optional[str] = None


class ResourceProviderError(Exception):
    """Error during resource discovery."""
    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(f"[{provider}] {message}" if provider else message)


class BaseResourceProvider(ABC):
    """
    Abstract base class for resource providers.

    Each authority/program should have a provider implementation that
    knows where to search for official and recommended resources.
    """

    # Subclasses should override these
    SEARCH_STRATEGY: str = "Not documented"
    SOURCE_URLS: list[str] = []

    @property
    @abstractmethod
    def authority_code(self) -> str:
        """Return the authority code (e.g., 'US_STATES', 'IB')."""
        pass

    @property
    @abstractmethod
    def program_code(self) -> str:
        """Return the program code (e.g., 'STATE_TX', 'IB_MYP')."""
        pass

    @abstractmethod
    def discover_resources(
        self,
        subject: str,
        grade_level: str,
    ) -> DiscoveryResult:
        """
        Discover resources for a specific subject/grade combination.

        Args:
            subject: Subject area (e.g., "Mathematics", "English Language Arts")
            grade_level: Grade level (e.g., "Grade 6", "Grades 6-8")

        Returns:
            DiscoveryResult with list of ResourceData objects

        Raises:
            ResourceProviderError: If discovery fails
        """
        pass

    def get_search_strategy(self) -> str:
        """Return description of where this provider searches for resources."""
        return self.SEARCH_STRATEGY

    def get_source_urls(self) -> list[str]:
        """Return list of URLs/sources this provider checks."""
        return self.SOURCE_URLS

    def list_available_subjects(self) -> list[str]:
        """Return list of subjects this provider can discover resources for."""
        return []

    def list_available_grades(self, subject: Optional[str] = None) -> list[str]:
        """Return list of grade levels this provider supports."""
        return []


# =============================================================================
# Provider Registry
# =============================================================================

_resource_provider_registry: dict[str, type[BaseResourceProvider]] = {}


def register_resource_provider(program_code: str):
    """
    Decorator to register a resource provider class.

    Usage:
        @register_resource_provider("STATE_TX")
        class TexasResourceProvider(BaseResourceProvider):
            ...
    """
    def decorator(cls: type[BaseResourceProvider]) -> type[BaseResourceProvider]:
        _resource_provider_registry[program_code] = cls
        logger.debug(f"Registered resource provider: {program_code} -> {cls.__name__}")
        return cls
    return decorator


def get_resource_provider(program_code: str) -> Optional[type[BaseResourceProvider]]:
    """Get provider class for a program code, or None if not registered."""
    return _resource_provider_registry.get(program_code)


def list_registered_resource_providers() -> list[str]:
    """Return list of all registered provider program codes."""
    return list(_resource_provider_registry.keys())


def create_resource_provider(program_code: str) -> Optional[BaseResourceProvider]:
    """Create an instance of the provider for a program code."""
    provider_cls = get_resource_provider(program_code)
    if provider_cls:
        return provider_cls()
    return None
