from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from django.db.models import Count, Max, Case, When, IntegerField, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from functools import wraps
from django.conf import settings

from django.http import JsonResponse
from django.http import FileResponse, Http404
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI
from core.services.standards.import_service import _compute_sha256, _generate_internal_codes

from .forms import (
    LessonFilterForm, StoryForm, StorySegmentFormSet, GlossaryForm, TermForm,
    LessonForm, QuizForm, ItemBankQuestionForm, ItemBankChoiceFormSet, RosterForm,
    StoryGeneratorForm, QuizGeneratorForm, UnitForm, UnitLessonFormSet, GlossaryGeneratorForm,
    CourseForm, CourseUnitFormSet, RosterAddStudentForm,
    ExternalBookSearchForm, ExternalBookImportForm
)
from .models import (
    Lesson, LessonProgress, RosterMembership, Term, GlossClickLog, ReadingEvent,
    Story, StorySegment, Glossary, Quiz, QuizQuestion, QuizSubmission, QuizSubmissionAnswer,
    ItemBankQuestion, ItemBankChoice, Roster, Site,
    Unit, UnitLesson, Course, CourseUnit, ExternalBookmark,
    # Standards models
    StandardsAuthority, AuthorityProgram, StandardsDocument, ObjectiveNode,
    AuthorityProgramMedia, AuthorityProgramMediaTag,
    # Background jobs
    BackgroundJob,
    StandardsArtifact,
)


def teacher_required(view_func):
    """Decorator to check if user is teacher or researcher."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("account_login")
        if not (user.is_teacher() or user.is_researcher()):
            # Redirect to home instead of student_lessons to avoid potential loops
            return redirect("core:home")
        return view_func(request, *args, **kwargs)
    return wrapper


def student_can_access_lesson(user, lesson):
    """
    Check if a student can access a lesson through:
    1. Direct roster assignment (Lesson.rosters)
    2. Course membership (Course.rosters → CourseUnit → UnitLesson)
    """
    roster_ids = list(RosterMembership.objects.filter(student=user).values_list("roster_id", flat=True))
    if not roster_ids:
        return False

    # Check direct assignment
    if lesson.rosters.filter(pk__in=roster_ids).exists():
        return True

    # Check course membership: lesson in a unit that's in a course assigned to student's roster
    # Get all units this lesson belongs to
    unit_ids = lesson.unit_memberships.values_list("unit_id", flat=True)
    if not unit_ids:
        return False

    # Check if any course containing these units is assigned to the student's rosters
    return Course.objects.filter(
        course_units__unit_id__in=unit_ids,
        rosters__in=roster_ids
    ).exists()


def home_redirect(request):
    if request.user.is_authenticated:
        if getattr(request.user, "role", "") in ("teacher", "researcher"):
            return redirect("core:teacher_dashboard")
        return redirect("core:student_lessons")
    return render(request, "core/home.html")


def login_redirect(request):
    """Redirect users to appropriate dashboard based on role after login."""
    user = request.user
    if not user.is_authenticated:
        return redirect("account_login")
    if user.is_teacher() or user.is_researcher():
        return redirect("core:teacher_dashboard")
    return redirect("core:student_lessons")


# =============================================================================
# STUDENT VIEWS
# =============================================================================

@login_required
def student_lessons(request):
    user = request.user
    # Only redirect to teacher dashboard if user is explicitly a teacher/researcher
    # Don't redirect students or users with unknown roles (they should see student view)
    if user.is_teacher() or user.is_researcher():
        return redirect("core:teacher_dashboard")

    roster_ids = list(RosterMembership.objects.filter(student=user).values_list("roster_id", flat=True))

    # Get courses assigned to student's rosters
    courses = (
        Course.objects.filter(rosters__in=roster_ids)
        .prefetch_related(
            "course_units__unit__unit_lessons__lesson__story",
            "course_units__unit__unit_lessons__lesson__quiz",
        )
        .distinct()
        .order_by("title")
    )

    # Build hierarchical structure: Course → Units → Lessons
    course_structure = []
    lessons_in_courses = set()

    for course in courses:
        course_data = {
            "course": course,
            "units": []
        }
        for course_unit in course.course_units.all().order_by("order"):
            unit = course_unit.unit
            unit_lessons = []
            for unit_lesson in unit.unit_lessons.all().order_by("order"):
                lesson = unit_lesson.lesson
                if lesson.is_active:
                    unit_lessons.append(lesson)
                    lessons_in_courses.add(lesson.pk)
            if unit_lessons:
                course_data["units"].append({
                    "unit": unit,
                    "lessons": unit_lessons
                })
        if course_data["units"]:
            course_structure.append(course_data)

    # Get standalone lessons (assigned directly to rosters but not in any course)
    standalone_lessons = (
        Lesson.objects.filter(rosters__in=roster_ids, is_active=True)
        .exclude(pk__in=lessons_in_courses)
        .select_related("story", "quiz")
        .distinct()
        .order_by("title")
    )

    # Collect all lesson IDs for progress lookup
    all_lesson_ids = list(lessons_in_courses) + list(standalone_lessons.values_list("pk", flat=True))

    form = LessonFilterForm(request.GET or None)
    search_term = ""
    if form.is_valid():
        search_term = form.cleaned_data.get("search") or ""

    # Filter by search if provided
    if search_term:
        # Filter standalone lessons
        standalone_lessons = standalone_lessons.filter(title__icontains=search_term)
        # Filter course structure
        filtered_course_structure = []
        for course_data in course_structure:
            filtered_units = []
            for unit_data in course_data["units"]:
                filtered_lessons = [l for l in unit_data["lessons"] if search_term.lower() in l.title.lower()]
                if filtered_lessons:
                    filtered_units.append({
                        "unit": unit_data["unit"],
                        "lessons": filtered_lessons
                    })
            if filtered_units:
                filtered_course_structure.append({
                    "course": course_data["course"],
                    "units": filtered_units
                })
        course_structure = filtered_course_structure

    progress_map = {
        lp.lesson_id: lp for lp in LessonProgress.objects.filter(student=user, lesson_id__in=all_lesson_ids)
    }

    context = {
        "course_structure": course_structure,
        "standalone_lessons": standalone_lessons,
        "progress_map": progress_map,
        "filter_form": form,
    }
    return render(request, "core/student_lesson_list.html", context)


@login_required
def lesson_intro(request, pk):
    """Lesson introduction page before reading."""
    user = request.user
    lesson = get_object_or_404(
        Lesson.objects.select_related("story", "quiz", "site"),
        pk=pk,
    )

    # Check access for students (via direct roster or course membership)
    if hasattr(user, "is_student") and user.is_student():
        if not student_can_access_lesson(user, lesson):
            messages.error(request, "You don't have access to this lesson.")
            return redirect("core:student_lessons")

    allowed_modes = lesson.allowed_modes or [lesson.default_mode]
    progress = LessonProgress.objects.filter(student=user, lesson=lesson).first()

    context = {
        "lesson": lesson,
        "allowed_modes": allowed_modes,
        "progress": progress,
    }
    return render(request, "core/student/lesson_intro.html", context)


@login_required
def lesson_read(request, pk):
    """Main reading view with mode support."""
    user = request.user
    lesson = get_object_or_404(
        Lesson.objects.select_related("story", "story__glossary", "quiz"),
        pk=pk,
    )

    # Check access for students (via direct roster or course membership)
    if hasattr(user, "is_student") and user.is_student():
        if not student_can_access_lesson(user, lesson):
            return redirect("core:student_lessons")

    mode = request.GET.get("mode") or lesson.default_mode
    allowed_modes = lesson.allowed_modes or [lesson.default_mode]

    if mode not in allowed_modes:
        mode = lesson.default_mode

    story = lesson.story
    segments = story.segments.order_by("index")

    # Create or update lesson progress
    progress, created = LessonProgress.objects.get_or_create(
        student=user,
        lesson=lesson,
        defaults={"reading_start": timezone.now()}
    )
    if created or not progress.reading_start:
        progress.reading_start = timezone.now()
        progress.save()

    context = {
        "lesson": lesson,
        "story": story,
        "segments": segments,
        "mode": mode,
        "allowed_modes": allowed_modes,
        "progress": progress,
    }
    return render(request, "core/student/lesson_read.html", context)


@login_required
def lesson_quiz(request, pk):
    """Quiz view for a lesson - handles both display (GET) and submission (POST)."""
    user = request.user
    lesson = get_object_or_404(
        Lesson.objects.select_related("story", "quiz"),
        pk=pk,
    )

    if not lesson.quiz:
        messages.info(request, "This lesson doesn't have a quiz.")
        return redirect("core:lesson_read", pk=pk)

    # Check access for students
    if hasattr(user, "is_student") and user.is_student():
        roster_ids = lesson.rosters.values_list("id", flat=True)
        if not RosterMembership.objects.filter(student=user, roster_id__in=roster_ids).exists():
            return redirect("core:student_lessons")

    quiz = lesson.quiz
    questions = quiz.quiz_questions.select_related("question").prefetch_related(
        "question__choices"
    ).order_by("order")

    # Get or create submission for this user/quiz
    submission, created = QuizSubmission.objects.get_or_create(
        student=user,
        quiz=quiz,
        submitted_at__isnull=True,  # Only get unsubmitted
        defaults={"started_at": timezone.now()}
    )

    # Update LessonProgress quiz_start if not set
    progress, _ = LessonProgress.objects.get_or_create(
        student=user, lesson=lesson
    )
    if not progress.quiz_start:
        progress.quiz_start = timezone.now()
        progress.save()

    if request.method == "POST":
        # Handle quiz submission
        import json

        # Get time tracking data from hidden field
        time_data = {}
        try:
            time_data = json.loads(request.POST.get("question_times", "{}"))
        except json.JSONDecodeError:
            pass

        total_score = 0
        max_score = 0

        for qq in questions:
            question = qq.question
            points = qq.points or question.default_points or 1

            # Get the answer(s) for this question
            answer_key = f"q_{question.pk}"
            answer_value = request.POST.getlist(answer_key)

            # Create submission answer
            question_time_data = time_data.get(str(question.pk), {})
            time_ms = question_time_data.get("time_ms", 0) if isinstance(question_time_data, dict) else 0
            answer = QuizSubmissionAnswer(
                submission=submission,
                question=question,
                question_type=question.question_type,
                time_spent_seconds=time_ms / 1000 if time_ms else None  # Convert ms to seconds
            )

            is_correct = None
            partial_credit = None

            if question.question_type in ("mcq_single", "true_false"):
                # Single choice - check if correct
                selected_ids = [int(v) for v in answer_value if v]
                answer.selected_choice_ids = selected_ids

                if selected_ids:
                    correct_choices = question.choices.filter(is_correct=True).values_list("pk", flat=True)
                    is_correct = set(selected_ids) == set(correct_choices)

            elif question.question_type == "mcq_multi":
                # Multiple choice - check all correct
                selected_ids = [int(v) for v in answer_value if v]
                answer.selected_choice_ids = selected_ids

                correct_choices = set(question.choices.filter(is_correct=True).values_list("pk", flat=True))
                selected_set = set(selected_ids)

                if correct_choices:
                    # Partial credit: correct selections / total correct choices
                    correct_selected = len(selected_set & correct_choices)
                    incorrect_selected = len(selected_set - correct_choices)
                    if incorrect_selected == 0 and correct_selected == len(correct_choices):
                        is_correct = True
                        partial_credit = 1.0
                    elif incorrect_selected == 0 and correct_selected > 0:
                        partial_credit = correct_selected / len(correct_choices)
                        is_correct = False
                    else:
                        is_correct = False
                        partial_credit = 0

            elif question.question_type == "short_answer":
                answer.short_answer_text = answer_value[0] if answer_value else ""
                # Short answers require manual grading

            elif question.question_type == "long_answer":
                answer.long_answer_text = answer_value[0] if answer_value else ""
                # Long answers require manual grading

            answer.is_correct = is_correct
            answer.partial_credit_ratio = partial_credit
            answer.save()

            # Calculate score
            max_score += points
            if is_correct:
                total_score += points
            elif partial_credit is not None:
                total_score += points * partial_credit

        # Mark submission as complete
        submission.submitted_at = timezone.now()
        submission.raw_score = total_score
        submission.max_score = max_score
        submission.save()

        # Update LessonProgress
        progress.quiz_end = timezone.now()
        progress.comprehension_score = (total_score / max_score * 100) if max_score > 0 else 0
        progress.save()

        return redirect("core:lesson_quiz_results", pk=pk)

    context = {
        "lesson": lesson,
        "quiz": quiz,
        "questions": questions,
        "submission": submission,
    }
    return render(request, "core/student/lesson_quiz.html", context)


@login_required
def lesson_quiz_results(request, pk):
    """Display quiz results after submission."""
    user = request.user
    lesson = get_object_or_404(
        Lesson.objects.select_related("story", "quiz"),
        pk=pk,
    )

    if not lesson.quiz:
        return redirect("core:lesson_intro", pk=pk)

    quiz = lesson.quiz

    # Get the most recent submitted submission
    submission = QuizSubmission.objects.filter(
        student=user,
        quiz=quiz,
        submitted_at__isnull=False
    ).order_by("-submitted_at").first()

    if not submission:
        return redirect("core:lesson_quiz", pk=pk)

    # Get answers with question details
    answers = submission.answers.select_related("question").prefetch_related(
        "question__choices"
    ).all()

    # Get quiz questions for points info
    quiz_questions = {
        qq.question_id: qq for qq in quiz.quiz_questions.all()
    }

    # Build results data
    results = []
    for answer in answers:
        question = answer.question
        correct_choice_ids = set(
            question.choices.filter(is_correct=True).values_list("pk", flat=True)
        )

        # Get points for this question
        qq = quiz_questions.get(question.pk)
        points_possible = qq.points if qq and qq.points else question.default_points or 1.0

        # Calculate points earned
        if answer.is_correct is True:
            points_earned = points_possible
        elif answer.partial_credit_ratio is not None:
            points_earned = points_possible * answer.partial_credit_ratio
        else:
            points_earned = 0.0

        # Determine if needs grading (text answers with is_correct=None)
        needs_grading = (
            question.question_type in ("short_answer", "long_answer")
            and answer.is_correct is None
        )

        # Get text answer
        text_answer = answer.short_answer_text or answer.long_answer_text or ""

        # Format time spent
        time_spent_formatted = None
        if answer.time_spent_seconds:
            secs = int(answer.time_spent_seconds)
            time_spent_formatted = f"{secs}s" if secs < 60 else f"{secs // 60}m {secs % 60}s"

        results.append({
            "question": question,
            "answer": answer,
            "correct_choice_ids": correct_choice_ids,
            "selected_ids": set(answer.selected_choice_ids) if answer.selected_choice_ids else set(),
            "points_possible": points_possible,
            "points_earned": points_earned,
            "needs_grading": needs_grading,
            "text_answer": text_answer,
            "time_spent_formatted": time_spent_formatted,
        })

    # Calculate time spent
    time_spent_seconds = None
    time_spent_formatted = None
    if submission.started_at and submission.submitted_at:
        time_spent_seconds = (submission.submitted_at - submission.started_at).total_seconds()
        minutes = int(time_spent_seconds // 60)
        seconds = int(time_spent_seconds % 60)
        if minutes > 0:
            time_spent_formatted = f"{minutes}m {seconds}s"
        else:
            time_spent_formatted = f"{seconds}s"

    context = {
        "lesson": lesson,
        "quiz": quiz,
        "submission": submission,
        "results": results,
        "time_spent_seconds": time_spent_seconds,
        "time_spent_formatted": time_spent_formatted,
        "score_percent": (submission.raw_score / submission.max_score * 100) if submission.max_score else 0,
    }
    return render(request, "core/student/lesson_quiz_results.html", context)


@login_required
def glossary_term_detail(request, lesson_id, term_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    term = get_object_or_404(Term, pk=term_id, glossary__story=lesson.story)

    if hasattr(request.user, "is_student") and request.user.is_student():
        GlossClickLog.objects.create(
            student=request.user,
            lesson=lesson,
            story=lesson.story,
            term=term,
        )

    return render(request, "core/_glossary_term_detail.html", {"lesson": lesson, "term": term})


@login_required
def log_reading_event(request, lesson_id):
    """API endpoint for logging reading events from JavaScript."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    lesson = get_object_or_404(Lesson, pk=lesson_id)
    user = request.user

    # Parse JSON body
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event_type = data.get("event_type")
    valid_types = [t[0] for t in ReadingEvent.EVENT_TYPES]
    if event_type not in valid_types:
        return JsonResponse({"error": f"Invalid event_type. Must be one of: {valid_types}"}, status=400)

    # Create the reading event
    ReadingEvent.objects.create(
        student=user,
        lesson=lesson,
        story=lesson.story,
        event_type=event_type,
        event_payload=data.get("payload", {}),
    )

    # If this is a finish event, update LessonProgress.reading_end
    if event_type == "finish":
        progress = LessonProgress.objects.filter(student=user, lesson=lesson).first()
        if progress and not progress.reading_end:
            progress.reading_end = timezone.now()
            progress.save()

    return JsonResponse({"status": "ok"})


