"""
Standards Provider Interface.

Defines the contract for fetching objectives from various standards authorities.
Each provider must return objectives with full provenance data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ObjectiveNodeData:
    """
    A single objective node in the tree.
    """
    id: str  # Temporary ID for building parent references
    parent_id: Optional[str]  # Reference to parent node's temp ID
    node_type: str  # strand, substrand, objective, note
    code: str  # Native authority code
    text: str  # Objective wording
    sort_order: int


@dataclass
class FetchResult:
    """
    Result of fetching objectives from a provider.
    Includes both the objective nodes and full provenance.
    """
    authority_code: str
    program_code: str
    subject: str
    grade_level: str
    version_label: str

    # Provenance (required - validated before import)
    provenance: dict

    # Objective nodes
    nodes: list[ObjectiveNodeData] = field(default_factory=list)

    # Optional: raw artifact data for evidence storage
    artifact_content: Optional[bytes] = None
    artifact_filename: Optional[str] = None
    artifact_content_type: Optional[str] = None


class BaseStandardsProvider(ABC):
    """
    Abstract base class for standards providers.

    Each authority/program should have a provider that implements this interface.
    The provider is responsible for:
    1. Fetching objectives from the source (API, web page, PDF, etc.)
    2. Parsing them into a canonical node structure
    3. Including complete provenance data
    """

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
    def fetch_objectives(
        self,
        subject: str,
        grade_level: str,
        version: Optional[str] = None,
    ) -> FetchResult:
        """
        Fetch objectives for a specific subject/grade combination.

        Args:
            subject: Subject area (e.g., 'Mathematics', 'Technology Applications')
            grade_level: Grade level (e.g., 'Grade 6', 'Grades 6-8')
            version: Optional version label; defaults to latest

        Returns:
            FetchResult containing nodes and provenance

        Raises:
            ProviderError: If fetching fails
        """
        pass

    @abstractmethod
    def list_available_subjects(self) -> list[str]:
        """Return list of available subjects for this program."""
        pass

    @abstractmethod
    def list_available_grades(self, subject: Optional[str] = None) -> list[str]:
        """Return list of available grade levels, optionally filtered by subject."""
        pass


class ProviderError(Exception):
    """Raised when a provider encounters an error fetching objectives."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.message = message
        self.provider = provider
        super().__init__(message)


# Provider registry
_providers: dict[str, type[BaseStandardsProvider]] = {}


def register_provider(program_code: str):
    """
    Decorator to register a provider class for a program code.

    Usage:
        @register_provider("STATE_TX")
        class TexasProvider(BaseStandardsProvider):
            ...
    """
    def decorator(cls: type[BaseStandardsProvider]):
        _providers[program_code] = cls
        return cls
    return decorator


def get_provider(program_code: str) -> Optional[type[BaseStandardsProvider]]:
    """Get the provider class for a program code, or None if not registered."""
    return _providers.get(program_code)


def list_registered_providers() -> list[str]:
    """Return list of registered program codes."""
    return list(_providers.keys())
