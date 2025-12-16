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

    # Instructor Dashboard
    path("instructor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),

    # Story management
    path("instructor/stories/", views.story_list, name="story_list"),
    path("instructor/stories/create/", views.story_create, name="story_create"),
    path("instructor/stories/generate/", views.story_generate, name="story_generate"),
    path("instructor/stories/generate/ai/", views.story_generate_ai, name="story_generate_ai"),
    path("instructor/stories/generate/preview/", views.story_generate_preview, name="story_generate_preview"),
    path("instructor/stories/generate/save/", views.story_generate_save, name="story_generate_save"),
    path("instructor/stories/<int:pk>/", views.story_edit, name="story_edit"),
    path("instructor/stories/<int:pk>/export/", views.story_export, name="story_export"),
    path("instructor/stories/<int:pk>/preview/", views.story_preview, name="story_preview"),
    path("instructor/stories/<int:pk>/delete/", views.story_delete, name="story_delete"),
    path("instructor/stories/<int:pk>/auto-segment/", views.story_auto_segment, name="story_auto_segment"),

    # Story import (from external sources)
    path("instructor/stories/import/", views.story_import_search, name="story_import_search"),
    path("instructor/stories/import/search/", views.story_import_search_results, name="story_import_search_results"),
    path("instructor/stories/import/details/<str:source>/<str:external_id>/", views.story_import_details, name="story_import_details"),
    path("instructor/stories/import/preview/", views.story_import_preview, name="story_import_preview"),
    path("instructor/stories/import/save/", views.story_import_save, name="story_import_save"),
    path("instructor/stories/import/bookmark/add/", views.story_import_bookmark_add, name="story_import_bookmark_add"),
    path("instructor/stories/import/bookmark/<int:pk>/remove/", views.story_import_bookmark_remove, name="story_import_bookmark_remove"),

    # Unit management
    path("instructor/units/", views.unit_list, name="unit_list"),
    path("instructor/units/create/", views.unit_create, name="unit_create"),
    path("instructor/units/<int:pk>/", views.unit_edit, name="unit_edit"),
    path("instructor/units/<int:pk>/delete/", views.unit_delete, name="unit_delete"),
    path("instructor/units/<int:pk>/available-lessons/", views.unit_available_lessons, name="unit_available_lessons"),
    path("instructor/units/<int:pk>/add-lesson/", views.unit_add_lesson, name="unit_add_lesson"),

    # Course management
    path("instructor/courses/", views.course_list, name="course_list"),
    path("instructor/courses/create/", views.course_create, name="course_create"),
    path("instructor/courses/<int:pk>/", views.course_edit, name="course_edit"),
    path("instructor/courses/<int:pk>/delete/", views.course_delete, name="course_delete"),

    # Term management (within stories)
    path("instructor/stories/<int:story_pk>/terms/create/", views.term_create, name="term_create"),
    path("instructor/stories/<int:story_pk>/terms/<int:term_pk>/", views.term_edit, name="term_edit"),
    path("instructor/stories/<int:story_pk>/terms/<int:term_pk>/delete/", views.term_delete, name="term_delete"),

    # Glossary generation (AI-powered)
    path("instructor/stories/<int:story_pk>/glossary/generate/", views.glossary_generate, name="glossary_generate"),
    path("instructor/stories/<int:story_pk>/glossary/generate/ai/", views.glossary_generate_ai, name="glossary_generate_ai"),
    path("instructor/stories/<int:story_pk>/glossary/generate/save/", views.glossary_generate_save, name="glossary_generate_save"),

    # Lesson management
    path("instructor/lessons/", views.instructor_lesson_list, name="instructor_lesson_list"),
    path("instructor/lessons/create/", views.lesson_create, name="lesson_create"),
    path("instructor/lessons/<int:pk>/", views.lesson_edit, name="lesson_edit"),
    path("instructor/lessons/<int:pk>/delete/", views.lesson_delete, name="lesson_delete"),
    path("instructor/lessons/quizzes-for-story/<int:story_pk>/", views.lesson_quizzes_for_story, name="lesson_quizzes_for_story"),

    # Quiz management
    path("instructor/quizzes/", views.quiz_list, name="quiz_list"),
    path("instructor/quizzes/create/", views.quiz_create, name="quiz_create"),
    path("instructor/quizzes/generate/", views.quiz_generate, name="quiz_generate"),
    path("instructor/quizzes/generate/ai/", views.quiz_generate_ai, name="quiz_generate_ai"),
    path("instructor/quizzes/generate/save/", views.quiz_generate_save, name="quiz_generate_save"),
    path("instructor/quizzes/<int:pk>/", views.quiz_edit, name="quiz_edit"),
    path("instructor/quizzes/<int:pk>/delete/", views.quiz_delete, name="quiz_delete"),
    path("instructor/quizzes/<int:pk>/add-question/", views.quiz_question_add, name="quiz_question_add"),
    path("instructor/quizzes/<int:pk>/create-question/", views.quiz_question_create, name="quiz_question_create"),
    path("instructor/quizzes/<int:pk>/remove-question/<int:qq_pk>/", views.quiz_question_remove, name="quiz_question_remove"),

    # Roster management
    path("instructor/rosters/", views.roster_list, name="roster_list"),
    path("instructor/rosters/create/", views.roster_create, name="roster_create"),
    path("instructor/rosters/<int:pk>/", views.roster_edit, name="roster_edit"),
    path("instructor/rosters/<int:pk>/add-student/", views.roster_add_student, name="roster_add_student"),
    path("instructor/rosters/<int:pk>/remove-student/<int:student_id>/", views.roster_remove_student, name="roster_remove_student"),
]
