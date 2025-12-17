"""
Job Worker.

Processes pending background jobs. Can be run via management command
or scheduled via cron.
"""

import logging
import traceback
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import BackgroundJob, AuthorityProgram, AuthorityProgramMedia

logger = logging.getLogger(__name__)


class JobError(Exception):
    """Error during job processing."""
    pass


def get_pending_jobs(limit: int = 10) -> list[BackgroundJob]:
    """
    Get pending jobs that are ready to run.

    Respects next_retry_at for jobs scheduled for retry.

    Args:
        limit: Maximum number of jobs to return

    Returns:
        List of BackgroundJob instances
    """
    now = timezone.now()

    return list(
        BackgroundJob.objects.filter(
            status="pending",
        ).filter(
            # Either no retry scheduled, or retry time has passed
            models.Q(next_retry_at__isnull=True) |
            models.Q(next_retry_at__lte=now)
        ).order_by("created_at")[:limit]
    )


from django.db import models  # Import at module level for Q


def process_job(job: BackgroundJob) -> bool:
    """
    Process a single job.

    Args:
        job: The BackgroundJob to process

    Returns:
        True if job completed successfully, False otherwise
    """
    logger.info(f"Processing job {job.pk}: {job.job_type}")

    try:
        job.mark_running()

        # Dispatch to appropriate handler
        if job.job_type == "sync_standards":
            result = _handle_sync_standards(job)
        elif job.job_type == "hydrate_media":
            result = _handle_hydrate_media(job)
        elif job.job_type == "bootstrap_courses":
            result = _handle_bootstrap_courses(job)
        elif job.job_type == "resync_authority":
            result = _handle_resync_authority(job)
        elif job.job_type == "sync_authority_objectives":
            result = _handle_sync_authority_objectives(job)
        elif job.job_type == "sync_authority_resources":
            result = _handle_sync_authority_resources(job)
        else:
            raise JobError(f"Unknown job type: {job.job_type}")

        job.mark_completed(result)
        logger.info(f"Job {job.pk} completed successfully")
        return True

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Job {job.pk} failed: {error_msg}")

        if job.can_retry():
            # Schedule retry with exponential backoff
            delay = 60 * (2 ** job.retry_count)  # 60s, 120s, 240s, ...
            job.schedule_retry(delay)
            logger.info(f"Job {job.pk} scheduled for retry in {delay}s")
        else:
            job.mark_failed(error_msg)

        return False


def process_pending_jobs(limit: int = 10) -> dict:
    """
    Process all pending jobs up to the limit.

    Args:
        limit: Maximum number of jobs to process

    Returns:
        Summary dict with success/failure counts
    """
    results = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "details": [],
    }

    jobs = get_pending_jobs(limit)
    logger.info(f"Found {len(jobs)} pending jobs")

    for job in jobs:
        results["processed"] += 1

        success = process_job(job)

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "job_id": job.pk,
            "job_type": job.job_type,
            "success": success,
            "status": job.status,
        })

    return results


# =============================================================================
# Job Handlers
# =============================================================================

def _handle_sync_standards(job: BackgroundJob) -> dict:
    """Handle sync_standards job."""
    from core.services.standards import sync_document
    from core.services.standards.providers import get_provider

    params = job.params
    program_code = params["program_code"]
    subject = params["subject"]
    grade_level = params["grade_level"]
    version = params.get("version")

    job.update_progress(10, f"Fetching standards from {program_code}...")

    # Check provider exists
    provider_cls = get_provider(program_code)
    if not provider_cls:
        raise JobError(f"No provider registered for: {program_code}")

    job.update_progress(30, "Validating provenance...")

    # Sync the document
    doc = sync_document(program_code, subject, grade_level, version)

    job.update_progress(90, "Finalizing...")

    return {
        "document_id": doc.pk,
        "subject": doc.subject,
        "grade_level": doc.grade_level,
        "objectives_count": doc.objective_nodes.count(),
    }


