"""
Management command to seed default tab configurations for each standards authority.
Creates ProviderTabConfig entries that define which tabs appear and how data is fetched.
"""

from django.core.management.base import BaseCommand

from core.models import StandardsAuthority, ProviderTabConfig


# Default tab configurations by authority code
DEFAULT_TAB_CONFIGS = {
    "CAMBRIDGE": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "syllabus", "label": "Syllabus", "icon": "bi-file-text", "fetch_method": "ai_extract", "sort_order": 1,
         "static_action_label": "View Official Syllabus", "static_action_url_field": "source_url"},
        {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 2},
        {"tab_id": "scheme", "label": "Scheme of Work", "icon": "bi-calendar3", "fetch_method": "ai_extract", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "examinations", "label": "Examinations", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "IB": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "subject_guide", "label": "Subject Guide", "icon": "bi-journal-text", "fetch_method": "ai_extract", "sort_order": 1,
         "static_action_label": "View on IBO", "static_action_url_field": "source_url"},
        {"tab_id": "objectives", "label": "Assessment Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 2},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 3},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "examinations", "label": "Examinations", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 5},
    ],
    "COLLEGE_BOARD": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "ced", "label": "Course & Exam Description", "icon": "bi-file-earmark-text", "fetch_method": "ai_extract", "sort_order": 1,
         "static_action_label": "View on College Board", "static_action_url_field": "source_url"},
        {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "ai_extract", "sort_order": 2,
         "ai_extraction_prompt": "collegeboard_objectives"},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 3},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "examinations", "label": "AP Exam", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 5},
    ],
    "WIDA": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "language_expectations", "label": "Language Expectations", "icon": "bi-chat-square-text", "fetch_method": "ai_extract", "sort_order": 1,
         "static_action_label": "View on WIDA", "static_action_url_field": "source_url"},
        {"tab_id": "proficiency_levels", "label": "Proficiency Levels", "icon": "bi-bar-chart-steps", "fetch_method": "ai_extract", "sort_order": 2},
        {"tab_id": "key_language_uses", "label": "Key Language Uses", "icon": "bi-diagram-3", "fetch_method": "ai_extract", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "access_assessment", "label": "ACCESS Assessment", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "BRITISH_COUNCIL": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "cefr_levels", "label": "CEFR Levels", "icon": "bi-bar-chart-steps", "fetch_method": "ai_extract", "sort_order": 1},
        {"tab_id": "course_content", "label": "Course Content", "icon": "bi-journal-text", "fetch_method": "ai_extract", "sort_order": 2},
        {"tab_id": "objectives", "label": "Learning Outcomes", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "assessment", "label": "Assessment", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "ETS": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "test_format", "label": "Test Format", "icon": "bi-layout-text-window", "fetch_method": "ai_extract", "sort_order": 1},
        {"tab_id": "scoring", "label": "Scoring", "icon": "bi-graph-up", "fetch_method": "ai_extract", "sort_order": 2},
        {"tab_id": "preparation", "label": "Preparation", "icon": "bi-book", "fetch_method": "ai_extract", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "registration", "label": "Registration", "icon": "bi-calendar-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "FOREIGN_MOE": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "curriculum_standards", "label": "Curriculum Standards", "icon": "bi-file-earmark-text", "fetch_method": "ai_extract", "sort_order": 1},
        {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 2},
        {"tab_id": "textbooks", "label": "Textbooks", "icon": "bi-book", "fetch_method": "ai_extract", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "national_exams", "label": "National Examinations", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "US_COMMON_CORE": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "standards", "label": "Standards", "icon": "bi-file-earmark-text", "fetch_method": "ai_extract", "sort_order": 1},
        {"tab_id": "strands_domains", "label": "Strands & Domains", "icon": "bi-diagram-3", "fetch_method": "ai_extract", "sort_order": 2},
        {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "assessments", "label": "Assessments", "icon": "bi-clipboard-check", "fetch_method": "ai_extract", "sort_order": 6},
    ],
    "US_STATES": [
        {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
        {"tab_id": "legal", "label": "Legal", "icon": "bi-file-earmark-text", "fetch_method": "ai_extract", "sort_order": 1,
         "static_description": "Texas Administrative Code (TAC) rules and legal requirements for this course."},
        {"tab_id": "state_board", "label": "State Board of Education", "icon": "bi-building", "fetch_method": "ai_extract", "sort_order": 2},
        {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 3},
        {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 4},
        {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 5},
        {"tab_id": "tests", "label": "Tests", "icon": "bi-pencil-square", "fetch_method": "ai_extract", "sort_order": 6},
    ],
}

# Default tabs for authorities without specific config
DEFAULT_TABS = [
    {"tab_id": "overview", "label": "Overview", "icon": "bi-info-circle", "fetch_method": "none", "sort_order": 0},
    {"tab_id": "objectives", "label": "Learning Objectives", "icon": "bi-list-check", "fetch_method": "objectives", "sort_order": 1},
    {"tab_id": "official_resources", "label": "Official Resources", "icon": "bi-patch-check", "fetch_method": "resources", "sort_order": 2},
    {"tab_id": "unofficial_resources", "label": "Unofficial Resources", "icon": "bi-collection", "fetch_method": "resources", "sort_order": 3},
]


class Command(BaseCommand):
    help = "Seed default tab configurations for each standards authority"

    def add_arguments(self, parser):
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
            "--authority",
            type=str,
            help="Only seed configs for a specific authority code",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        authority_filter = options.get("authority")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Get all authorities
        authorities = StandardsAuthority.objects.filter(is_active=True)
        if authority_filter:
            authorities = authorities.filter(code=authority_filter)

        for authority in authorities:
            self.stdout.write(f"\nProcessing {authority.name} ({authority.code})...")

            # Get tab configs for this authority
            tabs = DEFAULT_TAB_CONFIGS.get(authority.code, DEFAULT_TABS)

            for tab_data in tabs:
                tab_id = tab_data["tab_id"]

                # Check if exists
                existing = ProviderTabConfig.objects.filter(
                    authority=authority,
                    program__isnull=True,
                    tab_id=tab_id,
                ).first()

                if existing and not force:
                    skipped_count += 1
                    continue

                if dry_run:
                    action = "Would update" if existing else "Would create"
                    self.stdout.write(f"  {action}: {tab_id} ({tab_data['label']})")
                    if existing:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                # Build defaults
                defaults = {
                    "label": tab_data["label"],
                    "icon": tab_data.get("icon", "bi-file-text"),
                    "sort_order": tab_data.get("sort_order", 0),
                    "fetch_method": tab_data.get("fetch_method", "none"),
                    "is_active": True,
                }

                # Optional fields
                if "ai_extraction_prompt" in tab_data:
                    defaults["ai_extraction_prompt"] = tab_data["ai_extraction_prompt"]
                if "custom_handler" in tab_data:
                    defaults["custom_handler"] = tab_data["custom_handler"]
                if "static_description" in tab_data:
                    defaults["static_description"] = tab_data["static_description"]
                if "static_action_label" in tab_data:
                    defaults["static_action_label"] = tab_data["static_action_label"]
                if "static_action_url_field" in tab_data:
                    defaults["static_action_url_field"] = tab_data["static_action_url_field"]

                if existing:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                    self.stdout.write(f"  Updated: {tab_id}")
                else:
                    ProviderTabConfig.objects.create(
                        authority=authority,
                        tab_id=tab_id,
                        **defaults
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created: {tab_id}"))

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}"
        ))
