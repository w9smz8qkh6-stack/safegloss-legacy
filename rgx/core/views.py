from django.contrib import messages
from django.contrib.auth.decorators import login_required
import csv
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count
from django.utils import timezone
from functools import wraps

from .forms import (
    LessonFilterForm, StoryForm, StorySegmentFormSet, GlossaryForm, TermForm,
    LessonForm, QuizForm, ItemBankQuestionForm, ItemBankChoiceFormSet, RosterForm,
    JoinRosterForm
)
from django.db.models import Avg, Sum, F
from .models import (
    Lesson, LessonProgress, RosterMembership, Term, GlossClickLog, User, ReadingEvent,
    Story, StorySegment, Glossary, Quiz, QuizQuestion, QuizSubmission, QuizSubmissionAnswer,
    ItemBankQuestion, ItemBankChoice, Roster, Site, SegmentViewLog
)
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .utils import markup_glossary_terms, get_story_terms


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
    return redirect("account_login")


def offline(request):
    """Offline page for PWA."""
    return render(request, "core/offline.html")


# =============================================================================
# STUDENT VIEWS
# =============================================================================

@login_required
def join_roster(request):
    """Allow students to join a roster via invite code."""
    if request.method == "POST":
        form = JoinRosterForm(request.POST)
        if form.is_valid():
            roster = form.roster
            # Check if already a member
            if RosterMembership.objects.filter(roster=roster, student=request.user).exists():
                messages.info(request, f"You're already a member of {roster.name}.")
            else:
                RosterMembership.objects.create(roster=roster, student=request.user)
                # Associate user with roster's site if not already
                if not request.user.site:
                    request.user.site = roster.site
                    request.user.save()
                messages.success(request, f"You've joined {roster.name}!")
            return redirect("core:student_lessons")
    else:
        form = JoinRosterForm()

    return render(request, "core/join_roster.html", {"form": form})

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

    # Attach progress to each lesson for template access
    lessons = list(lessons)
    for lesson in lessons:
        lesson.progress = progress_map.get(lesson.pk)

    context = {
        "lessons": lessons,
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
    segments = list(story.segments.order_by("index"))

    # Get glossary terms and process HTML
    terms = get_story_terms(story)
    processed_story_html = markup_glossary_terms(story.text_html or "", terms)

    # Process segment HTML for card mode
    processed_segments = []
    for segment in segments:
        processed_segments.append({
            "index": segment.index,
            "title": segment.title,
            "text_html": markup_glossary_terms(segment.text_html or "", terms),
        })

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
        "story_html": processed_story_html,
        "segments": processed_segments,
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

    if request.method == "POST":
        # Create submission
        submission = QuizSubmission.objects.create(
            student=user,
            quiz=quiz,
            submitted_at=timezone.now(),
        )

        raw_score = 0
        max_score = 0

        for qq in questions:
            question = qq.question
            points = qq.points or question.default_points or 1.0
            max_score += points

            # Get submitted answer
            answer_key = f"q_{question.pk}"
            selected_ids = request.POST.getlist(answer_key)

            is_correct = None
            if question.question_type in ("mcq_single", "true_false"):
                # Single choice - check if selected choice is correct
                if selected_ids:
                    try:
                        choice = ItemBankChoice.objects.get(pk=selected_ids[0])
                        is_correct = choice.is_correct
                        if is_correct:
                            raw_score += points
                    except ItemBankChoice.DoesNotExist:
                        pass
            elif question.question_type == "mcq_multi":
                # Multiple choice - all correct choices must be selected, no incorrect ones
                correct_ids = set(
                    question.choices.filter(is_correct=True).values_list("pk", flat=True)
                )
                selected_set = set(int(x) for x in selected_ids if x.isdigit())
                is_correct = correct_ids == selected_set
                if is_correct:
                    raw_score += points

            QuizSubmissionAnswer.objects.create(
                submission=submission,
                question=question,
                question_type=question.question_type,
                selected_choice_ids=[int(x) for x in selected_ids if x.isdigit()],
                short_answer_text=request.POST.get(answer_key, "") if question.question_type == "short_answer" else "",
                long_answer_text=request.POST.get(answer_key, "") if question.question_type == "long_answer" else "",
                is_correct=is_correct,
            )

        # Update submission scores
        submission.raw_score = raw_score
        submission.max_score = max_score
        submission.save()

        # Update lesson progress
        progress = LessonProgress.objects.filter(student=user, lesson=lesson).first()
        if progress:
            progress.quiz_end = timezone.now()
            if max_score > 0:
                progress.comprehension_score = (raw_score / max_score) * 100
            progress.save()

        return redirect("core:quiz_results", pk=lesson.pk, submission_id=submission.pk)

    context = {
        "lesson": lesson,
        "quiz": quiz,
        "questions": questions,
    }
    return render(request, "core/student/lesson_quiz.html", context)


@login_required
def quiz_results(request, pk, submission_id):
    """Display quiz results after submission."""
    user = request.user
    lesson = get_object_or_404(Lesson.objects.select_related("quiz"), pk=pk)
    submission = get_object_or_404(
        QuizSubmission.objects.select_related("quiz"),
        pk=submission_id,
        student=user,
        quiz=lesson.quiz,
    )

    # Get answers with question details
    answers = submission.answers.select_related("question").prefetch_related(
        "question__choices"
    ).all()

    # Build results data
    results = []
    for answer in answers:
        question = answer.question
        selected_ids = set(answer.selected_choice_ids)
        choices_data = []

        for choice in question.choices.all():
            choices_data.append({
                "text": choice.text_html,
                "is_correct": choice.is_correct,
                "was_selected": choice.pk in selected_ids,
            })

        results.append({
            "question": question,
            "answer": answer,
            "choices": choices_data,
        })

    percentage = 0
    if submission.max_score and submission.max_score > 0:
        percentage = (submission.raw_score / submission.max_score) * 100

    context = {
        "lesson": lesson,
        "submission": submission,
        "results": results,
        "percentage": percentage,
    }
    return render(request, "core/student/quiz_results.html", context)


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


@login_required
@instructor_required
def quiz_add_question(request, pk):
    """Add a question to a quiz - either from item bank or create new."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    # Get existing questions in this quiz to exclude from selection
    existing_question_ids = quiz.quiz_questions.values_list("question_id", flat=True)

    # Get available questions from item bank
    available_questions = ItemBankQuestion.objects.filter(
        owner=request.user
    ).exclude(pk__in=existing_question_ids).order_by("-created_at")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_existing":
            # Add existing question from item bank
            question_id = request.POST.get("question_id")
            if question_id:
                question = get_object_or_404(ItemBankQuestion, pk=question_id, owner=request.user)
                max_order = quiz.quiz_questions.count()
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question=question,
                    order=max_order,
                )
                messages.success(request, "Question added to quiz.")
                return redirect("core:quiz_edit", pk=pk)

        elif action == "create_new":
            # Create new question and add to quiz
            question_form = ItemBankQuestionForm(request.POST)
            choice_formset = ItemBankChoiceFormSet(request.POST)

            if question_form.is_valid() and choice_formset.is_valid():
                question = question_form.save(commit=False)
                question.owner = request.user
                question.save()

                choice_formset.instance = question
                choice_formset.save()

                max_order = quiz.quiz_questions.count()
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question=question,
                    order=max_order,
                )
                messages.success(request, "New question created and added to quiz.")
                return redirect("core:quiz_edit", pk=pk)
        else:
            question_form = ItemBankQuestionForm()
            choice_formset = ItemBankChoiceFormSet()
    else:
        question_form = ItemBankQuestionForm()
        choice_formset = ItemBankChoiceFormSet()

    return render(request, "core/instructor/quiz_add_question.html", {
        "quiz": quiz,
        "available_questions": available_questions,
        "question_form": question_form,
        "choice_formset": choice_formset,
        "title": f"Add Question to {quiz.title}",
    })


@login_required
@instructor_required
def quiz_remove_question(request, pk, qq_pk):
    """Remove a question from a quiz."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)
    quiz_question = get_object_or_404(QuizQuestion, pk=qq_pk, quiz=quiz)

    if request.method == "POST":
        quiz_question.delete()
        # Reorder remaining questions
        for i, qq in enumerate(quiz.quiz_questions.order_by("order")):
            qq.order = i
            qq.save()
        messages.success(request, "Question removed from quiz.")
        return redirect("core:quiz_edit", pk=pk)

    return render(request, "core/instructor/quiz_remove_question.html", {
        "quiz": quiz,
        "quiz_question": quiz_question,
    })


@login_required
@instructor_required
def quiz_reorder_questions(request, pk):
    """Reorder questions in a quiz via AJAX."""
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    if request.method == "POST":
        import json
        try:
            data = json.loads(request.body)
            order_list = data.get("order", [])
            for i, qq_id in enumerate(order_list):
                QuizQuestion.objects.filter(pk=qq_id, quiz=quiz).update(order=i)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "POST required"})


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


