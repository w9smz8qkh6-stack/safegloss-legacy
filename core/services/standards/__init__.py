"""
Standards Import and Sync Services.

This module provides:
- Provider interface for fetching objectives from various authorities
- Provenance validation ensuring all imports are auditable
- Import/sync functions for persisting standards to the database
- Web-based discovery using AI extraction

Discovery Pipeline:
1. Fetch official standards pages from authority websites
2. Use AI to extract structured learning objectives
3. Convert to FetchResult for import
4. Import with full provenance tracking
"""

from .validation import validate_provenance, ProvenanceValidationError
from .import_service import import_standards_document, sync_document, import_standards_json
from .providers import BaseStandardsProvider, FetchResult, ObjectiveNodeData
from .discovery import (
    discover_standards_from_url,
    extract_standards_with_ai,
    convert_to_fetch_result,
    get_standards_url_for_program,
    DiscoveredStandards,
    ExtractedObjective,
    AUTHORITY_STANDARDS_PAGES,
)

__all__ = [
    # Validation
    "validate_provenance",
    "ProvenanceValidationError",
    # Import
    "import_standards_document",
    "import_standards_json",
    "sync_document",
    # Provider interface
    "BaseStandardsProvider",
    "FetchResult",
    "ObjectiveNodeData",
    # Discovery
    "discover_standards_from_url",
    "extract_standards_with_ai",
    "convert_to_fetch_result",
    "get_standards_url_for_program",
    "DiscoveredStandards",
    "ExtractedObjective",
    "AUTHORITY_STANDARDS_PAGES",
]

# Import provider implementations to trigger registration
from . import provider_implementations as _providers_module  # noqa: F401