def _handle_hydrate_media(job: BackgroundJob) -> dict:
    """Handle hydrate_media job."""
    from core.services.media import hydrate_media
    from core.services.media.hydration import hydrate_media_batch

    params = job.params
    media_id = params.get("media_id")
    program_code = params.get("program_code")
    force = params.get("force", False)

    if media_id:
        # Single media hydration
        job.update_progress(20, f"Hydrating media {media_id}...")

        try:
            media = AuthorityProgramMedia.objects.get(pk=media_id)
        except AuthorityProgramMedia.DoesNotExist:
            raise JobError(f"Media not found: {media_id}")

        result = hydrate_media(media, force=force)

        return {
            "media_id": media_id,
            "success": result.success,
            "source": result.source,
            "error": result.error,
        }

    elif program_code:
        # Program-wide hydration
        job.update_progress(10, f"Finding media for {program_code}...")

        try:
            program = AuthorityProgram.objects.get(code=program_code)
        except AuthorityProgram.DoesNotExist:
            raise JobError(f"Program not found: {program_code}")

        qs = AuthorityProgramMedia.objects.filter(authority_program=program)
        if not force:
            qs = qs.filter(retrieved_from="")

        total = qs.count()
        job.update_progress(20, f"Hydrating {total} media records...")

        results = hydrate_media_batch(qs, force=force)

        return results

    else:
        # All un-hydrated media
        job.update_progress(10, "Finding un-hydrated media...")

        qs = AuthorityProgramMedia.objects.filter(retrieved_from="")
        if force:
            qs = AuthorityProgramMedia.objects.all()

        total = qs.count()
        job.update_progress(20, f"Hydrating {total} media records...")

        results = hydrate_media_batch(qs, force=force)

        return results


def _handle_bootstrap_courses(job: BackgroundJob) -> dict:
    """Handle bootstrap_courses job."""
    from core.services.media import bootstrap_khan_academy_courses

    params = job.params
    program_code = params["program_code"]
    platform = params.get("platform", "khan_academy")

    job.update_progress(20, f"Bootstrapping {platform} courses for {program_code}...")

    try:
        program = AuthorityProgram.objects.get(code=program_code)
    except AuthorityProgram.DoesNotExist:
        raise JobError(f"Program not found: {program_code}")

    if platform == "khan_academy":
        results = bootstrap_khan_academy_courses(program)
    else:
        raise JobError(f"Unsupported platform: {platform}")

    job.update_progress(90, "Finalizing...")

    return results


def _handle_resync_authority(job: BackgroundJob) -> dict:
    """Handle resync_authority job."""
    from core.models import StandardsAuthority, StandardsDocument
    from core.services.standards import sync_document
    from core.services.standards.providers import get_provider, list_registered_providers

    params = job.params
    authority_code = params["authority_code"]

    job.update_progress(10, f"Finding programs for {authority_code}...")

    try:
        authority = StandardsAuthority.objects.get(code=authority_code)
    except StandardsAuthority.DoesNotExist:
        raise JobError(f"Authority not found: {authority_code}")

    # Get all programs for this authority
    programs = authority.programs.filter(is_active=True)
    registered = list_registered_providers()

    results = {
        "authority": authority_code,
        "programs_checked": 0,
        "documents_synced": 0,
        "errors": [],
    }

    for program in programs:
        results["programs_checked"] += 1

        if program.code not in registered:
            results["errors"].append(f"No provider for {program.code}")
            continue

        # Get existing documents to find what subjects/grades to sync
        docs = StandardsDocument.objects.filter(authority_program=program)

        for doc in docs:
            try:
                sync_document(
                    program.code,
                    doc.subject,
                    doc.grade_level,
                    None,  # Let provider fetch latest
                )
                results["documents_synced"] += 1
            except Exception as e:
                results["errors"].append(
                    f"{program.code} {doc.subject} {doc.grade_level}: {str(e)}"
                )

        pct = 10 + int(80 * results["programs_checked"] / programs.count())
        job.update_progress(pct, f"Synced {program.code}")

    return results