@login_required
@instructor_required
def roster_add_student(request, pk):
    """Add a student to a roster."""
    roster = get_object_or_404(Roster, pk=pk, site=request.user.site)

    # Get students at the same site who aren't already in this roster
    existing_student_ids = roster.memberships.values_list("student_id", flat=True)
    available_students = User.objects.filter(
        site=roster.site,
        role=User.ROLE_STUDENT
    ).exclude(pk__in=existing_student_ids).order_by("username")

    if request.method == "POST":
        student_ids = request.POST.getlist("student_ids")
        added_count = 0
        for student_id in student_ids:
            student = User.objects.filter(
                pk=student_id,
                site=roster.site,
                role=User.ROLE_STUDENT
            ).first()
            if student:
                RosterMembership.objects.get_or_create(roster=roster, student=student)
                added_count += 1

        if added_count:
            messages.success(request, f"Added {added_count} student(s) to the roster.")
        return redirect("core:roster_edit", pk=pk)

    return render(request, "core/instructor/roster_add_student.html", {
        "roster": roster,
        "available_students": available_students,
        "title": f"Add Students to {roster.name}",
    })


@login_required
@instructor_required
def roster_remove_student(request, pk, membership_pk):
    """Remove a student from a roster."""
    roster = get_object_or_404(Roster, pk=pk, site=request.user.site)
    membership = get_object_or_404(RosterMembership, pk=membership_pk, roster=roster)

    if request.method == "POST":
        student_name = membership.student.username
        membership.delete()
        messages.success(request, f"Removed {student_name} from the roster.")
        return redirect("core:roster_edit", pk=pk)

    return render(request, "core/instructor/roster_remove_student.html", {
        "roster": roster,
        "membership": membership,
    })


