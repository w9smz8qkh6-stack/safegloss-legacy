from __future__ import annotations

from typing import Iterable

from django.core.management.base import BaseCommand

from core.models import Course, StandardsAuthority, SubjectArea

DEFAULT_DESCRIPTION = "Texas Essential Knowledge and Skills course"


def _build_courses() -> list[dict[str, str]]:
    courses: list[dict[str, str]] = []

    def add(code: str, title: str, subject_area: str, grade_level: str, grade: str, description: str | None = None) -> None:
        courses.append(
            {
                "code": code,
                "title": title,
                "subject_area": subject_area,
                "grade_level": grade_level,
                "grade": grade,
                "description": description or DEFAULT_DESCRIPTION,
            }
        )

    # Elementary (K-5)
    elementary_grades = [
        ("K", "Kindergarten"),
        ("1", "Grade 1"),
        ("2", "Grade 2"),
        ("3", "Grade 3"),
        ("4", "Grade 4"),
        ("5", "Grade 5"),
    ]
    elementary_subjects = [
        ("ELA", "English Language Arts and Reading", "english"),
        ("MATH", "Mathematics", "math"),
        ("SCI", "Science", "science"),
        ("SS", "Social Studies", "history"),
        ("HEALTH", "Health Education", "health"),
        ("PE", "Physical Education", "physical_ed"),
        ("ART", "Art", "visual_arts"),
        ("MUSIC", "Music", "music"),
        ("THEATRE", "Theatre", "theater"),
        ("DANCE", "Dance", "dance"),
    ]
    for grade_code, grade_label in elementary_grades:
        for prefix, name, subject_code in elementary_subjects:
            title_suffix = "Kindergarten" if grade_code == "K" else f"Grade {grade_code}"
            add(f"TEKS-{prefix}-{grade_code}", f"{name} {title_suffix}", subject_code, "elementary", grade_code)

        tech_title = "Technology Applications (K-2)" if grade_code in {"K", "1", "2"} else "Technology Applications (3-5)"
        add(f"TEKS-TECH-{grade_code}", tech_title, "information_tech", "elementary", grade_code)

    # Middle school (6-8)
    middle_courses = [
        ("TEKS-ELA-6", "English Language Arts and Reading Grade 6", "english", "6"),
        ("TEKS-MATH-6", "Mathematics Grade 6", "math", "6"),
        ("TEKS-SCI-6", "Science Grade 6", "science", "6"),
        ("TEKS-SS-6", "World Cultures and Geography Grade 6", "geography", "6"),
        ("TEKS-HEALTH-6", "Health Education Grade 6", "health", "6"),
        ("TEKS-PE-6", "Physical Education Grade 6", "physical_ed", "6"),
        ("TEKS-ELA-7", "English Language Arts and Reading Grade 7", "english", "7"),
        ("TEKS-MATH-7", "Mathematics Grade 7", "math", "7"),
        ("TEKS-SCI-7", "Science Grade 7", "science", "7"),
        ("TEKS-SS-7", "Texas History Grade 7", "history", "7"),
        ("TEKS-HEALTH-7", "Health Education Grade 7", "health", "7"),
        ("TEKS-PE-7", "Physical Education Grade 7", "physical_ed", "7"),
        ("TEKS-ELA-8", "English Language Arts and Reading Grade 8", "english", "8"),
        ("TEKS-MATH-8", "Mathematics Grade 8", "math", "8"),
        ("TEKS-SCI-8", "Science Grade 8", "science", "8"),
        ("TEKS-SS-8", "United States History to 1877 Grade 8", "history", "8"),
        ("TEKS-HEALTH-8", "Health Education Grade 8", "health", "8"),
        ("TEKS-PE-8", "Physical Education Grade 8", "physical_ed", "8"),
    ]
    for code, title, subject_code, grade in middle_courses:
        add(code, title, subject_code, "middle", grade)

    add("TEKS-TECH-6-8", "Technology Applications (6-8)", "information_tech", "middle", "6-8")

    fine_arts_middle = [
        ("TEKS-ART-MS", "Art Middle School 1-3", "visual_arts"),
        ("TEKS-BAND-MS", "Band Middle School 1-3", "music"),
        ("TEKS-CHOIR-MS", "Choir Middle School 1-3", "music"),
        ("TEKS-ORCH-MS", "Orchestra Middle School 1-3", "music"),
        ("TEKS-THEATRE-MS", "Theatre Middle School 1-3", "theater"),
        ("TEKS-DANCE-MS", "Dance Middle School 1-3", "dance"),
    ]
    for code, title, subject_code in fine_arts_middle:
        add(code, title, subject_code, "middle", "6-8")

    # High school (9-12)
    def add_batch(records: Iterable[tuple[str, str, str]]) -> None:
        for code, title, subject_code in records:
            add(code, title, subject_code, "high", "9-12")

    add_batch(
        [
            ("TEKS-ENG-I", "English I", "english"),
            ("TEKS-ENG-II", "English II", "english"),
            ("TEKS-ENG-III", "English III", "english"),
            ("TEKS-ENG-IV", "English IV", "english"),
            ("TEKS-ENG-IS", "Independent Study in English", "english"),
            ("TEKS-ENG-LG", "Literary Genres", "english"),
            ("TEKS-ENG-CW", "Creative Writing", "english"),
            ("TEKS-ENG-RTW", "Research and Technical Writing", "english"),
            ("TEKS-ENG-HUM", "Humanities", "english"),
        ]
    )

    add_batch(
        [
            ("TEKS-ALG-I", "Algebra I", "math"),
            ("TEKS-GEOM", "Geometry", "math"),
            ("TEKS-ALG-II", "Algebra II", "math"),
            ("TEKS-PRECALC", "Precalculus", "math"),
            ("TEKS-AQR", "Advanced Quantitative Reasoning", "math"),
            ("TEKS-ALG-REASON", "Algebraic Reasoning", "math"),
            ("TEKS-STATS", "Statistics", "math"),
            ("TEKS-DISCRETE", "Discrete Mathematics for Problem Solving", "math"),
            ("TEKS-ISM", "Independent Study in Mathematics", "math"),
        ]
    )

    add_batch(
        [
            ("TEKS-IPC", "Integrated Physics and Chemistry", "science"),
            ("TEKS-BIO", "Biology", "biology"),
            ("TEKS-CHEM", "Chemistry", "chemistry"),
            ("TEKS-PHYS", "Physics", "physics"),
            ("TEKS-ESS", "Earth and Space Science", "earth_science"),
            ("TEKS-ASTRO", "Astronomy", "astronomy"),
            ("TEKS-AQUA", "Aquatic Science", "environmental"),
            ("TEKS-ENV", "Environmental Systems", "environmental"),
            ("TEKS-ANAT", "Anatomy and Physiology", "biology"),
            ("TEKS-SRD", "Scientific Research and Design", "science"),
            ("TEKS-ENG-DP", "Engineering Design and Problem Solving", "engineering"),
            ("TEKS-FORENSIC", "Forensic Science", "science"),
        ]
    )

    add_batch(
        [
            ("TEKS-WGEO", "World Geography Studies", "geography"),
            ("TEKS-WHIST", "World History Studies", "history"),
            ("TEKS-USHIST", "United States History Since 1877", "history"),
            ("TEKS-GOV", "United States Government", "civics"),
            ("TEKS-ECON", "Economics with Emphasis on the Free Enterprise System and Its Benefits", "economics"),
            ("TEKS-PFLECON", "Personal Financial Literacy and Economics", "economics"),
            ("TEKS-PSYCH", "Psychology", "psychology"),
            ("TEKS-SOC", "Sociology", "sociology"),
            ("TEKS-SSRM", "Social Studies Research Methods", "history"),
            ("TEKS-SSTS", "Special Topics in Social Studies", "history"),
            ("TEKS-ETH-MAS", "Ethnic Studies: Mexican American Studies", "history"),
            ("TEKS-ETH-AAS", "Ethnic Studies: African American Studies", "history"),
        ]
    )

    languages = [
        ("ASL", "American Sign Language"),
        ("ARABIC", "Arabic"),
        ("CHINESE", "Chinese"),
        ("FRENCH", "French"),
        ("GERMAN", "German"),
        ("HEBREW", "Hebrew"),
        ("HINDI", "Hindi"),
        ("ITALIAN", "Italian"),
        ("JAPANESE", "Japanese"),
        ("KOREAN", "Korean"),
        ("LATIN", "Latin"),
        ("PORTUGUESE", "Portuguese"),
        ("RUSSIAN", "Russian"),
        ("SPANISH", "Spanish"),
        ("TURKISH", "Turkish"),
        ("URDU", "Urdu"),
        ("VIETNAMESE", "Vietnamese"),
    ]
    level_map = [("I", 1), ("II", 2), ("III", 3), ("IV", 4)]
    for lang_code, lang_name in languages:
        for level_label, _ in level_map:
            add(
                f"TEKS-{lang_code}-{level_label}",
                f"{lang_name} Level {level_label}",
                "world_languages",
                "high",
                "9-12",
            )

    for level_label, _ in level_map:
        add(f"TEKS-ART-{level_label}", f"Art {level_label}", "visual_arts", "high", "9-12")
        add(f"TEKS-DANCE-{level_label}", f"Dance {level_label}", "dance", "high", "9-12")
        add(f"TEKS-BAND-{level_label}", f"Band {level_label}", "music", "high", "9-12")
        add(f"TEKS-CHOIR-{level_label}", f"Choir {level_label}", "music", "high", "9-12")
        add(f"TEKS-ORCH-{level_label}", f"Orchestra {level_label}", "music", "high", "9-12")
        add(f"TEKS-THEATRE-{level_label}", f"Theatre Arts {level_label}", "theater", "high", "9-12")
        add(f"TEKS-THEATRE-TECH-{level_label}", f"Technical Theatre {level_label}", "theater", "high", "9-12")
        add(f"TEKS-THEATRE-PROD-{level_label}", f"Theatre Production {level_label}", "theater", "high", "9-12")

        add(f"TEKS-VOC-ENS-{level_label}", f"Vocal Ensemble {level_label}", "music", "high", "9-12")
        add(f"TEKS-INS-ENS-{level_label}", f"Instrumental Ensemble {level_label}", "music", "high", "9-12")
        add(f"TEKS-JAZZ-{level_label}", f"Jazz Ensemble {level_label}", "music", "high", "9-12")

    add("TEKS-MUSIC-THEORY-I", "Music Theory I", "music", "high", "9-12")
    add("TEKS-MUSIC-THEORY-II", "Music Theory II", "music", "high", "9-12")

    add_batch(
        [
            ("TEKS-HEALTH-HS", "Health Education (0.5 credit)", "health"),
            ("TEKS-FITNESS", "Foundations of Personal Fitness", "physical_ed"),
            ("TEKS-LIFETIME-FIT", "Lifetime Fitness and Wellness Pursuits", "physical_ed"),
            ("TEKS-LEISURE", "Lifetime Leisure and Recreation", "physical_ed"),
            ("TEKS-INDIV-SPORTS", "Individual Sports", "physical_ed"),
            ("TEKS-TEAM-SPORTS", "Team Sports", "physical_ed"),
            ("TEKS-AEROBICS", "Aerobic Activities", "physical_ed"),
            ("TEKS-OUTDOOR", "Outdoor Adventures", "physical_ed"),
            ("TEKS-ADV-OUTDOOR", "Adventure and Outdoor Education", "physical_ed"),
            ("TEKS-PARTNERS-PE", "Partners Physical Education", "physical_ed"),
        ]
    )

    add_batch(
        [
            ("TEKS-DIGLIT", "Digital Literacy", "information_tech"),
            ("TEKS-CS-I", "Computer Science I", "computer_science"),
            ("TEKS-CS-II", "Computer Science II", "computer_science"),
            ("TEKS-CS-III", "Computer Science III", "computer_science"),
            ("TEKS-AP-CS-A", "AP Computer Science A", "computer_science"),
            ("TEKS-AP-CSP", "AP Computer Science Principles", "computer_science"),
            ("TEKS-CYBER", "Foundations of Cybersecurity", "computer_science"),
            ("TEKS-DISCRETE-CS", "Discrete Mathematics for Computer Science", "computer_science"),
            ("TEKS-WEB-DESIGN", "Web Design", "information_tech"),
            ("TEKS-IST", "Independent Study in Technology Applications", "information_tech"),
        ]
    )

    return courses