def _handle_sync_authority_objectives(job: BackgroundJob) -> dict:
    """
    Handle sync_authority_objectives job.

    Syncs learning objectives for all programs under an authority, or a subset of documents if provided.
    """
    from core.models import StandardsAuthority, StandardsDocument, AuthorityProgram
    from core.services.standards import sync_document
    from core.services.standards.providers import get_provider, list_registered_providers
    from django.utils import timezone

    params = job.params
    authority_id = params["authority_id"]
    document_ids = params.get("document_ids", [])
    syllabus_url_override = params.get("syllabus_url")

    job.update_progress(5, "Loading authority...")

    try:
        authority = StandardsAuthority.objects.get(pk=authority_id)
    except StandardsAuthority.DoesNotExist:
        raise JobError(f"Authority not found: {authority_id}")

    job.update_progress(10, f"Syncing objectives for {authority.name}...")

    # Get all active programs for this authority
    programs = authority.programs.filter(is_active=True)
    registered = list_registered_providers()

    # If document_ids provided, limit scope
    doc_map = {}
    if document_ids:
        docs = StandardsDocument.objects.filter(pk__in=document_ids, authority_program__authority=authority)
        programs = programs.filter(pk__in=docs.values_list("authority_program_id", flat=True))
        for doc in docs:
            doc_map.setdefault(doc.authority_program_id, []).append(doc)

    results = {
        "authority": authority.code,
        "authority_name": authority.name,
        "programs_checked": 0,
        "documents_synced": 0,
        "documents_superseded": 0,
        "errors": [],
    }

    total_programs = programs.count()
    for idx, program in enumerate(programs):
        results["programs_checked"] += 1

        # Update program sync status
        program.objectives_sync_status = "syncing"
        program.save(update_fields=["objectives_sync_status"])

        if program.code not in registered:
            results["errors"].append(f"No provider for {program.code}")
            program.objectives_sync_status = "error"
            program.save(update_fields=["objectives_sync_status"])
            continue

        try:
            provider_cls = get_provider(program.code)
            provider = provider_cls()

            if document_ids:
                docs = doc_map.get(program.pk, [])
                for doc in docs:
                    try:
                        new_doc = sync_document(
                            program.code,
                            doc.subject,
                            doc.grade_level,
                            None,
                            syllabus_url=syllabus_url_override,
                        )
                        if new_doc is None:
                            continue
                        if doc.pk != new_doc.pk:
                            doc.mark_superseded(new_doc)
                            results["documents_superseded"] += 1
                        results["documents_synced"] += 1
                    except Exception as e:
                        results["errors"].append(f"{program.code} {doc.subject} {doc.grade_level}: {str(e)}")
            else:
                # Get available subjects and grades from provider
                subjects = provider.list_available_subjects()
                for subject in subjects:
                    grades = provider.list_available_grades(subject)
                    for grade in grades:
                        try:
                            new_doc = sync_document(
                                program.code,
                                subject,
                                grade,
                                None,  # Let provider determine version
                            )

                            if new_doc is None:
                                continue

                            existing = StandardsDocument.objects.filter(
                                authority_program=program,
                                subject=subject,
                                grade_level=grade,
                                status="current",
                            ).exclude(pk=new_doc.pk).first()

                            if existing:
                                existing.mark_superseded(new_doc)
                                results["documents_superseded"] += 1

                            results["documents_synced"] += 1

                        except Exception as e:
                            results["errors"].append(
                                f"{program.code} {subject} {grade}: {str(e)}"
                            )

            # Update program sync status
            program.objectives_sync_status = "success"
            program.last_objectives_sync = timezone.now()
            program.save(update_fields=["objectives_sync_status", "last_objectives_sync"])

        except Exception as e:
            results["errors"].append(f"{program.code}: {str(e)}")
            program.objectives_sync_status = "error"
            program.save(update_fields=["objectives_sync_status"])

        pct = 10 + int(80 * (idx + 1) / total_programs)
        job.update_progress(pct, f"Synced {program.code}")

    job.update_progress(95, "Finalizing...")

    return results


