"""
Management command to seed Standards Authorities and Programs.
Based on the specification in docs/standards_syllabus_objectives_feature_build_guide.md
"""
from django.core.management.base import BaseCommand
from core.models import StandardsAuthority, AuthorityProgram


# Canonical seed data from the build guide
AUTHORITIES_AND_PROGRAMS = [
    # International Authorities
    {
        "code": "IB",
        "name": "International Baccalaureate",
        "description": "International Baccalaureate Organization offering globally recognized educational programs.",
        "programs": [
            {"code": "IB_PYP", "name": "Primary Years Programme (PYP)", "description": "For students aged 3-12"},
            {"code": "IB_MYP", "name": "Middle Years Programme (MYP)", "description": "For students aged 11-16"},
            {"code": "IB_DP", "name": "Diploma Programme", "description": "For students aged 16-19"},
        ]
    },
    {
        "code": "CAMBRIDGE",
        "name": "Cambridge Assessment International Education",
        "description": "Cambridge Assessment offering international qualifications and examinations.",
        "programs": [
            {"code": "CAM_IGCSE", "name": "IGCSE", "description": "International General Certificate of Secondary Education"},
            {"code": "CAM_STARTERS", "name": "Cambridge Starters", "description": "Cambridge English Young Learners Starters"},
        ]
    },
    {
        "code": "BC",
        "name": "British Council",
        "description": "British Council international English language testing.",
        "programs": [
            {"code": "BC_IELTS", "name": "IELTS", "description": "International English Language Testing System"},
        ]
    },
    # Testing & Assessment Organizations
    {
        "code": "ETS",
        "name": "Educational Testing Service",
        "description": "Educational Testing Service (ETS) standardized testing organization.",
        "programs": [
            {"code": "ETS_TOEFL", "name": "TOEFL", "description": "Test of English as a Foreign Language"},
        ]
    },
    {
        "code": "COLLEGE_BOARD",
        "name": "College Board",
        "description": "College Board standardized testing and college readiness programs.",
        "programs": [
            {"code": "CB_SAT", "name": "SAT", "description": "Scholastic Assessment Test"},
            {"code": "CB_AP", "name": "Advanced Placement (AP)", "description": "College-level courses and exams"},
        ]
    },
    {
        "code": "ACT",
        "name": "ACT, Inc.",
        "description": "ACT standardized testing for college admissions.",
        "programs": [
            {"code": "ACT_EXAM", "name": "ACT", "description": "American College Testing"},
        ]
    },
    # United States - State Standards
    {
        "code": "US_STATES",
        "name": "U.S. State Standards",
        "description": "State-level educational standards for K-12 education in the United States.",
        "programs": [
            {"code": "STATE_NY", "name": "New York", "description": "New York State Learning Standards"},
            {"code": "STATE_TX", "name": "Texas", "description": "Texas Essential Knowledge and Skills (TEKS)"},
            {"code": "STATE_IL", "name": "Illinois", "description": "Illinois Learning Standards"},
            {"code": "STATE_FL", "name": "Florida", "description": "Florida Standards / B.E.S.T. Standards"},
            {"code": "STATE_CA", "name": "California", "description": "California State Standards"},
        ]
    },
    # Common Core (multi-state)
    {
        "code": "CCSS",
        "name": "Common Core State Standards",
        "description": "Common Core State Standards Initiative for K-12 education.",
        "programs": [
            {"code": "CCSS_ELA", "name": "English Language Arts", "description": "Common Core ELA Standards"},
            {"code": "CCSS_MATH", "name": "Mathematics", "description": "Common Core Math Standards"},
        ]
    },
]


class Command(BaseCommand):
    help = "Seed Standards Authorities and Programs with canonical data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update existing records instead of skipping them",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created_authorities = 0
        updated_authorities = 0
        created_programs = 0
        updated_programs = 0

        for authority_data in AUTHORITIES_AND_PROGRAMS:
            programs_data = authority_data.pop("programs", [])

            authority, created = StandardsAuthority.objects.get_or_create(
                code=authority_data["code"],
                defaults={
                    "name": authority_data["name"],
                    "description": authority_data.get("description", ""),
                    "is_active": True,
                }
            )

            if created:
                created_authorities += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created authority: {authority.name} ({authority.code})")
                )
            elif force:
                authority.name = authority_data["name"]
                authority.description = authority_data.get("description", "")
                authority.save()
                updated_authorities += 1
                self.stdout.write(
                    self.style.WARNING(f"  Updated authority: {authority.name} ({authority.code})")
                )
            else:
                self.stdout.write(f"  Skipped existing authority: {authority.code}")

            # Create programs for this authority
            for program_data in programs_data:
                program, created = AuthorityProgram.objects.get_or_create(
                    authority=authority,
                    code=program_data["code"],
                    defaults={
                        "name": program_data["name"],
                        "description": program_data.get("description", ""),
                        "is_active": True,
                    }
                )

                if created:
                    created_programs += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"    + Program: {program.name} ({program.code})")
                    )
                elif force:
                    program.name = program_data["name"]
                    program.description = program_data.get("description", "")
                    program.save()
                    updated_programs += 1
                    self.stdout.write(
                        self.style.WARNING(f"    ~ Program: {program.name} ({program.code})")
                    )
                else:
                    self.stdout.write(f"    - Skipped existing program: {program.code}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {created_authorities} authorities, {created_programs} programs."
        ))
        if force:
            self.stdout.write(self.style.WARNING(
                f"Updated {updated_authorities} authorities, {updated_programs} programs."
            ))