COURSES = _build_courses()


class Command(BaseCommand):
    help = "Seed TEKS (Texas Essential Knowledge and Skills) course catalog for K-12."

    def handle(self, *args, **options) -> None:
        authority, created_auth = StandardsAuthority.objects.get_or_create(
            code="TEKS",
            defaults={
                "name": "Texas Essential Knowledge and Skills",
                "url": "https://tea.texas.gov/academics/curriculum-standards/teks",
                "description": "Texas K-12 academic standards",
            },
        )

        subject_lookup = {sa.code.lower(): sa for sa in SubjectArea.objects.all()}
        created_courses = 0
        updated_courses = 0
        skipped_missing_subject = 0
        missing_subjects: set[str] = set()

        for course in COURSES:
            subject = subject_lookup.get(course["subject_area"].lower())
            if not subject:
                missing_subjects.add(course["subject_area"])
                skipped_missing_subject += 1
                continue

            defaults = {
                "title": course["title"],
                "description": course.get("description") or DEFAULT_DESCRIPTION,
                "subject_area": subject,
                "standards_authority": authority,
                "grade_level": course["grade_level"],
                "grade": course["grade"],
                "is_active": True,
            }
            _, was_created = Course.objects.update_or_create(code=course["code"], defaults=defaults)
            if was_created:
                created_courses += 1
            else:
                updated_courses += 1

        if created_auth:
            self.stdout.write(self.style.SUCCESS("Created TEKS standards authority record"))
        else:
            self.stdout.write("TEKS standards authority already exists (updated courses only)")

        if missing_subjects:
            missing_list = ", ".join(sorted(missing_subjects))
            self.stdout.write(self.style.WARNING(f"Skipped {skipped_missing_subject} courses due to missing subject areas: {missing_list}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"TEKS courses processed. Created: {created_courses}; Updated: {updated_courses}; Skipped: {skipped_missing_subject}"
            )
        )
