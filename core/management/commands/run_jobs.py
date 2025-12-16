"""
Management command to process pending background jobs.

Usage:
    # Process up to 10 pending jobs
    python manage.py run_jobs

    # Process up to 50 jobs
    python manage.py run_jobs --limit=50

    # Run continuously (daemon mode)
    python manage.py run_jobs --daemon --interval=30

    # List pending jobs without processing
    python manage.py run_jobs --list

This can be scheduled via cron:
    */5 * * * * cd /path/to/project && python manage.py run_jobs
"""

import logging
import signal
import time
from django.core.management.base import BaseCommand
from core.models import BackgroundJob
from core.services.jobs import process_pending_jobs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process pending background jobs"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of jobs to process (default: 10)",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run continuously in daemon mode",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Seconds between job checks in daemon mode (default: 30)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List pending jobs without processing",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show job statistics",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self.list_jobs()
            return

        if options["stats"]:
            self.show_stats()
            return

        limit = options["limit"]

        if options["daemon"]:
            self.run_daemon(limit, options["interval"])
        else:
            self.run_once(limit)

    def run_once(self, limit: int):
        """Process jobs once and exit."""
        self.stdout.write(f"Processing up to {limit} pending jobs...")

        results = process_pending_jobs(limit)

        self.stdout.write(f"\nProcessed: {results['processed']}")
        self.stdout.write(self.style.SUCCESS(f"Success: {results['success']}"))
        self.stdout.write(self.style.ERROR(f"Failed: {results['failed']}"))

        if results["details"]:
            self.stdout.write("\nDetails:")
            for detail in results["details"]:
                status_style = (
                    self.style.SUCCESS if detail["success"]
                    else self.style.ERROR
                )
                self.stdout.write(
                    f"  [{detail['job_id']}] {detail['job_type']}: "
                    f"{status_style(detail['status'])}"
                )

    def run_daemon(self, limit: int, interval: int):
        """Run continuously, processing jobs every interval."""
        self.stdout.write(f"Starting daemon mode (interval: {interval}s, limit: {limit})")
        self.stdout.write("Press Ctrl+C to stop")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        while not self._shutdown:
            pending_count = BackgroundJob.objects.filter(status="pending").count()

            if pending_count > 0:
                self.stdout.write(f"\n[{time.strftime('%H:%M:%S')}] Found {pending_count} pending jobs")
                results = process_pending_jobs(limit)
                self.stdout.write(
                    f"  Processed: {results['processed']}, "
                    f"Success: {results['success']}, "
                    f"Failed: {results['failed']}"
                )
            else:
                self.stdout.write(f"[{time.strftime('%H:%M:%S')}] No pending jobs", ending="\r")

            # Sleep in small intervals to allow graceful shutdown
            for _ in range(interval):
                if self._shutdown:
                    break
                time.sleep(1)

        self.stdout.write("\nShutdown complete")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        self.stdout.write("\nReceived shutdown signal, finishing current job...")
        self._shutdown = True

    def list_jobs(self):
        """List pending jobs."""
        jobs = BackgroundJob.objects.filter(
            status__in=["pending", "running"]
        ).order_by("-created_at")[:50]

        if not jobs:
            self.stdout.write("No pending or running jobs")
            return

        self.stdout.write(f"\nPending/Running Jobs ({jobs.count()}):")
        self.stdout.write("-" * 80)

        for job in jobs:
            status_style = (
                self.style.WARNING if job.status == "running"
                else self.style.HTTP_INFO
            )
            self.stdout.write(
                f"[{job.pk}] {status_style(job.status.upper())} "
                f"{job.get_job_type_display()}\n"
                f"     Key: {job.idempotency_key}\n"
                f"     Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if job.retry_count > 0:
                self.stdout.write(f"     Retries: {job.retry_count}/{job.max_retries}")
            self.stdout.write("")

    def show_stats(self):
        """Show job statistics."""
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        self.stdout.write("\nJob Statistics")
        self.stdout.write("=" * 50)

        # Status breakdown
        status_counts = dict(
            BackgroundJob.objects.values("status").annotate(
                count=Count("id")
            ).values_list("status", "count")
        )

        self.stdout.write("\nBy Status:")
        for status, label in BackgroundJob.STATUS_CHOICES:
            count = status_counts.get(status, 0)
            if status == "completed":
                style = self.style.SUCCESS
            elif status == "failed":
                style = self.style.ERROR
            elif status == "running":
                style = self.style.WARNING
            else:
                style = lambda x: x
            self.stdout.write(f"  {label}: {style(str(count))}")

        # Recent activity
        recent_completed = BackgroundJob.objects.filter(
            status="completed",
            completed_at__gte=day_ago
        ).count()

        recent_failed = BackgroundJob.objects.filter(
            status="failed",
            completed_at__gte=day_ago
        ).count()

        self.stdout.write(f"\nLast 24 hours:")
        self.stdout.write(f"  Completed: {self.style.SUCCESS(str(recent_completed))}")
        self.stdout.write(f"  Failed: {self.style.ERROR(str(recent_failed))}")

        # By type (last week)
        type_counts = dict(
            BackgroundJob.objects.filter(
                created_at__gte=week_ago
            ).values("job_type").annotate(
                count=Count("id")
            ).values_list("job_type", "count")
        )

        if type_counts:
            self.stdout.write(f"\nLast 7 days by type:")
            for job_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {job_type}: {count}")
