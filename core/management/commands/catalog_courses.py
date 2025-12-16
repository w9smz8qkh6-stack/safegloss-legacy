"""
Management command to catalog platform courses for authority programs.

Usage:
    # Catalog a single course
    python manage.py catalog_courses --program=STATE_TX --url="https://khanacademy.org/math/algebra" --title="Algebra 1" --official

    # Bootstrap Khan Academy courses for a program
    python manage.py catalog_courses --program=CCSS_MATH --bootstrap-khan

    # Import from JSON file
    python manage.py catalog_courses --program=STATE_TX --json=courses.json
"""

import json
import logging
from django.core.management.base import BaseCommand, CommandError
from core.models import AuthorityProgram
from core.services.media.platform_courses import (
    catalog_course,
    catalog_courses_batch,
    detect_platform,
    bootstrap_khan_academy_courses,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Catalog platform courses (Khan Academy, YouTube, Udemy, etc.) for authority programs"

    def add_arguments(self, parser):
        # Target program (required)
        parser.add_argument(
            "--program",
            type=str,
            required=True,
            help="Authority program code (e.g., STATE_TX, CCSS_ELA)",
        )

        # Single course
        parser.add_argument(
            "--url",
            type=str,
            help="Course URL",
        )
        parser.add_argument(
            "--title",
            type=str,
            help="Course title",
        )
        parser.add_argument(
            "--description",
            type=str,
            default="",
            help="Course description",
        )
        parser.add_argument(
            "--author",
            type=str,
            default="",
            help="Course author/instructor",
        )
        parser.add_argument(
            "--official",
            action="store_true",
            help="Mark as officially endorsed",
        )
        parser.add_argument(
            "--notes",
            type=str,
            default="",
            help="Endorsement notes",
        )
        parser.add_argument(
            "--tags",
            type=str,
            help="Comma-separated tags",
        )

        # Bootstrap options
        parser.add_argument(
            "--bootstrap-khan",
            action="store_true",
            help="Bootstrap Khan Academy courses for the program",
        )

        # Batch import
        parser.add_argument(
            "--json",
            type=str,
            help="JSON file with courses to import",
        )

        # Dry run
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without saving",
        )

    def handle(self, *args, **options):
        # Get the authority program
        program_code = options["program"]
        try:
            program = AuthorityProgram.objects.get(code=program_code)
        except AuthorityProgram.DoesNotExist:
            available = AuthorityProgram.objects.values_list("code", flat=True)
            raise CommandError(
                f"Program not found: {program_code}\n"
                f"Available: {', '.join(available) or 'none (run sync_standards first)'}"
            )

        self.stdout.write(f"Target program: {program.name} ({program.code})")

        dry_run = options["dry_run"]

        if options["bootstrap_khan"]:
            self.bootstrap_khan(program, dry_run)
        elif options["json"]:
            self.import_from_json(program, options["json"], dry_run)
        elif options["url"]:
            self.catalog_single_course(program, options, dry_run)
        else:
            raise CommandError(
                "Specify one of: --url with --title, --bootstrap-khan, or --json"
            )

    def catalog_single_course(self, program, options, dry_run):
        """Catalog a single course from command line options."""
        url = options["url"]
        title = options.get("title")

        if not title:
            raise CommandError("--title is required when using --url")

        platform = detect_platform(url)

        self.stdout.write(f"\nCataloging course:")
        self.stdout.write(f"  URL: {url}")
        self.stdout.write(f"  Title: {title}")
        self.stdout.write(f"  Platform: {platform}")
        self.stdout.write(f"  Official: {options['official']}")

        if dry_run:
            self.stdout.write("\n[DRY RUN] Would create course record")
            return

        tags = options["tags"].split(",") if options.get("tags") else None

        media = catalog_course(
            authority_program=program,
            url=url,
            title=title,
            description=options.get("description", ""),
            author=options.get("author", ""),
            is_official=options["official"],
            endorsement_notes=options.get("notes", ""),
            tags=tags,
        )

        self.stdout.write(self.style.SUCCESS(f"\nCreated course: {media.title}"))
        self.stdout.write(f"  ID: {media.pk}")
        self.stdout.write(f"  Platform: {media.get_platform_display()}")

    def bootstrap_khan(self, program, dry_run):
        """Bootstrap Khan Academy courses for the program."""
        self.stdout.write(f"\nBootstrapping Khan Academy courses for {program.code}...")

        if dry_run:
            self.stdout.write("[DRY RUN] Would create Khan Academy courses")

            # Show what would be created
            from core.services.media.platform_courses import (
                KHAN_ACADEMY_MATH_COURSES,
                KHAN_ACADEMY_ELA_COURSES,
            )

            program_code = program.code.upper()
            courses = []

            if "MATH" in program_code or "CCSS" in program_code:
                courses.extend(KHAN_ACADEMY_MATH_COURSES)
            if "ELA" in program_code or "ENGLISH" in program_code:
                courses.extend(KHAN_ACADEMY_ELA_COURSES)
            if not courses:
                courses = KHAN_ACADEMY_MATH_COURSES

            self.stdout.write(f"\nWould create {len(courses)} courses:")
            for course in courses:
                self.stdout.write(f"  - {course['title']}")

            return

        results = bootstrap_khan_academy_courses(program)

        self.stdout.write(f"\n\nResults:")
        self.stdout.write(f"  Total: {results['total']}")
        self.stdout.write(self.style.SUCCESS(f"  Created: {results['created']}"))
        self.stdout.write(self.style.ERROR(f"  Failed: {results['failed']}"))

        if results["details"]:
            self.stdout.write("\nDetails:")
            for detail in results["details"]:
                if "error" in detail:
                    self.stdout.write(self.style.ERROR(f"  - {detail['title']}: {detail['error']}"))
                else:
                    self.stdout.write(f"  - {detail['title']} ({detail['platform']})")

    def import_from_json(self, program, json_path, dry_run):
        """Import courses from a JSON file."""
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Error reading JSON file: {e}")

        # Support both list of courses and {courses: [...]} format
        if isinstance(data, dict) and "courses" in data:
            courses = data["courses"]
        elif isinstance(data, list):
            courses = data
        else:
            raise CommandError("JSON must be a list of courses or {courses: [...]}")

        self.stdout.write(f"\nFound {len(courses)} courses in JSON file")

        if dry_run:
            self.stdout.write("[DRY RUN] Would import courses:")
            for course in courses[:10]:
                self.stdout.write(f"  - {course.get('title', 'Untitled')}")
            if len(courses) > 10:
                self.stdout.write(f"  ... and {len(courses) - 10} more")
            return

        results = catalog_courses_batch(program, courses)

        self.stdout.write(f"\n\nResults:")
        self.stdout.write(f"  Total: {results['total']}")
        self.stdout.write(self.style.SUCCESS(f"  Created: {results['created']}"))
        self.stdout.write(self.style.ERROR(f"  Failed: {results['failed']}"))
