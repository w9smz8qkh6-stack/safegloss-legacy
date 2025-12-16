"""
Data models for text acquisition, candidates, sources, and audit logging.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Course


class Text(models.Model):
    """Represents a textbook or required/alternative text."""

    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    authors = models.JSONField(default=list, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    edition = models.CharField(max_length=100, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    isbn10 = models.CharField(max_length=20, blank=True, db_index=True)
    isbn13 = models.CharField(max_length=20, blank=True, db_index=True)
    oclc = models.CharField(max_length=50, blank=True, db_index=True)
    lccn = models.CharField(max_length=50, blank=True, db_index=True)
    language_code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["isbn13"]),
            models.Index(fields=["isbn10"]),
            models.Index(fields=["oclc"]),
        ]

    def __str__(self) -> str:
        primary = self.title
        if self.isbn13:
            primary = f"{primary} ({self.isbn13})"
        return primary


class CourseText(models.Model):
    """Links a Text to a Course with requirement metadata."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    ALTERNATIVE = "alternative"
    REQUIREMENT_CHOICES = [
        (REQUIRED, "Required"),
        (RECOMMENDED, "Recommended"),
        (ALTERNATIVE, "Alternative"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_texts")
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="course_links")
    requirement_level = models.CharField(max_length=20, choices=REQUIREMENT_CHOICES, default=REQUIRED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("course", "text", "requirement_level")
        indexes = [
            models.Index(fields=["course", "requirement_level"]),
        ]

    def __str__(self) -> str:
        return f"{self.course_id}:{self.text_id} ({self.requirement_level})"


class TextSource(models.Model):
    """Catalog of providers/sources for acquisition."""

    LIBRARY = "library"
    PUBLISHER = "publisher"
    OER = "oer"
    INDEX = "index"
    MARKETPLACE = "marketplace"
    SOURCE_TYPES = [
        (LIBRARY, "Library"),
        (PUBLISHER, "Publisher"),
        (OER, "OER"),
        (INDEX, "Index"),
        (MARKETPLACE, "Marketplace"),
    ]

    AUTH_NONE = "none"
    AUTH_OAUTH = "oauth"
    AUTH_SAML = "saml"
    AUTH_CARD_PIN = "card_pin"
    AUTH_PROXY_VPN = "proxy_vpn"
    AUTH_API_KEY = "api_key"
    AUTH_CHOICES = [
        (AUTH_NONE, "None"),
        (AUTH_OAUTH, "OAuth"),
        (AUTH_SAML, "SAML/SSO"),
        (AUTH_CARD_PIN, "LibraryCard+PIN"),
        (AUTH_PROXY_VPN, "Proxy/VPN"),
        (AUTH_API_KEY, "API Key"),
    ]

    name = models.CharField(max_length=255, unique=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    auth_method = models.CharField(max_length=20, choices=AUTH_CHOICES, default=AUTH_NONE)
    supports_api = models.BooleanField(default=False)
    discovery_methods = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class UserTextSourceCredential(models.Model):
    """Stores per-user credentials for a given TextSource."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="text_source_credentials")
    text_source = models.ForeignKey(TextSource, on_delete=models.CASCADE, related_name="credentials")
    auth_method = models.CharField(max_length=20, choices=TextSource.AUTH_CHOICES, default=TextSource.AUTH_NONE)
    encrypted_secret_blob = models.TextField(help_text="Encrypted secret or token reference")
    scopes = models.JSONField(default=list, blank=True, help_text="Connector-declared capabilities")
    last_validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "text_source")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.text_source_id}"


class AcquisitionCandidate(models.Model):
    """Candidate result for a text from a given source."""

    BORROW = "borrow"
    READ_ONLINE = "read_online"
    DOWNLOAD_OPEN = "download_open"
    PURCHASE_ONLY = "purchase_only"
    LOGIN_REQUIRED = "login_required"
    ACCESS_TYPES = [
        (BORROW, "Borrow"),
        (READ_ONLINE, "Read Online"),
        (DOWNLOAD_OPEN, "Download Open"),
        (PURCHASE_ONLY, "Purchase Only"),
        (LOGIN_REQUIRED, "Login Required"),
    ]

    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="acquisition_candidates")
    text_source = models.ForeignKey(TextSource, on_delete=models.CASCADE, related_name="candidates")
    match_score = models.FloatField(default=0)
    match_signals = models.JSONField(default=dict, blank=True)
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES)
    url = models.TextField()
    availability_snapshot = models.JSONField(default=dict, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_currency = models.CharField(max_length=10, blank=True)
    fetched_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["text", "text_source"]),
            models.Index(fields=["access_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.text_id}:{self.text_source_id} ({self.access_type})"


class AcquisitionLog(models.Model):
    """Audit log for acquisition actions."""

    ROLE_ADMIN = "admin"
    ROLE_TEACHER_OVERRIDE = "teacher_dev_override"
    ACTOR_ROLES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_TEACHER_OVERRIDE, "Teacher Dev Override"),
    ]

    METHOD_API = "api"
    METHOD_OAUTH = "oauth"
    METHOD_CARD_PIN = "card_pin"
    METHOD_AUTOMATION = "automation"
    METHOD_MANUAL = "manual"
    METHODS = [
        (METHOD_API, "API"),
        (METHOD_OAUTH, "OAuth"),
        (METHOD_CARD_PIN, "Card+PIN"),
        (METHOD_AUTOMATION, "Automation"),
        (METHOD_MANUAL, "Manual"),
    ]

    ACTION_SEARCH = "search"
    ACTION_AVAILABILITY = "availability"
    ACTION_HOLD = "hold"
    ACTION_BORROW = "borrow"
    ACTION_SAVE_LINK = "save_link"
    ACTION_OPEN = "open"
    ACTIONS = [
        (ACTION_SEARCH, "Search"),
        (ACTION_AVAILABILITY, "Availability"),
        (ACTION_HOLD, "Hold"),
        (ACTION_BORROW, "Borrow"),
        (ACTION_SAVE_LINK, "Save Link"),
        (ACTION_OPEN, "Open"),
    ]

    RESULT_SUCCESS = "success"
    RESULT_BLOCKED = "blocked"
    RESULT_ERROR = "error"
    RESULTS = [
        (RESULT_SUCCESS, "Success"),
        (RESULT_BLOCKED, "Blocked"),
        (RESULT_ERROR, "Error"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acquisition_logs")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="acquisition_logs")
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="acquisition_logs")
    text_source = models.ForeignKey(
        TextSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="acquisition_logs",
    )
    actor_role = models.CharField(max_length=30, choices=ACTOR_ROLES)
    method = models.CharField(max_length=20, choices=METHODS)
    action = models.CharField(max_length=20, choices=ACTIONS)
    result = models.CharField(max_length=20, choices=RESULTS)
    error_code = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["course", "text", "action"]),
            models.Index(fields=["text_source"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.text_id}:{self.action}:{self.result}"
