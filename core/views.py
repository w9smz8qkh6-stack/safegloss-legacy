from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count
from django.utils import timezone
from functools import wraps

from .forms import (
    LessonFilterForm, StoryForm, StorySegmentFormSet, GlossaryForm, TermForm,
    LessonForm, QuizForm, ItemBankQuestionForm, ItemBankChoiceFormSet, RosterForm
)
from .models import (
    Lesson, LessonProgress, RosterMembership, Term, GlossClickLog,
    Story, StorySegment, Glossary, Quiz, ItemBankQuestion, Roster, Site
)


def instructor_required(view_func):
    """Decorator to check if user is instructor or researcher."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("account_login")
        if not (user.is_instructor() or user.is_researcher()):
            return redirect("core:student_lessons")
        return view_func(request, *args, **kwargs)
    return wrapper


def home_redirect(request):
    if request.user.is_authenticated:
        if getattr(request.user, "role", "") in ("instructor", "researcher"):
            return redirect("core:instructor_dashboard")
        return redirect("core:student_lessons")
    return render(request, "core/home.html")


# =============================================================================
# STUDENT VIEWS
# =============================================================================

@login_required
def student_lessons(request):
    user = request.user
    if hasattr(user, "is_student") and not user.is_student():
        return redirect("core:instructor_dashboard")

    roster_ids = RosterMembership.objects.filter(student=user).values_list("roster_id", flat=True)
    lessons = (
        Lesson.objects.filter(rosters__in=roster_ids, is_active=True)
        .select_related("story", "site")
        .distinct()
    )

    form = LessonFilterForm(request.GET or None)
    if form.is_valid():
        search = form.cleaned_data.get("search") or ""
        if search:
            lessons = lessons.filter(title__icontains=search)

    progress_map = {
        lp.lesson_id: lp for lp in LessonProgress.objects.filter(student=user, lesson__in=lessons)
    }

    context = {
        "lessons": lessons,
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

    # Check access for students
    if hasattr(user, "is_student") and user.is_student():
        roster_ids = lesson.rosters.values_list("id", flat=True)
        if not RosterMembership.objects.filter(student=user, roster_id__in=roster_ids).exists():
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

    # Check access for students
    if hasattr(user, "is_student") and user.is_student():
        roster_ids = lesson.rosters.values_list("id", flat=True)
        if not RosterMembership.objects.filter(student=user, roster_id__in=roster_ids).exists():
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
    """Quiz view for a lesson."""
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

    context = {
        "lesson": lesson,
        "quiz": quiz,
        "questions": questions,
    }
    return render(request, "core/student/lesson_quiz.html", context)


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


# =============================================================================
# INSTRUCTOR DASHBOARD
# =============================================================================

@login_required
@instructor_required
def instructor_dashboard(request):
    user = request.user

    story_count = Story.objects.filter(instructor=user).count()
    lesson_count = Lesson.objects.filter(instructor=user).count()
    quiz_count = Quiz.objects.filter(owner=user).count()
    roster_count = Roster.objects.filter(site=user.site).count() if user.site else 0

    recent_stories = Story.objects.filter(instructor=user).order_by("-created_at")[:5]
    active_lessons = (
        Lesson.objects.filter(instructor=user)
        .select_related("story", "site")
        .prefetch_related("rosters")
        .order_by("-created_at")[:5]
    )

    context = {
        "story_count": story_count,
        "lesson_count": lesson_count,
        "quiz_count": quiz_count,
        "roster_count": roster_count,
        "recent_stories": recent_stories,
        "active_lessons": active_lessons,
    }
    return render(request, "core/instructor_dashboard.html", context)


# =============================================================================
# STORY VIEWS
# =============================================================================

@login_required
@instructor_required
def story_list(request):
    stories = (
        Story.objects.filter(instructor=request.user)
        .annotate(segment_count=Count("segments"))
        .order_by("-created_at")
    )
    return render(request, "core/instructor/story_list.html", {"stories": stories})


@login_required
@instructor_required
def story_create(request):
    if request.method == "POST":
        form = StoryForm(request.POST)
        if form.is_valid():
            story = form.save(commit=False)
            story.instructor = request.user
            story.save()
            messages.success(request, f"Story '{story.title}' created successfully.")
            return redirect("core:story_edit", pk=story.pk)
    else:
        form = StoryForm()

    return render(request, "core/instructor/story_form.html", {
        "form": form,
        "title": "Create Story",
    })


@login_required
@instructor_required
def story_edit(request, pk):
    story = get_object_or_404(Story, pk=pk, instructor=request.user)
    tab = request.GET.get("tab", "details")

    if request.method == "POST":
        if tab == "details":
            form = StoryForm(request.POST, instance=story)
            if form.is_valid():
                form.save()
                messages.success(request, "Story details updated.")
                return redirect(f"{request.path}?tab=details")
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

    context = {
        "story": story,
        "form": form,
        "formset": formset,
        "glossary": glossary,
        "terms": terms,
        "tab": tab,
        "title": f"Edit Story: {story.title}",
    }
    return render(request, "core/instructor/story_edit.html", context)


@login_required
@instructor_required
def story_delete(request, pk):
    story = get_object_or_404(Story, pk=pk, instructor=request.user)
    if request.method == "POST":
        title = story.title
        story.delete()
        messages.success(request, f"Story '{title}' deleted.")
        return redirect("core:story_list")
    return render(request, "core/instructor/story_confirm_delete.html", {"story": story})


# =============================================================================
# LESSON VIEWS
# =============================================================================

@login_required
@instructor_required
def instructor_lesson_list(request):
    lessons = (
        Lesson.objects.filter(instructor=request.user)
        .select_related("story", "site", "quiz")
        .prefetch_related("rosters")
        .order_by("-created_at")
    )
    return render(request, "core/instructor/lesson_list.html", {"lessons": lessons})


@login_required
@instructor_required
def lesson_create(request):
    if request.method == "POST":
        form = LessonForm(request.POST, user=request.user)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.instructor = request.user
            lesson.save()
            form.save_m2m()
            messages.success(request, f"Lesson '{lesson.title}' created successfully.")
            return redirect("core:lesson_edit", pk=lesson.pk)
    else:
        form = LessonForm(user=request.user)

    return render(request, "core/instructor/lesson_form.html", {
        "form": form,
        "title": "Create Lesson",
    })


@login_required
@instructor_required
def lesson_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, instructor=request.user)

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Lesson updated successfully.")
            return redirect("core:lesson_edit", pk=pk)
    else:
        form = LessonForm(instance=lesson, user=request.user)

    return render(request, "core/instructor/lesson_form.html", {
        "form": form,
        "lesson": lesson,
        "title": f"Edit Lesson: {lesson.title}",
    })


@login_required
@instructor_required
def lesson_delete(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, instructor=request.user)
    if request.method == "POST":
        title = lesson.title
        lesson.delete()
        messages.success(request, f"Lesson '{title}' deleted.")
        return redirect("core:instructor_lesson_list")
    return render(request, "core/instructor/lesson_confirm_delete.html", {"lesson": lesson})


# =============================================================================
# QUIZ VIEWS
# =============================================================================

@login_required
@instructor_required
def quiz_list(request):
    quizzes = (
        Quiz.objects.filter(owner=request.user)
        .annotate(question_count=Count("quiz_questions"))
        .order_by("-created_at")
    )
    return render(request, "core/instructor/quiz_list.html", {"quizzes": quizzes})


@login_required
@instructor_required
def quiz_create(request):
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.owner = request.user
            quiz.save()
            messages.success(request, f"Quiz '{quiz.title}' created successfully.")
            return redirect("core:quiz_edit", pk=quiz.pk)
    else:
        form = QuizForm()

    return render(request, "core/instructor/quiz_form.html", {
        "form": form,
        "title": "Create Quiz",
    })


@login_required
@instructor_required
def quiz_edit(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    questions = quiz.quiz_questions.select_related("question").order_by("order")

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz updated successfully.")
            return redirect("core:quiz_edit", pk=pk)
    else:
        form = QuizForm(instance=quiz)

    return render(request, "core/instructor/quiz_edit.html", {
        "form": form,
        "quiz": quiz,
        "questions": questions,
        "title": f"Edit Quiz: {quiz.title}",
    })


@login_required
@instructor_required
def quiz_delete(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    if request.method == "POST":
        title = quiz.title
        quiz.delete()
        messages.success(request, f"Quiz '{title}' deleted.")
        return redirect("core:quiz_list")
    return render(request, "core/instructor/quiz_confirm_delete.html", {"quiz": quiz})


# =============================================================================
# ROSTER VIEWS
# =============================================================================

@login_required
@instructor_required
def roster_list(request):
    user = request.user
    if user.site:
        rosters = Roster.objects.filter(site=user.site).annotate(
            student_count=Count("memberships")
        ).order_by("-created_at")
    else:
        rosters = Roster.objects.none()

    return render(request, "core/instructor/roster_list.html", {"rosters": rosters})


@login_required
@instructor_required
def roster_create(request):
    if request.method == "POST":
        form = RosterForm(request.POST)
        if form.is_valid():
            roster = form.save()
            messages.success(request, f"Roster '{roster.name}' created successfully.")
            return redirect("core:roster_list")
    else:
        initial = {}
        if request.user.site:
            initial["site"] = request.user.site
        form = RosterForm(initial=initial)

    return render(request, "core/instructor/roster_form.html", {
        "form": form,
        "title": "Create Roster",
    })


@login_required
@instructor_required
def roster_edit(request, pk):
    roster = get_object_or_404(Roster, pk=pk)

    if request.method == "POST":
        form = RosterForm(request.POST, instance=roster)
        if form.is_valid():
            form.save()
            messages.success(request, "Roster updated successfully.")
            return redirect("core:roster_list")
    else:
        form = RosterForm(instance=roster)

    memberships = roster.memberships.select_related("student").order_by("student__username")

    return render(request, "core/instructor/roster_form.html", {
        "form": form,
        "roster": roster,
        "memberships": memberships,
        "title": f"Edit Roster: {roster.name}",
    })


# =============================================================================
# GLOSSARY / TERM VIEWS
# =============================================================================

@login_required
@instructor_required
def term_create(request, story_pk):
    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)
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

    return render(request, "core/instructor/term_form.html", {
        "form": form,
        "story": story,
        "title": "Add Term",
    })


@login_required
@instructor_required
def term_edit(request, story_pk, term_pk):
    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)
    term = get_object_or_404(Term, pk=term_pk, glossary__story=story)

    if request.method == "POST":
        form = TermForm(request.POST, instance=term)
        if form.is_valid():
            form.save()
            messages.success(request, f"Term '{term.term_text}' updated.")
            return redirect("core:story_edit", pk=story.pk)
    else:
        form = TermForm(instance=term)

    return render(request, "core/instructor/term_form.html", {
        "form": form,
        "story": story,
        "term": term,
        "title": f"Edit Term: {term.term_text}",
    })


@login_required
@instructor_required
def term_delete(request, story_pk, term_pk):
    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)
    term = get_object_or_404(Term, pk=term_pk, glossary__story=story)

    if request.method == "POST":
        term_text = term.term_text
        term.delete()
        messages.success(request, f"Term '{term_text}' deleted.")
        return redirect("core:story_edit", pk=story.pk)

    return render(request, "core/instructor/term_confirm_delete.html", {
        "term": term,
        "story": story,
    })
