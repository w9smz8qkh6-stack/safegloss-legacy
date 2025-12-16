"""
Management command to import media (books/resources) for authority programs.

Usage:
    # Import by ISBN
    python manage.py import_media --isbn=9780134685991 --program=STATE_TX --official

    # Import by title search
    python manage.py import_media --title="STAAR Math" --author="Lumos" --program=STATE_TX

    # Batch import from CSV
    python manage.py import_media --csv=media_list.csv --program=STATE_TX

    # Hydrate existing records
    python manage.py import_media --hydrate-all --program=STATE_TX
"""

import csv
import logging
from django.core.management.base import BaseCommand, CommandError
from core.models import AuthorityProgram, AuthorityProgramMedia
from core.services.media import (
    lookup_by_isbn,
    lookup_by_title,
    hydrate_media,
    HydrationResult,
)
from core.services.media.hydration import (
    create_media_from_isbn,
    create_media_from_search,
    hydrate_media_batch,
)
from core.services.media.google_books import GoogleBooksError, NotFoundError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import media (books/resources) for authority programs with Google Books hydration"

    def add_arguments(self, parser):
        # Lookup options
        parser.add_argument(
            "--isbn",
            type=str,
            help="ISBN-10 or ISBN-13 to import",
        )
        parser.add_argument(
            "--title",
            type=str,
            help="Title to search for",
        )
        parser.add_argument(
            "--author",
            type=str,
            help="Author name (used with --title)",
        )

        # Target program
        parser.add_argument(
            "--program",
            type=str,
            required=True,
            help="Authority program code (e.g., STATE_TX, CCSS_ELA)",
        )

        # Media attributes
        parser.add_argument(
            "--official",
            action="store_true",
            help="Mark as official/endorsed resource",
        )
        parser.add_argument(
            "--type",
            type=str,
            default="book",
            choices=["book", "guide", "practice_tests", "video_series", "course"],
            help="Media type",
        )
        parser.add_argument(
            "--tags",
            type=str,
            help="Comma-separated tags (e.g., 'exam_prep,official')",
        )
        parser.add_argument(
            "--notes",
            type=str,
            default="",
            help="Endorsement notes",
        )

        # Batch operations
        parser.add_argument(
            "--csv",
            type=str,
            help="CSV file with media to import (columns: isbn, title, author, official, type, tags, notes)",
        )
        parser.add_argument(
            "--hydrate-all",
            action="store_true",
            help="Hydrate all existing media for the program",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-hydration even if already hydrated",
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
            # List available programs
            available = AuthorityProgram.objects.values_list("code", flat=True)
            raise CommandError(
                f"Program not found: {program_code}\n"
                f"Available: {', '.join(available) or 'none (run sync_standards first)'}"
            )

        self.stdout.write(f"Target program: {program.name} ({program.code})")

        if options["hydrate_all"]:
            self.hydrate_all(program, options)
        elif options["csv"]:
            self.import_from_csv(program, options)
        elif options["isbn"]:
            self.import_by_isbn(program, options)
        elif options["title"]:
            self.import_by_title(program, options)
        else:
            raise CommandError(
                "Specify one of: --isbn, --title, --csv, or --hydrate-all"
            )

    def import_by_isbn(self, program, options):
        """Import a single resource by ISBN."""
        isbn = options["isbn"]
        is_official = options["official"]
        media_type = options["type"]
        notes = options["notes"]
        tags = options["tags"].split(",") if options["tags"] else None
        dry_run = options["dry_run"]

        self.stdout.write(f"\nLooking up ISBN: {isbn}")

        if dry_run:
            # Just preview the lookup
            try:
                metadata = lookup_by_isbn(isbn)
                self.stdout.write(self.style.SUCCESS("\nFound:"))
                self._print_metadata(metadata)
                self.stdout.write("\n[DRY RUN] Would create media record")
            except NotFoundError:
                self.stdout.write(self.style.WARNING(f"No book found for ISBN: {isbn}"))
            except GoogleBooksError as e:
                self.stdout.write(self.style.ERROR(f"API error: {e}"))
            return

        # Actually import
        result = create_media_from_isbn(
            authority_program=program,
            isbn=isbn,
            is_official=is_official,
            media_type=media_type,
            endorsement_notes=notes,
            tags=tags,
        )

        if result.success:
            self.stdout.write(self.style.SUCCESS(f"\nCreated media: {result.media.title}"))
            self.stdout.write(f"  ID: {result.media.pk}")
            self.stdout.write(f"  Author: {result.media.author}")
            self.stdout.write(f"  Publisher: {result.media.publisher}")
            self.stdout.write(f"  ISBN-13: {result.media.isbn_13}")
            self.stdout.write(f"  Official: {result.media.is_official}")
        else:
            self.stdout.write(self.style.ERROR(f"\nFailed to import: {result.error}"))

    def import_by_title(self, program, options):
        """Import a resource by title search."""
        title = options["title"]
        author = options["author"]
        is_official = options["official"]
        media_type = options["type"]
        notes = options["notes"]
        tags = options["tags"].split(",") if options["tags"] else None
        dry_run = options["dry_run"]

        self.stdout.write(f"\nSearching for: {title}")
        if author:
            self.stdout.write(f"  Author: {author}")

        if dry_run:
            try:
                results = lookup_by_title(title, author)
                self.stdout.write(self.style.SUCCESS(f"\nFound {len(results)} results:"))
                for i, metadata in enumerate(results, 1):
                    self.stdout.write(f"\n--- Result {i} ---")
                    self._print_metadata(metadata)
                self.stdout.write("\n[DRY RUN] Would create media from first result")
            except NotFoundError:
                self.stdout.write(self.style.WARNING(f"No books found for: {title}"))
            except GoogleBooksError as e:
                self.stdout.write(self.style.ERROR(f"API error: {e}"))
            return

        # Actually import
        result = create_media_from_search(
            authority_program=program,
            title=title,
            author=author,
            is_official=is_official,
            media_type=media_type,
            endorsement_notes=notes,
            tags=tags,
        )

        if result.success:
            self.stdout.write(self.style.SUCCESS(f"\nCreated media: {result.media.title}"))
            self.stdout.write(f"  ID: {result.media.pk}")
            self.stdout.write(f"  Author: {result.media.author}")
        else:
            self.stdout.write(self.style.WARNING(f"\nCreated with warning: {result.error}"))
            self.stdout.write(f"  Media ID: {result.media.pk}")

    def import_from_csv(self, program, options):
        """Import media from a CSV file."""
        csv_path = options["csv"]
        dry_run = options["dry_run"]

        try:
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            raise CommandError(f"Error reading CSV: {e}")

        self.stdout.write(f"\nFound {len(rows)} rows in CSV")

        success = 0
        failed = 0

        for i, row in enumerate(rows, 1):
            isbn = row.get("isbn", "").strip()
            title = row.get("title", "").strip()
            author = row.get("author", "").strip()
            is_official = row.get("official", "").lower() in ("true", "yes", "1")
            media_type = row.get("type", "book").strip() or "book"
            tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
            notes = row.get("notes", "").strip()

            self.stdout.write(f"\n[{i}/{len(rows)}] Processing: {isbn or title}")

            if dry_run:
                self.stdout.write("  [DRY RUN] Would import")
                continue

            try:
                if isbn:
                    result = create_media_from_isbn(
                        authority_program=program,
                        isbn=isbn,
                        is_official=is_official,
                        media_type=media_type,
                        endorsement_notes=notes,
                        tags=tags or None,
                    )
                elif title:
                    result = create_media_from_search(
                        authority_program=program,
                        title=title,
                        author=author or None,
                        is_official=is_official,
                        media_type=media_type,
                        endorsement_notes=notes,
                        tags=tags or None,
                    )
                else:
                    self.stdout.write(self.style.WARNING("  Skipped (no isbn or title)"))
                    failed += 1
                    continue

                if result.success:
                    self.stdout.write(self.style.SUCCESS(f"  Created: {result.media.title}"))
                    success += 1
                else:
                    self.stdout.write(self.style.WARNING(f"  Warning: {result.error}"))
                    success += 1  # Record was created even if metadata not found

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {e}"))
                failed += 1

        self.stdout.write(f"\n\nSummary: {success} imported, {failed} failed")

    def hydrate_all(self, program, options):
        """Hydrate all existing media for a program."""
        force = options["force"]
        dry_run = options["dry_run"]

        queryset = AuthorityProgramMedia.objects.filter(authority_program=program)

        if not force:
            # Only hydrate records that haven't been hydrated
            queryset = queryset.filter(retrieved_from="")

        count = queryset.count()
        self.stdout.write(f"\nFound {count} media records to hydrate")

        if dry_run:
            self.stdout.write("[DRY RUN] Would hydrate these records")
            for media in queryset[:10]:
                self.stdout.write(f"  - {media.title}")
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            return

        results = hydrate_media_batch(queryset, force=force)

        self.stdout.write(f"\n\nResults:")
        self.stdout.write(f"  Total: {results['total']}")
        self.stdout.write(self.style.SUCCESS(f"  Success: {results['success']}"))
        self.stdout.write(self.style.ERROR(f"  Failed: {results['failed']}"))

    def _print_metadata(self, metadata):
        """Print book metadata in a readable format."""
        self.stdout.write(f"  Title: {metadata.title}")
        if metadata.subtitle:
            self.stdout.write(f"  Subtitle: {metadata.subtitle}")
        self.stdout.write(f"  Authors: {', '.join(metadata.authors)}")
        self.stdout.write(f"  Publisher: {metadata.publisher}")
        self.stdout.write(f"  Published: {metadata.published_date}")
        self.stdout.write(f"  Pages: {metadata.page_count}")
        self.stdout.write(f"  ISBN-10: {metadata.isbn_10}")
        self.stdout.write(f"  ISBN-13: {metadata.isbn_13}")
        self.stdout.write(f"  Language: {metadata.language}")
        if metadata.categories:
            self.stdout.write(f"  Categories: {', '.join(metadata.categories)}")
