from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Max
from django.utils import timezone
from functools import wraps

from django.http import JsonResponse

from .forms import (
    LessonFilterForm, StoryForm, StorySegmentFormSet, GlossaryForm, TermForm,
    LessonForm, QuizForm, ItemBankQuestionForm, ItemBankChoiceFormSet, RosterForm,
    StoryGeneratorForm, QuizGeneratorForm, UnitForm, UnitLessonFormSet, GlossaryGeneratorForm,
    CourseForm, CourseUnitFormSet, RosterAddStudentForm,
    ExternalBookSearchForm, ExternalBookImportForm
)
from .models import (
    Lesson, LessonProgress, RosterMembership, Term, GlossClickLog,
    Story, StorySegment, Glossary, Quiz, QuizQuestion, ItemBankQuestion, ItemBankChoice, Roster, Site,
    Unit, UnitLesson, Course, CourseUnit, ExternalBookmark
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
        if getattr(request.user, "role", "") in ("instructor", "researcher"):
            return redirect("core:instructor_dashboard")
        return redirect("core:student_lessons")
    return render(request, "core/home.html")


@login_required
def login_redirect(request):
    """Redirect users to appropriate dashboard based on role after login."""
    user = request.user
    if user.is_instructor() or user.is_researcher():
        return redirect("core:instructor_dashboard")
    return redirect("core:student_lessons")


# =============================================================================
# STUDENT VIEWS
# =============================================================================

@login_required
def student_lessons(request):
    user = request.user
    if hasattr(user, "is_student") and not user.is_student():
        return redirect("core:instructor_dashboard")

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
    unit_count = Unit.objects.filter(instructor=user).count()
    course_count = Course.objects.filter(instructor=user).count()

    recent_stories = Story.objects.filter(instructor=user).order_by("-created_at")[:5]
    active_lessons = (
        Lesson.objects.filter(instructor=user)
        .select_related("story", "site")
        .prefetch_related("rosters")
        .order_by("-created_at")[:5]
    )
    recent_units = Unit.objects.filter(instructor=user).order_by("-created_at")[:5]
    recent_courses = Course.objects.filter(instructor=user).prefetch_related("rosters").order_by("-created_at")[:5]

    context = {
        "story_count": story_count,
        "lesson_count": lesson_count,
        "quiz_count": quiz_count,
        "roster_count": roster_count,
        "unit_count": unit_count,
        "course_count": course_count,
        "recent_stories": recent_stories,
        "active_lessons": active_lessons,
        "recent_units": recent_units,
        "recent_courses": recent_courses,
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
            # Compute reading levels if text was provided
            if story.text_html:
                story.update_reading_levels()
                story.save(update_fields=["reading_level_label", "reading_level_metrics"])
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


@login_required
@instructor_required
def story_preview(request, pk):
    """
    Preview a story as it would appear to a student.
    Supports switching between reading modes (continuous, cards, movie).
    """
    story = get_object_or_404(Story, pk=pk, instructor=request.user)

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

    return render(request, "core/instructor/story_preview.html", context)


@login_required
@instructor_required
def story_auto_segment(request, pk):
    """
    Auto-segment a story by splitting its HTML content into paragraphs.
    """
    import re
    from django.http import JsonResponse

    story = get_object_or_404(Story, pk=pk, instructor=request.user)

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
@instructor_required
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
    return render(request, "core/instructor/story_generate.html", context)


@login_required
@instructor_required
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
@instructor_required
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
    return render(request, "core/instructor/story_generate_preview.html", context)


@login_required
@instructor_required
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
        instructor=request.user,
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
@instructor_required
def story_export(request, pk):
    """
    Export a story in print-friendly format.

    Supports:
    - Web view (print-friendly HTML)
    - PDF (via browser print)
    """
    story = get_object_or_404(Story, pk=pk, instructor=request.user)

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
    return render(request, "core/instructor/story_export.html", context)


# =============================================================================
# STORY IMPORT VIEWS
# =============================================================================

@login_required
@instructor_required
def story_import_search(request):
    """Main import interface with search form and bookmarks."""
    form = ExternalBookSearchForm(request.GET or None)
    bookmarks = ExternalBookmark.objects.filter(instructor=request.user)[:10]

    return render(request, "core/instructor/story_import.html", {
        "form": form,
        "bookmarks": bookmarks,
        "title": "Import Story from Library",
    })


@login_required
@instructor_required
def story_import_search_results(request):
    """HTMX endpoint: Return search results from external sources."""
    from .services.external_books import GutendexService, OpenLibraryService, OpenTextbookService

    form = ExternalBookSearchForm(request.GET)
    if not form.is_valid():
        return render(request, "core/instructor/partials/import_search_results.html", {
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
        ExternalBookmark.objects.filter(instructor=request.user)
        .values_list("source", "external_id")
    )

    return render(request, "core/instructor/partials/import_search_results.html", {
        "results": results,
        "bookmarked": bookmarked,
        "query": query,
        "page": page,
        "total": total,
    })


@login_required
@instructor_required
def story_import_details(request, source, external_id):
    """HTMX endpoint: Get book details and import options."""
    from .services.external_books import get_service
    import json

    try:
        service = get_service(source)
        book = service.get_book_details(external_id)
    except Exception as e:
        return render(request, "core/instructor/partials/import_book_details.html", {
            "error": f"Failed to load book details: {str(e)}"
        })

    if not book:
        return render(request, "core/instructor/partials/import_book_details.html", {
            "error": "Book not found."
        })

    # Don't fetch full text here - it's too slow
    # We'll show the import form and fetch text only when user clicks Preview
    # For Gutenberg, we know text is available if has_full_text is True
    text_available = book.has_full_text

    import_form = ExternalBookImportForm()

    return render(request, "core/instructor/partials/import_book_details.html", {
        "book": book,
        "chapters": [],  # Will be detected during preview
        "text_available": text_available,
        "word_count": 0,  # Will be shown during preview
        "import_form": import_form,
        "book_json": json.dumps(book.to_dict()),
    })


@login_required
@instructor_required
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

    return render(request, "core/instructor/story_import_preview.html", {
        "preview": request.session["import_preview"],
        "book": book,
        "stats": stats,
        "title": "Preview Import",
    })


@login_required
@instructor_required
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
        instructor=request.user,
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
@instructor_required
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
        instructor=request.user,
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
@instructor_required
def story_import_bookmark_remove(request, pk):
    """Remove a bookmark via HTMX."""
    bookmark = get_object_or_404(ExternalBookmark, pk=pk, instructor=request.user)
    bookmark.delete()

    # Return updated bookmarks list
    bookmarks = ExternalBookmark.objects.filter(instructor=request.user)[:10]
    return render(request, "core/instructor/partials/import_bookmarks_list.html", {
        "bookmarks": bookmarks,
    })


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
    # Check if creating lesson for a specific unit
    unit_id = request.GET.get("unit") or request.POST.get("unit")
    unit = None
    if unit_id:
        unit = Unit.objects.filter(pk=unit_id, instructor=request.user).first()

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

    return render(request, "core/instructor/lesson_form.html", {
        "form": form,
        "title": "Create Lesson",
        "unit": unit,
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
def quiz_generate(request):
    """
    AI-powered quiz generation based on story content.
    Shows form for selecting story and quiz parameters.
    """
    import json

    form = QuizGeneratorForm(request.POST or None, user=request.user)
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

    return render(request, "core/instructor/quiz_generate.html", {
        "form": form,
        "generation_params": generation_params,
        "generation_params_json": generation_params_json,
        "title": "Generate Quiz with AI",
    })


@login_required
@instructor_required
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

    system_prompt = f"""You are an expert educational assessment designer. Generate quiz questions based on the provided reading passage.

Your task:
- Generate exactly {num_questions} questions
- Question types to include: {', '.join(type_instructions)}
- Difficulty level: {difficulty_desc}
- Focus area: {focus_desc}

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

For true_false questions, choices should be ["True", "False"].
For short_answer questions, omit the choices field.

Important:
- Questions should be directly answerable from the text
- Avoid ambiguous questions
- Ensure correct answers are unambiguously correct
- Distribute question types if multiple types are requested"""

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

        return JsonResponse({
            "success": True,
            "questions": questions,
            "model": model,
            "story_title": generation_params["story_title"],
            "quiz_title": generation_params["quiz_title"],
        })

    except json.JSONDecodeError as e:
        return JsonResponse({"success": False, "error": f"Invalid JSON in AI response: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@instructor_required
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

        # Create the quiz
        quiz = Quiz.objects.create(
            owner=request.user,
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
            "redirect_url": f"/instructor/quizzes/{quiz.pk}/",
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =============================================================================
# ROSTER VIEWS
# =============================================================================

@login_required
@instructor_required
def roster_list(request):
    rosters = Roster.objects.filter(instructor=request.user).annotate(
        student_count=Count("memberships")
    ).order_by("-created_at")

    return render(request, "core/instructor/roster_list.html", {"rosters": rosters})


@login_required
@instructor_required
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

    return render(request, "core/instructor/roster_form.html", {
        "form": form,
        "title": "Create Roster",
    })


@login_required
@instructor_required
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

    return render(request, "core/instructor/roster_form.html", {
        "form": form,
        "roster": roster,
        "memberships": memberships,
        "add_student_form": add_student_form,
        "title": f"Edit Roster: {roster.name}",
    })


@login_required
@instructor_required
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
            return render(request, "core/instructor/partials/roster_students.html", {
                "roster": roster,
                "memberships": memberships,
                "add_student_form": add_student_form,
            })
        else:
            # Return form with errors
            memberships = roster.memberships.select_related("student").order_by("student__username")
            return render(request, "core/instructor/partials/roster_students.html", {
                "roster": roster,
                "memberships": memberships,
                "add_student_form": form,
            })

    return redirect("core:roster_edit", pk=pk)


@login_required
@instructor_required
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
        return render(request, "core/instructor/partials/roster_students.html", {
            "roster": roster,
            "memberships": memberships,
            "add_student_form": add_student_form,
        })

    return redirect("core:roster_edit", pk=pk)


# =============================================================================
# UNIT VIEWS
# =============================================================================

@login_required
@instructor_required
def unit_list(request):
    """List all units for the current instructor with nested lessons."""
    units = Unit.objects.filter(instructor=request.user).prefetch_related(
        "unit_lessons__lesson__story"
    ).annotate(
        lessons_count=Count("unit_lessons")
    ).order_by("-created_at")

    return render(request, "core/instructor/unit_list.html", {
        "units": units,
        "title": "Units",
    })


@login_required
@instructor_required
def unit_create(request):
    """Create a new unit."""
    if request.method == "POST":
        form = UnitForm(request.POST)
        formset = UnitLessonFormSet(request.POST)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(instructor=request.user).order_by("title")

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
            f.fields["lesson"].queryset = Lesson.objects.filter(instructor=request.user).order_by("title")

    return render(request, "core/instructor/unit_form.html", {
        "form": form,
        "formset": formset,
        "title": "Create Unit",
    })


@login_required
@instructor_required
def unit_edit(request, pk):
    """Edit an existing unit."""
    unit = get_object_or_404(Unit, pk=pk, instructor=request.user)

    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)
        formset = UnitLessonFormSet(request.POST, instance=unit)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(instructor=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Unit updated successfully.")
            return redirect("core:unit_edit", pk=pk)
    else:
        form = UnitForm(instance=unit)
        formset = UnitLessonFormSet(instance=unit)
        for f in formset.forms:
            f.fields["lesson"].queryset = Lesson.objects.filter(instructor=request.user).order_by("title")

    return render(request, "core/instructor/unit_form.html", {
        "form": form,
        "formset": formset,
        "unit": unit,
        "title": f"Edit Unit: {unit.title}",
    })


@login_required
@instructor_required
def unit_delete(request, pk):
    """Delete a unit."""
    unit = get_object_or_404(Unit, pk=pk, instructor=request.user)

    if request.method == "POST":
        title = unit.title
        unit.delete()
        messages.success(request, f"Unit '{title}' deleted.")
        return redirect("core:unit_list")

    return render(request, "core/instructor/unit_confirm_delete.html", {
        "unit": unit,
        "title": f"Delete Unit: {unit.title}",
    })


# =============================================================================
# COURSE VIEWS
# =============================================================================

@login_required
@instructor_required
def course_list(request):
    """List all courses for the current instructor."""
    courses = Course.objects.filter(instructor=request.user).annotate(
        units_count=Count("course_units")
    ).order_by("-created_at")

    return render(request, "core/instructor/course_list.html", {
        "courses": courses,
        "title": "Courses",
    })


@login_required
@instructor_required
def course_create(request):
    """Create a new course."""
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        formset = CourseUnitFormSet(request.POST)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(instructor=request.user).order_by("title")

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
            f.fields["unit"].queryset = Unit.objects.filter(instructor=request.user).order_by("title")

    return render(request, "core/instructor/course_form.html", {
        "form": form,
        "formset": formset,
        "title": "Create Course",
    })


@login_required
@instructor_required
def course_edit(request, pk):
    """Edit an existing course."""
    course = get_object_or_404(Course, pk=pk, instructor=request.user)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course, user=request.user)
        formset = CourseUnitFormSet(request.POST, instance=course)

        # Set user on each formset form
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(instructor=request.user).order_by("title")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Course updated successfully.")
            return redirect("core:course_edit", pk=pk)
    else:
        form = CourseForm(instance=course, user=request.user)
        formset = CourseUnitFormSet(instance=course)
        for f in formset.forms:
            f.fields["unit"].queryset = Unit.objects.filter(instructor=request.user).order_by("title")

    return render(request, "core/instructor/course_form.html", {
        "form": form,
        "formset": formset,
        "course": course,
        "title": f"Edit Course: {course.title}",
    })


@login_required
@instructor_required
def course_delete(request, pk):
    """Delete a course."""
    course = get_object_or_404(Course, pk=pk, instructor=request.user)

    if request.method == "POST":
        title = course.title
        course.delete()
        messages.success(request, f"Course '{title}' deleted.")
        return redirect("core:course_list")

    return render(request, "core/instructor/course_confirm_delete.html", {
        "course": course,
        "title": f"Delete Course: {course.title}",
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


# =============================================================================
# GLOSSARY GENERATION VIEWS
# =============================================================================

@login_required
@instructor_required
def glossary_generate(request, story_pk):
    """
    AI-powered glossary generation based on story content.
    Shows form for configuring glossary generation parameters.
    """
    import json

    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)
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

    return render(request, "core/instructor/glossary_generate.html", {
        "form": form,
        "story": story,
        "glossary": glossary,
        "existing_terms_count": glossary.terms.count(),
        "generation_params": generation_params,
        "generation_params_json": generation_params_json,
        "title": f"Generate Glossary: {story.title}",
    })


@login_required
@instructor_required
def glossary_generate_ai(request, story_pk):
    """
    Call OpenRouter API to generate glossary terms using the stored parameters.
    """
    import json
    import re
    from django.http import JsonResponse
    from django.conf import settings

    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)

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
@instructor_required
def glossary_generate_save(request, story_pk):
    """
    Save the generated glossary terms to the database.
    """
    import json
    from django.http import JsonResponse

    story = get_object_or_404(Story, pk=story_pk, instructor=request.user)

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
            "redirect_url": f"/instructor/stories/{story.pk}/?tab=glossary"
        })

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
