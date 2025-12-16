"""
Standards Import Service.

Provides functions to import and sync standards documents with full provenance tracking.
Implements Section 17.6 of the build guide.
"""

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import (
    AuthorityProgram,
    ObjectiveCodeMap,
    ObjectiveNode,
    StandardsArtifact,
    StandardsDocument,
)

from .providers import FetchResult, ObjectiveNodeData, BaseStandardsProvider, get_provider
from .validation import validate_provenance, ProvenanceValidationError

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Raised when import fails."""
    pass


def _compute_sha256(content: bytes) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content).hexdigest()


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        # Handle various ISO formats
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_date(value: Optional[str]):
    """Parse ISO date string to date object."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _generate_internal_codes(nodes: list[ObjectiveNode]) -> None:
    """
    Generate internal codes for objective nodes based on tree structure.
    Updates nodes in place.
    """
    # Build parent->children map
    root_nodes = []
    children_map: dict[int, list[ObjectiveNode]] = {}

    for node in nodes:
        if node.parent_id is None:
            root_nodes.append(node)
        else:
            if node.parent_id not in children_map:
                children_map[node.parent_id] = []
            children_map[node.parent_id].append(node)

    # Sort by sort_order
    root_nodes.sort(key=lambda n: n.sort_order)
    for children in children_map.values():
        children.sort(key=lambda n: n.sort_order)

    def assign_codes(node_list: list[ObjectiveNode], prefix: str = "", depth: int = 0):
        for i, node in enumerate(node_list, 1):
            if prefix:
                node.internal_code = f"{prefix}.{i}"
                node.internal_path = f"{prefix}/{prefix}.{i}"
            else:
                node.internal_code = str(i)
                node.internal_path = str(i)

            # Zero-padded sort key for stable ordering
            node.internal_sort_key = f"{depth:02d}-{i:04d}"

            node.save(update_fields=["internal_code", "internal_path", "internal_sort_key"])

            # Process children
            if node.pk in children_map:
                assign_codes(children_map[node.pk], node.internal_code, depth + 1)

    assign_codes(root_nodes)


@transaction.atomic
def import_standards_document(
    fetch_result: FetchResult,
    artifact_file_path: Optional[str] = None,
) -> StandardsDocument:
    """
    Import a standards document from a FetchResult.

    This is the main import function that:
    1. Validates provenance
    2. Creates/updates StandardsDocument
    3. Creates ObjectiveNode tree
    4. Generates internal codes
    5. Creates ObjectiveCodeMap entries

    Args:
        fetch_result: Result from a provider's fetch_objectives()
        artifact_file_path: Optional path to stored artifact file

    Returns:
        The created/updated StandardsDocument

    Raises:
        ProvenanceValidationError: If provenance validation fails
        ImportError: If import fails for other reasons
    """
    # Step 1: Validate provenance (gate - must pass)
    provenance = validate_provenance(fetch_result.provenance)

    # Step 2: Find the authority program
    try:
        authority_program = AuthorityProgram.objects.select_related("authority").get(
            authority__code=fetch_result.authority_code,
            code=fetch_result.program_code,
        )
    except AuthorityProgram.DoesNotExist:
        raise ImportError(
            f"AuthorityProgram not found: {fetch_result.authority_code}/{fetch_result.program_code}"
        )

    # Step 3: Create or update artifact if provided
    artifact = None
    if artifact_file_path and fetch_result.artifact_content:
        artifact = StandardsArtifact.objects.create(
            file_path=artifact_file_path,
            content_type=fetch_result.artifact_content_type or "other",
            sha256_hash=_compute_sha256(fetch_result.artifact_content),
            file_size_bytes=len(fetch_result.artifact_content),
            original_filename=fetch_result.artifact_filename or "",
            metadata={
                "import_timestamp": timezone.now().isoformat(),
                "source_url": provenance.source_url,
            },
        )

    # Step 4: Create or update StandardsDocument
    # Look for existing document with same program/subject/grade/version
    existing_doc = StandardsDocument.objects.filter(
        authority_program=authority_program,
        subject=fetch_result.subject,
        grade_level=fetch_result.grade_level,
        version_label=fetch_result.version_label,
    ).first()

    if existing_doc:
        # Update existing document
        doc = existing_doc
        logger.info(f"Updating existing document: {doc}")
    else:
        # Create new document
        doc = StandardsDocument(
            authority_program=authority_program,
            subject=fetch_result.subject,
            grade_level=fetch_result.grade_level,
            version_label=fetch_result.version_label,
        )
        logger.info(f"Creating new document: {fetch_result.subject} - {fetch_result.grade_level}")

    # Map provenance fields
    doc.source_publisher_name = provenance.source_publisher_name
    doc.source_publisher_type = provenance.source_publisher_type
    doc.source_title = provenance.source_title
    doc.source_url = provenance.source_url
    doc.source_url_canonical = provenance.source_url_canonical
    doc.source_accessed_at = _parse_datetime(provenance.source_accessed_at)
    doc.source_content_type = provenance.source_content_type
    doc.source_version_label = provenance.source_version_label
    doc.source_effective_from = _parse_date(provenance.source_effective_from)
    doc.source_effective_until = _parse_date(provenance.source_effective_until)
    doc.source_license_notes = provenance.source_license_notes
    doc.acquisition_method = provenance.acquisition_method
    doc.acquisition_notes = provenance.acquisition_notes
    doc.evidence_sha256_raw = provenance.evidence_sha256_raw
    doc.evidence_sha256_canonical = provenance.evidence_sha256_canonical

    if artifact:
        doc.evidence_artifact = artifact

    doc.is_active = True
    doc.save()

    # Step 5: Delete existing objective nodes (for re-sync)
    if existing_doc:
        ObjectiveNode.objects.filter(document=doc).delete()

    # Step 6: Create objective nodes
    # First pass: create all nodes with temporary parent references
    temp_id_to_node: dict[str, ObjectiveNode] = {}
    nodes_needing_parent: list[tuple[ObjectiveNode, str]] = []

    for node_data in fetch_result.nodes:
        node = ObjectiveNode.objects.create(
            document=doc,
            parent=None,  # Set in second pass
            node_type=node_data.node_type,
            code=node_data.code,
            text=node_data.text,
            sort_order=node_data.sort_order,
        )
        temp_id_to_node[node_data.id] = node
        if node_data.parent_id:
            nodes_needing_parent.append((node, node_data.parent_id))

    # Second pass: set parent references
    for node, parent_temp_id in nodes_needing_parent:
        parent = temp_id_to_node.get(parent_temp_id)
        if parent:
            node.parent = parent
            node.save(update_fields=["parent"])

    # Step 7: Generate internal codes
    all_nodes = list(ObjectiveNode.objects.filter(document=doc))
    _generate_internal_codes(all_nodes)

    # Step 8: Create ObjectiveCodeMap entries for audit
    for node in ObjectiveNode.objects.filter(document=doc):
        ObjectiveCodeMap.objects.create(
            objective_node=node,
            native_code=node.code,
            internal_code=node.internal_code,
            mapping_method="algorithmic",
            notes=f"Auto-generated during import at {timezone.now().isoformat()}",
        )

    logger.info(
        f"Imported {len(fetch_result.nodes)} objectives for "
        f"{doc.authority_program.code} - {doc.subject} ({doc.grade_level})"
    )

    return doc


