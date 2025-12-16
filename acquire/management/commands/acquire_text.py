from django.core.management.base import BaseCommand, CommandParser

from acquire.services.acquire_text import run_acquire_for_course


class Command(BaseCommand):
    help = "Run Acquire Text for a course (placeholder orchestration)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--course", type=int, required=True, help="Course ID to run acquisition for")
        parser.add_argument("--actor", type=int, required=True, help="User ID running the command")
        parser.add_argument("--role", type=str, default="teacher_dev_override", help="Actor role label")
        parser.add_argument("--force", action="store_true", help="Force refresh even if cached")

    def handle(self, *args, **options):
        course_id = options["course"]
        actor_id = options["actor"]
        role = options["role"]
        force = options["force"]

        run_acquire_for_course(course_id=course_id, actor_user_id=actor_id, actor_role=role, force=force)
        self.stdout.write(self.style.SUCCESS(f"Acquire Text run initiated for course={course_id} actor={actor_id}"))
