from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Site, User, Roster, RosterMembership, Story, StorySegment,
    MediaAsset, SegmentMedia, Glossary, Term, TermOccurrence,
    ItemBankQuestion, ItemBankChoice, Quiz, QuizQuestion,
    QuizSubmission, QuizSubmissionAnswer, Lesson, LessonProgress,
    GlossClickLog, ReadingEvent,
    # Standards models
    StandardsAuthority, AuthorityProgram, StandardsArtifact,
    StandardsDocument, ObjectiveNode, ObjectiveCodeMap,
    AuthorityProgramMedia, AuthorityProgramMediaTag,
    # Background jobs
    BackgroundJob,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'site', 'is_staff')
    list_filter = ('role', 'site', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'site')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'site')}),
    )


@admin.register(Roster)
class RosterAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'grade_band', 'created_at')
    list_filter = ('site', 'grade_band')
    search_fields = ('name',)


@admin.register(RosterMembership)
class RosterMembershipAdmin(admin.ModelAdmin):
    list_display = ('roster', 'student')
    list_filter = ('roster',)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'source_type', 'reading_level_label', 'created_at')
    list_filter = ('source_type', 'teacher')
    search_fields = ('title',)


@admin.register(StorySegment)
class StorySegmentAdmin(admin.ModelAdmin):
    list_display = ('story', 'index', 'title')
    list_filter = ('story',)
    ordering = ('story', 'index')


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('media_type', 'file_path', 'owner', 'created_at')
    list_filter = ('media_type', 'owner')


@admin.register(SegmentMedia)
class SegmentMediaAdmin(admin.ModelAdmin):
    list_display = ('segment', 'media', 'role', 'order')
    list_filter = ('role',)


@admin.register(Glossary)
class GlossaryAdmin(admin.ModelAdmin):
    list_display = ('name', 'story', 'language_code', 'native_language_code')
    search_fields = ('name', 'story__title')


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('term_text', 'glossary', 'part_of_speech', 'is_ai_suggested', 'is_selected_for_glossary')
    list_filter = ('glossary', 'is_ai_suggested', 'is_selected_for_glossary')
    search_fields = ('term_text', 'lemma')


@admin.register(TermOccurrence)
class TermOccurrenceAdmin(admin.ModelAdmin):
    list_display = ('term', 'story', 'segment', 'anchor_text')
    list_filter = ('story', 'term')


@admin.register(ItemBankQuestion)
class ItemBankQuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'question_type', 'owner', 'status', 'default_points')
    list_filter = ('question_type', 'status', 'owner')


@admin.register(ItemBankChoice)
class ItemBankChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'label', 'is_correct', 'order')
    list_filter = ('is_correct',)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'total_points', 'created_at')
    search_fields = ('title',)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question', 'order', 'points')
    list_filter = ('quiz',)


@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'started_at', 'submitted_at', 'raw_score')
    list_filter = ('quiz', 'student')


@admin.register(QuizSubmissionAnswer)
class QuizSubmissionAnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'is_correct')
    list_filter = ('is_correct',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'site', 'story', 'is_active', 'created_at')
    list_filter = ('site', 'is_active', 'teacher')
    search_fields = ('title',)
    filter_horizontal = ('rosters',)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'reading_start', 'reading_end', 'comprehension_score')
    list_filter = ('lesson',)


@admin.register(GlossClickLog)
class GlossClickLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'term', 'clicked_at')
    list_filter = ('lesson', 'term')


@admin.register(ReadingEvent)
class ReadingEventAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'event_type', 'created_at')
    list_filter = ('event_type', 'lesson')


# =============================================================================
# Standards & Learning Objectives Admin
# =============================================================================

@admin.register(StandardsAuthority)
class StandardsAuthorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(AuthorityProgram)
class AuthorityProgramAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'authority', 'is_active', 'created_at')
    list_filter = ('authority', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('authority', 'name')


@admin.register(StandardsArtifact)
class StandardsArtifactAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'content_type', 'sha256_hash', 'created_at')
    list_filter = ('content_type',)
    search_fields = ('original_filename', 'file_path')


