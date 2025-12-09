from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Home
    path("", views.home_redirect, name="home"),

    # Student views
    path("lessons/", views.student_lessons, name="student_lessons"),
    path("lessons/<int:pk>/read/", views.lesson_read, name="lesson_read"),
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

    # Roster management
    path("instructor/rosters/", views.roster_list, name="roster_list"),
    path("instructor/rosters/create/", views.roster_create, name="roster_create"),
    path("instructor/rosters/<int:pk>/", views.roster_edit, name="roster_edit"),
]
