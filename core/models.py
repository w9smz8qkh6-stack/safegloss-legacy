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
    ROLE_INSTRUCTOR = "instructor"
    ROLE_RESEARCHER = "researcher"
    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_INSTRUCTOR, "Instructor"),
        (ROLE_RESEARCHER, "Researcher"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL)

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_instructor(self):
        return self.role == self.ROLE_INSTRUCTOR

    def is_researcher(self):
        return self.role == self.ROLE_RESEARCHER


class Roster(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rosters", null=True, blank=True)
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

    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
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

    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_bookmarks")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=500, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("instructor", "source", "external_id")
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
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="units")
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
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    rosters = models.ManyToManyField("Roster", related_name="courses", blank=True)
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
    title = models.CharField(max_length=255)
    instructions_html = models.TextField(blank=True)
    total_points = models.FloatField(default=0)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

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

    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lessons")
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
