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
    profile_completed = models.BooleanField(default=False)
    display_name = models.CharField(max_length=100, blank=True)

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_instructor(self):
        return self.role == self.ROLE_INSTRUCTOR

    def is_researcher(self):
        return self.role == self.ROLE_RESEARCHER

    def get_display_name(self):
        """Return display name, falling back to username or email."""
        if self.display_name:
            return self.display_name
        if self.first_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username or self.email.split('@')[0]


class Roster(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    grade_band = models.CharField(max_length=50, blank=True)
    invite_code = models.CharField(max_length=8, unique=True, blank=True, null=True)
    invite_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.site.code})"

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_invite_code():
        import secrets
        import string
        chars = string.ascii_uppercase + string.digits
        # Remove confusing characters
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(6))
            if not Roster.objects.filter(invite_code=code).exists():
                return code


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
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    introduction_html = models.TextField()
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


class SegmentViewLog(models.Model):
    """Tracks time spent viewing each segment for granular analytics."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="segment_views")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="segment_views")
    segment = models.ForeignKey(StorySegment, on_delete=models.CASCADE, related_name="view_logs")
    segment_index = models.PositiveIntegerField()

    # Timing data
    view_start = models.DateTimeField()
    view_end = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Reading behavior indicators
    scroll_depth_percent = models.FloatField(default=0)  # How far they scrolled in segment
    revisit_count = models.PositiveIntegerField(default=0)  # Times they came back to this segment
    hesitation_count = models.PositiveIntegerField(default=0)  # Pauses > 3 seconds

    # Interaction data
    gloss_clicks = models.PositiveIntegerField(default=0)  # Glossary terms clicked in segment
    copy_events = models.PositiveIntegerField(default=0)  # Text copied

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['view_start']

    @property
    def reading_speed_wpm(self):
        """Estimate words per minute based on segment content and time spent."""
        if self.duration_seconds and self.duration_seconds > 0 and self.segment:
            # Rough word count from HTML
            import re
            text = re.sub(r'<[^>]+>', '', self.segment.text_html)
            word_count = len(text.split())
            return (word_count / self.duration_seconds) * 60
        return None
