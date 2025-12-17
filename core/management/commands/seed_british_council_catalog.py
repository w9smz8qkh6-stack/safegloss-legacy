"""
Management command to seed British Council course catalog from JSON.
Creates StandardsDocument entries for English courses, teaching qualifications, and assessments.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import StandardsAuthority, AuthorityProgram, StandardsDocument


class Command(BaseCommand):
    help = "Seed British Council course catalog from JSON file into StandardsDocument entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/seeds/british_council_course_catalog.json",
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

        # Create programs
        programs = {}
        for program_data in catalog["programs"]:
            program, prog_created = AuthorityProgram.objects.get_or_create(
                authority=authority,
                code=program_data["code"],
                defaults={
                    "name": program_data["name"],
                    "description": program_data.get("description", ""),
                    "is_active": True,
                }
            )
            programs[program_data["code"]] = program
            if prog_created:
                self.stdout.write(self.style.SUCCESS(f"Created program: {program.name}"))

        # Process subjects and courses
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for subject_data in catalog["subjects"]:
            subject_name = subject_data["name"]
            program_code = subject_data["program"]
            program = programs[program_code]

            self.stdout.write(f"\nProcessing {subject_name} ({program_code})...")

            for course in subject_data["courses"]:
                course_code = course["code"]
                course_name = course["name"]
                grade = course["grade"]
                grade_band = course.get("grade_band", "adult")
                course_type = course.get("course_type", "")
                discipline = course.get("discipline", "")
                cefr_level = course.get("cefr_level", "")
                credits = course.get("credits")
                qcf_level = course.get("qcf_level")
                hours = course.get("hours")

                # Build grade level string
                if grade_band == "adult":
                    grade_level = "Adult"
                elif grade_band == "elementary":
                    grade_level = f"Ages {grade}" if "Ages" not in str(grade) else grade
                elif grade_band == "middle_school":
                    grade_level = f"Ages {grade}" if "Ages" not in str(grade) else grade
                elif grade_band == "high_school":
                    grade_level = f"Ages {grade}" if "Ages" not in str(grade) else grade
                else:
                    grade_level = str(grade)

                # Check if document already exists
                existing = StandardsDocument.objects.filter(
                    authority_program=program,
                    syllabus_code=course_code,
                ).first()

                if existing and not force:
                    skipped_count += 1
                    continue

                if dry_run:
                    action = "Would update" if existing else "Would create"
                    self.stdout.write(f"  {action}: {course_name} ({course_code})")
                    if existing:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                # Build document defaults
                defaults = {
                    "grade_level": grade_level,
                    "version_label": "2024-25",
                    "source_publisher_name": source_data["publisher"],
                    "source_publisher_type": source_data["publisher_type"],
                    "source_title": course_name,
                    "source_url": source_data["url"],
                    "acquisition_method": source_data["acquisition_method"],
                    "acquisition_notes": f"Course catalog entry for {course_name}. Code: {course_code}.",
                    "is_active": True,
                    "status": "current",
                }

                # Add metadata to acquisition_notes
                metadata_parts = []
                if cefr_level:
                    metadata_parts.append(f"CEFR: {cefr_level}")
                if credits:
                    metadata_parts.append(f"Credits: {credits}")
                if qcf_level:
                    metadata_parts.append(f"QCF Level: {qcf_level}")
                if hours:
                    metadata_parts.append(f"Hours: {hours}")
                if course_type:
                    metadata_parts.append(f"Type: {course_type}")
                if discipline:
                    metadata_parts.append(f"Discipline: {discipline}")
                if metadata_parts:
                    defaults["acquisition_notes"] += f" ({', '.join(metadata_parts)})"

                if existing:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                    self.stdout.write(f"  Updated: {course_name}")
                else:
                    StandardsDocument.objects.create(
                        authority_program=program,
                        subject=subject_name,
                        syllabus_code=course_code,
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