# =============================================================================
# DATA EXPORT VIEWS
# =============================================================================

@login_required
@instructor_required
def export_quiz_results(request, pk):
    """Export quiz results for a lesson as CSV."""
    lesson = get_object_or_404(Lesson, pk=pk)

    # Get all submissions for this lesson's quiz
    submissions = QuizSubmission.objects.filter(
        lesson=lesson
    ).select_related("student").order_by("-submitted_at")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="quiz_results_{lesson.pk}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Student Username",
        "Student Email",
        "Raw Score",
        "Max Score",
        "Percentage",
        "Submitted At",
    ])

    for sub in submissions:
        percentage = (sub.raw_score / sub.max_score * 100) if sub.max_score else 0
        writer.writerow([
            sub.student.username,
            sub.student.email,
            sub.raw_score,
            sub.max_score,
            f"{percentage:.1f}%",
            sub.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if sub.submitted_at else "",
        ])

    return response


@login_required
@instructor_required
def export_roster_progress(request, pk):
    """Export student progress for a roster as CSV."""
    roster = get_object_or_404(Roster, pk=pk, site=request.user.site)

    # Get all students in the roster
    memberships = roster.memberships.select_related("student").order_by("student__username")
    student_ids = [m.student_id for m in memberships]

    # Get all lessons assigned to this roster
    lessons = Lesson.objects.filter(rosters=roster, is_active=True).order_by("title")

    # Get progress records for all students
    progress_records = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons
    ).select_related("student", "lesson")

    # Build a lookup dict
    progress_lookup = {}
    for p in progress_records:
        key = (p.student_id, p.lesson_id)
        progress_lookup[key] = p

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="roster_progress_{roster.pk}.csv"'

    writer = csv.writer(response)

    # Header row
    header = ["Student Username", "Student Email"]
    for lesson in lessons:
        header.extend([
            f"{lesson.title[:30]} - Status",
            f"{lesson.title[:30]} - Score",
        ])
    writer.writerow(header)

    # Data rows
    for membership in memberships:
        student = membership.student
        row = [student.username, student.email]

        for lesson in lessons:
            progress = progress_lookup.get((student.pk, lesson.pk))
            if progress:
                if progress.quiz_end:
                    status = "Completed"
                elif progress.reading_end:
                    status = "Reading Done"
                elif progress.reading_start:
                    status = "In Progress"
                else:
                    status = "Not Started"
                score = f"{progress.comprehension_score:.0f}%" if progress.comprehension_score else ""
            else:
                status = "Not Started"
                score = ""

            row.extend([status, score])

        writer.writerow(row)

    return response


