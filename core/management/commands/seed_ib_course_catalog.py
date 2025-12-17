"""
Management command to seed International Baccalaureate course catalog from JSON.
Creates StandardsDocument entries for each course in the catalog.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import StandardsAuthority, AuthorityProgram, StandardsDocument


class Command(BaseCommand):
    help = "Seed International Baccalaureate course catalog from JSON file into StandardsDocument entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/seeds/ib_course_catalog.json",
            help="Path to the course catalog JSON file",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update existing records instead of skipping them",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        force = options["force"]
        dry_run = options["dry_run"]

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, "r") as f:
            catalog = json.load(f)

        # Get or create the authority
        authority_data = catalog["authority"]
        program_data = catalog["program"]
        source_data = catalog["source"]

        authority, auth_created = StandardsAuthority.objects.get_or_create(
            code=authority_data["code"],
            defaults={
                "name": authority_data["name"],
                "is_active": True,
            }
        )
        if auth_created:
            self.stdout.write(self.style.SUCCESS(f"Created authority: {authority.name}"))

        # Create the main IB program
        main_program, prog_created = AuthorityProgram.objects.get_or_create(
            authority=authority,
            code=program_data["code"],
            defaults={
                "name": program_data["name"],
                "description": program_data.get("description", ""),
                "is_active": True,
            }
        )
        if prog_created:
            self.stdout.write(self.style.SUCCESS(f"Created program: {main_program.name}"))

        # Process each programme (PYP, MYP, DP, CP)
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for programme in catalog["programmes"]:
            programme_name = programme["name"]
            programme_code = programme["code"]
            age_range = programme["age_range"]
            programme_desc = programme.get("description", "")

            # Create sub-program for each IB programme level
            sub_program, sub_created = AuthorityProgram.objects.get_or_create(
                authority=authority,
                code=f"IB_{programme_code}",
                defaults={
                    "name": programme_name,
                    "description": programme_desc,
                    "is_active": True,
                }
            )
            if sub_created:
                self.stdout.write(self.style.SUCCESS(f"  Created sub-program: {programme_name}"))

            self.stdout.write(f"\nProcessing {programme_name} (Ages {age_range})...")

            for course in programme["courses"]:
                syllabus_code = course["syllabus_code"]
                course_name = course["name"]
                subject_group = course.get("subject_group", "General")
                levels = course.get("levels", [])  # For DP courses with SL/HL
                version = course.get("version", "Current")
                course_url = course.get("url")  # Course-specific URL if available

                # Build grade level string based on programme
                if programme_code == "PYP":
                    grade_level = "Primary Years (Ages 3-12)"
                elif programme_code == "MYP":
                    grade_level = "Middle Years (Ages 11-16)"
                elif programme_code == "DP":
                    if levels:
                        level_str = "/".join(levels)
                        grade_level = f"Diploma ({level_str}, Ages 16-19)"
                    else:
                        grade_level = "Diploma (Ages 16-19)"
                elif programme_code == "CP":
                    grade_level = "Career-related (Ages 16-19)"
                else:
                    grade_level = f"Ages {age_range}"

                # Check if document already exists (by syllabus_code, which is unique per course)
                existing = StandardsDocument.objects.filter(
                    authority_program=sub_program,
                    syllabus_code=syllabus_code,
                ).first()

                if existing and not force:
                    skipped_count += 1
                    continue

                if dry_run:
                    action = "Would update" if existing else "Would create"
                    self.stdout.write(f"  {action}: {course_name} ({syllabus_code})")
                    if existing:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                # Use course-specific URL if available, otherwise fall back to program URL
                document_url = course_url if course_url else programme.get("url", source_data["url"])

                # Build document defaults
                defaults = {
                    "grade_level": grade_level,
                    "version_label": version,
                    "source_publisher_name": source_data["publisher"],
                    "source_publisher_type": source_data["publisher_type"],
                    "source_title": course_name,
                    "source_url": document_url,
                    "acquisition_method": source_data["acquisition_method"],
                    "acquisition_notes": f"{programme_name} - {course_name} (Code {syllabus_code}). Subject Group: {subject_group}.",
                    "is_active": True,
                    "status": "current",
                }

                # Add level info for DP courses
                if levels:
                    defaults["acquisition_notes"] += f" Levels: {', '.join(levels)}."

                if existing:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                    self.stdout.write(f"  Updated: {course_name}")
                else:
                    StandardsDocument.objects.create(
                        authority_program=sub_program,
                        subject=subject_group,
                        syllabus_code=syllabus_code,
                        **defaults
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created: {course_name}"))

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}"
        ))
        self.stdout.write(f"Total courses in catalog: {created_count + updated_count + skipped_count}")
