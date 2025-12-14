from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Home
    path("", views.home_redirect, name="home"),
    path("offline/", views.offline, name="offline"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),

    # Student views
    path("join/", views.join_roster, name="join_roster"),
    path("lessons/", views.student_lessons, name="student_lessons"),
    path("lessons/<int:pk>/", views.lesson_intro, name="lesson_intro"),
    path("lessons/<int:pk>/read/", views.lesson_read, name="lesson_read"),
    path("lessons/<int:pk>/quiz/", views.lesson_quiz, name="lesson_quiz"),
    path("lessons/<int:pk>/quiz/results/<int:submission_id>/", views.quiz_results, name="quiz_results"),
    path("lessons/<int:lesson_id>/term/<int:term_id>/", views.glossary_term_detail, name="glossary_term_detail"),

    # Instructor Dashboard
    path("instructor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),

    # Story management
    path("instructor/stories/", views.story_list, name="story_list"),
    path("instructor/stories/create/", views.story_create, name="story_create"),
    path("instructor/stories/<int:pk>/", views.story_edit, name="story_edit"),
    path("instructor/stories/<int:pk>/delete/", views.story_delete, name="story_delete"),

    # Term management (within stories)
    path("instructor/stories/<int:story_pk>/terms/create/", views.term_create, name="term_create"),
    path("instructor/stories/<int:story_pk>/terms/<int:term_pk>/", views.term_edit, name="term_edit"),
    path("instructor/stories/<int:story_pk>/terms/<int:term_pk>/delete/", views.term_delete, name="term_delete"),

    # Lesson management
    path("instructor/lessons/", views.instructor_lesson_list, name="instructor_lesson_list"),
    path("instructor/lessons/create/", views.lesson_create, name="lesson_create"),
    path("instructor/lessons/<int:pk>/", views.lesson_edit, name="lesson_edit"),
    path("instructor/lessons/<int:pk>/delete/", views.lesson_delete, name="lesson_delete"),

    # Quiz management
    path("instructor/quizzes/", views.quiz_list, name="quiz_list"),
    path("instructor/quizzes/create/", views.quiz_create, name="quiz_create"),
    path("instructor/quizzes/<int:pk>/", views.quiz_edit, name="quiz_edit"),
    path("instructor/quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path("instructor/quizzes/<int:pk>/add-question/", views.quiz_add_question, name="quiz_add_question"),
    path("instructor/quizzes/<int:pk>/remove-question/<int:qq_pk>/", views.quiz_remove_question, name="quiz_remove_question"),
    path("instructor/quizzes/<int:pk>/reorder-questions/", views.quiz_reorder_questions, name="quiz_reorder_questions"),

    # Roster management
    path("instructor/rosters/", views.roster_list, name="roster_list"),
    path("instructor/rosters/create/", views.roster_create, name="roster_create"),
    path("instructor/rosters/<int:pk>/", views.roster_edit, name="roster_edit"),
    path("instructor/rosters/<int:pk>/add-student/", views.roster_add_student, name="roster_add_student"),
    path("instructor/rosters/<int:pk>/remove-student/<int:membership_pk>/", views.roster_remove_student, name="roster_remove_student"),
    path("instructor/rosters/<int:pk>/export/", views.export_roster_progress, name="export_roster_progress"),

    # Data exports
    path("instructor/lessons/<int:pk>/export-quiz/", views.export_quiz_results, name="export_quiz_results"),
    path("instructor/lessons/<int:pk>/export-progress/", views.export_lesson_progress, name="export_lesson_progress"),

    # Analytics
    path("instructor/rosters/<int:pk>/analytics/", views.roster_analytics, name="roster_analytics"),
    path("instructor/rosters/<int:pk>/analytics/data/", views.roster_analytics_data, name="roster_analytics_data"),
    path("instructor/rosters/<int:roster_pk>/students/<int:student_pk>/", views.student_detail, name="student_detail"),
    path("instructor/analytics/compare/", views.roster_comparison, name="roster_comparison"),
    path("instructor/export/full/", views.export_full_data, name="export_full_data"),

    # API endpoints for tracking
    path("api/segment-view/", views.log_segment_view, name="log_segment_view"),
    path("api/lesson/<int:pk>/cache-data/", views.lesson_cache_data, name="lesson_cache_data"),
    path("api/lexile-analyze/", views.lexile_analyze_api, name="lexile_analyze_api"),

    # AI Story Generation
    path("instructor/stories/generate/", views.story_generate, name="story_generate"),
    path("instructor/stories/generate/save/", views.story_generate_save, name="story_generate_save"),
    path("instructor/stories/<int:pk>/adjust-lexile/", views.story_adjust_lexile, name="story_adjust_lexile"),
    path("instructor/stories/<int:pk>/adjust-lexile/save/", views.story_adjust_save, name="story_adjust_save"),
    path("instructor/lexile-analyze/", views.lexile_analyze, name="lexile_analyze"),

    # AI Glossary Generation
    path("instructor/stories/<int:pk>/glossary/generate/", views.glossary_generate, name="glossary_generate"),
    path("instructor/stories/<int:pk>/glossary/generate/save/", views.glossary_generate_save, name="glossary_generate_save"),
    path("api/stories/<int:pk>/glossary/generate/", views.glossary_generate_api, name="glossary_generate_api"),

    # AI Quiz Generation
    path("instructor/stories/<int:story_pk>/quiz/generate/", views.quiz_generate, name="quiz_generate"),
    path("instructor/stories/<int:story_pk>/quiz/generate/save/", views.quiz_generate_save, name="quiz_generate_save"),
    path("api/stories/<int:story_pk>/quiz/generate/", views.quiz_generate_api, name="quiz_generate_api"),
]
