"""
Provenance validation for standards imports.

Implements Section 17.4 of the build guide:
- source_url is present and begins with https://
- source_publisher_name is present
- acquisition_method is one of the controlled values
- Additional checks for reference-only methods
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


# Controlled vocabulary for acquisition methods (Section 17.2)
VALID_ACQUISITION_METHODS = frozenset([
    "official_api",
    "official_web_page",
    "official_pdf",
    "official_download_bundle",
    "publisher_portal_reference_only",
    "third_party_mirror_reference",
    "teacher_provided_upload",
    "manual_curated",
    "hybrid",
])

# Methods that require acquisition_notes explaining why
REFERENCE_ONLY_METHODS = frozenset([
    "publisher_portal_reference_only",
    "third_party_mirror_reference",
])


class ProvenanceValidationError(Exception):
    """Raised when provenance validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


@dataclass
class ProvenanceData:
    """
    Structured provenance data as returned by providers.
    Maps to StandardsDocument provenance fields.
    """
    source_publisher_name: str
    source_publisher_type: str = ""
    source_title: str = ""
    source_url: str = ""
    source_url_canonical: str = ""
    source_accessed_at: Optional[str] = None  # ISO datetime string
    source_content_type: str = ""
    source_version_label: str = ""
    source_effective_from: Optional[str] = None  # ISO date string
    source_effective_until: Optional[str] = None  # ISO date string
    source_license_notes: str = ""
    acquisition_method: str = ""
    acquisition_notes: str = ""
    evidence_sha256_raw: str = ""
    evidence_sha256_canonical: str = ""


def validate_provenance(provenance: dict) -> ProvenanceData:
    """
    Validate provenance data and return a structured ProvenanceData object.

    Args:
        provenance: Dictionary containing provenance fields

    Returns:
        ProvenanceData object with validated fields

    Raises:
        ProvenanceValidationError: If validation fails
    """
    errors = []

    # Required: source_url must be present and HTTPS
    source_url = provenance.get("source_url", "").strip()
    if not source_url:
        errors.append(("source_url", "source_url is required"))
    else:
        parsed = urlparse(source_url)
        if parsed.scheme != "https":
            errors.append(("source_url", "source_url must use HTTPS"))

    # Required: source_publisher_name must be present
    source_publisher_name = provenance.get("source_publisher_name", "").strip()
    if not source_publisher_name:
        errors.append(("source_publisher_name", "source_publisher_name is required"))

    # Required: acquisition_method must be in controlled vocabulary
    acquisition_method = provenance.get("acquisition_method", "").strip()
    if not acquisition_method:
        errors.append(("acquisition_method", "acquisition_method is required"))
    elif acquisition_method not in VALID_ACQUISITION_METHODS:
        errors.append((
            "acquisition_method",
            f"acquisition_method must be one of: {', '.join(sorted(VALID_ACQUISITION_METHODS))}"
        ))

    # If reference-only method, acquisition_notes must explain why
    if acquisition_method in REFERENCE_ONLY_METHODS:
        acquisition_notes = provenance.get("acquisition_notes", "").strip()
        if not acquisition_notes:
            errors.append((
                "acquisition_notes",
                f"acquisition_notes is required when acquisition_method is '{acquisition_method}'"
            ))

    # Validate source_publisher_type if provided
    source_publisher_type = provenance.get("source_publisher_type", "").strip()
    valid_publisher_types = {"government", "nonprofit", "publisher", "testing_org", "other", ""}
    if source_publisher_type and source_publisher_type not in valid_publisher_types:
        errors.append((
            "source_publisher_type",
            f"source_publisher_type must be one of: government, nonprofit, publisher, testing_org, other"
        ))

    # Validate source_content_type if provided
    source_content_type = provenance.get("source_content_type", "").strip()
    valid_content_types = {"html", "pdf", "json", "docx", "api", ""}
    if source_content_type and source_content_type not in valid_content_types:
        errors.append((
            "source_content_type",
            f"source_content_type must be one of: html, pdf, json, docx, api"
        ))

    # Raise combined errors
    if errors:
        error_messages = [f"{field}: {msg}" for field, msg in errors]
        raise ProvenanceValidationError(
            f"Provenance validation failed:\n" + "\n".join(f"  - {e}" for e in error_messages),
            field=errors[0][0] if len(errors) == 1 else None
        )

    # Build and return validated ProvenanceData
    return ProvenanceData(
        source_publisher_name=source_publisher_name,
        source_publisher_type=source_publisher_type,
        source_title=provenance.get("source_title", "").strip(),
        source_url=source_url,
        source_url_canonical=provenance.get("source_url_canonical", "").strip(),
        source_accessed_at=provenance.get("source_accessed_at"),
        source_content_type=source_content_type,
        source_version_label=provenance.get("source_version_label", "").strip(),
        source_effective_from=provenance.get("source_effective_from"),
        source_effective_until=provenance.get("source_effective_until"),
        source_license_notes=provenance.get("source_license_notes", "").strip(),
        acquisition_method=acquisition_method,
        acquisition_notes=provenance.get("acquisition_notes", "").strip(),
        evidence_sha256_raw=provenance.get("evidence_sha256_raw", "").strip(),
        evidence_sha256_canonical=provenance.get("evidence_sha256_canonical", "").strip(),
    )
