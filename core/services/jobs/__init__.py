"""
Background Job Processing Service.

This module provides a lightweight job queue system for async processing of:
- Standards imports and syncs
- Media hydration
- Platform course cataloging

Jobs are stored in the BackgroundJob model and can be processed via:
- Management command (cron): `python manage.py run_jobs`
- Future upgrade to Celery/django-q workers
"""

from .dispatcher import (
    enqueue_job,
    enqueue_standards_sync,
    enqueue_media_hydration,
    enqueue_course_bootstrap,
    enqueue_authority_resync,
    enqueue_authority_objectives_sync,
    enqueue_authority_resources_sync,
    get_or_create_job,
)
from .worker import process_pending_jobs, process_job, JobError

__all__ = [
    "enqueue_job",
    "enqueue_standards_sync",
    "enqueue_media_hydration",
    "enqueue_course_bootstrap",
    "enqueue_authority_resync",
    "enqueue_authority_objectives_sync",
    "enqueue_authority_resources_sync",
    "get_or_create_job",
    "process_pending_jobs",
    "process_job",
    "JobError",
]
