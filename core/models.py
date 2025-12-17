from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Site(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_RESEARCHER = "researcher"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_TEACHER, "Teacher"),
        (ROLE_RESEARCHER, "Researcher"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL)

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    def is_researcher(self):
        return self.role == self.ROLE_RESEARCHER


class Roster(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rosters", null=True, blank=True)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    grade_band = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.site:
            return f"{self.name} ({self.site.code})"
        return self.name


class RosterMembership(models.Model):
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="memberships")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roster_memberships")

    class Meta:
        unique_together = ("roster", "student")


class Story(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_AI = "ai_generated"
    SOURCE_EXTERNAL = "external"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_AI, "AI Generated"),
        (SOURCE_EXTERNAL, "External"),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    title = models.CharField(max_length=255)
    text_html = models.TextField()
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    source_metadata = models.JSONField(blank=True, default=dict)
    reading_level_label = models.CharField(max_length=100, blank=True)
    reading_level_metrics = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    def update_reading_levels(self) -> bool:
        """
        Compute and store reading level metrics from text_html.
        Returns True if metrics were computed, False if text was too short.
        """
        from core.services.reading_levels import analyze_reading_level, format_reading_level_display

        if not self.text_html:
            return False

        metrics = analyze_reading_level(self.text_html)
        if not metrics:
            return False

        self.reading_level_metrics = metrics.to_dict()
        self.reading_level_label = format_reading_level_display(metrics, format="compact")
        return True

    @property
    def word_count(self) -> int:
        """Return word count from metrics or estimate from text."""
        if self.reading_level_metrics:
            return self.reading_level_metrics.get("word_count", 0)
        # Fallback: rough estimate
        from core.services.reading_levels import strip_html
        return len(strip_html(self.text_html).split()) if self.text_html else 0

    @property
    def ar_level(self) -> str:
        """Return ATOS/AR level display string."""
        if self.reading_level_metrics:
            atos = self.reading_level_metrics.get("atos_level")
            if atos:
                return f"{atos:.1f}"
        return ""

    @property
    def lexile_level(self) -> str:
        """Return Lexile display string."""
        if self.reading_level_metrics:
            lexile = self.reading_level_metrics.get("lexile_estimate")
            if lexile:
                return f"{lexile}L"
        return ""

    @property
    def guided_reading_level(self) -> str:
        """Return Guided Reading level."""
        if self.reading_level_metrics:
            return self.reading_level_metrics.get("guided_reading", "")
        return ""


class ExternalBookmark(models.Model):
    """Bookmark for external texts (Open Library, Gutenberg, Open Textbook Library) pending import."""
    SOURCE_OPENLIBRARY = "openlibrary"
    SOURCE_GUTENBERG = "gutenberg"
    SOURCE_OPENTEXTBOOK = "opentextbook"
    SOURCE_CHOICES = [
        (SOURCE_OPENLIBRARY, "Open Library"),
        (SOURCE_GUTENBERG, "Project Gutenberg"),
        (SOURCE_OPENTEXTBOOK, "Open Textbook Library"),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_bookmarks")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=500, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("teacher", "source", "external_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_source_display()})"


class StorySegment(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="segments")
    index = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True)
    text_html = models.TextField()
    start_char = models.IntegerField(null=True, blank=True)
    end_char = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("story", "index")
        ordering = ["index"]

    def __str__(self):
        return f"{self.story.title} – segment {self.index}"


class Unit(models.Model):
    """A unit is a container for two or more related lessons."""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="units")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def lesson_count(self):
        return self.unit_lessons.count()


class UnitLesson(models.Model):
    """Through model for Unit-Lesson relationship with ordering."""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="unit_lessons")
    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE, related_name="unit_memberships")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("unit", "lesson")
        ordering = ["order"]

    def __str__(self):
        return f"{self.unit.title} - {self.lesson.title} (#{self.order})"


