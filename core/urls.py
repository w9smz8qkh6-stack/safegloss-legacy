from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Home
    path("", views.home_redirect, name="home"),
    path("login-redirect/", views.login_redirect, name="login_redirect"),

    # Student views
    path("lessons/", views.student_lessons, name="student_lessons"),
    path("lessons/<int:pk>/", views.lesson_intro, name="lesson_intro"),
    path("lessons/<int:pk>/read/", views.lesson_read, name="lesson_read"),
    path("lessons/<int:pk>/quiz/", views.lesson_quiz, name="lesson_quiz"),
    path("lessons/<int:pk>/quiz/results/", views.lesson_quiz_results, name="lesson_quiz_results"),
    path("lessons/<int:lesson_id>/term/<int:term_id>/", views.glossary_term_detail, name="glossary_term_detail"),
    path("lessons/<int:lesson_id>/reading-event/", views.log_reading_event, name="log_reading_event"),

    # Teacher Dashboard
    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),

    # Story management
    path("teacher/stories/", views.story_list, name="story_list"),
    path("teacher/stories/create/", views.story_create, name="story_create"),
    path("teacher/stories/generate/", views.story_generate, name="story_generate"),
    path("teacher/stories/generate/ai/", views.story_generate_ai, name="story_generate_ai"),
    path("teacher/stories/generate/preview/", views.story_generate_preview, name="story_generate_preview"),
    path("teacher/stories/generate/save/", views.story_generate_save, name="story_generate_save"),
    path("teacher/stories/<int:pk>/", views.story_edit, name="story_edit"),
    path("teacher/stories/<int:pk>/export/", views.story_export, name="story_export"),
    path("teacher/stories/<int:pk>/preview/", views.story_preview, name="story_preview"),
    path("teacher/stories/<int:pk>/delete/", views.story_delete, name="story_delete"),
    path("teacher/stories/<int:pk>/auto-segment/", views.story_auto_segment, name="story_auto_segment"),

    # Story import (from external sources)
    path("teacher/stories/import/", views.story_import_search, name="story_import_search"),
    path("teacher/stories/import/search/", views.story_import_search_results, name="story_import_search_results"),
    path("teacher/stories/import/details/<str:source>/<str:external_id>/", views.story_import_details, name="story_import_details"),
    path("teacher/stories/import/preview/", views.story_import_preview, name="story_import_preview"),
    path("teacher/stories/import/save/", views.story_import_save, name="story_import_save"),
    path("teacher/stories/import/bookmark/add/", views.story_import_bookmark_add, name="story_import_bookmark_add"),
    path("teacher/stories/import/bookmark/<int:pk>/remove/", views.story_import_bookmark_remove, name="story_import_bookmark_remove"),

    # Unit management
    path("teacher/units/", views.unit_list, name="unit_list"),
    path("teacher/units/create/", views.unit_create, name="unit_create"),
    path("teacher/units/<int:pk>/", views.unit_edit, name="unit_edit"),
    path("teacher/units/<int:pk>/delete/", views.unit_delete, name="unit_delete"),
    path("teacher/units/<int:pk>/available-lessons/", views.unit_available_lessons, name="unit_available_lessons"),
    path("teacher/units/<int:pk>/add-lesson/", views.unit_add_lesson, name="unit_add_lesson"),

    # Course management
    path("teacher/courses/", views.course_list, name="course_list"),
    path("teacher/courses/create/", views.course_create, name="course_create"),
    path("teacher/courses/<int:pk>/", views.course_edit, name="course_edit"),
    path("teacher/courses/<int:pk>/delete/", views.course_delete, name="course_delete"),

    # Term management (within stories)
    path("teacher/stories/<int:story_pk>/terms/create/", views.term_create, name="term_create"),
    path("teacher/stories/<int:story_pk>/terms/<int:term_pk>/", views.term_edit, name="term_edit"),
    path("teacher/stories/<int:story_pk>/terms/<int:term_pk>/delete/", views.term_delete, name="term_delete"),

    # Glossary generation (AI-powered)
    path("teacher/stories/<int:story_pk>/glossary/generate/", views.glossary_generate, name="glossary_generate"),
    path("teacher/stories/<int:story_pk>/glossary/generate/ai/", views.glossary_generate_ai, name="glossary_generate_ai"),
    path("teacher/stories/<int:story_pk>/glossary/generate/save/", views.glossary_generate_save, name="glossary_generate_save"),

    # Lesson management
    path("teacher/lessons/", views.teacher_lesson_list, name="teacher_lesson_list"),
    path("teacher/lessons/create/", views.lesson_create, name="lesson_create"),
    path("teacher/lessons/<int:pk>/", views.lesson_edit, name="lesson_edit"),
    path("teacher/lessons/<int:pk>/delete/", views.lesson_delete, name="lesson_delete"),
    path("teacher/lessons/quizzes-for-story/<int:story_pk>/", views.lesson_quizzes_for_story, name="lesson_quizzes_for_story"),

    # Quiz management
    path("teacher/quizzes/", views.quiz_list, name="quiz_list"),
    path("teacher/quizzes/create/", views.quiz_create, name="quiz_create"),
    path("teacher/quizzes/generate/", views.quiz_generate, name="quiz_generate"),
    path("teacher/quizzes/generate/ai/", views.quiz_generate_ai, name="quiz_generate_ai"),
    path("teacher/quizzes/generate/save/", views.quiz_generate_save, name="quiz_generate_save"),
    path("teacher/quizzes/<int:pk>/", views.quiz_edit, name="quiz_edit"),
    path("teacher/quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path("teacher/quizzes/<int:pk>/add-question/", views.quiz_question_add, name="quiz_question_add"),
    path("teacher/quizzes/<int:pk>/create-question/", views.quiz_question_create, name="quiz_question_create"),
    path("teacher/quizzes/<int:pk>/remove-question/<int:qq_pk>/", views.quiz_question_remove, name="quiz_question_remove"),
    path("teacher/quizzes/<int:pk>/reorder/", views.quiz_question_reorder, name="quiz_question_reorder"),
    path("teacher/quizzes/<int:pk>/toggle-freeze/<int:qq_pk>/", views.quiz_question_toggle_freeze, name="quiz_question_toggle_freeze"),
    path("teacher/questions/<int:pk>/edit/", views.question_edit, name="question_edit"),

    # Roster management
    path("teacher/rosters/", views.roster_list, name="roster_list"),
    path("teacher/rosters/create/", views.roster_create, name="roster_create"),
    path("teacher/rosters/<int:pk>/", views.roster_edit, name="roster_edit"),
    path("teacher/rosters/<int:pk>/add-student/", views.roster_add_student, name="roster_add_student"),
    path("teacher/rosters/<int:pk>/remove-student/<int:student_id>/", views.roster_remove_student, name="roster_remove_student"),

    # Standards & Learning Objectives
    path("teacher/standards/", views.standards_browse, name="standards_browse"),
    path("teacher/standards/api/authorities/", views.standards_api_authorities, name="standards_api_authorities"),
    path("teacher/standards/api/programs/", views.standards_api_programs, name="standards_api_programs"),
    path("teacher/standards/api/grades/", views.standards_api_grades, name="standards_api_grades"),
    path("teacher/standards/api/subjects/", views.standards_api_subjects, name="standards_api_subjects"),
    path("teacher/standards/api/courses/", views.standards_api_courses, name="standards_api_courses"),
    path("teacher/standards/api/results/", views.standards_api_results, name="standards_api_results"),
    path("teacher/standards/api/document/<int:document_id>/objectives/", views.standards_api_objectives, name="standards_api_document_objectives"),
    path("teacher/standards/api/document/<int:document_id>/assets/", views.standards_api_cambridge_assets, name="standards_api_document_assets"),
    path("teacher/standards/api/search/", views.standards_api_search, name="standards_api_search"),
    path("teacher/standards/api/media/", views.standards_api_media, name="standards_api_media"),
    path("teacher/standards/api/sync/objectives/", views.standards_api_sync_objectives, name="standards_api_sync_objectives"),
    path("teacher/standards/api/sync/resources/", views.standards_api_sync_resources, name="standards_api_sync_resources"),
    path("teacher/standards/api/job/<int:job_id>/", views.standards_api_job_status, name="standards_api_job_status"),
    path("teacher/standards/api/artifact/<int:artifact_id>/download/", views.standards_api_artifact_download, name="standards_api_artifact_download"),
    path("teacher/standards/api/import/resources/", views.standards_api_import_resources, name="standards_api_import_resources"),
    path("teacher/standards/api/import/resources/ai/", views.standards_api_import_resources_ai, name="standards_api_import_resources_ai"),
    path("teacher/standards/api/import/objectives/ai/", views.standards_api_import_objectives_ai, name="standards_api_import_objectives_ai"),

    # Unified Tab Data API (Provider Tab Configuration)
    path("teacher/standards/api/tab-config/", views.standards_api_tab_config, name="standards_api_tab_config"),
    path("teacher/standards/api/document/<int:document_id>/tab/<str:tab_id>/", views.standards_api_tab_data, name="standards_api_tab_data"),
]
