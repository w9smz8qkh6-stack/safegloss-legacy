"""
Management command to import standards from a JSON file.

Usage:
    python manage.py import_standards path/to/standards.json

Expected JSON format:
{
    "authority": "US_STATES",
    "program": "STATE_TX",
    "subject": "Technology Applications",
    "grade": "Grades 6-8",
    "version": "Adopted 2022",
    "provenance": {
        "source_publisher_name": "Texas Education Agency",
        "source_publisher_type": "government",
        "source_title": "Technology Applications TEKS",
        "source_url": "https://tea.texas.gov/...",
        "source_accessed_at": "2025-01-15T10:00:00Z",
        "source_content_type": "pdf",
        "acquisition_method": "official_pdf",
        "acquisition_notes": "Downloaded from TEA website and parsed."
    },
    "nodes": [
        {"id": "1", "parent": null, "type": "strand", "code": "1", "text": "Creativity and Innovation", "order": 1},
        {"id": "1.A", "parent": "1", "type": "objective", "code": "1.A", "text": "...", "order": 1}
    ]
}
"""

import json
from django.core.management.base import BaseCommand, CommandError
from core.services.standards import import_standards_json, ProvenanceValidationError
from core.services.standards.import_service import ImportError


class Command(BaseCommand):
    help = "Import standards from a JSON file with provenance validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to the JSON file containing standards data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate without importing",
        )

    def handle(self, *args, **options):
        json_file = options["json_file"]
        dry_run = options["dry_run"]

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_file}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        self.stdout.write(f"Loaded JSON from: {json_file}")
        self.stdout.write(f"  Authority: {data.get('authority', 'N/A')}")
        self.stdout.write(f"  Program: {data.get('program', 'N/A')}")
        self.stdout.write(f"  Subject: {data.get('subject', 'N/A')}")
        self.stdout.write(f"  Grade: {data.get('grade', 'N/A')}")
        self.stdout.write(f"  Version: {data.get('version', 'N/A')}")
        self.stdout.write(f"  Nodes: {len(data.get('nodes', []))}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run mode - validating only..."))
            try:
                from core.services.standards.validation import validate_provenance
                provenance = validate_provenance(data.get("provenance", {}))
                self.stdout.write(self.style.SUCCESS("Provenance validation passed!"))
                self.stdout.write(f"  Publisher: {provenance.source_publisher_name}")
                self.stdout.write(f"  Method: {provenance.acquisition_method}")
                self.stdout.write(f"  URL: {provenance.source_url}")
            except ProvenanceValidationError as e:
                self.stdout.write(self.style.ERROR(f"Provenance validation failed:\n{e}"))
                return
        else:
            try:
                doc = import_standards_json(data)
                self.stdout.write(self.style.SUCCESS(f"\nImport successful!"))
                self.stdout.write(f"  Document ID: {doc.pk}")
                self.stdout.write(f"  Objectives: {doc.objective_nodes.count()}")
                self.stdout.write(f"  Publisher: {doc.source_publisher_name}")
                self.stdout.write(f"  Method: {doc.acquisition_method}")
            except ProvenanceValidationError as e:
                raise CommandError(f"Provenance validation failed:\n{e}")
            except ImportError as e:
                raise CommandError(f"Import failed: {e}")
