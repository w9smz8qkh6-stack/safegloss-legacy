"""
Management command to seed WIDA ELD Standards catalog from JSON.
Creates StandardsDocument entries for each standard × grade cluster combination.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import StandardsAuthority, AuthorityProgram, StandardsDocument


class Command(BaseCommand):
    help = "Seed WIDA ELD Standards catalog from JSON file into StandardsDocument entries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/seeds/wida_eld_standards_catalog.json",
            help="Path to the WIDA catalog JSON file",
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
        else:
            # Update name if it exists but has different name
            if authority.name != authority_data["name"]:
                authority.name = authority_data["name"]
                authority.save()
                self.stdout.write(f"Updated authority name: {authority.name}")

        # Get or create the program
        program, prog_created = AuthorityProgram.objects.get_or_create(
            authority=authority,
            code=program_data["code"],
            defaults={
                "name": program_data["name"],
                "description": program_data.get("description", ""),
                "is_active": True,
            }
        )
        if prog_created:
            self.stdout.write(self.style.SUCCESS(f"Created program: {program.name}"))

        # Process standards × grade clusters
        standards = catalog["standards"]
        grade_clusters = catalog["grade_clusters"]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for standard in standards:
            standard_code = standard["code"]
            standard_name = standard["name"]
            standard_desc = standard["description"]

            self.stdout.write(f"\nProcessing {standard_name}...")

            for grade_cluster in grade_clusters:
                cluster_code = grade_cluster["code"]
                cluster_name = grade_cluster["name"]
                grade_level = grade_cluster["grade_level"]

                # Build syllabus code: e.g., ELD-SI.K, ELD-LA.2-3
                syllabus_code = f"{standard_code}.{cluster_code}"

                # Build course name: e.g., "Language for Language Arts - Grades 2-3"
                course_name = f"{standard_name} - {cluster_name}"

                # Check if document already exists
                existing = StandardsDocument.objects.filter(
                    authority_program=program,
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

                # Build document defaults
                defaults = {
                    "grade_level": grade_level,
                    "version_label": "2020 Edition",
                    "source_publisher_name": source_data["publisher"],
                    "source_publisher_type": source_data["publisher_type"],
                    "source_title": course_name,
                    "source_url": source_data["url"],
                    "acquisition_method": source_data["acquisition_method"],
                    "acquisition_notes": f"{standard_desc} Key Language Uses: Narrate, Inform, Explain, Argue. Proficiency Levels: 1-6.",
                    "is_active": True,
                    "status": "current",
                }

                if existing:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                    self.stdout.write(f"  Updated: {course_name}")
                else:
                    StandardsDocument.objects.create(
                        authority_program=program,
                        subject=standard_name,
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
        self.stdout.write(f"Total documents in catalog: {created_count + updated_count + skipped_count}")