@login_required
@instructor_required
def export_lesson_progress(request, pk):
    """Export all student progress for a specific lesson as CSV."""
    lesson = get_object_or_404(Lesson, pk=pk)

    # Get all progress records for this lesson
    progress_records = LessonProgress.objects.filter(
        lesson=lesson
    ).select_related("student").order_by("student__username")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="lesson_progress_{lesson.pk}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Student Username",
        "Student Email",
        "Status",
        "Reading Started",
        "Reading Ended",
        "Reading Duration (min)",
        "Quiz Started",
        "Quiz Ended",
        "Quiz Score",
    ])

    for progress in progress_records:
        # Determine status
        if progress.quiz_end:
            status = "Completed"
        elif progress.reading_end:
            status = "Reading Done"
        elif progress.reading_start:
            status = "In Progress"
        else:
            status = "Not Started"

        # Calculate reading duration
        duration = ""
        if progress.reading_duration_seconds:
            duration = f"{progress.reading_duration_seconds / 60:.1f}"

        writer.writerow([
            progress.student.username,
            progress.student.email,
            status,
            progress.reading_start.strftime("%Y-%m-%d %H:%M:%S") if progress.reading_start else "",
            progress.reading_end.strftime("%Y-%m-%d %H:%M:%S") if progress.reading_end else "",
            duration,
            progress.quiz_start.strftime("%Y-%m-%d %H:%M:%S") if progress.quiz_start else "",
            progress.quiz_end.strftime("%Y-%m-%d %H:%M:%S") if progress.quiz_end else "",
            f"{progress.comprehension_score:.0f}%" if progress.comprehension_score else "",
        ])

    return response


# =============================================================================
# ROSTER ANALYTICS VIEWS
# =============================================================================

@login_required
@instructor_required
def roster_analytics(request, pk):
    """Roster analytics dashboard showing student progress and behavior."""
    roster = get_object_or_404(Roster, pk=pk, site=request.user.site)

    # Get all students in the roster
    memberships = roster.memberships.select_related("student").order_by("student__username")
    student_ids = [m.student_id for m in memberships]
    students = [m.student for m in memberships]

    # Get all lessons assigned to this roster
    lessons = list(Lesson.objects.filter(rosters=roster, is_active=True).order_by("title"))

    # Get progress records for all students
    progress_records = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons
    ).select_related("student", "lesson")

    # Build lookup dict
    progress_lookup = {}
    for p in progress_records:
        progress_lookup[(p.student_id, p.lesson_id)] = p

    # Calculate overall stats
    total_assignments = len(students) * len(lessons)
    completed_count = sum(1 for p in progress_records if p.quiz_end or (p.reading_end and not p.lesson.quiz_id))
    in_progress_count = sum(1 for p in progress_records if p.reading_start and not p.quiz_end and not (p.reading_end and not p.lesson.quiz_id))

    # Average quiz score
    scores = [p.comprehension_score for p in progress_records if p.comprehension_score is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Average reading time (in minutes)
    reading_times = [p.reading_duration_seconds / 60 for p in progress_records if p.reading_duration_seconds]
    avg_reading_time = sum(reading_times) / len(reading_times) if reading_times else None

    # Glossary engagement
    gloss_clicks = GlossClickLog.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons
    ).count()

    # Per-lesson stats
    lesson_stats = []
    for lesson in lessons:
        lesson_progress = [p for p in progress_records if p.lesson_id == lesson.pk]
        completed = sum(1 for p in lesson_progress if p.quiz_end or (p.reading_end and not lesson.quiz_id))
        lesson_scores = [p.comprehension_score for p in lesson_progress if p.comprehension_score is not None]
        lesson_avg = sum(lesson_scores) / len(lesson_scores) if lesson_scores else None

        lesson_stats.append({
            "lesson": lesson,
            "completed": completed,
            "total": len(students),
            "completion_pct": (completed / len(students) * 100) if students else 0,
            "avg_score": lesson_avg,
        })

    # Per-student stats
    student_stats = []
    for student in students:
        student_progress = [p for key, p in progress_lookup.items() if key[0] == student.pk]
        completed = sum(1 for p in student_progress if p.quiz_end or (p.reading_end and not p.lesson.quiz_id))
        student_scores = [p.comprehension_score for p in student_progress if p.comprehension_score is not None]
        student_avg = sum(student_scores) / len(student_scores) if student_scores else None
        student_reading = [p.reading_duration_seconds / 60 for p in student_progress if p.reading_duration_seconds]
        total_reading = sum(student_reading) if student_reading else 0

        # Glossary clicks for this student
        student_clicks = GlossClickLog.objects.filter(
            student=student,
            lesson__in=lessons
        ).count()

        student_stats.append({
            "student": student,
            "completed": completed,
            "total": len(lessons),
            "completion_pct": (completed / len(lessons) * 100) if lessons else 0,
            "avg_score": student_avg,
            "total_reading_time": total_reading,
            "gloss_clicks": student_clicks,
        })

    # Sort by completion rate descending
    student_stats.sort(key=lambda x: (-x["completion_pct"], -(x["avg_score"] or 0)))

    context = {
        "roster": roster,
        "lessons": lessons,
        "students": students,
        "total_assignments": total_assignments,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
        "not_started_count": total_assignments - completed_count - in_progress_count,
        "completion_pct": (completed_count / total_assignments * 100) if total_assignments else 0,
        "avg_score": avg_score,
        "avg_reading_time": avg_reading_time,
        "total_gloss_clicks": gloss_clicks,
        "lesson_stats": lesson_stats,
        "student_stats": student_stats,
    }
    return render(request, "core/instructor/roster_analytics.html", context)