class Course(models.Model):
    """A course is a container for one or more units, assigned to rosters."""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    rosters = models.ManyToManyField("Roster", related_name="courses", blank=True)
    aligned_objectives = models.ManyToManyField(
        "ObjectiveNode",
        related_name="aligned_courses",
        blank=True,
        help_text="Learning objectives this course is aligned to"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def unit_count(self):
        return self.course_units.count()


class CourseUnit(models.Model):
    """Through model for Course-Unit relationship with ordering."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_units")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="course_memberships")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("course", "unit")
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} - {self.unit.title} (#{self.order})"


class MediaAsset(models.Model):
    MEDIA_IMAGE = "image"
    MEDIA_AUDIO = "audio"
    MEDIA_VIDEO = "video"
    MEDIA_CHOICES = [
        (MEDIA_IMAGE, "Image"),
        (MEDIA_AUDIO, "Audio"),
        (MEDIA_VIDEO, "Video"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="media_assets")
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES)
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.media_type}: {self.file_path}"


class SegmentMedia(models.Model):
    ROLE_BACKGROUND_IMAGE = "background_image"
    ROLE_INLINE_IMAGE = "inline_image"
    ROLE_AUDIO = "audio_narration"
    ROLE_VIDEO = "video_clip"
    ROLE_CHOICES = [
        (ROLE_BACKGROUND_IMAGE, "Background image"),
        (ROLE_INLINE_IMAGE, "Inline image"),
        (ROLE_AUDIO, "Audio"),
        (ROLE_VIDEO, "Video"),
    ]

    segment = models.ForeignKey(StorySegment, on_delete=models.CASCADE, related_name="segment_media")
    media = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="segment_links")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    start_offset_ms = models.IntegerField(default=0)
    end_offset_ms = models.IntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class Glossary(models.Model):
    story = models.OneToOneField(Story, on_delete=models.CASCADE, related_name="glossary")
    name = models.CharField(max_length=255, blank=True)
    language_code = models.CharField(max_length=10, help_text="L2 language code, e.g. en")
    native_language_code = models.CharField(max_length=10, help_text="L1 language code, e.g. vi")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name or f"Glossary for {self.story.title}"


class Term(models.Model):
    glossary = models.ForeignKey(Glossary, on_delete=models.CASCADE, related_name="terms")
    term_text = models.CharField(max_length=255)
    lemma = models.CharField(max_length=255, blank=True)
    part_of_speech = models.CharField(max_length=50, blank=True)
    definition_html = models.TextField(help_text="L2 definition")
    translation = models.CharField(max_length=255, blank=True)
    translation_lang_code = models.CharField(max_length=10, blank=True)
    ipa = models.CharField(max_length=255, blank=True)
    difficulty_rating = models.FloatField(null=True, blank=True)
    is_ai_suggested = models.BooleanField(default=False)
    is_selected_for_glossary = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.term_text


class TermOccurrence(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="term_occurrences")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="occurrences")
    segment = models.ForeignKey(StorySegment, null=True, blank=True, on_delete=models.SET_NULL, related_name="term_occurrences")
    start_char = models.IntegerField()
    end_char = models.IntegerField()
    token_index = models.IntegerField(null=True, blank=True)
    sentence_index = models.IntegerField(null=True, blank=True)
    anchor_text = models.CharField(max_length=255)
    anchor_version = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)


class ItemBankQuestion(models.Model):
    QUESTION_TYPES = [
        ("mcq_single", "Multiple choice (single)"),
        ("mcq_multi", "Multiple choice (multi)"),
        ("true_false", "True / False"),
        ("short_answer", "Short answer"),
        ("long_answer", "Long answer"),
        ("matching", "Matching"),
        ("ordering", "Ordering"),
        ("cloze", "Cloze"),
        ("file_upload", "File upload"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item_bank_questions")
    prompt_html = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    default_points = models.FloatField(default=1.0)
    subject = models.CharField(max_length=100, blank=True)
    grade_band = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        default="draft",
    )

    def __str__(self):
        return f"{self.prompt_html[:60]}..."


class ItemBankChoice(models.Model):
    question = models.ForeignKey(ItemBankQuestion, on_delete=models.CASCADE, related_name="choices")
    label = models.CharField(max_length=5, blank=True)
    text_html = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class Quiz(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="quizzes", null=True, blank=True)
    title = models.CharField(max_length=255)
    instructions_html = models.TextField(blank=True)
    total_points = models.FloatField(default=0)
    time_limit_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time limit in minutes. Leave blank for no time limit."
    )
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def time_limit_seconds(self):
        """Return time limit in seconds for JavaScript timer."""
        return self.time_limit_minutes * 60 if self.time_limit_minutes else None

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_questions")
    question = models.ForeignKey(ItemBankQuestion, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    points = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["order"]


class QuizSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_submissions")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="submissions")
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    raw_score = models.FloatField(null=True, blank=True)
    max_score = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(blank=True, default=dict)

    @property
    def is_submitted(self):
        return self.submitted_at is not None


class QuizSubmissionAnswer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(ItemBankQuestion, on_delete=models.CASCADE)
    question_type = models.CharField(max_length=20)
    selected_choice_ids = models.JSONField(blank=True, default=list)
    short_answer_text = models.TextField(blank=True)
    long_answer_text = models.TextField(blank=True)
    file_upload_path = models.CharField(max_length=500, blank=True)
    file_metadata = models.JSONField(blank=True, default=dict)
    is_correct = models.BooleanField(null=True, blank=True)
    partial_credit_ratio = models.FloatField(null=True, blank=True)
    time_spent_seconds = models.FloatField(null=True, blank=True)


class Lesson(models.Model):
    MODE_CONTINUOUS = "continuous"
    MODE_CARDS = "cards"
    MODE_MOVIE = "movie"

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lessons")
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL, related_name="lessons")
    title = models.CharField(max_length=255)
    introduction_html = models.TextField(blank=True, default="")
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="lessons")
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.SET_NULL)
    rosters = models.ManyToManyField(Roster, related_name="lessons", blank=True)
    is_active = models.BooleanField(default=True)
    allowed_modes = models.JSONField(default=list)
    default_mode = models.CharField(
        max_length=20,
        choices=[
            (MODE_CONTINUOUS, "Continuous"),
            (MODE_CARDS, "Cards"),
            (MODE_MOVIE, "Movie"),
        ],
        default=MODE_CONTINUOUS,
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    reading_start = models.DateTimeField(null=True, blank=True)
    reading_end = models.DateTimeField(null=True, blank=True)
    quiz_start = models.DateTimeField(null=True, blank=True)
    quiz_end = models.DateTimeField(null=True, blank=True)
    comprehension_score = models.FloatField(null=True, blank=True)
    self_efficacy_rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def reading_duration_seconds(self):
        if self.reading_start and self.reading_end:
            delta = self.reading_end - self.reading_start
            return delta.total_seconds()
        return None


class GlossClickLog(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gloss_click_logs")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="gloss_click_logs")
    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    term_occurrence = models.ForeignKey('TermOccurrence', null=True, blank=True, on_delete=models.SET_NULL)
    segment = models.ForeignKey(StorySegment, null=True, blank=True, on_delete=models.SET_NULL)
    clicked_at = models.DateTimeField(default=timezone.now)
    client_info = models.JSONField(blank=True, default=dict)


class ReadingEvent(models.Model):
    EVENT_TYPES = [
        ("start", "Start"),
        ("scroll", "Scroll"),
        ("pause", "Pause"),
        ("resume", "Resume"),
        ("finish", "Finish"),
        ("mode_change", "Mode change"),
        ("segment_view", "Segment view"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_events")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="reading_events")
    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    event_payload = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)


# =============================================================================
# Standards & Learning Objectives Models
# =============================================================================

class StandardsAuthority(models.Model):
    """
    Top-level standards authority (e.g., IB, Cambridge, College Board, U.S. States).
    """
    name = models.CharField(max_length=255, help_text="e.g., 'International Baccalaureate'")
    code = models.CharField(max_length=50, unique=True, help_text="Stable key, e.g., 'IB', 'CAMBRIDGE'")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Standards authorities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AuthorityProgram(models.Model):
    """
    Sub-category/framework within an authority (e.g., MYP, IGCSE, Texas).
    All downstream entities reference AuthorityProgram, not Authority directly.
    """
    authority = models.ForeignKey(
        StandardsAuthority,
        on_delete=models.CASCADE,
        related_name="programs"
    )
    name = models.CharField(max_length=255, help_text="e.g., 'Middle Years Programme'")
    code = models.CharField(max_length=50, help_text="Stable key, e.g., 'IB_MYP', 'STATE_TX'")
    description = models.TextField(blank=True)
    provider_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Maps to provider/parser implementation"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Sync status tracking
    SYNC_STATUS_CHOICES = [
        ("never", "Never Synced"),
        ("syncing", "Syncing"),
        ("success", "Success"),
        ("error", "Error"),
    ]
    last_objectives_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful objectives sync"
    )
    last_resources_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful resources sync"
    )
    objectives_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default="never"
    )
    resources_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default="never"
    )

    class Meta:
        unique_together = ("authority", "code")
        ordering = ["authority", "name"]

    def __str__(self):
        return f"{self.authority.code} - {self.name}"


class StandardsArtifact(models.Model):
    """
    Raw evidence snapshot (downloaded PDF, HTML, JSON) for audit trail.
    """
    CONTENT_TYPES = [
        ("html", "HTML"),
        ("pdf", "PDF"),
        ("json", "JSON"),
        ("docx", "DOCX"),
        ("zip", "ZIP"),
        ("other", "Other"),
    ]

    file_path = models.CharField(max_length=500)
    remote_url = models.URLField(max_length=1000, blank=True, help_text="Original URL where artifact was fetched")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    sha256_hash = models.CharField(max_length=64)
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.original_filename or self.file_path} ({self.content_type})"


class StandardsDocument(models.Model):
    """
    A versioned document containing learning objectives for a specific
    program/subject/grade combination. Includes full provenance tracking.
    """
    # Controlled vocabulary for acquisition methods
    ACQUISITION_METHODS = [
        ("official_api", "Official API"),
        ("official_web_page", "Official Web Page"),
        ("official_pdf", "Official PDF"),
        ("official_download_bundle", "Official Download Bundle"),
        ("publisher_portal_reference_only", "Publisher Portal (Reference Only)"),
        ("third_party_mirror_reference", "Third Party Mirror (Reference)"),
        ("teacher_provided_upload", "Teacher Provided Upload"),
        ("manual_curated", "Manual Curated"),
        ("hybrid", "Hybrid"),
    ]

    PUBLISHER_TYPES = [
        ("government", "Government"),
        ("nonprofit", "Non-Profit"),
        ("publisher", "Publisher"),
        ("testing_org", "Testing Organization"),
        ("other", "Other"),
    ]

    # Pipeline tier for organizing documents in the standards hierarchy
    TIER_CHOICES = [
        ("legislative", "Legislative Authority"),
        ("standards_board", "Standards Board"),
        ("testing_agency", "Testing Agency"),
        ("publisher", "Publisher Materials"),
    ]

    CONTENT_TYPES = [
        ("html", "HTML"),
        ("pdf", "PDF"),
        ("json", "JSON"),
        ("docx", "DOCX"),
        ("api", "API"),
    ]

    # Core identification
    authority_program = models.ForeignKey(
        AuthorityProgram,
        on_delete=models.CASCADE,
        related_name="standards_documents"
    )
    subject = models.CharField(max_length=100, help_text="e.g., 'Mathematics', 'Technology Applications'")
    grade_level = models.CharField(max_length=50, help_text="e.g., 'Grade 6', 'Grades 6-8', 'HL'")
    syllabus_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Course/syllabus identifier, e.g., '0580' for Cambridge IGCSE Mathematics"
    )
    version_label = models.CharField(max_length=100, help_text="e.g., 'Adopted 2022', '2024-2026'")

    # Provenance fields (Section 17.1)
    source_publisher_name = models.CharField(max_length=255, help_text="e.g., 'Texas Education Agency'")
    source_publisher_type = models.CharField(max_length=20, choices=PUBLISHER_TYPES, blank=True)
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default="standards_board",
        help_text="Position in the standards pipeline hierarchy"
    )
    source_title = models.CharField(max_length=500, help_text="Human-readable doc title")
    source_url = models.URLField(max_length=1000, help_text="Primary official URL")
    source_url_canonical = models.URLField(max_length=1000, blank=True, help_text="Clean landing page URL")
    source_accessed_at = models.DateTimeField(null=True, blank=True, help_text="When source was fetched/verified")
    source_content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, blank=True)
    source_version_label = models.CharField(max_length=100, blank=True)
    source_effective_from = models.DateField(null=True, blank=True)
    source_effective_until = models.DateField(null=True, blank=True)
    source_license_notes = models.TextField(blank=True, help_text="Redistribution restrictions")
    description = models.TextField(blank=True, help_text="Official course description")

    # Acquisition method (required - Section 17.2)
    acquisition_method = models.CharField(
        max_length=50,
        choices=ACQUISITION_METHODS,
        help_text="How objectives were obtained"
    )
    acquisition_notes = models.TextField(blank=True, help_text="Brief explanation of acquisition process")

    # Evidence tracking
    evidence_artifact = models.ForeignKey(
        StandardsArtifact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
        help_text="Raw downloaded file snapshot"
    )
    evidence_sha256_raw = models.CharField(max_length=64, blank=True)
    evidence_sha256_canonical = models.CharField(max_length=64, blank=True)

    # Status
    DOCUMENT_STATUS_CHOICES = [
        ("current", "Current"),
        ("superseded", "Superseded"),
        ("draft", "Draft"),
    ]
    is_active = models.BooleanField(default=True)
    is_reference_only = models.BooleanField(
        default=False,
        help_text="True if only codes/structure stored due to licensing"
    )
    status = models.CharField(
        max_length=20,
        choices=DOCUMENT_STATUS_CHOICES,
        default="current",
        help_text="Document lifecycle status"
    )
    superseded_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supersedes",
        help_text="Newer document that supersedes this one"
    )
    superseded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this document was superseded"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["authority_program", "subject", "grade_level", "-version_label"]
        indexes = [
            models.Index(fields=["authority_program", "subject", "grade_level"]),
            models.Index(fields=["status"]),
            models.Index(fields=["tier"]),
        ]

    def __str__(self):
        return f"{self.authority_program.code} - {self.subject} ({self.grade_level}) [{self.version_label}]"

    def mark_superseded(self, new_document: "StandardsDocument") -> None:
        """Mark this document as superseded by a newer version."""
        from django.utils import timezone as tz
        self.status = "superseded"
        self.superseded_by = new_document
        self.superseded_at = tz.now()
        self.save(update_fields=["status", "superseded_by", "superseded_at", "updated_at"])


class ObjectiveNode(models.Model):
    """
    Tree structure for learning objectives within a StandardsDocument.
    Supports native codes and internal numbering for cross-authority search.
    """
    NODE_TYPES = [
        ("strand", "Strand"),
        ("substrand", "Substrand"),
        ("objective", "Objective"),
        ("note", "Note"),
    ]

    document = models.ForeignKey(
        StandardsDocument,
        on_delete=models.CASCADE,
        related_name="objective_nodes"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children"
    )
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)

    # Native authority code (stored exactly as published)
    code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Native authority code, e.g., '(6)(1)(A)', 'CCSS.MATH.CONTENT.6.RP.A.1'"
    )
    text = models.TextField(help_text="Objective wording (may be short if reference-only)")

    # Internal numbering for cross-authority consistency
    internal_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Internal numbering, e.g., '1', '1.1', '1.1.1'"
    )
    internal_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Full path, e.g., '1/1.1/1.1.1'"
    )
    internal_sort_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stable ordering key"
    )

    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["document", "sort_order"]
        indexes = [
            models.Index(fields=["document", "parent", "sort_order"]),
            models.Index(fields=["document", "code"]),
            models.Index(fields=["document", "internal_code"]),
        ]

    def __str__(self):
        code_display = self.code or self.internal_code or f"#{self.sort_order}"
        return f"[{code_display}] {self.text[:50]}..."

    def get_ancestors(self):
        """Return list of ancestors from root to parent."""
        ancestors = []
        node = self.parent
        while node:
            ancestors.insert(0, node)
            node = node.parent
        return ancestors


class ObjectiveCodeMap(models.Model):
    """
    Audit log mapping native codes to internal numbering.
    Separate from standards provenance for reporting.
    """
    MAPPING_METHODS = [
        ("algorithmic", "Algorithmic"),
        ("manual_curated", "Manual Curated"),
        ("hybrid", "Hybrid"),
    ]

    objective_node = models.OneToOneField(
        ObjectiveNode,
        on_delete=models.CASCADE,
        related_name="code_map"
    )
    native_code = models.CharField(max_length=100, blank=True)
    internal_code = models.CharField(max_length=50)
    mapping_method = models.CharField(max_length=20, choices=MAPPING_METHODS)
    mapped_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="code_mappings"
    )
    mapped_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.native_code} → {self.internal_code}"


class AuthorityProgramMedia(models.Model):
    """
    Educational resources for an authority/program.
    Includes textbooks, guides, exam prep materials, and platform courses.

    Resources are categorized by recommendation tier:
    - official: Published/endorsed by the standards authority itself
    - recommended: Recommended by professional organizations or experts
    - commonly_used: Found on school district/school websites
    """
    MEDIA_TYPES = [
        ("book", "Book"),
        ("guide", "Guide"),
        ("curriculum", "Curriculum"),
        ("practice_tests", "Practice Tests"),
        ("video_series", "Video Series"),
        ("course", "Course"),
        ("website", "Website"),
    ]

    PLATFORMS = [
        ("print", "Print"),
        ("authority", "Authority Website"),
        ("google_books", "Google Books"),
        ("amazon", "Amazon"),
        ("khan_academy", "Khan Academy"),
        ("udemy", "Udemy"),
        ("coursera", "Coursera"),
        ("youtube", "YouTube"),
        ("district", "School District"),
        ("publisher", "Publisher"),
        ("other", "Other"),
    ]

    RETRIEVAL_SOURCES = [
        ("authority_website", "Authority Website"),
        ("professional_org", "Professional Organization"),
        ("district_website", "School District Website"),
        ("ai_discovery", "AI-Assisted Discovery"),
        ("google_books_enrichment", "Google Books (Metadata)"),
        ("manual", "Manual Entry"),
    ]

    RECOMMENDATION_TIERS = [
        ("official", "Official"),
        ("recommended", "Recommended"),
        ("commonly_used", "Commonly Used"),
    ]

    RESOURCE_CATEGORIES = [
        ("official", "Official"),
        ("endorsed", "Endorsed"),
        ("non_textbook", "Non-Textbook"),
        ("offering", "Offering"),
        ("youtube", "YouTube"),
    ]

    AUDIENCE_CHOICES = [
        ("general", "General"),
        ("student", "Student-Facing"),
        ("teacher", "Teacher-Facing"),
        ("both", "Student & Teacher"),
    ]

    authority_program = models.ForeignKey(
        AuthorityProgram,
        on_delete=models.CASCADE,
        related_name="media"
    )
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=500, blank=True)
    publisher = models.CharField(max_length=255, blank=True)

    # Identifiers
    isbn_10 = models.CharField(max_length=10, blank=True)
    isbn_13 = models.CharField(max_length=13, blank=True)

    # URLs and images
    source_url = models.URLField(max_length=1000, help_text="Canonical link to resource")
    cover_image_url = models.URLField(max_length=1000, blank=True)
    publisher_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="Official publisher page / purchase link for this resource"
    )

    # Content
    description = models.TextField(blank=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    platform = models.CharField(max_length=20, choices=PLATFORMS)

    # Recommendation tier (replaces is_official/is_unofficial)
    recommendation_tier = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TIERS,
        default="commonly_used",
        help_text="How authoritative is this resource?"
    )

    # New resource classification (supersedes recommendation_tier for UI grouping)
    resource_category = models.CharField(
        max_length=30,
        choices=RESOURCE_CATEGORIES,
        default="official",
        help_text="Grouping for resource display (official, endorsed, non-textbook, offering, youtube)"
    )

    # Audience and companion flags
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default="general",
        help_text="Primary audience for this resource"
    )
    is_companion = models.BooleanField(
        default=False,
        help_text="True if this is a companion/extra tied to a core text (e.g., DVD, online extras)"
    )

    # Legacy fields (for backwards compatibility during migration)
    is_official = models.BooleanField(
        default=False,
        help_text="DEPRECATED: Use recommendation_tier='official' instead"
    )
    is_unofficial = models.BooleanField(
        default=False,
        help_text="DEPRECATED: Use recommendation_tier instead"
    )
    endorsement_notes = models.TextField(blank=True)

    # Discovery provenance
    discovered_from_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="URL where this resource was discovered"
    )
    recommending_organization = models.CharField(
        max_length=255,
        blank=True,
        help_text="Organization that recommended this resource"
    )

    # Features (JSON for flexibility)
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text="e.g., {online_text: true, practice_tests: 5, video_hours: 12}"
    )

    # Metadata retrieval
    retrieved_from = models.CharField(max_length=30, choices=RETRIEVAL_SOURCES, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    metadata_raw = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw API payload for audit"
    )

    # Objective alignment
    aligned_objectives = models.ManyToManyField(
        "ObjectiveNode",
        related_name="supporting_resources",
        blank=True,
        help_text="Learning objectives this resource supports"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Authority program media"
        ordering = ["resource_category", "recommendation_tier", "title"]
        indexes = [
            models.Index(fields=["authority_program", "recommendation_tier"]),
            models.Index(fields=["authority_program", "resource_category"]),
            models.Index(fields=["isbn_13"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_media_type_display()})"


class AuthorityProgramMediaTag(models.Model):
    """
    Tags for categorizing and filtering media resources.
    """
    media = models.ForeignKey(
        AuthorityProgramMedia,
        on_delete=models.CASCADE,
        related_name="tags"
    )
    label = models.CharField(
        max_length=50,
        help_text="e.g., official, exam_prep, beginner, video, open_course"
    )

    class Meta:
        unique_together = ("media", "label")
        ordering = ["label"]

    def __str__(self):
        return self.label


# =============================================================================
# Background Job Processing
# =============================================================================

class BackgroundJob(models.Model):
    """
    Tracks background jobs for async processing of standards imports,
    media hydration, and other long-running tasks.

    Jobs can be triggered via admin UI and processed via management command
    (cron) or upgraded to Celery/django-q workers later.
    """
    JOB_TYPES = [
        ("sync_standards", "Sync Standards"),
        ("hydrate_media", "Hydrate Media"),
        ("import_standards_json", "Import Standards from JSON"),
        ("bootstrap_courses", "Bootstrap Platform Courses"),
        ("resync_authority", "Re-sync Authority"),
        ("sync_authority_objectives", "Sync Authority Objectives"),
        ("sync_authority_resources", "Sync Authority Resources"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    # Job identification
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique key to prevent duplicate jobs (e.g., sync_standards:STATE_TX:Grades6-8)"
    )

    # Job parameters (JSON)
    params = models.JSONField(
        default=dict,
        help_text="Job-specific parameters"
    )

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    progress_pct = models.IntegerField(default=0, help_text="0-100 progress percentage")
    progress_message = models.TextField(blank=True, help_text="Current operation description")

    # Results
    result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Job result data"
    )
    error_message = models.TextField(blank=True)

    # Retry handling
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Triggered by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="background_jobs"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} ({self.status})"

    def mark_running(self):
        """Mark job as running."""
        self.status = "running"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self, result: dict = None):
        """Mark job as completed with optional result."""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.progress_pct = 100
        if result:
            self.result = result
        self.save(update_fields=["status", "completed_at", "progress_pct", "result"])

    def mark_failed(self, error: str):
        """Mark job as failed with error message."""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error
        self.save(update_fields=["status", "completed_at", "error_message"])

    def update_progress(self, pct: int, message: str = ""):
        """Update job progress."""
        self.progress_pct = min(100, max(0, pct))
        if message:
            self.progress_message = message
        self.save(update_fields=["progress_pct", "progress_message"])

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries

    def schedule_retry(self, delay_seconds: int = 60):
        """Schedule a retry after the specified delay."""
        from datetime import timedelta
        self.retry_count += 1
        self.status = "pending"
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.save(update_fields=["retry_count", "status", "next_retry_at"])
