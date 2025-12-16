"""
Management command to export standards provenance for audit purposes.

Implements Section 17.5 of the build guide:
- authority, subject, grade
- version label
- acquisition method
- publisher name
- source_url
- source_accessed_at
- checksums

Usage:
    python manage.py export_standards_provenance --format=csv > provenance.csv
    python manage.py export_standards_provenance --format=json > provenance.json
    python manage.py export_standards_provenance --authority=US_STATES --format=csv
"""

import csv
import json
import sys
from django.core.management.base import BaseCommand
from core.models import StandardsDocument


class Command(BaseCommand):
    help = "Export standards provenance data for audit (CSV or JSON)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["csv", "json"],
            default="csv",
            help="Output format (default: csv)",
        )
        parser.add_argument(
            "--authority",
            type=str,
            help="Filter by authority code (e.g., US_STATES, IB)",
        )
        parser.add_argument(
            "--program",
            type=str,
            help="Filter by program code (e.g., STATE_TX, IB_MYP)",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: stdout)",
        )

    def handle(self, *args, **options):
        output_format = options["format"]
        authority_filter = options["authority"]
        program_filter = options["program"]
        output_file = options["output"]

        # Build queryset
        qs = StandardsDocument.objects.select_related(
            "authority_program__authority",
            "evidence_artifact",
        ).order_by(
            "authority_program__authority__code",
            "authority_program__code",
            "subject",
            "grade_level",
        )

        if authority_filter:
            qs = qs.filter(authority_program__authority__code=authority_filter)
        if program_filter:
            qs = qs.filter(authority_program__code=program_filter)

        # Build data
        records = []
        for doc in qs:
            records.append({
                "authority_code": doc.authority_program.authority.code,
                "authority_name": doc.authority_program.authority.name,
                "program_code": doc.authority_program.code,
                "program_name": doc.authority_program.name,
                "subject": doc.subject,
                "grade_level": doc.grade_level,
                "version_label": doc.version_label,
                "source_publisher_name": doc.source_publisher_name,
                "source_publisher_type": doc.source_publisher_type,
                "source_title": doc.source_title,
                "source_url": doc.source_url,
                "source_url_canonical": doc.source_url_canonical,
                "source_accessed_at": doc.source_accessed_at.isoformat() if doc.source_accessed_at else "",
                "source_content_type": doc.source_content_type,
                "source_version_label": doc.source_version_label,
                "source_effective_from": doc.source_effective_from.isoformat() if doc.source_effective_from else "",
                "source_effective_until": doc.source_effective_until.isoformat() if doc.source_effective_until else "",
                "acquisition_method": doc.acquisition_method,
                "acquisition_notes": doc.acquisition_notes,
                "evidence_sha256_raw": doc.evidence_sha256_raw,
                "evidence_sha256_canonical": doc.evidence_sha256_canonical,
                "evidence_artifact_id": doc.evidence_artifact_id or "",
                "is_active": doc.is_active,
                "is_reference_only": doc.is_reference_only,
                "objective_count": doc.objective_nodes.count(),
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            })

        # Output
        if output_file:
            outfile = open(output_file, "w", encoding="utf-8", newline="")
        else:
            outfile = sys.stdout

        try:
            if output_format == "json":
                json.dump({
                    "export_type": "standards_provenance",
                    "total_documents": len(records),
                    "filters": {
                        "authority": authority_filter,
                        "program": program_filter,
                    },
                    "documents": records,
                }, outfile, indent=2)
                if output_file:
                    self.stdout.write(self.style.SUCCESS(
                        f"Exported {len(records)} documents to {output_file}"
                    ))
            else:
                if records:
                    fieldnames = list(records[0].keys())
                    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
                    if output_file:
                        self.stdout.write(self.style.SUCCESS(
                            f"Exported {len(records)} documents to {output_file}"
                        ))
                else:
                    self.stdout.write(self.style.WARNING("No documents found matching filters."))
        finally:
            if output_file:
                outfile.close()

        if not output_file:
            self.stderr.write(f"\n# Total: {len(records)} documents")