@login_required
@instructor_required
def student_detail(request, roster_pk, student_pk):
    """Detailed view of a single student's progress in a roster."""
    roster = get_object_or_404(Roster, pk=roster_pk, site=request.user.site)
    student = get_object_or_404(User, pk=student_pk)

    # Verify student is in roster
    if not roster.memberships.filter(student=student).exists():
        messages.error(request, "Student not found in this roster.")
        return redirect("core:roster_analytics", pk=roster_pk)

    # Get lessons assigned to this roster
    lessons = Lesson.objects.filter(rosters=roster, is_active=True).order_by("title")

    # Get progress for this student
    progress_records = LessonProgress.objects.filter(
        student=student,
        lesson__in=lessons
    ).select_related("lesson")

    progress_lookup = {p.lesson_id: p for p in progress_records}

    # Build lesson progress details
    lesson_details = []
    for lesson in lessons:
        progress = progress_lookup.get(lesson.pk)

        # Get quiz submission if exists
        submission = None
        if progress and progress.quiz_end and lesson.quiz_id:
            submission = QuizSubmission.objects.filter(
                student=student,
                lesson=lesson
            ).order_by("-submitted_at").first()

        # Get glossary clicks for this lesson
        gloss_clicks = GlossClickLog.objects.filter(
            student=student,
            lesson=lesson
        ).select_related("term").order_by("-clicked_at")

        # Determine status
        if progress:
            if progress.quiz_end:
                status = "completed"
            elif progress.reading_end:
                status = "reading_done"
            elif progress.reading_start:
                status = "in_progress"
            else:
                status = "not_started"
        else:
            status = "not_started"

        lesson_details.append({
            "lesson": lesson,
            "progress": progress,
            "submission": submission,
            "gloss_clicks": gloss_clicks[:10],  # Latest 10 clicks
            "gloss_click_count": gloss_clicks.count(),
            "status": status,
            "reading_duration": progress.reading_duration_seconds / 60 if progress and progress.reading_duration_seconds else None,
        })

    # Get unique glossary terms clicked across all lessons
    clicked_terms = GlossClickLog.objects.filter(
        student=student,
        lesson__in=lessons
    ).values("term__term_text").annotate(
        click_count=Count("id")
    ).order_by("-click_count")[:20]

    # Overall stats
    completed_count = sum(1 for ld in lesson_details if ld["status"] == "completed")
    scores = [ld["submission"].raw_score / ld["submission"].max_score * 100
              for ld in lesson_details
              if ld["submission"] and ld["submission"].max_score]
    avg_score = sum(scores) / len(scores) if scores else None

    total_reading = sum(ld["reading_duration"] or 0 for ld in lesson_details)
    total_gloss_clicks = sum(ld["gloss_click_count"] for ld in lesson_details)

    context = {
        "roster": roster,
        "student": student,
        "lesson_details": lesson_details,
        "clicked_terms": clicked_terms,
        "completed_count": completed_count,
        "total_lessons": len(lessons),
        "completion_pct": (completed_count / len(lessons) * 100) if lessons else 0,
        "avg_score": avg_score,
        "total_reading_time": total_reading,
        "total_gloss_clicks": total_gloss_clicks,
    }
    return render(request, "core/instructor/student_detail.html", context)


# =============================================================================
# ANALYTICS API VIEWS
# =============================================================================

