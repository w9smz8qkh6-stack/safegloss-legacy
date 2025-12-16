from django.contrib import admin

from .models import (
    AcquisitionCandidate,
    AcquisitionLog,
    CourseText,
    Text,
    TextSource,
    UserTextSourceCredential,
)


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn13", "isbn10", "publisher", "publication_year")
    search_fields = ("title", "isbn13", "isbn10", "oclc", "authors")
    list_filter = ("publisher", "publication_year")


@admin.register(CourseText)
class CourseTextAdmin(admin.ModelAdmin):
    list_display = ("course", "text", "requirement_level")
    search_fields = ("course__title", "text__title", "text__isbn13", "text__isbn10")
    list_filter = ("requirement_level",)


@admin.register(TextSource)
class TextSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "auth_method", "supports_api")
    list_filter = ("source_type", "auth_method", "supports_api")
    search_fields = ("name",)


@admin.register(UserTextSourceCredential)
class UserTextSourceCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "text_source", "auth_method", "last_validated_at")
    list_filter = ("auth_method", "text_source")
    search_fields = ("user__email", "user__username", "text_source__name")


@admin.register(AcquisitionCandidate)
class AcquisitionCandidateAdmin(admin.ModelAdmin):
    list_display = ("text", "text_source", "access_type", "match_score", "fetched_at")
    list_filter = ("access_type", "text_source")
    search_fields = ("text__title", "text__isbn13", "text__isbn10", "url")


@admin.register(AcquisitionLog)
class AcquisitionLogAdmin(admin.ModelAdmin):
    list_display = ("text", "text_source", "action", "result", "actor_role", "created_at")
    list_filter = ("action", "result", "actor_role", "text_source")
    search_fields = ("text__title", "course__title", "user__email", "user__username")