# =============================================================================
# INSTRUCTOR DASHBOARD
# =============================================================================

@login_required
@teacher_required
def teacher_dashboard(request):
    user = request.user

    story_count = Story.objects.filter(teacher=user).count()
    lesson_count = Lesson.objects.filter(teacher=user).count()
    quiz_count = Quiz.objects.filter(owner=user).count()
    roster_count = Roster.objects.filter(teacher=user).count()
    student_count = RosterMembership.objects.filter(roster__teacher=user).values("student").distinct().count()
    unit_count = Unit.objects.filter(teacher=user).count()
    course_count = Course.objects.filter(teacher=user).count()

    recent_stories = Story.objects.filter(teacher=user).order_by("-created_at")[:5]
    active_lessons = (
        Lesson.objects.filter(teacher=user)
        .select_related("story", "site")
        .prefetch_related("rosters")
        .order_by("-created_at")[:5]
    )
    recent_units = Unit.objects.filter(teacher=user).order_by("-created_at")[:5]
    recent_courses = Course.objects.filter(teacher=user).prefetch_related("rosters").order_by("-created_at")[:5]

    context = {
        "story_count": story_count,
        "lesson_count": lesson_count,
        "quiz_count": quiz_count,
        "roster_count": roster_count,
        "student_count": student_count,
        "unit_count": unit_count,
        "course_count": course_count,
        "recent_stories": recent_stories,
        "active_lessons": active_lessons,
        "recent_units": recent_units,
        "recent_courses": recent_courses,
    }
    return render(request, "core/teacher_dashboard.html", context)


# =============================================================================
# STORY VIEWS
# =============================================================================

@login_required
@teacher_required
def story_list(request):
    stories = (
        Story.objects.filter(teacher=request.user)
        .annotate(segment_count=Count("segments"))
        .order_by("-created_at")
    )
    return render(request, "core/teacher/story_list.html", {"stories": stories})


@login_required
@teacher_required
def story_create(request):
    if request.method == "POST":
        form = StoryForm(request.POST)
        if form.is_valid():
            story = form.save(commit=False)
            story.instructor = request.user
            story.save()
            # Compute reading levels if text was provided
            if story.text_html:
                story.update_reading_levels()
                story.save(update_fields=["reading_level_label", "reading_level_metrics"])
            messages.success(request, f"Story '{story.title}' created successfully.")
            return redirect("core:story_edit", pk=story.pk)
    else:
        form = StoryForm()

    return render(request, "core/teacher/story_form.html", {
        "form": form,
        "title": "Create Story",
    })


@login_required
@teacher_required
def story_edit(request, pk):
    story = get_object_or_404(Story, pk=pk, teacher=request.user)
    tab = request.GET.get("tab", "details")

    # Auto-compute reading levels if story has content but no metrics
    if story.text_html and not story.reading_level_metrics:
        if story.update_reading_levels():
            story.save(update_fields=["reading_level_label", "reading_level_metrics"])

    if request.method == "POST":
        if tab == "details":
            form = StoryForm(request.POST, instance=story)
            if form.is_valid():
                form.save()
                messages.success(request, "Story details updated.")
                return redirect(f"{request.path}?tab=details")
        elif tab == "content":
            story.text_html = request.POST.get("text_html", "")
            # Recompute reading levels when content changes
            story.update_reading_levels()
            story.save()
            messages.success(request, "Story content updated.")
            return redirect(f"{request.path}?tab=content")
        elif tab == "segments":
            formset = StorySegmentFormSet(request.POST, instance=story)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Segments updated.")
                return redirect(f"{request.path}?tab=segments")

    form = StoryForm(instance=story)
    formset = StorySegmentFormSet(instance=story)

    # Get or create glossary
    glossary, _ = Glossary.objects.get_or_create(
        story=story,
        defaults={"language_code": "en", "native_language_code": "vi"}
    )
    terms = Term.objects.filter(glossary=glossary).order_by("term_text")

    # Get quizzes for this story
    quizzes = story.quizzes.annotate(question_count=Count("quiz_questions")).order_by("-created_at")

    context = {
        "story": story,
        "form": form,
        "formset": formset,
        "glossary": glossary,
        "terms": terms,
        "quizzes": quizzes,
        "tab": tab,
        "title": f"Edit Story: {story.title}",
    }
    return render(request, "core/teacher/story_edit.html", context)


@login_required
@teacher_required
def story_delete(request, pk):
    story = get_object_or_404(Story, pk=pk, teacher=request.user)
    if request.method == "POST":
        title = story.title
        story.delete()
        messages.success(request, f"Story '{title}' deleted.")
        return redirect("core:story_list")
    return render(request, "core/teacher/story_confirm_delete.html", {"story": story})


@login_required
@teacher_required
def story_preview(request, pk):
    """
    Preview a story as it would appear to a student.
    Supports switching between reading modes (continuous, cards, movie).
    """
    story = get_object_or_404(Story, pk=pk, teacher=request.user)

    # Get reading mode from query params
    mode = request.GET.get("mode", "continuous")
    if mode not in ["continuous", "cards", "movie"]:
        mode = "continuous"

    # Get segments for card/movie mode
    segments = story.segments.order_by("index")

    # Get glossary terms if available
    glossary = getattr(story, "glossary", None)
    terms = []
    if glossary:
        terms = list(glossary.terms.filter(is_selected_for_glossary=True).order_by("term_text"))

    context = {
        "story": story,
        "segments": segments,
        "mode": mode,
        "allowed_modes": ["continuous", "cards", "movie"],
        "glossary": glossary,
        "terms": terms,
        "title": f"Preview: {story.title}",
        "is_preview": True,
    }

    return render(request, "core/teacher/story_preview.html", context)


@login_required
@teacher_required
def story_auto_segment(request, pk):
    """
    Auto-segment a story by splitting its HTML content into paragraphs.
    """
    import re
    from django.http import JsonResponse

    story = get_object_or_404(Story, pk=pk, teacher=request.user)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    # Get segmentation options
    mode = request.POST.get("mode", "paragraph")  # paragraph, heading, or custom
    clear_existing = request.POST.get("clear_existing", "true") == "true"

    if not story.text_html or not story.text_html.strip():
        return JsonResponse({"success": False, "error": "Story has no content to segment"}, status=400)

    # Parse HTML and extract segments
    html_content = story.text_html

    if mode == "paragraph":
        # Split by <p> tags
        pattern = r'<p[^>]*>(.*?)</p>'
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        segments_content = [f"<p>{m.strip()}</p>" for m in matches if m.strip()]
    elif mode == "heading":
        # Split by headings (h1-h6), keeping heading with following content
        pattern = r'(<h[1-6][^>]*>.*?</h[1-6]>)'
        parts = re.split(pattern, html_content, flags=re.DOTALL | re.IGNORECASE)
        segments_content = []
        current_segment = ""
        for part in parts:
            if re.match(r'<h[1-6]', part, re.IGNORECASE):
                if current_segment.strip():
                    segments_content.append(current_segment.strip())
                current_segment = part
            else:
                current_segment += part
        if current_segment.strip():
            segments_content.append(current_segment.strip())
    elif mode == "linebreak":
        # Split by <br> tags (single or multiple)
        segments_content = [s.strip() for s in re.split(r'<br\s*/?>', html_content, flags=re.IGNORECASE) if s.strip()]
    else:
        # Default: split by double newlines or paragraph breaks
        segments_content = [s.strip() for s in re.split(r'\n\n+|<br\s*/?>\s*<br\s*/?>', html_content) if s.strip()]

    if not segments_content:
        return JsonResponse({"success": False, "error": "Could not find segments in content"}, status=400)

    # Clear existing segments if requested
    if clear_existing:
        story.segments.all().delete()

    # Create new segments
    start_index = 0 if clear_existing else story.segments.count()
    created_count = 0

    for i, content in enumerate(segments_content):
        StorySegment.objects.create(
            story=story,
            index=start_index + i,
            text_html=content,
            title=""
        )
        created_count += 1

    return JsonResponse({
        "success": True,
        "segments_created": created_count,
        "message": f"Created {created_count} segments"
    })


@login_required
@teacher_required
def story_generate(request):
    """
    AI-powered story generation with Lexile-aligned constraints.

    Shows form for generation parameters, creates prompt, and displays
    the composed prompt for review (actual AI generation requires API integration).
    """
    from .story_engine import compose_story_prompt, validate_story, extract_metrics

    composed_prompt = None
    validation_result = None
    generation_params = None

    if request.method == "POST":
        form = StoryGeneratorForm(request.POST)
        if form.is_valid():
            generation_params = form.get_generation_params()

            try:
                # Compose the prompt using the story engine
                composed_prompt = compose_story_prompt(**generation_params)

                # Store params in session for later use
                request.session["story_generation_params"] = generation_params
                request.session["story_generation_prompt_hash"] = composed_prompt.profile_hash

                messages.success(
                    request,
                    "Story prompt generated successfully. Review the constraints below."
                )

            except ValueError as e:
                messages.error(request, f"Generation error: {e}")

    else:
        form = StoryGeneratorForm()

    context = {
        "form": form,
        "composed_prompt": composed_prompt,
        "generation_params": generation_params,
        "title": "Generate AI Story",
    }
    return render(request, "core/teacher/story_generate.html", context)