@login_required
@instructor_required
def roster_analytics_data(request, pk):
    """JSON API for roster analytics charts."""
    from django.db.models.functions import TruncDate
    from collections import defaultdict
    import json

    roster = get_object_or_404(Roster, pk=pk, site=request.user.site)
    student_ids = list(roster.memberships.values_list("student_id", flat=True))
    lessons = Lesson.objects.filter(rosters=roster, is_active=True)

    # Progress over time (completions by date)
    progress_by_date = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons,
        quiz_end__isnull=False
    ).annotate(
        completed_date=TruncDate("quiz_end")
    ).values("completed_date").annotate(
        count=Count("id")
    ).order_by("completed_date")

    # Also include reading completions for lessons without quizzes
    reading_only = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons,
        lesson__quiz__isnull=True,
        reading_end__isnull=False
    ).annotate(
        completed_date=TruncDate("reading_end")
    ).values("completed_date").annotate(
        count=Count("id")
    ).order_by("completed_date")

    # Merge completions by date
    date_counts = defaultdict(int)
    for item in progress_by_date:
        if item["completed_date"]:
            date_counts[item["completed_date"].isoformat()] += item["count"]
    for item in reading_only:
        if item["completed_date"]:
            date_counts[item["completed_date"].isoformat()] += item["count"]

    # Sort and create cumulative data
    sorted_dates = sorted(date_counts.keys())
    cumulative = 0
    completion_timeline = []
    for date in sorted_dates:
        cumulative += date_counts[date]
        completion_timeline.append({"date": date, "completions": cumulative})

    # Score distribution
    scores = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons,
        comprehension_score__isnull=False
    ).values_list("comprehension_score", flat=True)

    score_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for score in scores:
        if score <= 20:
            score_buckets["0-20"] += 1
        elif score <= 40:
            score_buckets["21-40"] += 1
        elif score <= 60:
            score_buckets["41-60"] += 1
        elif score <= 80:
            score_buckets["61-80"] += 1
        else:
            score_buckets["81-100"] += 1

    # Reading time distribution
    reading_times = LessonProgress.objects.filter(
        student_id__in=student_ids,
        lesson__in=lessons,
        reading_duration_seconds__isnull=False
    ).values_list("reading_duration_seconds", flat=True)

    time_buckets = {"0-2min": 0, "2-5min": 0, "5-10min": 0, "10-20min": 0, "20+min": 0}
    for seconds in reading_times:
        minutes = seconds / 60
        if minutes <= 2:
            time_buckets["0-2min"] += 1
        elif minutes <= 5:
            time_buckets["2-5min"] += 1
        elif minutes <= 10:
            time_buckets["5-10min"] += 1
        elif minutes <= 20:
            time_buckets["10-20min"] += 1
        else:
            time_buckets["20+min"] += 1

    return JsonResponse({
        "completion_timeline": completion_timeline,
        "score_distribution": score_buckets,
        "reading_time_distribution": time_buckets,
    })


@login_required
@instructor_required
def roster_comparison(request):
    """Compare multiple rosters side by side."""
    rosters = Roster.objects.filter(site=request.user.site).order_by("name")

    comparison_data = []
    for roster in rosters:
        student_ids = list(roster.memberships.values_list("student_id", flat=True))
        lessons = Lesson.objects.filter(rosters=roster, is_active=True)
        total_assignments = len(student_ids) * lessons.count()

        # Count completions
        completed = LessonProgress.objects.filter(
            student_id__in=student_ids,
            lesson__in=lessons,
            quiz_end__isnull=False
        ).count()

        # Also count reading-only completions
        completed += LessonProgress.objects.filter(
            student_id__in=student_ids,
            lesson__in=lessons,
            lesson__quiz__isnull=True,
            reading_end__isnull=False
        ).count()

        # Average score
        scores = LessonProgress.objects.filter(
            student_id__in=student_ids,
            lesson__in=lessons,
            comprehension_score__isnull=False
        ).values_list("comprehension_score", flat=True)
        avg_score = sum(scores) / len(scores) if scores else None

        # Average reading time
        reading = LessonProgress.objects.filter(
            student_id__in=student_ids,
            lesson__in=lessons,
            reading_duration_seconds__isnull=False
        ).aggregate(avg=Avg("reading_duration_seconds"))
        avg_reading = reading["avg"] / 60 if reading["avg"] else None

        # Glossary engagement
        gloss_clicks = GlossClickLog.objects.filter(
            student_id__in=student_ids,
            lesson__in=lessons
        ).count()
        avg_clicks = gloss_clicks / len(student_ids) if student_ids else 0

        comparison_data.append({
            "roster": roster,
            "student_count": len(student_ids),
            "lesson_count": lessons.count(),
            "total_assignments": total_assignments,
            "completed": completed,
            "completion_pct": (completed / total_assignments * 100) if total_assignments else 0,
            "avg_score": avg_score,
            "avg_reading_time": avg_reading,
            "avg_gloss_clicks": avg_clicks,
        })

    return render(request, "core/instructor/roster_comparison.html", {
        "comparison_data": comparison_data,
    })