def _handle_sync_authority_resources(job: BackgroundJob) -> dict:
    """
    Handle sync_authority_resources job.

    Discovers and syncs educational resources for all programs under an authority.
    """
    from core.models import (
        StandardsAuthority,
        AuthorityProgram,
        AuthorityProgramMedia,
        StandardsDocument,
        ObjectiveNode,
    )
    from core.services.resources import (
        create_resource_provider,
        list_registered_resource_providers,
    )
    from django.utils import timezone

    params = job.params
    authority_id = params["authority_id"]

    job.update_progress(5, "Loading authority...")

    try:
        authority = StandardsAuthority.objects.get(pk=authority_id)
    except StandardsAuthority.DoesNotExist:
        raise JobError(f"Authority not found: {authority_id}")

    job.update_progress(10, f"Discovering resources for {authority.name}...")

    # Get all active programs for this authority
    programs = authority.programs.filter(is_active=True)
    registered_providers = list_registered_resource_providers()

    results = {
        "authority": authority.code,
        "authority_name": authority.name,
        "programs_checked": 0,
        "resources_discovered": 0,
        "resources_created": 0,
        "resources_updated": 0,
        "errors": [],
    }

    # Limit scope to specific documents if provided
    if document_ids:
        docs = StandardsDocument.objects.filter(pk__in=document_ids, authority_program__authority=authority)
        programs = programs.filter(pk__in=docs.values_list("authority_program_id", flat=True))
        doc_map = {}
        for doc in docs:
            doc_map.setdefault(doc.authority_program_id, []).append(doc)
    else:
        doc_map = {}

    total_programs = programs.count()
    for idx, program in enumerate(programs):
        results["programs_checked"] += 1

        # Update program sync status
        program.resources_sync_status = "syncing"
        program.save(update_fields=["resources_sync_status"])

        if program.code not in registered_providers:
            results["errors"].append(f"No resource provider for {program.code}")
            program.resources_sync_status = "error"
            program.save(update_fields=["resources_sync_status"])
            continue

        try:
            provider = create_resource_provider(program.code)

            # Get target documents (limited set or all current)
            if document_ids:
                docs = doc_map.get(program.pk, [])
            else:
                docs = StandardsDocument.objects.filter(
                    authority_program=program,
                    status="current",
                )

            for doc in docs:
                try:
                    # Discover resources for this subject/grade
                    discovery_result = provider.discover_resources(
                        doc.subject,
                        doc.grade_level,
                    )

                    results["resources_discovered"] += len(discovery_result.resources)

                    # Create or update media records
                    for resource_data in discovery_result.resources:
                        media, created = AuthorityProgramMedia.objects.update_or_create(
                            authority_program=program,
                            source_url=resource_data.source_url,
                            defaults={
                                "title": resource_data.title,
                                "author": resource_data.author,
                                "publisher": resource_data.publisher,
                                "description": resource_data.description,
                                "media_type": resource_data.media_type,
                                "platform": resource_data.platform,
                                "isbn_10": resource_data.isbn_10,
                                "isbn_13": resource_data.isbn_13,
                                "cover_image_url": resource_data.cover_image_url,
                                "publisher_url": resource_data.publisher_url,
                                "is_official": resource_data.is_official,
                                "recommendation_tier": resource_data.recommendation_tier,
                                "resource_category": resource_data.resource_category or "official",
                                "audience": resource_data.audience or "general",
                                "is_companion": bool(resource_data.is_companion),
                                "endorsement_notes": resource_data.endorsement_notes,
                                "features": resource_data.features,
                                "retrieved_from": resource_data.retrieved_from or "platform_scrape",
                                "retrieved_at": timezone.now(),
                                "metadata_raw": resource_data.metadata or {},
                            },
                        )

                        if created:
                            results["resources_created"] += 1
                        else:
                            results["resources_updated"] += 1

                        # Link to objectives if codes provided
                        if resource_data.aligned_objective_codes:
                            objectives = ObjectiveNode.objects.filter(
                                document__authority_program=program,
                                code__in=resource_data.aligned_objective_codes,
                            )
                            media.aligned_objectives.add(*objectives)

                except Exception as e:
                    results["errors"].append(
                        f"{program.code} {doc.subject} {doc.grade_level}: {str(e)}"
                    )

            # Update program sync status
            program.resources_sync_status = "success"
            program.last_resources_sync = timezone.now()
            program.save(update_fields=["resources_sync_status", "last_resources_sync"])

        except Exception as e:
            results["errors"].append(f"{program.code}: {str(e)}")
            program.resources_sync_status = "error"
            program.save(update_fields=["resources_sync_status"])

        pct = 10 + int(80 * (idx + 1) / total_programs)
        job.update_progress(pct, f"Synced resources for {program.code}")

    job.update_progress(95, "Finalizing...")

    return results
