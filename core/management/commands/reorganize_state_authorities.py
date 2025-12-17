"""
Management command to reorganize state standards authorities under a parent
'U.S. State Standards' authority.

This migrates existing state authorities (STATE_FL, STATE_CA, etc.) to be
programs under a single US_STATE_STANDARDS authority.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import StandardsAuthority, AuthorityProgram, StandardsDocument


class Command(BaseCommand):
    help = "Reorganize state standards authorities under U.S. State Standards"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without actually changing",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Define state mappings
        state_mappings = {
            "STATE_FL": {
                "code": "FLORIDA",
                "name": "Florida",
                "full_name": "Florida Department of Education",
            },
            "STATE_CA": {
                "code": "CALIFORNIA",
                "name": "California",
                "full_name": "California Department of Education",
            },
            "STATE_NY": {
                "code": "NEW_YORK",
                "name": "New York",
                "full_name": "New York State Education Department",
            },
            "STATE_IL": {
                "code": "ILLINOIS",
                "name": "Illinois",
                "full_name": "Illinois State Board of Education",
            },
            "STATE_TX": {
                "code": "TEXAS",
                "name": "Texas",
                "full_name": "Texas Education Agency",
            },
        }

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        with transaction.atomic():
            # Create or get the parent authority
            parent_authority, created = StandardsAuthority.objects.get_or_create(
                code="US_STATE_STANDARDS",
                defaults={
                    "name": "U.S. State Standards",
                    "is_active": True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created parent authority: {parent_authority.name}"))
            else:
                self.stdout.write(f"Using existing parent authority: {parent_authority.name}")

            # Process each state
            for old_code, state_info in state_mappings.items():
                old_authority = StandardsAuthority.objects.filter(code=old_code).first()

                if old_authority:
                    self.stdout.write(f"\nProcessing {state_info['name']}...")

                    # Get old programs and their documents
                    old_programs = AuthorityProgram.objects.filter(authority=old_authority)

                    for old_program in old_programs:
                        doc_count = StandardsDocument.objects.filter(authority_program=old_program).count()
                        self.stdout.write(f"  Found program: {old_program.name} ({doc_count} docs)")

                        # Create new program under parent authority
                        new_program_code = f"{state_info['code']}_{old_program.code}"
                        new_program_name = f"{state_info['name']} - {old_program.name}"

                        if dry_run:
                            self.stdout.write(f"  Would create program: {new_program_name} ({new_program_code})")
                            self.stdout.write(f"  Would migrate {doc_count} documents")
                        else:
                            new_program, prog_created = AuthorityProgram.objects.get_or_create(
                                authority=parent_authority,
                                code=new_program_code,
                                defaults={
                                    "name": new_program_name,
                                    "description": f"{state_info['full_name']} - {old_program.description}" if old_program.description else state_info['full_name'],
                                    "is_active": True,
                                }
                            )

                            if prog_created:
                                self.stdout.write(self.style.SUCCESS(f"  Created program: {new_program.name}"))
                            else:
                                self.stdout.write(f"  Using existing program: {new_program.name}")

                            # Migrate documents
                            migrated = StandardsDocument.objects.filter(
                                authority_program=old_program
                            ).update(authority_program=new_program)
                            self.stdout.write(self.style.SUCCESS(f"  Migrated {migrated} documents"))

                            # Delete old program
                            old_program.delete()
                            self.stdout.write(f"  Deleted old program: {old_program.code}")

                    # Delete old authority
                    if not dry_run:
                        old_authority.delete()
                        self.stdout.write(f"  Deleted old authority: {old_code}")
                else:
                    self.stdout.write(f"\n{state_info['name']}: No existing authority found (will be available for future seeding)")

            # Create placeholder programs for states without data
            if not dry_run:
                for old_code, state_info in state_mappings.items():
                    # Check if any program exists for this state
                    existing = AuthorityProgram.objects.filter(
                        authority=parent_authority,
                        code__startswith=state_info['code']
                    ).exists()

                    if not existing:
                        # Create a placeholder program
                        placeholder = AuthorityProgram.objects.create(
                            authority=parent_authority,
                            code=state_info['code'],
                            name=f"{state_info['name']} State Standards",
                            description=state_info['full_name'],
                            is_active=True,
                        )
                        self.stdout.write(self.style.SUCCESS(f"Created placeholder program: {placeholder.name}"))

            if dry_run:
                # Rollback in dry run
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("")
        if not dry_run:
            total_programs = AuthorityProgram.objects.filter(authority=parent_authority).count()
            total_docs = StandardsDocument.objects.filter(authority_program__authority=parent_authority).count()
            self.stdout.write(self.style.SUCCESS(f"Done! U.S. State Standards now has {total_programs} programs with {total_docs} documents"))