@login_required
@instructor_required
def export_full_data(request):
    """Export all research data as a ZIP file with multiple CSVs."""
    import zipfile
    from io import BytesIO

    site = request.user.site

    # Create ZIP file in memory
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Students CSV
        students_csv = BytesIO()
        writer = csv.writer(students_csv)
        writer.writerow(["student_id", "username", "email", "first_name", "last_name", "site"])
        for student in User.objects.filter(site=site, role="student"):
            writer.writerow([student.pk, student.username, student.email, student.first_name, student.last_name, site.name])
        zf.writestr("students.csv", students_csv.getvalue().decode("utf-8"))

        # 2. Rosters CSV
        rosters_csv = BytesIO()
        writer = csv.writer(rosters_csv)
        writer.writerow(["roster_id", "name", "grade_band", "created_at"])
        for roster in Roster.objects.filter(site=site):
            writer.writerow([roster.pk, roster.name, roster.grade_band or "", roster.created_at.isoformat()])
        zf.writestr("rosters.csv", rosters_csv.getvalue().decode("utf-8"))

        # 3. Roster Memberships CSV
        memberships_csv = BytesIO()
        writer = csv.writer(memberships_csv)
        writer.writerow(["roster_id", "student_id", "joined_at"])
        for m in RosterMembership.objects.filter(roster__site=site):
            writer.writerow([m.roster_id, m.student_id, m.joined_at.isoformat()])
        zf.writestr("roster_memberships.csv", memberships_csv.getvalue().decode("utf-8"))

        # 4. Lessons CSV
        lessons_csv = BytesIO()
        writer = csv.writer(lessons_csv)
        writer.writerow(["lesson_id", "title", "story_id", "quiz_id", "is_active", "created_at"])
        for lesson in Lesson.objects.filter(site=site):
            writer.writerow([lesson.pk, lesson.title, lesson.story_id or "", lesson.quiz_id or "", lesson.is_active, lesson.created_at.isoformat()])
        zf.writestr("lessons.csv", lessons_csv.getvalue().decode("utf-8"))

        # 5. Lesson Progress CSV (main data)
        progress_csv = BytesIO()
        writer = csv.writer(progress_csv)
        writer.writerow([
            "progress_id", "student_id", "lesson_id", "reading_start", "reading_end",
            "reading_duration_seconds", "quiz_start", "quiz_end", "comprehension_score"
        ])
        for p in LessonProgress.objects.filter(lesson__site=site).select_related("student", "lesson"):
            writer.writerow([
                p.pk, p.student_id, p.lesson_id,
                p.reading_start.isoformat() if p.reading_start else "",
                p.reading_end.isoformat() if p.reading_end else "",
                p.reading_duration_seconds or "",
                p.quiz_start.isoformat() if p.quiz_start else "",
                p.quiz_end.isoformat() if p.quiz_end else "",
                p.comprehension_score or ""
            ])
        zf.writestr("lesson_progress.csv", progress_csv.getvalue().decode("utf-8"))

        # 6. Quiz Submissions CSV
        submissions_csv = BytesIO()
        writer = csv.writer(submissions_csv)
        writer.writerow(["submission_id", "student_id", "lesson_id", "raw_score", "max_score", "submitted_at"])
        for sub in QuizSubmission.objects.filter(lesson__site=site):
            writer.writerow([sub.pk, sub.student_id, sub.lesson_id, sub.raw_score, sub.max_score, sub.submitted_at.isoformat()])
        zf.writestr("quiz_submissions.csv", submissions_csv.getvalue().decode("utf-8"))

        # 7. Quiz Answers CSV
        answers_csv = BytesIO()
        writer = csv.writer(answers_csv)
        writer.writerow(["submission_id", "question_id", "selected_choice_id", "is_correct"])
        for ans in QuizSubmissionAnswer.objects.filter(submission__lesson__site=site):
            writer.writerow([ans.submission_id, ans.question_id, ans.selected_choice_id, ans.is_correct])
        zf.writestr("quiz_answers.csv", answers_csv.getvalue().decode("utf-8"))

        # 8. Glossary Clicks CSV
        clicks_csv = BytesIO()
        writer = csv.writer(clicks_csv)
        writer.writerow(["click_id", "student_id", "lesson_id", "term_id", "term_text", "clicked_at"])
        for click in GlossClickLog.objects.filter(lesson__site=site).select_related("term"):
            writer.writerow([
                click.pk, click.student_id, click.lesson_id, click.term_id,
                click.term.term_text if click.term else "", click.clicked_at.isoformat()
            ])
        zf.writestr("glossary_clicks.csv", clicks_csv.getvalue().decode("utf-8"))

        # 9. Reading Events CSV (if exists)
        if ReadingEvent._meta.db_table:
            events_csv = BytesIO()
            writer = csv.writer(events_csv)
            writer.writerow(["event_id", "student_id", "lesson_id", "event_type", "segment_index", "timestamp", "data"])
            for event in ReadingEvent.objects.filter(lesson__site=site):
                writer.writerow([
                    event.pk, event.student_id, event.lesson_id, event.event_type,
                    event.segment_index or "", event.timestamp.isoformat(),
                    event.data if hasattr(event, "data") else ""
                ])
            zf.writestr("reading_events.csv", events_csv.getvalue().decode("utf-8"))

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="safegloss_export_{site.name}_{timezone.now().strftime("%Y%m%d")}.zip"'
    return response


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