@admin.register(StandardsDocument)
class StandardsDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'subject', 'grade_level', 'authority_program',
        'version_label', 'acquisition_method', 'is_active', 'created_at'
    )
    list_filter = (
        'authority_program__authority', 'authority_program',
        'acquisition_method', 'is_active', 'is_reference_only'
    )
    search_fields = ('subject', 'grade_level', 'source_title', 'source_publisher_name')
    ordering = ('authority_program', 'subject', 'grade_level')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identification', {
            'fields': ('authority_program', 'subject', 'grade_level', 'version_label')
        }),
        ('Provenance', {
            'fields': (
                'source_publisher_name', 'source_publisher_type', 'source_title',
                'source_url', 'source_url_canonical', 'source_accessed_at',
                'source_content_type', 'source_version_label',
                'source_effective_from', 'source_effective_until', 'source_license_notes'
            )
        }),
        ('Acquisition', {
            'fields': ('acquisition_method', 'acquisition_notes')
        }),
        ('Evidence', {
            'fields': ('evidence_artifact', 'evidence_sha256_raw', 'evidence_sha256_canonical')
        }),
        ('Status', {
            'fields': ('is_active', 'is_reference_only', 'created_at', 'updated_at')
        }),
    )


class ObjectiveNodeInline(admin.TabularInline):
    model = ObjectiveNode
    fk_name = 'document'
    extra = 0
    fields = ('sort_order', 'node_type', 'code', 'text', 'internal_code')
    readonly_fields = ('internal_code',)
    show_change_link = True


@admin.register(ObjectiveNode)
class ObjectiveNodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'internal_code', 'node_type', 'document', 'sort_order')
    list_filter = ('document__authority_program', 'node_type')
    search_fields = ('code', 'internal_code', 'text')
    ordering = ('document', 'sort_order')
    raw_id_fields = ('document', 'parent')


@admin.register(ObjectiveCodeMap)
class ObjectiveCodeMapAdmin(admin.ModelAdmin):
    list_display = ('native_code', 'internal_code', 'mapping_method', 'mapped_by', 'mapped_at')
    list_filter = ('mapping_method',)
    search_fields = ('native_code', 'internal_code')
    raw_id_fields = ('objective_node', 'mapped_by')


class AuthorityProgramMediaTagInline(admin.TabularInline):
    model = AuthorityProgramMediaTag
    extra = 1


@admin.register(AuthorityProgramMedia)
class AuthorityProgramMediaAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'authority_program', 'media_type', 'platform',
        'is_official', 'is_unofficial', 'created_at'
    )
    list_filter = ('authority_program__authority', 'media_type', 'platform', 'is_official')
    search_fields = ('title', 'author', 'isbn_10', 'isbn_13', 'description')
    ordering = ('-is_official', 'title')
    raw_id_fields = ('authority_program',)
    inlines = [AuthorityProgramMediaTagInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('authority_program', 'title', 'author', 'publisher', 'description')
        }),
        ('Identifiers', {
            'fields': ('isbn_10', 'isbn_13', 'source_url', 'cover_image_url')
        }),
        ('Classification', {
            'fields': ('media_type', 'platform', 'is_official', 'is_unofficial', 'endorsement_notes')
        }),
        ('Features', {
            'fields': ('features',)
        }),
        ('Metadata', {
            'fields': ('retrieved_from', 'retrieved_at', 'metadata_raw'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AuthorityProgramMediaTag)
class AuthorityProgramMediaTagAdmin(admin.ModelAdmin):
    list_display = ('label', 'media')
    list_filter = ('label',)
    search_fields = ('label', 'media__title')


# =============================================================================
# Background Jobs Admin
# =============================================================================

@admin.register(BackgroundJob)
class BackgroundJobAdmin(admin.ModelAdmin):
    list_display = (
        'job_type', 'status', 'progress_pct', 'created_by',
        'created_at', 'started_at', 'completed_at'
    )
    list_filter = ('job_type', 'status', 'created_at')
    search_fields = ('idempotency_key', 'progress_message', 'error_message')
    readonly_fields = (
        'idempotency_key', 'started_at', 'completed_at',
        'progress_pct', 'progress_message', 'result', 'error_message',
        'retry_count', 'created_at'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Job Info', {
            'fields': ('job_type', 'idempotency_key', 'params', 'created_by')
        }),
        ('Status', {
            'fields': ('status', 'progress_pct', 'progress_message')
        }),
        ('Results', {
            'fields': ('result', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Retry', {
            'fields': ('retry_count', 'max_retries', 'next_retry_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at'),
        }),
    )

    actions = ['cancel_jobs', 'retry_jobs']

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'running']).update(status='cancelled')
        self.message_user(request, f"{updated} job(s) cancelled.")

    @admin.action(description="Retry failed jobs")
    def retry_jobs(self, request, queryset):
        count = 0
        for job in queryset.filter(status='failed'):
            if job.can_retry():
                job.schedule_retry()
                count += 1
        self.message_user(request, f"{count} job(s) scheduled for retry.")
