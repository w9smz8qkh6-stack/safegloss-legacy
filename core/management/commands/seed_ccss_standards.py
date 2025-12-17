"""
Management command to seed US Common Core State Standards from JSON.
Creates StandardsDocument and ObjectiveNode entries for ELA and Mathematics.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import StandardsAuthority, AuthorityProgram, StandardsDocument, ObjectiveNode


class Command(BaseCommand):
    help = "Seed US Common Core State Standards with full objectives from JSON files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ela-file",
            type=str,
            default="docs/gpt/ccss_ela_standards.json",
            help="Path to the ELA standards JSON file",
        )
        parser.add_argument(
            "--math-file",
            type=str,
            default="docs/gpt/ccss_math_standards.json",
            help="Path to the Math standards JSON file",
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
        parser.add_argument(
            "--ela-only",
            action="store_true",
            help="Only process ELA standards",
        )
        parser.add_argument(
            "--math-only",
            action="store_true",
            help="Only process Math standards",
        )

    def handle(self, *args, **options):
        ela_file = Path(options["ela_file"])
        math_file = Path(options["math_file"])
        force = options["force"]
        dry_run = options["dry_run"]
        ela_only = options["ela_only"]
        math_only = options["math_only"]

        # Track totals
        total_docs = 0
        total_objectives = 0

        # Process files
        files_to_process = []
        if not math_only and ela_file.exists():
            files_to_process.append(ela_file)
        elif not math_only:
            self.stderr.write(self.style.WARNING(f"ELA file not found: {ela_file}"))

        if not ela_only and math_file.exists():
            files_to_process.append(math_file)
        elif not ela_only:
            self.stderr.write(self.style.WARNING(f"Math file not found: {math_file}"))

        if not files_to_process:
            self.stderr.write(self.style.ERROR("No files to process"))
            return

        for file_path in files_to_process:
            self.stdout.write(f"\nProcessing {file_path}...")
            docs, objs = self.process_file(file_path, force, dry_run)
            total_docs += docs
            total_objectives += objs

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        self.stdout.write(self.style.SUCCESS(
            f"Done! Documents: {total_docs}, Objectives: {total_objectives}"
        ))

    def process_file(self, file_path: Path, force: bool, dry_run: bool) -> tuple[int, int]:
        """Process a single JSON file and return (doc_count, objective_count)."""
        with open(file_path, "r") as f:
            data = json.load(f)

        # Get or create authority
        authority_data = data["authority"]
        source_data = data["source"]
        program_data = data["program"]

        if dry_run:
            self.stdout.write(f"  Authority: {authority_data['code']} - {authority_data['name']}")
            self.stdout.write(f"  Program: {program_data['code']} - {program_data['name']}")
            authority = None
            program = None
        else:
            authority, auth_created = StandardsAuthority.objects.get_or_create(
                code=authority_data["code"],
                defaults={
                    "name": authority_data["name"],
                    "is_active": True,
                }
            )
            if auth_created:
                self.stdout.write(self.style.SUCCESS(f"  Created authority: {authority.name}"))

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
                self.stdout.write(self.style.SUCCESS(f"  Created program: {program.name}"))

        # Process documents
        doc_count = 0
        obj_count = 0

        for doc_data in data["documents"]:
            syllabus_code = doc_data["syllabus_code"]
            subject = doc_data["subject"]
            grade_level = doc_data["grade_level"]

            if dry_run:
                self.stdout.write(f"  Would create document: {syllabus_code} - {subject} ({grade_level})")
                doc_count += 1
                # Count objectives
                for strand in doc_data.get("strands", []):
                    obj_count += len(strand.get("objectives", []))
                    for cluster in strand.get("clusters", []):
                        obj_count += len(cluster.get("objectives", []))
                continue

            # Check if document exists
            existing_doc = StandardsDocument.objects.filter(
                authority_program=program,
                syllabus_code=syllabus_code,
            ).first()

            if existing_doc and not force:
                self.stdout.write(f"  Skipping existing: {syllabus_code}")
                continue

            with transaction.atomic():
                if existing_doc and force:
                    # Delete existing objectives for this document
                    existing_doc.objective_nodes.all().delete()
                    document = existing_doc
                    # Update document fields
                    document.subject = subject
                    document.grade_level = grade_level
                    document.version_label = source_data.get("version_label", "2010 Standards")
                    document.source_publisher_name = source_data["publisher"]
                    document.source_publisher_type = source_data.get("publisher_type", "nonprofit")
                    document.source_title = f"Common Core State Standards - {subject} ({grade_level})"
                    document.source_url = source_data["url"]
                    document.acquisition_method = source_data.get("acquisition_method", "official_pdf")
                    document.is_active = True
                    document.status = "current"
                    document.save()
                    self.stdout.write(f"  Updated document: {syllabus_code}")
                else:
                    # Create new document
                    document = StandardsDocument.objects.create(
                        authority_program=program,
                        subject=subject,
                        grade_level=grade_level,
                        syllabus_code=syllabus_code,
                        version_label=source_data.get("version_label", "2010 Standards"),
                        source_publisher_name=source_data["publisher"],
                        source_publisher_type=source_data.get("publisher_type", "nonprofit"),
                        source_title=f"Common Core State Standards - {subject} ({grade_level})",
                        source_url=source_data["url"],
                        acquisition_method=source_data.get("acquisition_method", "official_pdf"),
                        is_active=True,
                        status="current",
                    )
                    self.stdout.write(self.style.SUCCESS(f"  Created document: {syllabus_code}"))

                doc_count += 1

                # Create objective nodes
                strand_order = 0
                for strand_data in doc_data.get("strands", []):
                    strand_order += 1
                    strand_node = ObjectiveNode.objects.create(
                        document=document,
                        parent=None,
                        node_type="strand",
                        code=strand_data.get("code", ""),
                        text=strand_data.get("name", ""),
                        internal_code=str(strand_order),
                        sort_order=strand_order,
                    )
                    obj_count += 1

                    # Process clusters (substrand level) if present
                    if "clusters" in strand_data:
                        cluster_order = 0
                        for cluster_data in strand_data["clusters"]:
                            cluster_order += 1
                            cluster_node = ObjectiveNode.objects.create(
                                document=document,
                                parent=strand_node,
                                node_type="substrand",
                                code=cluster_data.get("code", ""),
                                text=cluster_data.get("name", ""),
                                internal_code=f"{strand_order}.{cluster_order}",
                                sort_order=cluster_order,
                            )
                            obj_count += 1

                            # Process objectives within cluster
                            for obj_data in cluster_data.get("objectives", []):
                                obj_node = ObjectiveNode.objects.create(
                                    document=document,
                                    parent=cluster_node,
                                    node_type=obj_data.get("node_type", "objective"),
                                    code=obj_data.get("code", ""),
                                    text=obj_data.get("text", ""),
                                    internal_code=f"{strand_order}.{cluster_order}.{obj_data.get('sort_order', 0)}",
                                    sort_order=obj_data.get("sort_order", 0),
                                )
                                obj_count += 1

                    # Process direct objectives under strand (no cluster level)
                    for obj_data in strand_data.get("objectives", []):
                        obj_node = ObjectiveNode.objects.create(
                            document=document,
                            parent=strand_node,
                            node_type=obj_data.get("node_type", "objective"),
                            code=obj_data.get("code", ""),
                            text=obj_data.get("text", ""),
                            internal_code=f"{strand_order}.{obj_data.get('sort_order', 0)}",
                            sort_order=obj_data.get("sort_order", 0),
                        )
                        obj_count += 1

        return doc_count, obj_count