# =============================================================================
# PWA & API VIEWS
# =============================================================================

def service_worker(request):
    """Serve service worker from root URL for full site scope."""
    from django.conf import settings
    import os

    sw_path = os.path.join(settings.BASE_DIR, "core", "static", "core", "sw.js")
    with open(sw_path, "r") as f:
        sw_content = f.read()

    response = HttpResponse(sw_content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


@login_required
@require_POST
def log_segment_view(request):
    """API endpoint to log segment view data for analytics."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    lesson_id = data.get("lesson_id")
    segment_id = data.get("segment_id")
    segment_index = data.get("segment_index", 0)

    if not lesson_id or not segment_id:
        return JsonResponse({"error": "Missing lesson_id or segment_id"}, status=400)

    # Get or create the segment view log
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    segment = get_object_or_404(StorySegment, pk=segment_id)

    # Check if this is an update to an existing view or a new view
    view_log, created = SegmentViewLog.objects.get_or_create(
        student=request.user,
        lesson=lesson,
        segment=segment,
        segment_index=segment_index,
        view_end__isnull=True,  # Only get incomplete views
        defaults={
            "view_start": timezone.now(),
        }
    )

    # Update the view log with new data
    if data.get("view_end"):
        view_log.view_end = timezone.now()
        if view_log.view_start:
            view_log.duration_seconds = (view_log.view_end - view_log.view_start).total_seconds()

    if "scroll_depth_percent" in data:
        view_log.scroll_depth_percent = max(view_log.scroll_depth_percent, data["scroll_depth_percent"])

    if data.get("revisit"):
        view_log.revisit_count += 1

    if data.get("hesitation"):
        view_log.hesitation_count += 1

    if data.get("gloss_click"):
        view_log.gloss_clicks += 1

    if data.get("copy_event"):
        view_log.copy_events += 1

    view_log.save()

    return JsonResponse({
        "status": "ok",
        "view_log_id": view_log.pk,
        "created": created,
    })


@login_required
def lesson_cache_data(request, pk):
    """Return lesson data as JSON for offline caching."""
    lesson = get_object_or_404(
        Lesson.objects.select_related("story", "story__glossary", "quiz"),
        pk=pk
    )

    # Check access
    if request.user.is_student():
        roster_ids = lesson.rosters.values_list("id", flat=True)
        if not RosterMembership.objects.filter(student=request.user, roster_id__in=roster_ids).exists():
            return JsonResponse({"error": "Access denied"}, status=403)

    story = lesson.story
    segments = list(story.segments.order_by("order").values(
        "id", "order", "title", "text_html"
    ))

    # Get glossary terms
    terms = []
    if hasattr(story, "glossary"):
        terms = list(story.glossary.terms.values(
            "id", "term_text", "definition", "translation", "ipa_pronunciation",
            "difficulty_level", "example_sentence"
        ))

    # Get quiz data if exists
    quiz_data = None
    if lesson.quiz:
        quiz = lesson.quiz
        questions = []
        for qq in quiz.questions.select_related("question").prefetch_related("question__choices"):
            q = qq.question
            choices = list(q.choices.values("id", "text_html", "order"))
            questions.append({
                "id": q.id,
                "prompt_html": q.prompt_html,
                "question_type": q.question_type,
                "choices": choices,
                "points": qq.points_override or q.default_points,
            })
        quiz_data = {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "time_limit_seconds": quiz.time_limit_seconds,
            "questions": questions,
        }

    return JsonResponse({
        "lesson": {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "default_mode": lesson.default_mode,
            "allowed_modes": lesson.allowed_modes,
        },
        "story": {
            "id": story.id,
            "title": story.title,
            "segments": segments,
        },
        "terms": terms,
        "quiz": quiz_data,
        "cached_at": timezone.now().isoformat(),
    })
