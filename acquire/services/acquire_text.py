"""
Acquire Text orchestration service (placeholder).

Implements run_acquire_for_course signature and logging hooks.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from acquire.conf import DEFAULT_ACQUIRE_TTL_HOURS
from acquire.connectors import CONNECTOR_REGISTRY, initialize_default_connectors
from acquire.models import AcquisitionCandidate, AcquisitionLog, CourseText, Text, TextSource
from acquire.services import matching, ranking

# Ensure default connectors are registered for orchestration.
if not CONNECTOR_REGISTRY:
    initialize_default_connectors()


@transaction.atomic
def run_acquire_for_course(course_id: int, actor_user_id: int, actor_role: str, force: bool = False) -> None:
    """
    Run acquisition across registered connectors for all CourseText entries.

    Placeholder: currently no external calls are made; inserts minimal logs.
    """
    course_texts = CourseText.objects.select_related("text").filter(course_id=course_id)
    connector_sources = _map_connectors_to_sources()

    for course_text in course_texts:
        text = course_text.text
        for name, connector in CONNECTOR_REGISTRY.items():
            text_source = connector_sources.get(name)
            _process_connector(
                name,
                connector,
                text_source,
                text,
                course_id,
                actor_user_id,
                actor_role,
                force=force,
            )


def _process_connector(
    name,
    connector,
    text_source: TextSource,
    text: Text,
    course_id: int,
    actor_user_id: int,
    actor_role: str,
    *,
    force: bool,
) -> None:
    """
    Run a single connector search and store results.

    Includes a simple freshness check to avoid re-querying within TTL unless forced.
    """
    now = timezone.now()
    ttl_cutoff = now - timedelta(hours=24)
    ttl_hours = getattr(settings, "ACQUIRE_TEXT_TTL_HOURS", DEFAULT_ACQUIRE_TTL_HOURS)
    ttl_cutoff = now - timedelta(hours=ttl_hours)

    if text_source is None:
        # Skip if the TextSource row is missing; seed command should create it.
        return

    if not force:
        has_fresh = AcquisitionCandidate.objects.filter(
            text=text,
            text_source=text_source,
            fetched_at__gte=ttl_cutoff,
        ).exists()
        if has_fresh:
            return

    try:
        text_payload = {
            "isbn13": text.isbn13,
            "isbn10": text.isbn10,
            "oclc": text.oclc,
            "title": text.title,
            "authors": text.authors,
            "edition": text.edition,
            "publication_year": text.publication_year,
        }
        raw_candidates = connector.search(text_payload)
    except Exception:
        raw_candidates = []

    ranked = ranking.rank_candidates(raw_candidates)
    for cand in ranked:
        cand_source = cand.get("text_source") or text_source
        url = cand.get("url", "")
        if not cand_source or not url:
            # Skip candidates without a source or URL.
            continue

        defaults = {
            "match_score": cand.get("match_score", 0.0),
            "match_signals": cand.get("match_signals") or matching.default_match_signals(text_payload, cand),
            "access_type": cand.get("access_type", AcquisitionCandidate.PURCHASE_ONLY),
            "availability_snapshot": cand.get("availability_snapshot", {}),
            "price_amount": cand.get("price_amount"),
            "price_currency": cand.get("price_currency", ""),
            "fetched_at": now,
            "expires_at": cand.get("expires_at"),
        }
        AcquisitionCandidate.objects.update_or_create(
            text=text,
            text_source=cand_source,
            url=url,
            defaults=defaults,
        )

    AcquisitionLog.objects.create(
        user_id=actor_user_id,
        course_id=course_id,
        text=text,
        text_source=text_source,
        actor_role=actor_role,
        method=AcquisitionLog.METHOD_API,
        action=AcquisitionLog.ACTION_SEARCH,
        result=AcquisitionLog.RESULT_SUCCESS,
        metadata={"connector": name, "text_source_id": text_source.id, "candidates": len(ranked)},
    )


def _map_connectors_to_sources() -> dict:
    """
    Return a mapping of connector registry names to TextSource rows by source_name.
    """
    connector_names = {name: getattr(connector, "source_name", name) for name, connector in CONNECTOR_REGISTRY.items()}
    sources = TextSource.objects.in_bulk(connector_names.values(), field_name="name")
    return {name: sources.get(source_name) for name, source_name in connector_names.items()}