def sync_document(
    program_code: str,
    subject: str,
    grade_level: str,
    version: Optional[str] = None,
) -> StandardsDocument:
    """
    Sync a document using the registered provider.

    This is a convenience function that:
    1. Looks up the provider for the program
    2. Fetches objectives
    3. Imports/updates the document

    Args:
        program_code: Program code (e.g., 'STATE_TX')
        subject: Subject area
        grade_level: Grade level
        version: Optional version; defaults to latest

    Returns:
        The synced StandardsDocument

    Raises:
        ImportError: If no provider is registered or sync fails
    """
    provider_cls = get_provider(program_code)
    if not provider_cls:
        raise ImportError(f"No provider registered for program: {program_code}")

    provider = provider_cls()
    fetch_result = provider.fetch_objectives(subject, grade_level, version)

    return import_standards_document(fetch_result)


def import_standards_json(
    json_data: dict,
    artifact_file_path: Optional[str] = None,
) -> StandardsDocument:
    """
    Import standards from a JSON payload.

    Expected JSON format (from Section 17.3):
    {
        "authority": "TX_TEKS",
        "program": "STATE_TX",
        "subject": "TECH_APPS",
        "grade": "Grade 6",
        "version": "Adopted 2022",
        "provenance": { ... },
        "nodes": [
            {"id": "n1", "parent": null, "type": "strand", "code": "CT", "text": "...", "order": 1},
            ...
        ]
    }

    Args:
        json_data: Dictionary with standards data
        artifact_file_path: Optional path to stored artifact

    Returns:
        The imported StandardsDocument
    """
    # Validate required fields
    required = ["authority", "program", "subject", "grade", "version", "provenance", "nodes"]
    missing = [f for f in required if f not in json_data]
    if missing:
        raise ImportError(f"Missing required fields: {', '.join(missing)}")

    # Build node data
    nodes = []
    for node_dict in json_data["nodes"]:
        nodes.append(ObjectiveNodeData(
            id=node_dict["id"],
            parent_id=node_dict.get("parent"),
            node_type=node_dict.get("type", "objective"),
            code=node_dict.get("code", ""),
            text=node_dict.get("text", ""),
            sort_order=node_dict.get("order", 0),
        ))

    # Build FetchResult
    fetch_result = FetchResult(
        authority_code=json_data["authority"],
        program_code=json_data["program"],
        subject=json_data["subject"],
        grade_level=json_data["grade"],
        version_label=json_data["version"],
        provenance=json_data["provenance"],
        nodes=nodes,
    )

    return import_standards_document(fetch_result, artifact_file_path)