@login_required
@teacher_required
def story_generate_ai(request):
    """
    Call OpenRouter API to generate a story using the composed prompt.
    """
    import json
    from django.http import JsonResponse
    from django.conf import settings

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    # Get generation params and prompt from session
    generation_params = request.session.get("story_generation_params")
    if not generation_params:
        return JsonResponse({"success": False, "error": "No generation parameters found. Please generate a prompt first."}, status=400)

    # Check API key
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return JsonResponse({"success": False, "error": "OPENROUTER_API_KEY not configured"}, status=500)

    # Re-compose the prompt to get fresh system and user messages
    from .story_engine import compose_story_prompt
    try:
        composed_prompt = compose_story_prompt(**generation_params)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    # Call OpenRouter API
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        word_count = generation_params.get("word_count", 400)
        model = request.POST.get("model", "openai/gpt-4o-mini")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": composed_prompt.system_message},
                {"role": "user", "content": composed_prompt.user_prompt}
            ],
            temperature=0.7,
            max_tokens=word_count * 4,
        )

        generated_text = response.choices[0].message.content.strip()

        # Analyze the generated text
        from .story_engine import extract_metrics
        metrics = extract_metrics(generated_text)

        return JsonResponse({
            "success": True,
            "story_text": generated_text,
            "metrics": metrics.to_dict() if hasattr(metrics, 'to_dict') else {},
            "model": model,
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@teacher_required
def story_generate_preview(request):
    """
    Preview a generated story before saving.

    This view receives generated story text (from AI or manual input),
    validates it, and shows metrics and transparency information.
    """
    from .story_engine import validate_story, extract_metrics

    if request.method != "POST":
        return redirect("core:story_generate")

    story_text = request.POST.get("story_text", "").strip()
    lexile_band = request.POST.get("lexile_band", "500-600L")
    target_word_count = int(request.POST.get("word_count", 400))

    if not story_text:
        messages.error(request, "No story text provided.")
        return redirect("core:story_generate")

    # Validate the story
    validation = validate_story(story_text, lexile_band, target_word_count)
    metrics = extract_metrics(story_text)

    # Get generation params from session
    generation_params = request.session.get("story_generation_params", {})

    context = {
        "story_text": story_text,
        "validation": validation,
        "metrics": metrics,
        "generation_params": generation_params,
        "lexile_band": lexile_band,
        "title": "Preview Generated Story",
    }
    return render(request, "core/teacher/story_generate_preview.html", context)


@login_required
@teacher_required
def story_generate_save(request):
    """
    Save a generated story after preview.
    """
    if request.method != "POST":
        return redirect("core:story_generate")

    story_text = request.POST.get("story_text", "").strip()
    title = request.POST.get("title", "").strip()

    if not story_text or not title:
        messages.error(request, "Title and story text are required.")
        return redirect("core:story_generate")

    # Get generation params from session
    generation_params = request.session.get("story_generation_params", {})
    prompt_hash = request.session.get("story_generation_prompt_hash", "")

    # Create the story
    story = Story.objects.create(
        teacher=request.user,
        title=title,
        text_html=f"<p>{story_text.replace(chr(10)+chr(10), '</p><p>').replace(chr(10), '<br>')}</p>",
        source_type=Story.SOURCE_AI,
        source_metadata={
            "generation_params": generation_params,
            "prompt_hash": prompt_hash,
            "generator_version": "1.0.0",
        },
        reading_level_label=generation_params.get("lexile_band", ""),
    )

    # Compute and store metrics
    from .story_engine import extract_metrics
    metrics = extract_metrics(story_text)
    story.reading_level_metrics = metrics.to_dict()
    story.save()

    # Clear session data
    request.session.pop("story_generation_params", None)
    request.session.pop("story_generation_prompt_hash", None)

    messages.success(request, f"Story '{title}' created successfully!")
    return redirect("core:story_edit", pk=story.pk)


@login_required
@teacher_required
def story_export(request, pk):
    """
    Export a story in print-friendly format.

    Supports:
    - Web view (print-friendly HTML)
    - PDF (via browser print)
    """
    story = get_object_or_404(Story, pk=pk, teacher=request.user)

    # Get metrics if available
    metrics = story.reading_level_metrics or {}

    # Get glossary terms
    glossary = getattr(story, 'glossary', None)
    terms = []
    if glossary:
        terms = list(glossary.terms.filter(is_selected_for_glossary=True).order_by('term_text'))

    # Get segments
    segments = story.segments.order_by('index')

    context = {
        "story": story,
        "metrics": metrics,
        "terms": terms,
        "segments": segments,
        "title": f"Export: {story.title}",
    }
    return render(request, "core/teacher/story_export.html", context)


# =============================================================================
# STORY IMPORT VIEWS
# =============================================================================

@login_required
@teacher_required
def story_import_search(request):
    """Main import interface with search form and bookmarks."""
    form = ExternalBookSearchForm(request.GET or None)
    bookmarks = ExternalBookmark.objects.filter(teacher=request.user)[:10]

    return render(request, "core/teacher/story_import.html", {
        "form": form,
        "bookmarks": bookmarks,
        "title": "Import Story from Library",
    })


@login_required
@teacher_required
def story_import_search_results(request):
    """HTMX endpoint: Return search results from external sources."""
    from .services.external_books import GutendexService, OpenLibraryService, OpenTextbookService

    form = ExternalBookSearchForm(request.GET)
    if not form.is_valid():
        return render(request, "core/teacher/partials/import_search_results.html", {
            "error": "Please enter a search term.",
            "results": [],
        })

    query = form.cleaned_data["query"]
    source = form.cleaned_data.get("source", "all")
    language = form.cleaned_data.get("language", "en")
    page = int(request.GET.get("page", 1))

    results = []
    total = 0

    # Search Gutenberg
    if source in ("all", "gutenberg"):
        try:
            gutenberg = GutendexService()
            gb_results, gb_total = gutenberg.search(query, page, language)
            results.extend(gb_results)
            total += gb_total
        except Exception as e:
            pass  # Log but don't fail

    # Search Open Library
    if source in ("all", "openlibrary"):
        try:
            openlibrary = OpenLibraryService()
            ol_results, ol_total = openlibrary.search(query, page, language)
            results.extend(ol_results)
            total += ol_total
        except Exception as e:
            pass  # Log but don't fail

    # Search Open Textbook Library
    if source in ("all", "opentextbook"):
        try:
            opentextbook = OpenTextbookService()
            ot_results, ot_total = opentextbook.search(query, page, language)
            results.extend(ot_results)
            total += ot_total
        except Exception as e:
            pass  # Log but don't fail

    # Check which are already bookmarked
    bookmarked = set(
        ExternalBookmark.objects.filter(teacher=request.user)
        .values_list("source", "external_id")
    )

    return render(request, "core/teacher/partials/import_search_results.html", {
        "results": results,
        "bookmarked": bookmarked,
        "query": query,
        "page": page,
        "total": total,
    })


@login_required
@teacher_required
def story_import_details(request, source, external_id):
    """HTMX endpoint: Get book details and import options."""
    from .services.external_books import get_service
    import json

    try:
        service = get_service(source)
        book = service.get_book_details(external_id)
    except Exception as e:
        return render(request, "core/teacher/partials/import_book_details.html", {
            "error": f"Failed to load book details: {str(e)}"
        })

    if not book:
        return render(request, "core/teacher/partials/import_book_details.html", {
            "error": "Book not found."
        })

    # Don't fetch full text here - it's too slow
    # We'll show the import form and fetch text only when user clicks Preview
    # For Gutenberg, we know text is available if has_full_text is True
    text_available = book.has_full_text

    import_form = ExternalBookImportForm()

    return render(request, "core/teacher/partials/import_book_details.html", {
        "book": book,
        "chapters": [],  # Will be detected during preview
        "text_available": text_available,
        "word_count": 0,  # Will be shown during preview
        "import_form": import_form,
        "book_json": json.dumps(book.to_dict()),
    })


@login_required
@teacher_required
def story_import_preview(request):
    """Preview the imported text before saving."""
    from .services.external_books import get_service, TextProcessor

    if request.method != "POST":
        return redirect("core:story_import_search")

    source = request.POST.get("source")
    external_id = request.POST.get("external_id")
    import_mode = request.POST.get("import_mode", "excerpt")
    chapter_number = request.POST.get("chapter_number")
    excerpt_words = int(request.POST.get("excerpt_words", 2000))
    custom_title = request.POST.get("custom_title", "").strip()

    try:
        service = get_service(source)
        book = service.get_book_details(external_id)
        if not book:
            messages.error(request, f"Could not find book details for {source}/{external_id}.")
            return redirect("core:story_import_search")

        text_result = service.get_full_text(external_id)
        if not text_result:
            messages.error(request, f"Could not retrieve text for '{book.title}'. The source may be temporarily unavailable.")
            return redirect("core:story_import_search")
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Error fetching {source}/{external_id}")
        messages.error(request, f"Failed to retrieve book: {str(e)}")
        return redirect("core:story_import_search")

    # Process text
    text = TextProcessor.clean_gutenberg_headers(text_result.text)

    if import_mode == "chapter" and chapter_number:
        chapter_text = TextProcessor.extract_chapter(text, int(chapter_number))
        if chapter_text:
            text = chapter_text
        else:
            messages.warning(request, f"Chapter {chapter_number} not found. Using excerpt instead.")
            text, _ = TextProcessor.truncate_with_summary(text, excerpt_words)
    elif import_mode == "excerpt":
        text, was_truncated = TextProcessor.truncate_with_summary(text, excerpt_words)
    # else: full text

    html_text = TextProcessor.convert_to_html(text)
    stats = TextProcessor.get_text_stats(text)

    # Store in session for save
    request.session["import_preview"] = {
        "source": source,
        "external_id": external_id,
        "title": custom_title or book.title,
        "author": book.author,
        "text_html": html_text,
        "word_count": stats["word_count"],
        "metadata": book.raw_metadata,
    }

    return render(request, "core/teacher/story_import_preview.html", {
        "preview": request.session["import_preview"],
        "book": book,
        "stats": stats,
        "title": "Preview Import",
    })


@login_required
@teacher_required
def story_import_save(request):
    """Save the imported text as a new Story."""
    if request.method != "POST":
        return redirect("core:story_import_search")

    preview = request.session.get("import_preview")
    if not preview:
        messages.error(request, "Import session expired. Please try again.")
        return redirect("core:story_import_search")

    # Create Story
    story = Story.objects.create(
        teacher=request.user,
        title=preview["title"],
        text_html=preview["text_html"],
        source_type=Story.SOURCE_EXTERNAL,
        source_metadata={
            "source": preview["source"],
            "external_id": preview["external_id"],
            "author": preview["author"],
            "imported_at": timezone.now().isoformat(),
            "original_metadata": preview["metadata"],
        },
    )

    # Compute reading levels
    if story.update_reading_levels():
        story.save(update_fields=["reading_level_label", "reading_level_metrics"])

    # Clear session
    del request.session["import_preview"]

    messages.success(request, f"Story '{story.title}' imported successfully!")
    return redirect("core:story_edit", pk=story.pk)


@login_required
@teacher_required
def story_import_bookmark_add(request):
    """Add a bookmark via HTMX (JSON response)."""
    import json

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    bookmark, created = ExternalBookmark.objects.get_or_create(
        teacher=request.user,
        source=data.get("source"),
        external_id=data.get("external_id"),
        defaults={
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "cover_url": data.get("cover_url", ""),
            "metadata": data.get("metadata", {}),
        }
    )

    return JsonResponse({
        "success": True,
        "created": created,
        "bookmark_id": bookmark.pk,
    })


@login_required
@teacher_required
def story_import_bookmark_remove(request, pk):
    """Remove a bookmark via HTMX."""
    bookmark = get_object_or_404(ExternalBookmark, pk=pk, teacher=request.user)
    bookmark.delete()

    # Return updated bookmarks list
    bookmarks = ExternalBookmark.objects.filter(teacher=request.user)[:10]
    return render(request, "core/teacher/partials/import_bookmarks_list.html", {
        "bookmarks": bookmarks,
    })


# =============================================================================
# LESSON VIEWS
# =============================================================================

@login_required
@teacher_required
def teacher_lesson_list(request):
    lessons = (
        Lesson.objects.filter(teacher=request.user)
        .select_related("story", "site", "quiz")
        .prefetch_related("rosters")
        .order_by("-created_at")
    )
    return render(request, "core/teacher/lesson_list.html", {"lessons": lessons})


@login_required
@teacher_required
def lesson_create(request):
    # Check if creating lesson for a specific unit
    unit_id = request.GET.get("unit") or request.POST.get("unit")
    unit = None
    if unit_id:
        unit = Unit.objects.filter(pk=unit_id, teacher=request.user).first()

    if request.method == "POST":
        form = LessonForm(request.POST, user=request.user)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.instructor = request.user
            lesson.save()
            form.save_m2m()

            # If unit specified, add lesson to that unit
            if unit:
                max_order = unit.unit_lessons.aggregate(max_order=Max("order"))["max_order"] or 0
                UnitLesson.objects.create(unit=unit, lesson=lesson, order=max_order + 1)
                messages.success(request, f"Lesson '{lesson.title}' created and added to unit '{unit.title}'.")
            else:
                messages.success(request, f"Lesson '{lesson.title}' created successfully.")

            return redirect("core:lesson_edit", pk=lesson.pk)
    else:
        form = LessonForm(user=request.user)

    return render(request, "core/teacher/lesson_form.html", {
        "form": form,
        "title": "Create Lesson",
        "unit": unit,
    })


@login_required
@teacher_required
def lesson_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, teacher=request.user)

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson updated successfully.")
            return redirect("core:lesson_edit", pk=pk)
    else:
        form = LessonForm(instance=lesson, user=request.user)

    # Get quizzes for the lesson's story (ordered by most recent)
    story_quizzes = []
    if lesson.story:
        story_quizzes = Quiz.objects.filter(
            owner=request.user,
            story=lesson.story
        ).order_by("-created_at")

    return render(request, "core/teacher/lesson_form.html", {
        "form": form,
        "lesson": lesson,
        "title": f"Edit Lesson: {lesson.title}",
        "story_quizzes": story_quizzes,
    })


@login_required
@teacher_required
def lesson_delete(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, teacher=request.user)
    if request.method == "POST":
        title = lesson.title
        lesson.delete()
        messages.success(request, f"Lesson '{title}' deleted.")
        return redirect("core:teacher_lesson_list")
    return render(request, "core/teacher/lesson_confirm_delete.html", {"lesson": lesson})


@login_required
@teacher_required
def lesson_quizzes_for_story(request, story_pk):
    """HTMX endpoint: return quiz options for a given story."""
    quizzes = Quiz.objects.filter(
        owner=request.user,
        story_id=story_pk
    ).order_by("-created_at")
    return render(request, "core/teacher/partials/quiz_options.html", {
        "quizzes": quizzes,
    })


# =============================================================================
# QUIZ VIEWS
# =============================================================================

@login_required
@teacher_required
def quiz_list(request):
    quizzes = (
        Quiz.objects.filter(owner=request.user)
        .select_related("story")
        .annotate(question_count=Count("quiz_questions"))
        .order_by("-created_at")
    )
    return render(request, "core/teacher/quiz_list.html", {"quizzes": quizzes})


@login_required
@teacher_required
def quiz_create(request):
    # Check if a story_id was passed (e.g., from story page)
    story_id = request.GET.get("story")
    initial = {}
    if story_id:
        story = Story.objects.filter(pk=story_id, teacher=request.user).first()
        if story:
            initial["story"] = story

    if request.method == "POST":
        form = QuizForm(request.POST, user=request.user)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.owner = request.user
            quiz.save()
            messages.success(request, f"Quiz '{quiz.title}' created successfully.")
            return redirect("core:quiz_edit", pk=quiz.pk)
    else:
        form = QuizForm(user=request.user, initial=initial)

    return render(request, "core/teacher/quiz_form.html", {
        "form": form,
        "title": "Create Quiz",
    })


@login_required
@teacher_required
def quiz_edit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    questions = quiz.quiz_questions.select_related("question").order_by("order")

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz updated successfully.")
            return redirect("core:quiz_edit", pk=pk)
    else:
        form = QuizForm(instance=quiz, user=request.user)

    return render(request, "core/teacher/quiz_edit.html", {
        "form": form,
        "quiz": quiz,
        "questions": questions,
        "title": f"Edit Quiz: {quiz.title}",
    })


@login_required
@teacher_required
def quiz_delete(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    if request.method == "POST":
        title = quiz.title
        quiz.delete()
        messages.success(request, f"Quiz '{title}' deleted.")
        return redirect("core:quiz_list")
    return render(request, "core/teacher/quiz_confirm_delete.html", {"quiz": quiz})


@login_required
@teacher_required
def quiz_question_add(request, pk):
    """Add an existing question from item bank to quiz."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    if request.method == "POST":
        question_id = request.POST.get("question_id")
        if question_id:
            question = get_object_or_404(ItemBankQuestion, pk=question_id, owner=request.user)
            # Get next order number
            max_order = quiz.quiz_questions.aggregate(models.Max("order"))["order__max"] or 0
            QuizQuestion.objects.create(
                quiz=quiz,
                question=question,
                order=max_order + 1,
                points=question.default_points,
            )
            messages.success(request, f"Question added to quiz.")
        return redirect("core:quiz_edit", pk=pk)

    # GET: Show list of available questions
    existing_question_ids = quiz.quiz_questions.values_list("question_id", flat=True)
    available_questions = ItemBankQuestion.objects.filter(
        owner=request.user,
        status="active"
    ).exclude(pk__in=existing_question_ids).order_by("-created_at")

    return render(request, "core/teacher/quiz_question_add.html", {
        "quiz": quiz,
        "available_questions": available_questions,
        "title": f"Add Question to {quiz.title}",
    })


@login_required
@teacher_required
def quiz_question_create(request, pk):
    """Create a new question and add it to the quiz."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    if request.method == "POST":
        form = ItemBankQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.owner = request.user
            question.save()

            # Handle choices based on question type
            if question.question_type in ["mcq_single", "mcq_multiple"]:
                # Create choices from form data
                labels = ["A", "B", "C", "D"]
                for i, label in enumerate(labels):
                    choice_text = request.POST.get(f"choice_text_{i}", "").strip()
                    is_correct = request.POST.get(f"choice_correct_{i}") == "on"
                    freeze_position = request.POST.get(f"choice_freeze_{i}") == "on"
                    if choice_text:
                        ItemBankChoice.objects.create(
                            question=question,
                            label=label,
                            text_html=choice_text,
                            is_correct=is_correct,
                            order=i,
                            freeze_position=freeze_position,
                        )
            elif question.question_type == "true_false":
                # Create True/False choices
                tf_answer = request.POST.get("true_false_answer", "true")
                ItemBankChoice.objects.create(
                    question=question,
                    label="",
                    text_html="True",
                    is_correct=(tf_answer == "true"),
                    order=0,
                )
                ItemBankChoice.objects.create(
                    question=question,
                    label="",
                    text_html="False",
                    is_correct=(tf_answer == "false"),
                    order=1,
                )
            elif question.question_type == "short_answer":
                # Store expected answer in metadata
                expected_answer = request.POST.get("expected_answer", "").strip()
                if expected_answer:
                    question.metadata["expected_answer"] = expected_answer
                    question.save()

            # Add to quiz
            max_order = quiz.quiz_questions.aggregate(models.Max("order"))["order__max"] or 0
            QuizQuestion.objects.create(
                quiz=quiz,
                question=question,
                order=max_order + 1,
                points=question.default_points,
            )

            messages.success(request, "Question created and added to quiz.")
            return redirect("core:quiz_edit", pk=pk)
    else:
        form = ItemBankQuestionForm()

    return render(request, "core/teacher/quiz_question_create.html", {
        "quiz": quiz,
        "form": form,
        "title": f"Create Question for {quiz.title}",
    })


@login_required
@teacher_required
def quiz_question_remove(request, pk, qq_pk):
    """Remove a question from quiz."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    quiz_question = get_object_or_404(QuizQuestion, pk=qq_pk, quiz=quiz)

    if request.method == "POST":
        quiz_question.delete()
        messages.success(request, "Question removed from quiz.")

    return redirect("core:quiz_edit", pk=pk)


@login_required
@teacher_required
@require_POST
def quiz_question_reorder(request, pk):
    """Reorder questions in a quiz via AJAX."""
    import json
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    try:
        data = json.loads(request.body)
        question_order = data.get("order", [])

        for item in question_order:
            qq_id = item.get("id")
            new_order = item.get("order")
            freeze = item.get("freeze", False)

            QuizQuestion.objects.filter(pk=qq_id, quiz=quiz).update(
                order=new_order,
                freeze_position=freeze
            )

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@teacher_required
@require_POST
def quiz_question_toggle_freeze(request, pk, qq_pk):
    """Toggle freeze_position for a quiz question."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    quiz_question = get_object_or_404(QuizQuestion, pk=qq_pk, quiz=quiz)

    quiz_question.freeze_position = not quiz_question.freeze_position
    quiz_question.save()

    return JsonResponse({
        "success": True,
        "freeze_position": quiz_question.freeze_position
    })


@login_required
@teacher_required
def question_edit(request, pk):
    """Edit an item bank question and its answer choices."""
    question = get_object_or_404(ItemBankQuestion, pk=pk, owner=request.user)

    if request.method == "POST":
        form = ItemBankQuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()

            # Handle choices based on question type
            if question.question_type in ["mcq_single", "mcq_multi"]:
                # Update existing choices or create new ones
                labels = ["A", "B", "C", "D"]
                existing_choices = {c.label: c for c in question.choices.all()}

                for i, label in enumerate(labels):
                    choice_text = request.POST.get(f"choice_text_{i}", "").strip()
                    is_correct = request.POST.get(f"choice_correct_{i}") == "on"
                    freeze_position = request.POST.get(f"choice_freeze_{i}") == "on"

                    if label in existing_choices:
                        choice = existing_choices[label]
                        if choice_text:
                            choice.text_html = choice_text
                            choice.is_correct = is_correct
                            choice.order = i
                            choice.freeze_position = freeze_position
                            choice.save()
                        else:
                            choice.delete()
                    elif choice_text:
                        ItemBankChoice.objects.create(
                            question=question,
                            label=label,
                            text_html=choice_text,
                            is_correct=is_correct,
                            order=i,
                            freeze_position=freeze_position,
                        )

            elif question.question_type == "true_false":
                tf_answer = request.POST.get("true_false_answer", "true")
                question.choices.all().delete()
                ItemBankChoice.objects.create(
                    question=question,
                    label="",
                    text_html="True",
                    is_correct=(tf_answer == "true"),
                    order=0,
                )
                ItemBankChoice.objects.create(
                    question=question,
                    label="",
                    text_html="False",
                    is_correct=(tf_answer == "false"),
                    order=1,
                )

            elif question.question_type == "short_answer":
                expected_answer = request.POST.get("expected_answer", "").strip()
                if expected_answer:
                    question.metadata["expected_answer"] = expected_answer
                    question.save()

            messages.success(request, "Question updated successfully.")

            # Redirect back to the referring quiz if available
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("core:quiz_list")
    else:
        form = ItemBankQuestionForm(instance=question)

    # Get existing choices for pre-populating the form
    choices = {c.label: c for c in question.choices.all()}

    # Get True/False answer if applicable
    tf_answer = "true"
    if question.question_type == "true_false":
        true_choice = question.choices.filter(text_html="True").first()
        if true_choice and not true_choice.is_correct:
            tf_answer = "false"

    return render(request, "core/teacher/question_edit.html", {
        "question": question,
        "form": form,
        "choices": choices,
        "tf_answer": tf_answer,
        "expected_answer": question.metadata.get("expected_answer", ""),
        "title": "Edit Question",
        "next": request.GET.get("next", ""),
    })


@login_required
@teacher_required
def quiz_generate(request):
    """
    AI-powered quiz generation based on story content.
    Shows form for selecting story and quiz parameters.
    """
    import json

    # Check if a story_id was passed (e.g., from story page)
    initial = {}
    story_id = request.GET.get("story")
    if story_id:
        story = Story.objects.filter(pk=story_id, teacher=request.user).first()
        if story:
            initial["story"] = story

    form = QuizGeneratorForm(request.POST or None, user=request.user, initial=initial)
    generated_questions = None
    generation_params = None
    generation_params_json = None

    if request.method == "POST" and form.is_valid():
        # Store generation params in session for AI call
        story = form.cleaned_data["story"]
        generation_params = {
            "story_id": story.pk,
            "story_title": story.title,
            "story_content": story.text_html,
            "num_questions": form.cleaned_data["num_questions"],
            "question_types": form.cleaned_data["question_types"],
            "difficulty": form.cleaned_data["difficulty"],
            "focus": form.cleaned_data["focus"],
            "quiz_title": form.cleaned_data.get("quiz_title") or f"Quiz: {story.title}",
            "include_instructions": form.cleaned_data.get("include_instructions", True),
        }
        request.session["quiz_generation_params"] = generation_params

        # Create JSON-safe version for JavaScript (exclude story_content as it's not needed in frontend)
        generation_params_json = json.dumps({
            "story_id": generation_params["story_id"],
            "story_title": generation_params["story_title"],
            "num_questions": generation_params["num_questions"],
            "question_types": generation_params["question_types"],
            "difficulty": generation_params["difficulty"],
            "focus": generation_params["focus"],
            "quiz_title": generation_params["quiz_title"],
            "include_instructions": generation_params["include_instructions"],
        })

    return render(request, "core/teacher/quiz_generate.html", {
        "form": form,
        "generation_params": generation_params,
        "generation_params_json": generation_params_json,
        "title": "Generate Quiz with AI",
    })


@login_required
@teacher_required
def quiz_generate_ai(request):
    """
    Call OpenRouter API to generate quiz questions using the stored parameters.
    """
    import json
    import re
    from django.http import JsonResponse
    from django.conf import settings

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    # Get generation params from session
    generation_params = request.session.get("quiz_generation_params")
    if not generation_params:
        return JsonResponse({"success": False, "error": "No generation parameters found. Please configure quiz options first."}, status=400)

    # Check API key
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return JsonResponse({"success": False, "error": "OPENROUTER_API_KEY not configured"}, status=500)

    # Build the prompt for quiz generation
    story_content = generation_params["story_content"]
    # Strip HTML tags for cleaner text
    clean_text = re.sub(r'<[^>]+>', ' ', story_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    num_questions = generation_params["num_questions"]
    question_types = generation_params["question_types"]
    difficulty = generation_params["difficulty"]
    focus = generation_params["focus"]

    # Build question type instructions
    type_instructions = []
    if "mcq_single" in question_types:
        type_instructions.append("Multiple choice questions with 4 options (A, B, C, D) and one correct answer")
    if "true_false" in question_types:
        type_instructions.append("True/False questions")
    if "short_answer" in question_types:
        type_instructions.append("Short answer questions (1-2 sentence response expected)")

    difficulty_desc = {
        "easy": "basic recall and literal comprehension",
        "medium": "understanding, application, and making connections",
        "hard": "analysis, inference, and critical thinking"
    }.get(difficulty, "medium difficulty")

    focus_desc = {
        "comprehension": "reading comprehension and understanding the main ideas",
        "vocabulary": "vocabulary understanding and word meanings in context",
        "inference": "making inferences and drawing conclusions",
        "mixed": "a mix of comprehension, vocabulary, and inference questions"
    }.get(focus, "mixed question types")

    # Build specific type requirements
    allowed_types = question_types  # List like ["mcq_single"]
    type_names = {
        "mcq_single": "multiple choice (mcq_single)",
        "true_false": "true/false (true_false)",
        "short_answer": "short answer (short_answer)"
    }
    allowed_type_names = [type_names.get(t, t) for t in allowed_types]

    system_prompt = f"""You are an expert educational assessment designer. Generate quiz questions based on the provided reading passage.

Your task:
- Generate exactly {num_questions} questions
- ONLY use these question types: {', '.join(allowed_type_names)}
- DO NOT generate any other question types
- Difficulty level: {difficulty_desc}
- Focus area: {focus_desc}

Question type specifications:
{chr(10).join(f'- {instr}' for instr in type_instructions)}

Output format - Return a JSON array of question objects:
[
  {{
    "type": "mcq_single" or "true_false" or "short_answer",
    "question": "The question text",
    "choices": ["A) option1", "B) option2", "C) option3", "D) option4"],  // only for mcq_single
    "correct_answer": "A" or "True/False" or "expected answer text",
    "explanation": "Brief explanation of why this is correct"
  }}
]

For mcq_single questions: include exactly 4 choices labeled A), B), C), D).
For true_false questions: choices must be ["True", "False"].
For short_answer questions: omit the choices field entirely.

CRITICAL RULES:
- Generate exactly {num_questions} questions, no more, no less
- ONLY use question types from this list: {allowed_types}
- Questions must be directly answerable from the text
- Avoid ambiguous questions
- Ensure correct answers are unambiguously correct"""

    user_prompt = f"""Based on this reading passage, generate {num_questions} quiz questions:

PASSAGE:
{clean_text[:8000]}

Generate the questions as a JSON array."""

    # Call OpenRouter API
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        model = request.POST.get("model", "openai/gpt-4o-mini")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        generated_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        # Try to extract JSON array from the response
        json_match = re.search(r'\[[\s\S]*\]', generated_text)
        if json_match:
            questions_json = json_match.group()
            questions = json.loads(questions_json)
        else:
            return JsonResponse({"success": False, "error": "Could not parse questions from AI response"}, status=500)

        # Validate and filter questions to only allowed types
        valid_questions = []
        for q in questions:
            q_type = q.get("type", "")
            if q_type in allowed_types:
                valid_questions.append(q)
            else:
                # Log the rejected question type for debugging
                pass

        # If we filtered out questions, warn the user
        filtered_count = len(questions) - len(valid_questions)
        warning = None
        if filtered_count > 0:
            warning = f"Filtered out {filtered_count} question(s) with incorrect type. Requested: {allowed_types}"

        if not valid_questions:
            return JsonResponse({
                "success": False,
                "error": f"AI generated questions with wrong types. Requested types: {allowed_types}. Please try again."
            }, status=500)

        return JsonResponse({
            "success": True,
            "questions": valid_questions,
            "model": model,
            "story_title": generation_params["story_title"],
            "quiz_title": generation_params["quiz_title"],
            "warning": warning,
            "requested_count": num_questions,
            "generated_count": len(valid_questions),
        })

    except json.JSONDecodeError as e:
        return JsonResponse({"success": False, "error": f"Invalid JSON in AI response: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@teacher_required
def quiz_generate_save(request):
    """
    Save generated quiz questions to the database.
    """
    import json
    from django.http import JsonResponse

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        questions = data.get("questions", [])
        quiz_title = data.get("quiz_title", "Generated Quiz")
        quiz_instructions = data.get("quiz_instructions", "")
        story_id = data.get("story_id")

        if not questions:
            return JsonResponse({"success": False, "error": "No questions to save"}, status=400)

        # Get the story if provided
        story = None
        if story_id:
            story = Story.objects.filter(pk=story_id, teacher=request.user).first()

        # Create the quiz
        quiz = Quiz.objects.create(
            owner=request.user,
            story=story,
            title=quiz_title,
            instructions_html=quiz_instructions,
            total_points=len(questions),  # 1 point per question by default
        )

        # Create questions and link to quiz
        for i, q_data in enumerate(questions):
            q_type = q_data.get("type", "mcq_single")
            if q_type == "true_false":
                q_type = "true_false"

            # Create ItemBankQuestion
            item_question = ItemBankQuestion.objects.create(
                owner=request.user,
                prompt_html=q_data.get("question", ""),
                question_type=q_type,
                default_points=1.0,
                status="active",
                metadata={
                    "correct_answer": q_data.get("correct_answer", ""),
                    "explanation": q_data.get("explanation", ""),
                    "ai_generated": True,
                    "story_id": story_id,
                }
            )

            # Create choices for MCQ and True/False
            choices = q_data.get("choices", [])
            correct_answer = q_data.get("correct_answer", "")

            if q_type in ["mcq_single", "true_false"] and choices:
                for j, choice_text in enumerate(choices):
                    # Determine if this choice is correct
                    label = chr(65 + j) if q_type == "mcq_single" else ""  # A, B, C, D
                    is_correct = False

                    if q_type == "mcq_single":
                        # Check if correct_answer matches the label (A, B, C, D)
                        is_correct = correct_answer.upper().startswith(label)
                    elif q_type == "true_false":
                        is_correct = choice_text.lower() == correct_answer.lower()

                    ItemBankChoice.objects.create(
                        question=item_question,
                        label=label,
                        text_html=choice_text.lstrip("ABCD) "),
                        is_correct=is_correct,
                        order=j,
                    )

            # Link question to quiz
            QuizQuestion.objects.create(
                quiz=quiz,
                question=item_question,
                order=i,
                points=1.0,
            )

        return JsonResponse({
            "success": True,
            "quiz_id": quiz.pk,
            "quiz_title": quiz.title,
            "questions_created": len(questions),
            "redirect_url": f"/teacher/quizzes/{quiz.pk}/",
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =============================================================================
# ROSTER VIEWS
# =============================================================================

@login_required
@teacher_required
def roster_list(request):
    rosters = Roster.objects.filter(teacher=request.user).annotate(
        student_count=Count("memberships")
    ).order_by("-created_at")

    return render(request, "core/teacher/roster_list.html", {"rosters": rosters})


@login_required
@teacher_required
def roster_create(request):
    if request.method == "POST":
        form = RosterForm(request.POST, user=request.user)
        if form.is_valid():
            roster = form.save()
            messages.success(request, f"Roster '{roster.name}' created successfully.")
            return redirect("core:roster_list")
    else:
        initial = {}
        if request.user.site:
            initial["site"] = request.user.site
        form = RosterForm(initial=initial, user=request.user)

    return render(request, "core/teacher/roster_form.html", {
        "form": form,
        "title": "Create Roster",
    })


@login_required
@teacher_required
def roster_edit(request, pk):
    roster = get_object_or_404(Roster, pk=pk)

    if request.method == "POST":
        form = RosterForm(request.POST, instance=roster, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Roster updated successfully.")
            return redirect("core:roster_list")
    else:
        form = RosterForm(instance=roster, user=request.user)

    memberships = roster.memberships.select_related("student").order_by("student__username")
    add_student_form = RosterAddStudentForm(roster=roster)

    return render(request, "core/teacher/roster_form.html", {
        "form": form,
        "roster": roster,
        "memberships": memberships,
        "add_student_form": add_student_form,
        "title": f"Edit Roster: {roster.name}",
    })


@login_required
@teacher_required
def roster_add_student(request, pk):
    """Bulk add students to a roster via HTMX."""
    roster = get_object_or_404(Roster, pk=pk)

    if request.method == "POST":
        form = RosterAddStudentForm(request.POST, roster=roster)
        if form.is_valid():
            students = form.cleaned_data["students"]

            # Create memberships for all valid students
            for student in students:
                RosterMembership.objects.create(roster=roster, student=student)

            # Build result message
            results = form.results
            msg_parts = []
            if results["added"]:
                msg_parts.append(f"Added {len(results['added'])} existing student(s)")
            if results["created"]:
                msg_parts.append(f"Created {len(results['created'])} new account(s)")
            if results["skipped"]:
                msg_parts.append(f"Skipped {len(results['skipped'])} (already in roster)")
            if results["errors"]:
                msg_parts.append(f"{len(results['errors'])} error(s)")

            if msg_parts:
                messages.success(request, ". ".join(msg_parts) + ".")

            if results["errors"]:
                for error in results["errors"]:
                    messages.warning(request, error)

            # Return updated student list partial for HTMX
            memberships = roster.memberships.select_related("student").order_by("student__username")
            add_student_form = RosterAddStudentForm(roster=roster)
            return render(request, "core/teacher/partials/roster_students.html", {
                "roster": roster,
                "memberships": memberships,
                "add_student_form": add_student_form,
            })
        else:
            # Return form with errors
            memberships = roster.memberships.select_related("student").order_by("student__username")
            return render(request, "core/teacher/partials/roster_students.html", {
                "roster": roster,
                "memberships": memberships,
                "add_student_form": form,
            })

    return redirect("core:roster_edit", pk=pk)


@login_required
@teacher_required
def roster_remove_student(request, pk, student_id):
    """Remove a student from a roster via HTMX."""
    roster = get_object_or_404(Roster, pk=pk)

    if request.method == "POST":
        membership = get_object_or_404(RosterMembership, roster=roster, student_id=student_id)
        student_name = membership.student.username
        membership.delete()
        messages.success(request, f"Removed {student_name} from roster.")

        # Return updated student list partial for HTMX
        memberships = roster.memberships.select_related("student").order_by("student__username")
        add_student_form = RosterAddStudentForm(roster=roster)
        return render(request, "core/teacher/partials/roster_students.html", {
            "roster": roster,
            "memberships": memberships,
            "add_student_form": add_student_form,
        })

    return redirect("core:roster_edit", pk=pk)


# =============================================================================
# UNIT VIEWS
# =============================================================================

@login_required
@teacher_required
def unit_list(request):
    """List all units for the current instructor with nested lessons."""
    units = Unit.objects.filter(teacher=request.user).prefetch_related(
        "unit_lessons__lesson__story"
    ).annotate(
        lessons_count=Count("unit_lessons")
    ).order_by("-created_at")

    return render(request, "core/teacher/unit_list.html", {
        "units": units,
        "title": "Units",
    })


@login_required
@teacher_required
def unit_create(request):
    """Create a new unit."""
    if request.method == "POST":
        form = UnitForm(request.POST)
        formset = UnitLessonFormSet(request.POST)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(teacher=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            unit = form.save(commit=False)
            unit.instructor = request.user
            unit.save()

            formset.instance = unit
            formset.save()

            messages.success(request, f"Unit '{unit.title}' created successfully.")
            return redirect("core:unit_edit", pk=unit.pk)
    else:
        form = UnitForm()
        formset = UnitLessonFormSet()
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(teacher=request.user).order_by("title")

    return render(request, "core/teacher/unit_form.html", {
        "form": form,
        "formset": formset,
        "title": "Create Unit",
    })


@login_required
@teacher_required
def unit_edit(request, pk):
    """Edit an existing unit."""
    unit = get_object_or_404(Unit, pk=pk, teacher=request.user)

    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)
        formset = UnitLessonFormSet(request.POST, instance=unit)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(teacher=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Unit updated successfully.")
            return redirect("core:unit_edit", pk=pk)
    else:
        form = UnitForm(instance=unit)
        formset = UnitLessonFormSet(instance=unit)
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(teacher=request.user).order_by("title")

    return render(request, "core/teacher/unit_form.html", {
        "form": form,
        "formset": formset,
        "unit": unit,
        "title": f"Edit Unit: {unit.title}",
    })


@login_required
@teacher_required
def unit_delete(request, pk):
    """Delete a unit."""
    unit = get_object_or_404(Unit, pk=pk, teacher=request.user)

    if request.method == "POST":
        title = unit.title
        unit.delete()
        messages.success(request, f"Unit '{title}' deleted.")
        return redirect("core:unit_list")

    return render(request, "core/teacher/unit_confirm_delete.html", {
        "unit": unit,
        "title": f"Delete Unit: {unit.title}",
    })


@login_required
@teacher_required
def unit_available_lessons(request, pk):
    """HTMX endpoint: return lessons not already in this unit."""
    unit = get_object_or_404(Unit, pk=pk, teacher=request.user)
    existing_lesson_ids = unit.unit_lessons.values_list("lesson_id", flat=True)
    available_lessons = Lesson.objects.filter(
        teacher=request.user
    ).exclude(
        pk__in=existing_lesson_ids
    ).order_by("-id")
    return render(request, "core/teacher/partials/unit_available_lessons.html", {
        "unit": unit,
        "lessons": available_lessons,
    })


@login_required
@teacher_required
def unit_add_lesson(request, pk):
    """Add an existing lesson to a unit."""
    unit = get_object_or_404(Unit, pk=pk, teacher=request.user)

    if request.method == "POST":
        lesson_id = request.POST.get("lesson_id")
        if lesson_id:
            lesson = get_object_or_404(Lesson, pk=lesson_id, teacher=request.user)
            # Check if already in unit
            if not UnitLesson.objects.filter(unit=unit, lesson=lesson).exists():
                max_order = unit.unit_lessons.aggregate(max_order=Max("order"))["max_order"] or 0
                UnitLesson.objects.create(unit=unit, lesson=lesson, order=max_order + 1)
                messages.success(request, f"Lesson '{lesson.title}' added to unit.")

    return redirect("core:unit_list")


# =============================================================================
# COURSE VIEWS
# =============================================================================

@login_required
@teacher_required
def course_list(request):
    """List all courses for the current instructor."""
    courses = Course.objects.filter(teacher=request.user).annotate(
        units_count=Count("course_units")
    ).order_by("-created_at")

    return render(request, "core/teacher/course_list.html", {
        "courses": courses,
        "title": "Courses",
    })


@login_required
@teacher_required
def course_create(request):
    """Create a new course."""
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        formset = CourseUnitFormSet(request.POST)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(teacher=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            form.save_m2m()  # Save rosters

            formset.instance = course
            formset.save()

            messages.success(request, f"Course '{course.title}' created successfully.")
            return redirect("core:course_edit", pk=course.pk)
    else:
        form = CourseForm(user=request.user)
        formset = CourseUnitFormSet()
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(teacher=request.user).order_by("title")

    return render(request, "core/teacher/course_form.html", {
        "form": form,
        "formset": formset,
        "title": "Create Course",
    })


@login_required
@teacher_required
def course_edit(request, pk):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=pk, teacher=request.user)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course, user=request.user)
        formset = CourseUnitFormSet(request.POST, instance=course)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(teacher=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Course updated successfully.")
            return redirect("core:course_edit", pk=pk)
    else:
        form = CourseForm(instance=course, user=request.user)
        formset = CourseUnitFormSet(instance=course)
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(teacher=request.user).order_by("title")

    return render(request, "core/teacher/course_form.html", {
        "form": form,
        "formset": formset,
        "course": course,
        "title": f"Edit Course: {course.title}",
    })


@login_required
@teacher_required
def course_delete(request, pk):
    """Delete a course."""
    course = get_object_or_404(Course, pk=pk, teacher=request.user)

    if request.method == "POST":
        title = course.title
        course.delete()
        messages.success(request, f"Course '{title}' deleted.")
        return redirect("core:course_list")

    return render(request, "core/teacher/course_confirm_delete.html", {
        "course": course,
        "title": f"Delete Course: {course.title}",
    })


# =============================================================================
# GLOSSARY / TERM VIEWS
# =============================================================================

@login_required
@teacher_required
def term_create(request, story_pk):
    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)
    glossary, _ = Glossary.objects.get_or_create(
        story=story,
        defaults={"language_code": "en", "native_language_code": "vi"}
    )

    if request.method == "POST":
        form = TermForm(request.POST)
        if form.is_valid():
            term = form.save(commit=False)
            term.glossary = glossary
            term.save()
            messages.success(request, f"Term '{term.term_text}' added.")
            return redirect("core:story_edit", pk=story.pk)
    else:
        form = TermForm()

    return render(request, "core/teacher/term_form.html", {
        "form": form,
        "story": story,
        "title": "Add Term",
    })


@login_required
@teacher_required
def term_edit(request, story_pk, term_pk):
    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)
    term = get_object_or_404(Term, pk=term_pk, glossary__story=story)

    if request.method == "POST":
        form = TermForm(request.POST, instance=term)
        if form.is_valid():
            form.save()
            messages.success(request, f"Term '{term.term_text}' updated.")
            return redirect("core:story_edit", pk=story.pk)
    else:
        form = TermForm(instance=term)

    return render(request, "core/teacher/term_form.html", {
        "form": form,
        "story": story,
        "term": term,
        "title": f"Edit Term: {term.term_text}",
    })


@login_required
@teacher_required
def term_delete(request, story_pk, term_pk):
    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)
    term = get_object_or_404(Term, pk=term_pk, glossary__story=story)

    if request.method == "POST":
        term_text = term.term_text
        term.delete()
        messages.success(request, f"Term '{term_text}' deleted.")
        return redirect("core:story_edit", pk=story.pk)

    return render(request, "core/teacher/term_confirm_delete.html", {
        "term": term,
        "story": story,
    })


# =============================================================================
# GLOSSARY GENERATION VIEWS
# =============================================================================

@login_required
@teacher_required
def glossary_generate(request, story_pk):
    """
    AI-powered glossary generation based on story content.
    Shows form for configuring glossary generation parameters.
    """
    import json

    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)
    form = GlossaryGeneratorForm(request.POST or None)
    generation_params = None
    generation_params_json = None

    # Get or create glossary for the story
    glossary, _ = Glossary.objects.get_or_create(
        story=story,
        defaults={"language_code": "en", "native_language_code": "vi"}
    )

    if request.method == "POST" and form.is_valid():
        # Store generation params in session for AI call
        generation_params = {
            "story_id": story.pk,
            "story_title": story.title,
            "story_content": story.text_html,
            "reading_level": story.reading_level_label or "unknown",
            "num_terms": form.cleaned_data["num_terms"],
            "difficulty": form.cleaned_data["difficulty"],
            "focus": form.cleaned_data["focus"],
            "translation_language": form.cleaned_data["translation_language"],
            "include_definitions": form.cleaned_data["include_definitions"],
            "include_translations": form.cleaned_data["include_translations"],
            "include_part_of_speech": form.cleaned_data["include_part_of_speech"],
            "clear_existing": form.cleaned_data["clear_existing"],
        }
        request.session["glossary_generation_params"] = generation_params

        # Create JSON-safe version for JavaScript
        generation_params_json = json.dumps({
            "story_id": generation_params["story_id"],
            "story_title": generation_params["story_title"],
            "reading_level": generation_params["reading_level"],
            "num_terms": generation_params["num_terms"],
            "difficulty": generation_params["difficulty"],
            "focus": generation_params["focus"],
            "translation_language": generation_params["translation_language"],
            "include_definitions": generation_params["include_definitions"],
            "include_translations": generation_params["include_translations"],
            "include_part_of_speech": generation_params["include_part_of_speech"],
            "clear_existing": generation_params["clear_existing"],
        })

    return render(request, "core/teacher/glossary_generate.html", {
        "form": form,
        "story": story,
        "glossary": glossary,
        "existing_terms_count": glossary.terms.count(),
        "generation_params": generation_params,
        "generation_params_json": generation_params_json,
        "title": f"Generate Glossary: {story.title}",
    })


@login_required
@teacher_required
def glossary_generate_ai(request, story_pk):
    """
    Call OpenRouter API to generate glossary terms using the stored parameters.
    """
    import json
    import re
    from django.http import JsonResponse
    from django.conf import settings

    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    # Get generation params from session
    generation_params = request.session.get("glossary_generation_params")
    if not generation_params:
        return JsonResponse({"success": False, "error": "No generation parameters found. Please configure options first."}, status=400)

    # Verify story matches
    if generation_params.get("story_id") != story.pk:
        return JsonResponse({"success": False, "error": "Story mismatch. Please reconfigure."}, status=400)

    # Check API key
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return JsonResponse({"success": False, "error": "OPENROUTER_API_KEY not configured"}, status=500)

    # Build the prompt for glossary generation
    story_content = generation_params["story_content"]
    # Strip HTML tags for cleaner text
    clean_text = re.sub(r'<[^>]+>', ' ', story_content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    num_terms = generation_params["num_terms"]
    difficulty = generation_params["difficulty"]
    focus = generation_params["focus"]
    reading_level = generation_params["reading_level"]
    translation_language = generation_params["translation_language"]
    include_definitions = generation_params["include_definitions"]
    include_translations = generation_params["include_translations"]
    include_part_of_speech = generation_params["include_part_of_speech"]

    # Build difficulty description
    if difficulty == "auto" and reading_level != "unknown":
        difficulty_desc = f"appropriate for {reading_level} reading level"
    else:
        difficulty_desc = {
            "beginner": "basic, high-frequency vocabulary that beginners might not know",
            "intermediate": "moderately challenging vocabulary including some academic words",
            "advanced": "advanced vocabulary including rare and technical terms",
            "auto": "vocabulary appropriate for the text's complexity level"
        }.get(difficulty, "moderately challenging vocabulary")

    focus_desc = {
        "general": "general vocabulary words",
        "academic": "academic and scholarly vocabulary",
        "domain": "domain-specific and technical terms",
        "mixed": "a mix of general, academic, and domain-specific vocabulary"
    }.get(focus, "mixed vocabulary types")

    output_format = []
    output_format.append('"term": "the vocabulary word as it appears in the text"')
    output_format.append('"lemma": "the base/dictionary form of the word"')
    if include_part_of_speech:
        output_format.append('"part_of_speech": "noun, verb, adjective, etc."')
    if include_definitions:
        output_format.append('"definition": "a clear, simple definition in English"')
    if include_translations:
        output_format.append(f'"translation": "translation in {translation_language}"')
    output_format.append('"difficulty": 1-5 rating (1=easy, 5=very difficult)')

    system_prompt = f"""You are an expert vocabulary instructor and lexicographer. Analyze the reading passage and identify vocabulary words that would benefit language learners.

Your task:
- Identify exactly {num_terms} vocabulary terms from the passage
- Focus on {focus_desc}
- Select words that are {difficulty_desc}
- Choose words that are important for understanding the text
- Avoid very common words (the, is, and, etc.) unless they have special meanings in context

For each term, provide:
{chr(10).join('- ' + item for item in output_format)}

IMPORTANT: Return ONLY a valid JSON array. No markdown, no explanations, just the JSON array.

Example output format:
[
  {{"term": "example", "lemma": "example", "part_of_speech": "noun", "definition": "a representative instance", "translation": "ví dụ", "difficulty": 2}},
  ...
]"""

    user_prompt = f"""Analyze this reading passage and identify {num_terms} vocabulary terms:

{clean_text[:8000]}"""

    # Get model from POST data
    model = request.POST.get("model", "openai/gpt-4o-mini")

    # Call OpenRouter API
    import urllib.request
    import urllib.error

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": request.build_absolute_uri("/"),
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response
        # Try to extract JSON array from the response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            terms = json.loads(json_match.group())
        else:
            return JsonResponse({"success": False, "error": "Could not parse AI response as JSON"}, status=500)

        return JsonResponse({"success": True, "terms": terms})

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        return JsonResponse({"success": False, "error": f"API error: {error_body}"}, status=500)
    except json.JSONDecodeError as e:
        return JsonResponse({"success": False, "error": f"JSON parse error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@teacher_required
def glossary_generate_save(request, story_pk):
    """
    Save the generated glossary terms to the database.
    """
    import json
    from django.http import JsonResponse

    story = get_object_or_404(Story, pk=story_pk, teacher=request.user)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        terms = data.get("terms", [])
        clear_existing = data.get("clear_existing", False)

        if not terms:
            return JsonResponse({"success": False, "error": "No terms to save"}, status=400)

        # Get or create glossary
        glossary, _ = Glossary.objects.get_or_create(
            story=story,
            defaults={"language_code": "en", "native_language_code": "vi"}
        )

        # Update native language code based on translation language if provided
        translation_lang = data.get("translation_language", "")
        if translation_lang:
            lang_code_map = {
                "vietnamese": "vi", "spanish": "es", "chinese": "zh",
                "french": "fr", "german": "de", "japanese": "ja",
                "korean": "ko", "portuguese": "pt", "arabic": "ar",
            }
            code = lang_code_map.get(translation_lang.lower(), translation_lang[:2].lower())
            glossary.native_language_code = code
            glossary.save()

        # Clear existing terms if requested
        if clear_existing:
            glossary.terms.all().delete()

        # Create new terms
        created_count = 0
        for term_data in terms:
            term_text = term_data.get("term", "").strip()
            if not term_text:
                continue

            # Check if term already exists
            if glossary.terms.filter(term_text__iexact=term_text).exists():
                continue

            Term.objects.create(
                glossary=glossary,
                term_text=term_text,
                lemma=term_data.get("lemma", ""),
                part_of_speech=term_data.get("part_of_speech", ""),
                definition_html=term_data.get("definition", ""),
                translation=term_data.get("translation", ""),
                translation_lang_code=glossary.native_language_code,
                difficulty_rating=term_data.get("difficulty"),
                is_ai_suggested=True,
                is_selected_for_glossary=True,
            )
            created_count += 1

        # Clear the session params
        if "glossary_generation_params" in request.session:
            del request.session["glossary_generation_params"]

        return JsonResponse({
            "success": True,
            "created_count": created_count,
            "redirect_url": f"/teacher/stories/{story.pk}/?tab=glossary"
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =============================================================================
# STANDARDS & LEARNING OBJECTIVES VIEWS
# =============================================================================

@login_required
@teacher_required
def standards_browse(request):
    """
    Main standards browsing page with cascading filters.
    Teacher can filter by Authority → Program → Grade → Subject.
    """
    authorities = StandardsAuthority.objects.filter(is_active=True).order_by("name")

    return render(request, "core/teacher/standards_browse.html", {
        "authorities": authorities,
        "title": "Browse Learning Standards",
    })


@login_required
@teacher_required
def standards_api_authorities(request):
    """API endpoint: return all active authorities as JSON."""
    authorities = StandardsAuthority.objects.filter(is_active=True).order_by("name")

    seen_codes = set()
    data = []
    for a in authorities:
        if a.code in seen_codes:
            continue
        seen_codes.add(a.code)
        data.append({"id": a.pk, "code": a.code, "name": a.name})

    return JsonResponse({"authorities": data})


@login_required
@teacher_required
def standards_api_programs(request):
    """API endpoint: return programs for selected authorities."""
    authority_ids = request.GET.getlist("authorities")

    if not authority_ids:
        return JsonResponse({"programs": []})

    programs = AuthorityProgram.objects.filter(
        authority_id__in=authority_ids,
        is_active=True
    ).select_related("authority").order_by("authority__name", "name")

    # Filter out redundant parent programs (e.g., Cambridge "Cambridge International" wrapper)
    def _skip_program(p: AuthorityProgram) -> bool:
        if p.authority.code == "CAMBRIDGE" and p.code in ("CAM_INTL", "CAM_STARTERS"):
            return True
        if p.authority.code == "IB" and p.code == "IB_INTL":
            return True
        if p.authority.code == "COLLEGE_BOARD" and p.code == "CB_AP":
            return True
        if p.authority.code in ("US_STATE_STANDARDS", "US_STATES") and p.name.strip().lower() == "us state standards":
            return True
        return False

    # Custom sort order for Cambridge programs
    cambridge_order = {
        "CAM_PRIMARY": 0,
        "CAM_LOWER_SECONDARY": 1,
        "CAM_IGCSE": 2,
        "CAM_AS_A_LEVEL": 3,
        "CAM_O_LEVEL": 4,
    }

    def _sort_key(p: AuthorityProgram):
        if p.authority.code == "CAMBRIDGE" and p.code in cambridge_order:
            return (p.authority.name, cambridge_order[p.code], p.name)
        return (p.authority.name, 99, p.name)

    seen = set()
    data = [
        {
            "id": p.pk,
            "code": p.code,
            "name": p.name,
            "authority_code": p.authority.code,
            "authority_name": p.authority.name,
        }
        for p in sorted(programs, key=_sort_key)
        if not _skip_program(p)
        if not (
            (p.authority_id, p.name.lower().strip()) in seen or seen.add((p.authority_id, p.name.lower().strip()))
        )
    ]
    return JsonResponse({"programs": data})


@login_required
@teacher_required
def standards_api_grades(request):
    """API endpoint: return distinct grade levels for selected programs."""
    program_ids = request.GET.getlist("programs")

    if not program_ids:
        return JsonResponse({"grades": []})

    # Get distinct grade levels from documents
    grades = (
        StandardsDocument.objects
        .filter(authority_program_id__in=program_ids, is_active=True)
        .values_list("grade_level", flat=True)
        .distinct()
        .order_by("grade_level")
    )

    data = [{"value": g, "label": g} for g in grades if g]
    return JsonResponse({"grades": data})


@login_required
@teacher_required
def standards_api_subjects(request):
    """API endpoint: return distinct subjects for selected programs."""
    program_ids = request.GET.getlist("programs")

    if not program_ids:
        return JsonResponse({"subjects": []})

    # Get distinct subjects from documents
    subjects = (
        StandardsDocument.objects
        .filter(authority_program_id__in=program_ids, is_active=True)
        .values_list("subject", flat=True)
        .distinct()
        .order_by("subject")
    )

    data = [{"value": s, "label": s} for s in subjects if s]
    return JsonResponse({"subjects": data})


@login_required
@teacher_required
def standards_api_courses(request):
    """API endpoint: return distinct courses for selected programs and subjects."""
    program_ids = request.GET.getlist("programs")
    subjects = request.GET.getlist("subjects")

    if not program_ids:
        return JsonResponse({"courses": []})

    # Get documents (courses) filtered by program and optionally subject
    queryset = (
        StandardsDocument.objects
        .filter(authority_program_id__in=program_ids, is_active=True)
    )

    if subjects:
        queryset = queryset.filter(subject__in=subjects)

    # Return course info with ID, syllabus_code, name (source_title), and version_label
    courses = (
        queryset
        .values("id", "syllabus_code", "source_title", "version_label", "grade_level", "subject")
        .order_by("subject", "syllabus_code", "source_title")
    )

    data = [
        {
            "id": c["id"],
            "syllabus_code": c["syllabus_code"],
            "name": c["source_title"] or c["version_label"],
            "version_label": c["version_label"],
            "grade_level": c["grade_level"],
            "subject": c["subject"],
        }
        for c in courses
    ]
    return JsonResponse({"courses": data})


def _expand_grade_levels(selected_grades: list[str]) -> set[str]:
    """
    Expand grade level selections to include hierarchical matches.

    Examples:
    - "Grade 6" also matches "Grades 6-8", "Middle School"
    - "Grades 6-8" also matches "Grade 6", "Grade 7", "Grade 8"
    """
    import re

    expanded = set(selected_grades)

    # Common grade band patterns
    GRADE_BANDS = {
        "K-2": ["K", "Kindergarten", "1", "2"],
        "Grades K-2": ["K", "Kindergarten", "1", "2"],
        "3-5": ["3", "4", "5"],
        "Grades 3-5": ["3", "4", "5"],
        "6-8": ["6", "7", "8"],
        "Grades 6-8": ["6", "7", "8"],
        "9-12": ["9", "10", "11", "12"],
        "Grades 9-12": ["9", "10", "11", "12"],
        "Middle School": ["6", "7", "8"],
        "High School": ["9", "10", "11", "12"],
        "Elementary": ["K", "Kindergarten", "1", "2", "3", "4", "5"],
    }

    # Reverse mapping: individual grades to their bands
    GRADE_TO_BANDS = {}
    for band, grades in GRADE_BANDS.items():
        for g in grades:
            if g not in GRADE_TO_BANDS:
                GRADE_TO_BANDS[g] = []
            GRADE_TO_BANDS[g].append(band)

    for selected in selected_grades:
        # Extract numeric grade from patterns like "Grade 6", "Grade K", etc.
        match = re.match(r'^Grade\s+(\w+)$', selected, re.IGNORECASE)
        if match:
            grade_num = match.group(1)
            # Add the grade bands this individual grade belongs to
            if grade_num in GRADE_TO_BANDS:
                expanded.update(GRADE_TO_BANDS[grade_num])

        # If a band is selected, expand to include individual grades
        if selected in GRADE_BANDS:
            for g in GRADE_BANDS[selected]:
                expanded.add(f"Grade {g}")
                # Also add common variations
                if g == "K":
                    expanded.add("Grade Kindergarten")
                    expanded.add("Kindergarten")

    return expanded


@login_required
@teacher_required
def standards_api_results(request):
    """
    API endpoint: return course catalog organized by subject and grade level.
    Returns courses (StandardsDocuments) as the browsable items.
    """
    program_ids = request.GET.getlist("programs")
    document_id = request.GET.get("document_id")
    grades = request.GET.getlist("grades")
    subjects = request.GET.getlist("subjects")
    course_ids = request.GET.getlist("courses")

    if document_id:
        doc = get_object_or_404(
            StandardsDocument.objects.select_related("authority_program__authority"),
            pk=document_id,
        )
        return JsonResponse({
            "documents": [{
                "id": doc.pk,
                "syllabus_code": doc.syllabus_code,
                "source_title": doc.source_title,
                "authority_name": doc.authority_program.authority.name,
                "authority_code": doc.authority_program.authority.code,
                "authority_id": doc.authority_program.authority_id,
                "program_name": doc.authority_program.name,
                "program_id": doc.authority_program_id,
                "program_code": doc.authority_program.code,
                "subject": doc.subject,
                "grade_level": doc.grade_level,
                "version_label": doc.version_label,
                "source_url": doc.source_url,
                "description": doc.description or doc.acquisition_notes or "",
                "tab_config": "cambridge" if doc.authority_program.authority.code == "CAMBRIDGE" else "default",
            }]
        })

    if not program_ids:
        return JsonResponse({"documents": [], "message": "Please select at least one program."})

    # Build query
    queryset = StandardsDocument.objects.filter(
        authority_program_id__in=program_ids,
        is_active=True
    ).select_related("authority_program__authority")

    if grades:
        # Expand grades to include hierarchical matches
        expanded_grades = _expand_grade_levels(grades)
        queryset = queryset.filter(grade_level__in=expanded_grades)
    if subjects:
        queryset = queryset.filter(subject__in=subjects)
    if course_ids:
        queryset = queryset.filter(id__in=course_ids)

    queryset = queryset.order_by(
        "subject",
        "syllabus_code",
        "grade_level"
    )

    documents_data = []
    for doc in queryset:
        authority_code = doc.authority_program.authority.code

        # Determine tab configuration based on authority type
        if authority_code == "CAMBRIDGE":
            tab_config = "cambridge"
        elif authority_code == "IB":
            tab_config = "ib"
        elif authority_code == "COLLEGE_BOARD":
            tab_config = "college_board"
        elif authority_code == "WIDA":
            tab_config = "wida"
        elif authority_code == "BRITISH_COUNCIL":
            tab_config = "british_council"
        elif authority_code == "ETS":
            tab_config = "ets"
        elif authority_code == "FOREIGN_MOE":
            tab_config = "foreign_moe"
        elif authority_code == "CCSS":
            tab_config = "common_core"
        elif authority_code.startswith("STATE_") or authority_code in ("US_STATES", "US_STATE_STANDARDS"):
            tab_config = "us_state"
        else:
            tab_config = "default"

        documents_data.append({
            "id": doc.pk,
            "syllabus_code": doc.syllabus_code,
            "source_title": doc.source_title,
            "authority_name": doc.authority_program.authority.name,
            "authority_id": doc.authority_program.authority_id,
            "authority_code": authority_code,
            "program_name": doc.authority_program.name,
            "program_id": doc.authority_program_id,
            "program_code": doc.authority_program.code,
            "subject": doc.subject,
            "grade_level": doc.grade_level,
            "version_label": doc.version_label,
            "source_url": doc.source_url,
            "description": doc.description or doc.acquisition_notes or "",
            "tab_config": tab_config,
        })

    return JsonResponse({
        "documents": documents_data,
        "total_documents": len(documents_data),
    })


@login_required
@teacher_required
def standards_api_document_objectives(request, document_id):
    """
    API endpoint: return the objective tree for a specific document (course).
    Returns hierarchical structure: strands -> substrands -> objectives
    """
    try:
        document = StandardsDocument.objects.select_related(
            "authority_program__authority"
        ).get(pk=document_id, is_active=True)
    except StandardsDocument.DoesNotExist:
        return JsonResponse({"error": "Document not found"}, status=404)

    def build_tree(parent=None):
        """Recursively build the objective tree."""
        nodes = ObjectiveNode.objects.filter(
            document=document,
            parent=parent
        ).order_by("sort_order", "code")

        result = []
        for node in nodes:
            node_data = {
                "id": node.pk,
                "code": node.code,
                "text": node.text,
                "node_type": node.node_type,
                "internal_code": node.internal_code,
                "sort_order": node.sort_order,
                "children": build_tree(parent=node)
            }
            result.append(node_data)
        return result

    objectives_tree = build_tree(parent=None)

    return JsonResponse({
        "document_id": document.pk,
        "syllabus_code": document.syllabus_code,
        "subject": document.subject,
        "grade_level": document.grade_level,
        "total_objectives": document.objective_nodes.count(),
        "objectives": objectives_tree,
    })


@login_required
@teacher_required
def standards_api_search(request):
    """
    API endpoint: search objectives by keyword or code.

    Query parameters:
    - q: Search query (searches text, native code, and internal code)
    - programs: Comma-separated program IDs to filter
    - limit: Maximum results (default 50)
    """
    query = request.GET.get("q", "").strip()
    program_ids = request.GET.getlist("programs")
    limit = min(int(request.GET.get("limit", 50)), 200)

    if not query or len(query) < 2:
        return JsonResponse({"error": "Query must be at least 2 characters"}, status=400)

    # Build base queryset
    from django.db.models import Q
    qs = ObjectiveNode.objects.select_related(
        "document__authority_program__authority"
    ).filter(
        document__is_active=True
    )

    # Filter by programs if specified
    if program_ids:
        qs = qs.filter(document__authority_program_id__in=program_ids)

    # Search across text, native code, and internal code
    qs = qs.filter(
        Q(text__icontains=query) |
        Q(code__icontains=query) |
        Q(internal_code__icontains=query)
    )

    # Order by relevance (exact code matches first, then by sort order)
    qs = qs.order_by(
        "document__authority_program__authority__code",
        "document__subject",
        "sort_order"
    )[:limit]

    results = []
    for node in qs:
        doc = node.document
        results.append({
            "id": node.pk,
            "code": node.code,
            "internal_code": node.internal_code,
            "text": node.text,
            "node_type": node.node_type,
            "document_id": doc.pk,
            "subject": doc.subject,
            "grade_level": doc.grade_level,
            "syllabus_code": doc.syllabus_code,
            "authority_code": doc.authority_program.authority.code,
            "authority_name": doc.authority_program.authority.name,
            "program_code": doc.authority_program.code,
            "program_name": doc.authority_program.name,
        })

    return JsonResponse({
        "results": results,
        "total": len(results),
        "query": query,
        "limit": limit,
    })


@login_required
@teacher_required
def standards_api_media(request):
    """
    API endpoint: get media/resources for authority programs.

    Query parameters:
    - programs: Comma-separated program IDs to filter
    - syllabus_code: If provided, only return media tagged with this syllabus code
    - official_only: If "true", only show official/endorsed resources
    - platform: Filter by platform (google_books, amazon, etc.)
    - media_type: Filter by type (book, guide, course, etc.)
    - q: Search by title/author/ISBN
    """
    program_ids = request.GET.getlist("programs")
    syllabus_code = request.GET.get("syllabus_code", "").strip()
    official_only = request.GET.get("official_only", "").lower() == "true"
    platform = request.GET.get("platform", "").strip()
    media_type = request.GET.get("media_type", "").strip()
    query = request.GET.get("q", "").strip()

    # Build queryset
    qs = AuthorityProgramMedia.objects.select_related(
        "authority_program__authority"
    ).prefetch_related("tags")

    # Filter by programs
    if program_ids:
        qs = qs.filter(authority_program_id__in=program_ids)

    # Filter by syllabus code when provided (course-specific resources)
    if syllabus_code:
        qs = qs.filter(features__syllabus_code=syllabus_code)

    # Filter by official status
    if official_only:
        qs = qs.filter(is_official=True)

    # Filter by platform
    if platform:
        qs = qs.filter(platform=platform)

    # Filter by media type
    if media_type:
        qs = qs.filter(media_type=media_type)

    # Search
    if query:
        from django.db.models import Q
        qs = qs.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(isbn_10__icontains=query) |
            Q(isbn_13__icontains=query)
        )

    # Order: official first, then by title
    qs = qs.order_by("-is_official", "title")[:100]

    results = []
    for media in qs:
        results.append({
            "id": media.pk,
            "title": media.title,
            "author": media.author,
            "publisher": media.publisher,
            "description": media.description[:300] + "..." if len(media.description) > 300 else media.description,
            "isbn_10": media.isbn_10,
            "isbn_13": media.isbn_13,
            "source_url": media.source_url,
            "cover_image_url": media.cover_image_url,
            "publisher_url": media.publisher_url,
            "media_type": media.media_type,
            "media_type_display": media.get_media_type_display(),
            "platform": media.platform,
            "platform_display": media.get_platform_display(),
            "retrieved_from": media.retrieved_from,
            "resource_category": getattr(media, "resource_category", "") or "",
            "audience": getattr(media, "audience", "") or "",
            "is_companion": getattr(media, "is_companion", False),
            "is_official": media.is_official,
            "is_unofficial": media.is_unofficial,
            "endorsement_notes": media.endorsement_notes,
            "features": media.features,
            "tags": [tag.label for tag in media.tags.all()],
            "program_id": media.authority_program_id,
            "program_code": media.authority_program.code,
            "program_name": media.authority_program.name,
            "authority_code": media.authority_program.authority.code,
        })

    return JsonResponse({
        "results": results,
        "total": len(results),
    })


@login_required
@teacher_required
def standards_api_objectives(request, document_id):
    """
    API endpoint: return objective tree for a specific StandardsDocument.
    """
    doc = get_object_or_404(
        StandardsDocument.objects.select_related("authority_program__authority"),
        pk=document_id,
        is_active=True,
    )

    def build_tree(parent=None):
        nodes = ObjectiveNode.objects.filter(document=doc, parent=parent).order_by("sort_order")
        data = []
        for node in nodes:
            data.append({
                "id": node.pk,
                "code": node.code,
                "text": node.text,
                "node_type": node.node_type,
                "children": build_tree(node),
            })
        return data

    return JsonResponse({
        "document_id": doc.pk,
        "objectives": build_tree(None),
    })


@login_required
@teacher_required
def standards_api_cambridge_assets(request, document_id):
    """
    Fetch syllabus, scheme (if present), and past paper/endorsed resource links from official Cambridge pages.
    Runtime scrape per document to avoid aggressive crawling.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    doc = get_object_or_404(
        StandardsDocument.objects.select_related("authority_program__authority"),
        pk=document_id,
        is_active=True,
    )

    if doc.authority_program.authority.code != "CAMBRIDGE":
        return JsonResponse({"error": "Only supported for Cambridge courses"}, status=400)

    base_url = doc.source_url or ""
    results = {
        "syllabus_pdf": None,
        "scheme_pdf": None,
        "past_papers": [],
        "endorsed_resources": [],
        "catalog_resources": [],
        "hachette_resources": [],
        "description": "",
    }

    def fetch_html(url):
        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "SafeglossBot/1.0"})
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            return ""

    def find_pdf_links(html, base):
        links = []
        if not html:
            return links
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue
            full = urljoin(base, href)
            text = (a.get_text() or "").strip()
            links.append({"url": full, "text": text})
        return links

    # Main course page: syllabus + maybe scheme + endorsed listings
    main_html = fetch_html(base_url)
    if main_html:
        soup_main = BeautifulSoup(main_html, "html.parser")

        def extract_overview(soup):
            # Prefer a heading that includes "Syllabus overview"
            heading = None
            for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
                if "syllabus overview" in (tag.get_text() or "").lower():
                    heading = tag
                    break
            if heading:
                # Grab following paragraph(s) until next heading or empty
                parts = []
                for sib in heading.find_all_next():
                    if sib.name in ["h1", "h2", "h3", "h4"]:
                        break
                    if sib.name == "p":
                        txt = (sib.get_text() or "").strip()
                        if txt:
                            parts.append(txt)
                    if len(parts) >= 2:  # stop after a couple paragraphs
                        break
                return "\n\n".join(parts)
            # Fallback: meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                return meta_desc.get("content", "").strip()
            # Fallback: first paragraph
            first_p = soup.find("p")
            if first_p:
                return (first_p.get_text() or "").strip()
            return ""

        raw_desc = extract_overview(soup_main)
        if raw_desc:
            # Remove availability notice if present
            notice = "Available in a limited number of Administrative zones. See our 'Syllabus availability notice' below for details."
            results["description"] = raw_desc.replace(notice, "").strip()
        else:
            results["description"] = ""
        # Cache description on document
        if results["description"] and not doc.description:
            doc.description = results["description"]
            doc.save(update_fields=["description", "updated_at"])
    pdfs = find_pdf_links(main_html, base_url)

    def pick_link(keywords):
        for p in pdfs:
            text_lower = p["text"].lower()
            url_lower = p["url"].lower()
            if any(k in text_lower or k in url_lower for k in keywords):
                return p
        return None

    syllabus_link = pick_link(["syllabus", "specimen", "sg"])
    if syllabus_link:
        results["syllabus_pdf"] = _download_artifact(syllabus_link, doc, "syllabus")

    scheme_link = pick_link(["scheme", "sow"])
    if scheme_link:
        results["scheme_pdf"] = _download_artifact(scheme_link, doc, "scheme")

    # Past papers page
    past_url = urljoin(base_url + "/", "./past-papers/")
    past_html = fetch_html(past_url)
    past_pdfs = find_pdf_links(past_html, past_url)
    for p in past_pdfs:
        art = _download_artifact(p, doc, "past_paper")
        results["past_papers"].append({
            "name": art.get("label") or p["text"] or p["url"].split("/")[-1],
            "url": art.get("local_url") or art.get("remote_url") or p["url"],
            "remote_url": art.get("remote_url"),
        })

    # Endorsed resources page
    endorsed_url = urljoin(base_url + "/", "./endorsed-resources/")
    endorsed_html = fetch_html(endorsed_url)
    results["endorsed_resources"] = _extract_endorsed_resources(endorsed_html, endorsed_url, doc)

    # Cambridge catalog search (official cambridge.org products)
    results["catalog_resources"] = _search_cambridge_catalog(doc)
    # Hachette Learning catalog search (public pages)
    results["hachette_resources"] = _search_hachette_catalog(doc)

    return JsonResponse(results)


def _download_artifact(link: dict, doc: StandardsDocument, kind: str, download: bool = True) -> dict:
    """
    Download a PDF and register a StandardsArtifact; return local/remote URLs and label.
    """
    url = link.get("url")
    label = (link.get("text") or "").strip() or url.split("/")[-1]
    if not download:
        return {"remote_url": url, "label": label}

    try:
        resp = requests.get(url, timeout=25, headers={"User-Agent": "SafeglossBot/1.0"})
        resp.raise_for_status()
        content = resp.content
    except Exception:
        return {"remote_url": url, "label": label}

    # Validate PDF content (some endpoints serve HTML/captcha)
    content_type = resp.headers.get("Content-Type", "").lower()
    if "pdf" not in content_type and not content.startswith(b"%PDF"):
        return {"remote_url": url, "label": label}

    # Build safe filename
    import re, os
    safe_label = re.sub(r"[^a-zA-Z0-9._-]+", "_", label)[:80]
    if not safe_label.lower().endswith(".pdf"):
        safe_label += ".pdf"
    base_dir = os.path.join("data", "artifacts", "cambridge", f"doc_{doc.pk}")
    os.makedirs(base_dir, exist_ok=True)
    file_path = os.path.join(base_dir, safe_label)
    with open(file_path, "wb") as f:
        f.write(content)

    artifact = StandardsArtifact.objects.create(
        file_path=file_path,
        remote_url=url,
        content_type="pdf",
        sha256_hash=_compute_sha256(content),
        file_size_bytes=len(content),
        original_filename=safe_label,
        metadata={"kind": kind, "document_id": doc.pk},
    )

    return {
        "remote_url": url,
        "local_url": reverse("core:standards_api_artifact_download", args=[artifact.pk]),
        "label": label,
        "artifact_id": artifact.pk,
    }


def _extract_endorsed_resources(html: str, base_url: str, doc: StandardsDocument) -> list[dict]:
    """
    Extract endorsed resources from the endorsed-resources page, avoiding nav noise.
    Prefer links under the 'Endorsed resources' heading and PDF/product links.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup

    def collect_links(scope):
        found = []
        for a in scope.find_all("a", href=True):
            text = (a.get_text() or "").strip()
            href = a["href"]
            if not text:
                continue
            full = urljoin(base_url, href)
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            # Allow PDFs and Cambridge product/resource pages
            if ".pdf" in href.lower() or "cambridge.org" in href or "cambridgeinternational.org" in href:
                found.append({"title": text, "url": full})
        return found

    # Scope under heading containing "endorsed resources"
    section_links = []
    for h in main.find_all(["h1", "h2", "h3", "h4"]):
        if "endorsed resources" in (h.get_text() or "").lower():
            siblings = []
            for sib in h.find_all_next():
                if sib.name in ["h1", "h2", "h3", "h4"]:
                    break
                siblings.append(sib)
            wrapper = BeautifulSoup("<div></div>", "html.parser")
            container = wrapper.div
            for s in siblings:
                container.append(s)
            section_links = collect_links(container)
            break

    if section_links:
        return [_enrich_resource_link(link) for link in section_links]

    # Fallback: PDFs only from main content
    pdfs = []
    for a in main.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():
            continue
        text = (a.get_text() or "").strip()
        full = urljoin(base_url, href)
        if text or full:
            pdfs.append({"title": text or full.split("/")[-1], "url": full})
    return [_enrich_resource_link(link) for link in pdfs]


def _search_cambridge_catalog(doc: StandardsDocument) -> list[dict]:
    """
    Light search on cambridge.org for the course title/syllabus code.
    Avoids aggressive crawling; returns top product links with metadata.
    """
    import urllib.parse
    query_parts = [doc.source_title or "", doc.syllabus_code or ""]
    query = " ".join([q for q in query_parts if q]).strip()
    if not query:
        return []
    search_url = f"https://www.cambridge.org/gb/education/search?searchTerm={urllib.parse.quote(query)}"
    try:
        resp = requests.get(search_url, timeout=10, headers={"User-Agent": "SafeglossBot/1.0"})
        resp.raise_for_status()
    except Exception:
        return []
    if "text/html" not in resp.headers.get("Content-Type", "").lower():
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").strip()
        if not text:
            continue
        if "/education/subject/" not in href:
            continue
        full = href if href.startswith("http") else f"https://www.cambridge.org{href}"
        items.append({"title": text, "url": full})
        if len(items) >= 5:
            break
    return [_enrich_resource_link(link) for link in items]


def _search_hachette_catalog(doc: StandardsDocument) -> list[dict]:
    """
    Light search on hachettelearning.com for Cambridge titles.
    Uses site search with course title/syllabus code; keeps a few matches.
    """
    import urllib.parse
    query_parts = [doc.source_title or "", doc.syllabus_code or ""]
    query = " ".join([q for q in query_parts if q]).strip()
    if not query:
        return []
    search_url = f"https://www.hachettelearning.com/?s={urllib.parse.quote(query)}"
    try:
        resp = requests.get(search_url, timeout=10, headers={"User-Agent": "SafeglossBot/1.0"})
        resp.raise_for_status()
    except Exception:
        return []
    if "text/html" not in resp.headers.get("Content-Type", "").lower():
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").strip()
        if not text:
            continue
        if "hachettelearning.com" not in href:
            continue
        if "cambridge" not in href.lower():
            continue
        items.append({"title": text, "url": href})
        if len(items) >= 5:
            break
    return [_enrich_resource_link(link) for link in items]


def _enrich_resource_link(link: dict) -> dict:
    """
    Fetch a resource link and try to extract title/description/image metadata.
    Light-touch: short timeout, no JS, skip if HTML looks like captcha.
    """
    url = link.get("url")
    title = link.get("title") or url.split("/")[-1]
    data = {
        "title": title,
        "url": url,
        "description": "",
        "cover_image_url": "",
        "author": "",
        "publisher": "",
    }
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "SafeglossBot/1.0"})
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype.lower():
            return data
        soup = BeautifulSoup(resp.text, "html.parser")
        # Captcha check
        if "captcha" in soup.get_text(" ", strip=True).lower():
            return data
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        if og_title and og_title.get("content"):
            data["title"] = og_title["content"]
        if og_desc and og_desc.get("content"):
            data["description"] = og_desc["content"]
        if og_image and og_image.get("content"):
            data["cover_image_url"] = og_image["content"]
        # Fallback description: first paragraph
        if not data["description"]:
            p = soup.find("p")
            if p:
                desc = (p.get_text() or "").strip()
                data["description"] = desc[:500]
    except Exception:
        return data
    return data


@login_required
@teacher_required
def standards_api_artifact_download(request, artifact_id):
    """
    Serve an artifact file (PDF).
    """
    try:
        artifact = StandardsArtifact.objects.get(pk=artifact_id)
    except StandardsArtifact.DoesNotExist:
        raise Http404()

    try:
        return FileResponse(open(artifact.file_path, "rb"), content_type="application/pdf")
    except FileNotFoundError:
        raise Http404()


@login_required
@teacher_required
@require_POST
def standards_api_import_resources_ai(request):
    """
    Call OpenRouter to fetch resource metadata for a document (Cambridge) and import it.
    """
    document_id = request.POST.get("document_id")
    if not document_id:
        return JsonResponse({"error": "document_id is required"}, status=400)
    try:
        document_id = int(document_id)
    except ValueError:
        return JsonResponse({"error": "document_id must be an integer"}, status=400)

    doc = get_object_or_404(
        StandardsDocument.objects.select_related("authority_program__authority"),
        pk=document_id,
        is_active=True,
    )

    if doc.authority_program.authority.code != "CAMBRIDGE":
        return JsonResponse({"error": "Only supported for Cambridge courses"}, status=400)

    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not api_key:
        return JsonResponse({"error": "OPENROUTER_API_KEY not configured"}, status=500)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"""
You are an expert at gathering publicly available official Cambridge International course materials.
Return a JSON array with exactly one entry for THIS course only (do not include other courses):
- course_code (string)
- course_name (string)
- syllabi: list of objects {{title, url, format="pdf", version_label, notes}}
- past_papers: list of objects {{title, session, url, paper_code, notes}}
- endorsed_resources: list of objects {{
    title,
    authors[], publisher,
    isbn_10, isbn_13,
    format,
    url, cover_image_url,
    audience ("student"|"teacher"|"both"),
    is_companion (true if a companion/extra such as workbook, teacher's resource, digital access, online extras, DVD),
    notes
  }}
Include ALL endorsed/official resources for this course, both student-facing and teacher-facing, including companion media (workbooks, teacher's resources, digital coursebooks, online extras, DVDs, etc).
Only include publicly accessible URLs. If you do not find an item, leave the list empty. Do not invent resources.
Course:
{doc.source_title} ({doc.syllabus_code})
    """.strip()

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You return only valid JSON as described."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
        )
        content = completion.choices[0].message.content
        payload = json.loads(content)
        if isinstance(payload, dict):
            # Expect a list; wrap if single object
            payload = [payload]
    except Exception as e:
        return JsonResponse({"error": f"OpenRouter call failed: {e}"}, status=500)

    results = _import_resources_payload(payload)
    return JsonResponse({"import_result": results})


@login_required
@teacher_required
@require_POST
def standards_api_import_objectives_ai(request):
    """
    Call OpenRouter to fetch learning objectives for a document and import them as a numbered tree.
    """
    document_id = request.POST.get("document_id")
    if not document_id:
        return JsonResponse({"error": "document_id is required"}, status=400)
    try:
        document_id = int(document_id)
    except ValueError:
        return JsonResponse({"error": "document_id must be an integer"}, status=400)

    doc = get_object_or_404(
        StandardsDocument.objects.select_related("authority_program__authority"),
        pk=document_id,
        is_active=True,
    )

    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not api_key:
        return JsonResponse({"error": "OPENROUTER_API_KEY not configured"}, status=500)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    prompt = f"""
You are an expert at summarizing and structuring Cambridge International learning objectives.
Return a JSON object with a single key "objectives": an array of hierarchical nodes for THIS course only.
Each node: {{ "title": string, "code": string (optional), "children": [] }}
- Keep hierarchy and number like "1", "1.1", "1.1.1" etc. If no native code, create clear numbered codes.
- Include all key learning and assessment objectives you know for this course.
- Do not include any other courses.
Course: {doc.source_title} ({doc.syllabus_code})
    """.strip()

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You return only valid JSON as described."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )
        content = completion.choices[0].message.content
        payload = json.loads(content)
    except Exception as e:
        return JsonResponse({"error": f"OpenRouter call failed: {e}"}, status=500)

    nodes = payload.get("objectives") if isinstance(payload, dict) else None
    if not isinstance(nodes, list):
        return JsonResponse({"error": "Invalid objectives payload"}, status=400)

    # Replace existing objectives with AI tree
    ObjectiveNode.objects.filter(document=doc).delete()

    created_nodes = []

    def create_nodes(items, parent=None, prefix=""):
        for idx, item in enumerate(items, start=1):
            title = item.get("title") or item.get("text") or ""
            raw_code = item.get("code") or ""
            code = raw_code if raw_code else (prefix + str(idx) if prefix else str(idx))
            node = ObjectiveNode.objects.create(
                document=doc,
                parent=parent,
                node_type="objective",
                code=code,
                text=title,
                sort_order=idx,
            )
            created_nodes.append(node)
            children = item.get("children") or []
            create_nodes(children, node, prefix=code + ".")

    create_nodes(nodes, parent=None, prefix="")

    # Generate internal codes for consistency
    _generate_internal_codes(list(ObjectiveNode.objects.filter(document=doc)))

    # Build response tree
    def build_tree(parent=None):
        qs = ObjectiveNode.objects.filter(document=doc, parent=parent).order_by("sort_order")
        data = []
        for n in qs:
            data.append({
                "id": n.pk,
                "code": n.code,
                "text": n.text,
                "node_type": n.node_type,
                "children": build_tree(n),
            })
        return data

    return JsonResponse({"objectives": build_tree(None)})


@login_required
@teacher_required
@require_POST
def standards_api_sync_objectives(request):
    """
    API endpoint: Trigger objectives sync for an authority.

    POST parameters:
    - authority_id: ID of the StandardsAuthority to sync
    - document_id: optional StandardsDocument ID to sync only that course
    - syllabus_url: optional override for syllabus URL (provider-dependent)
    """
    from core.services.jobs import enqueue_authority_objectives_sync

    authority_id = request.POST.get("authority_id")
    document_id = request.POST.get("document_id")
    syllabus_url = request.POST.get("syllabus_url")
    if not authority_id:
        return JsonResponse({"error": "authority_id is required"}, status=400)

    try:
        authority_id = int(authority_id)
    except ValueError:
        return JsonResponse({"error": "authority_id must be an integer"}, status=400)

    # Verify authority exists
    try:
        authority = StandardsAuthority.objects.get(pk=authority_id)
    except StandardsAuthority.DoesNotExist:
        return JsonResponse({"error": f"Authority not found: {authority_id}"}, status=404)

    document_ids = None
    if document_id:
        try:
            document_ids = [int(document_id)]
        except ValueError:
            return JsonResponse({"error": "document_id must be an integer"}, status=400)

    # Enqueue the job
    job = enqueue_authority_objectives_sync(
        authority_id=authority_id,
        document_ids=document_ids,
        extra_params={"syllabus_url": syllabus_url} if syllabus_url else None,
        created_by=request.user,
    )

    return JsonResponse({
        "job_id": job.pk,
        "status": job.status,
        "authority_id": authority_id,
        "authority_name": authority.name,
        "message": f"Objectives sync queued for {authority.name}",
    })


@login_required
@teacher_required
@require_POST
def standards_api_sync_resources(request):
    """
    API endpoint: Trigger resources sync for an authority.

    POST parameters:
    - authority_id: ID of the StandardsAuthority to sync
    - document_id: optional StandardsDocument ID to limit sync to one course
    """
    from core.services.jobs import enqueue_authority_resources_sync

    authority_id = request.POST.get("authority_id")
    document_id = request.POST.get("document_id")
    if not authority_id:
        return JsonResponse({"error": "authority_id is required"}, status=400)

    try:
        authority_id = int(authority_id)
    except ValueError:
        return JsonResponse({"error": "authority_id must be an integer"}, status=400)

    # Verify authority exists
    try:
        authority = StandardsAuthority.objects.get(pk=authority_id)
    except StandardsAuthority.DoesNotExist:
        return JsonResponse({"error": f"Authority not found: {authority_id}"}, status=404)

    document_ids = None
    if document_id:
        try:
            document_ids = [int(document_id)]
        except ValueError:
            return JsonResponse({"error": "document_id must be an integer"}, status=400)

    # Enqueue the job
    job = enqueue_authority_resources_sync(
        authority_id=authority_id,
        document_ids=document_ids,
        created_by=request.user,
    )

    return JsonResponse({
        "job_id": job.pk,
        "status": job.status,
        "authority_id": authority_id,
        "authority_name": authority.name,
        "message": f"Resources sync queued for {authority.name}",
    })


@login_required
def standards_api_job_status(request, job_id):
    """
    API endpoint: Check job progress and status.

    GET parameters:
    - job_id: ID of the BackgroundJob (in URL)
    """
    try:
        job = BackgroundJob.objects.get(pk=job_id)
    except BackgroundJob.DoesNotExist:
        return JsonResponse({"error": f"Job not found: {job_id}"}, status=404)

    return JsonResponse({
        "job_id": job.pk,
        "job_type": job.job_type,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "progress_message": job.progress_message,
        "result": job.result if job.status == "completed" else None,
        "error_message": job.error_message if job.status == "failed" else None,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    })


@login_required
@teacher_required
@require_POST
def standards_api_import_resources(request):
    """
    Import resources from an external JSON payload (e.g., OpenRouter output).

    Expected payload: list of course objects with course_code/syllabus_code and arrays:
    syllabi, past_papers, endorsed_resources (see prompt schema).
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(payload, list):
        return JsonResponse({"error": "Payload must be a list of courses"}, status=400)

    results = _import_resources_payload(payload)
    return JsonResponse(results)


def _import_resources_payload(payload: list[dict]) -> dict:
    results = {"processed": 0, "errors": []}

    for course in payload:
        code = course.get("course_code") or course.get("syllabus_code")
        name = course.get("course_name", "")
        doc = None
        if code:
            doc = StandardsDocument.objects.filter(syllabus_code=code).first()
        if not doc and name:
            doc = StandardsDocument.objects.filter(source_title__icontains=name).first()
        if not doc:
            results["errors"].append(f"No document found for {code or name}")
            continue

        # Import syllabi/past papers as artifacts
        for item in course.get("syllabi", []):
            _download_artifact({"url": item.get("url"), "text": item.get("title")}, doc, "syllabus")
        for item in course.get("past_papers", []):
            _download_artifact({"url": item.get("url"), "text": item.get("title")}, doc, "past_paper")

        # Import endorsed resources as AuthorityProgramMedia
        for res in course.get("endorsed_resources", []):
            try:
                AuthorityProgramMedia.objects.update_or_create(
                    authority_program=doc.authority_program,
                    source_url=res.get("url") or "",
                    defaults={
                        "title": res.get("title", "")[:500],
                        "author": ", ".join(res.get("authors", []))[:500],
                        "publisher": (res.get("publisher") or "")[:255],
                        "isbn_10": (res.get("isbn_10") or "")[:10],
                        "isbn_13": (res.get("isbn_13") or "")[:13],
                        "cover_image_url": res.get("cover_image_url") or "",
                        "media_type": "book",
                        "platform": "publisher",
                        "recommendation_tier": "official",
                        "resource_category": res.get("resource_category") or "endorsed",
                        "audience": res.get("audience") or "general",
                        "is_companion": bool(res.get("is_companion", False)),
                        "description": res.get("notes", "")[:500],
                        "endorsement_notes": res.get("notes", "")[:500],
                        "features": {
                            "syllabus_code": doc.syllabus_code,
                            "course_title": doc.source_title,
                        },
                    },
                )
            except Exception as e:
                results["errors"].append(f"{code}: resource import failed for {res.get('title')}: {e}")

        results["processed"] += 1

    return results


# =============================================================================
# Unified Tab Data API (Provider Tab Configuration)
# =============================================================================

@login_required
def standards_api_tab_config(request):
    """
    Get tab configuration for an authority/program.

    Query params:
    - authority_code: Authority code (e.g., CAMBRIDGE)
    - program_code: Optional program code for program-specific overrides
    """
    from core.models import ProviderTabConfig

    authority_code = request.GET.get("authority_code", "")
    program_code = request.GET.get("program_code", "")

    if not authority_code:
        return JsonResponse({"error": "authority_code is required"}, status=400)

    authority = StandardsAuthority.objects.filter(code=authority_code).first()
    if not authority:
        return JsonResponse({"error": f"Authority not found: {authority_code}"}, status=404)

    program = None
    if program_code:
        program = AuthorityProgram.objects.filter(
            authority=authority,
            code=program_code,
        ).first()

    # Get authority-level configs
    authority_configs = {
        c.tab_id: c
        for c in ProviderTabConfig.objects.filter(
            authority=authority,
            program__isnull=True,
            is_active=True,
        )
    }

    # Get program-specific configs (override authority)
    if program:
        program_configs = {
            c.tab_id: c
            for c in ProviderTabConfig.objects.filter(
                program=program,
                is_active=True,
            )
        }
        # Merge: program overrides authority
        authority_configs.update(program_configs)

    # If no configs found, return empty (frontend will use defaults)
    if not authority_configs:
        return JsonResponse({"tabs": [], "using_defaults": True})

    # Convert to serializable format
    tabs = sorted(authority_configs.values(), key=lambda c: (c.sort_order, c.tab_id))
    tab_list = [
        {
            "id": c.tab_id,
            "label": c.label,
            "icon": c.icon,
            "fetch_method": c.fetch_method,
            "static_description": c.static_description,
            "static_action_label": c.static_action_label,
            "static_action_url_field": c.static_action_url_field,
        }
        for c in tabs
    ]

    return JsonResponse({"tabs": tab_list, "using_defaults": False})


@login_required
def standards_api_tab_data(request, document_id, tab_id):
    """
    Unified endpoint for fetching tab data.
    Routes to appropriate fetcher based on tab config.

    URL params:
    - document_id: StandardsDocument ID
    - tab_id: Tab identifier (e.g., 'objectives', 'resources', 'syllabus')

    Query params:
    - force_refresh: Set to '1' to bypass cache
    """
    from core.models import TabDataCache, ObjectiveNode
    from core.services.external.ai_fetcher import UnifiedAIFetcher, get_tab_config

    document = get_object_or_404(
        StandardsDocument.objects.select_related("authority_program__authority"),
        pk=document_id,
        is_active=True,
    )

    force_refresh = request.GET.get("force_refresh") == "1"

    # Get tab config (may be None if no database config exists)
    tab_config = get_tab_config(document, tab_id)

    # Check cache first (unless forcing refresh)
    if not force_refresh:
        cache = TabDataCache.objects.filter(
            document=document,
            tab_id=tab_id,
            fetch_status="success",
        ).first()
        if cache and cache.is_fresh():
            return JsonResponse({
                "data": cache.data,
                "cached": True,
                "fetched_at": cache.fetched_at.isoformat(),
            })

    # Determine fetch method
    fetch_method = tab_config.fetch_method if tab_config else "none"

    # Route to appropriate fetcher
    try:
        if fetch_method == "ai_extract":
            fetcher = UnifiedAIFetcher()
            data = fetcher.fetch_tab_data(document, tab_config=tab_config, force_refresh=True)
        elif fetch_method == "objectives":
            data = _fetch_objectives_data(document)
        elif fetch_method == "resources":
            data = _fetch_resources_data(document, tab_id)
        elif fetch_method == "custom" and tab_config and tab_config.custom_handler:
            data = _call_custom_handler(tab_config.custom_handler, document)
        else:
            # Static content or no config - return document-derived data
            data = _get_static_tab_data(document, tab_id, tab_config)

        return JsonResponse({
            "data": data,
            "cached": False,
            "fetch_method": fetch_method,
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "fetch_method": fetch_method,
        }, status=500)


def _fetch_objectives_data(document) -> dict:
    """Fetch objectives tree for a document."""
    from core.models import ObjectiveNode

    def build_tree(parent=None):
        nodes = ObjectiveNode.objects.filter(
            document=document,
            parent=parent,
        ).order_by("sort_order")

        return [
            {
                "id": n.pk,
                "code": n.code,
                "text": n.text,
                "node_type": n.node_type,
                "children": build_tree(n),
            }
            for n in nodes
        ]

    objectives = build_tree(None)
    return {
        "objectives": objectives,
        "count": ObjectiveNode.objects.filter(document=document).count(),
    }


def _fetch_resources_data(document, tab_id: str = "official_resources") -> dict:
    """Fetch resources for a document's program."""
    queryset = AuthorityProgramMedia.objects.filter(
        authority_program=document.authority_program,
    )

    # Filter by official vs unofficial based on tab
    if tab_id == "official_resources":
        # Official = recommendation_tier is 'official' OR resource_category is 'official'
        queryset = queryset.filter(
            Q(recommendation_tier="official") | Q(resource_category="official")
        )
    elif tab_id == "unofficial_resources":
        # Unofficial = everything that's not official
        queryset = queryset.exclude(
            Q(recommendation_tier="official") & Q(resource_category="official")
        )

    resources = queryset.order_by("recommendation_tier", "title")

    # Group by category
    grouped = {}
    for r in resources:
        cat = r.resource_category or "other"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "id": r.pk,
            "title": r.title,
            "author": r.author,
            "publisher": r.publisher,
            "source_url": r.source_url,
            "cover_image_url": r.cover_image_url,
            "media_type": r.media_type,
            "recommendation_tier": r.recommendation_tier,
            "audience": r.audience,
            "is_companion": r.is_companion,
        })

    return {
        "resources": grouped,
        "count": resources.count(),
    }


def _get_static_tab_data(document, tab_id: str, tab_config) -> dict:
    """Get static data derived from document fields."""
    data = {
        "course_name": document.source_title,
        "syllabus_code": document.syllabus_code,
        "source_url": document.source_url,
        "description": document.description,
        "subject": document.subject,
        "grade_level": document.grade_level,
        "version": document.version_label,
        "authority": document.authority_program.authority.name,
        "program": document.authority_program.name,
    }

    # Add static config content if available
    if tab_config:
        data["static_description"] = tab_config.static_description
        data["static_action_label"] = tab_config.static_action_label
        if tab_config.static_action_url_field:
            data["action_url"] = getattr(document, tab_config.static_action_url_field, "")

    return data


def _call_custom_handler(handler_path: str, document):
    """
    Call a custom handler function by dotted path.

    Handler should be a function that takes a document and returns a dict.
    Example: 'core.services.external.cambridge.fetch_cambridge_assets'
    """
    import importlib

    try:
        module_path, func_name = handler_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        handler = getattr(module, func_name)
        return handler(document)
    except Exception as e:
        raise ValueError(f"Failed to call custom handler '{handler_path}': {e}")
