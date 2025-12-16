"""
Management command to sync standards from registered providers.

Usage:
    python manage.py sync_standards STATE_TX "Technology Applications" "Grades 6-8"
    python manage.py sync_standards CCSS_ELA "English Language Arts" "Grade 6"
    python manage.py sync_standards --list-providers
"""

from django.core.management.base import BaseCommand, CommandError
from core.services.standards import sync_document, ProvenanceValidationError
from core.services.standards.providers import list_registered_providers, get_provider
from core.services.standards.import_service import ImportError

# Import provider implementations to register them
from core.services.standards.provider_implementations import TexasTEKSProvider, CommonCoreProvider  # noqa


class Command(BaseCommand):
    help = "Sync standards from registered providers"

    def add_arguments(self, parser):
        parser.add_argument(
            "program_code",
            nargs="?",
            type=str,
            help="Program code (e.g., STATE_TX, CCSS_ELA)",
        )
        parser.add_argument(
            "subject",
            nargs="?",
            type=str,
            help="Subject area (e.g., 'Technology Applications')",
        )
        parser.add_argument(
            "grade_level",
            nargs="?",
            type=str,
            help="Grade level (e.g., 'Grades 6-8', 'Grade 6')",
        )
        parser.add_argument(
            "--standards-version",
            type=str,
            dest="standards_version",
            help="Optional version label (defaults to latest)",
        )
        parser.add_argument(
            "--list-providers",
            action="store_true",
            help="List all registered providers",
        )

    def handle(self, *args, **options):
        if options["list_providers"]:
            self.list_providers()
            return

        program_code = options["program_code"]
        subject = options["subject"]
        grade_level = options["grade_level"]
        version = options.get("standards_version")

        if not all([program_code, subject, grade_level]):
            raise CommandError(
                "Required: program_code, subject, and grade_level. "
                "Use --list-providers to see available providers."
            )

        # Check if provider exists
        provider_cls = get_provider(program_code)
        if not provider_cls:
            raise CommandError(
                f"No provider registered for program: {program_code}\n"
                f"Available: {', '.join(list_registered_providers())}"
            )

        self.stdout.write(f"Syncing standards from {program_code}...")
        self.stdout.write(f"  Subject: {subject}")
        self.stdout.write(f"  Grade: {grade_level}")
        if version:
            self.stdout.write(f"  Version: {version}")

        try:
            doc = sync_document(program_code, subject, grade_level, version)
            self.stdout.write(self.style.SUCCESS(f"\nSync successful!"))
            self.stdout.write(f"  Document ID: {doc.pk}")
            self.stdout.write(f"  Subject: {doc.subject}")
            self.stdout.write(f"  Grade: {doc.grade_level}")
            self.stdout.write(f"  Version: {doc.version_label}")
            self.stdout.write(f"  Publisher: {doc.source_publisher_name}")
            self.stdout.write(f"  Method: {doc.acquisition_method}")
            self.stdout.write(f"  Objectives: {doc.objective_nodes.count()}")
        except ProvenanceValidationError as e:
            raise CommandError(f"Provenance validation failed:\n{e}")
        except ImportError as e:
            raise CommandError(f"Import failed: {e}")

    def list_providers(self):
        """List all registered providers."""
        providers = list_registered_providers()
        if not providers:
            self.stdout.write(self.style.WARNING("No providers registered."))
            return

        self.stdout.write("Registered providers:")
        for code in sorted(providers):
            provider_cls = get_provider(code)
            if provider_cls:
                provider = provider_cls()
                subjects = provider.list_available_subjects()
                grades = provider.list_available_grades()
                self.stdout.write(f"\n  {code}")
                self.stdout.write(f"    Authority: {provider.authority_code}")
                self.stdout.write(f"    Subjects: {', '.join(subjects)}")
                self.stdout.write(f"    Grades: {', '.join(grades)}")
