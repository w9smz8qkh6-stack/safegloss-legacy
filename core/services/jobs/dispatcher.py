"""
Job Dispatcher.

Functions for enqueueing background jobs. Jobs are idempotent - if a job
with the same idempotency key already exists and is pending/running,
the existing job is returned instead of creating a duplicate.
"""

import logging
from typing import Optional
from django.db import IntegrityError

from core.models import BackgroundJob, User

logger = logging.getLogger(__name__)


def get_or_create_job(
    job_type: str,
    idempotency_key: str,
    params: dict = None,
    created_by: Optional[User] = None,
) -> tuple[BackgroundJob, bool]:
    """
    Get an existing pending job or create a new one.

    Args:
        job_type: Type of job (sync_standards, hydrate_media, etc.)
        idempotency_key: Unique key to prevent duplicates
        params: Job parameters as dict
        created_by: User who triggered the job (optional)

    Returns:
        Tuple of (job, created) where created is True if new job was created
    """
    # Check for existing pending/running job
    existing = BackgroundJob.objects.filter(
        idempotency_key=idempotency_key,
        status__in=["pending", "running"],
    ).first()

    if existing:
        logger.info(f"Job already exists: {idempotency_key} (status: {existing.status})")
        return existing, False

    # Create new job
    try:
        job = BackgroundJob.objects.create(
            job_type=job_type,
            idempotency_key=idempotency_key,
            params=params or {},
            created_by=created_by,
        )
        logger.info(f"Created job: {job_type} ({idempotency_key})")
        return job, True
    except IntegrityError:
        # Race condition - another process created the job
        existing = BackgroundJob.objects.get(idempotency_key=idempotency_key)
        return existing, False


def enqueue_job(
    job_type: str,
    idempotency_key: str,
    params: dict = None,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue a background job.

    Args:
        job_type: Type of job
        idempotency_key: Unique key for deduplication
        params: Job parameters
        created_by: User who triggered the job

    Returns:
        The created or existing BackgroundJob
    """
    job, created = get_or_create_job(job_type, idempotency_key, params, created_by)
    return job


def enqueue_standards_sync(
    program_code: str,
    subject: str,
    grade_level: str,
    version: Optional[str] = None,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue a standards sync job.

    Args:
        program_code: Authority program code (e.g., STATE_TX)
        subject: Subject area
        grade_level: Grade level
        version: Optional version label
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    # Build idempotency key
    key_parts = [
        "sync_standards",
        program_code,
        subject.replace(" ", "_"),
        grade_level.replace(" ", "_"),
    ]
    if version:
        key_parts.append(version)
    idempotency_key = ":".join(key_parts)

    params = {
        "program_code": program_code,
        "subject": subject,
        "grade_level": grade_level,
    }
    if version:
        params["version"] = version

    return enqueue_job(
        job_type="sync_standards",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )


def enqueue_media_hydration(
    media_id: int = None,
    program_code: str = None,
    force: bool = False,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue a media hydration job.

    Either hydrate a single media record (by media_id) or all
    un-hydrated media for a program.

    Args:
        media_id: Specific media ID to hydrate (optional)
        program_code: Program code to hydrate all media for (optional)
        force: Re-hydrate even if already done
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    if media_id:
        idempotency_key = f"hydrate_media:id:{media_id}"
        params = {"media_id": media_id, "force": force}
    elif program_code:
        idempotency_key = f"hydrate_media:program:{program_code}"
        params = {"program_code": program_code, "force": force}
    else:
        idempotency_key = "hydrate_media:all"
        params = {"force": force}

    return enqueue_job(
        job_type="hydrate_media",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )


def enqueue_course_bootstrap(
    program_code: str,
    platform: str = "khan_academy",
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue a platform course bootstrap job.

    Args:
        program_code: Authority program code
        platform: Platform to bootstrap (khan_academy, etc.)
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    idempotency_key = f"bootstrap_courses:{program_code}:{platform}"
    params = {
        "program_code": program_code,
        "platform": platform,
    }

    return enqueue_job(
        job_type="bootstrap_courses",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )


def enqueue_authority_resync(
    authority_code: str,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue a full authority re-sync job.

    Re-syncs all documents for an authority.

    Args:
        authority_code: Authority code (e.g., US_STATES)
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    idempotency_key = f"resync_authority:{authority_code}"
    params = {
        "authority_code": authority_code,
    }

    return enqueue_job(
        job_type="resync_authority",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )


def enqueue_authority_objectives_sync(
    authority_id: int,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue an authority objectives sync job.

    Syncs learning objectives for all programs under an authority.
    Checks for newer versions, imports them, and marks old versions
    as superseded.

    Args:
        authority_id: StandardsAuthority primary key
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    idempotency_key = f"sync_authority_objectives:{authority_id}"
    params = {
        "authority_id": authority_id,
    }

    return enqueue_job(
        job_type="sync_authority_objectives",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )


def enqueue_authority_resources_sync(
    authority_id: int,
    created_by: Optional[User] = None,
) -> BackgroundJob:
    """
    Enqueue an authority resources sync job.

    Discovers and syncs educational resources (textbooks, courses, etc.)
    for all programs under an authority.

    Args:
        authority_id: StandardsAuthority primary key
        created_by: User who triggered the job

    Returns:
        BackgroundJob instance
    """
    idempotency_key = f"sync_authority_resources:{authority_id}"
    params = {
        "authority_id": authority_id,
    }

    return enqueue_job(
        job_type="sync_authority_resources",
        idempotency_key=idempotency_key,
        params=params,
        created_by=created_by,
    )
