# Reading Experiment Platform – Full Implementation Spec

> A Django + Postgres web app for experimental reading, glossaries, and assessment, with mobile-first, asynchronous UI and AI integration.

---

## 0. Overall Goals

Build a **fully featured experimental reading platform** that:

1. Presents **reading passages** to students in multiple formats:
   - Continuous text
   - Card-based slideshow (segment-by-segment)
   - Image-synchronized “movie” mode (text + timed media)
2. Provides a **rich glossary engine**:
   - Precise term indexing in each passage
   - AI-assisted candidate glossary term selection based on difficulty and pedagogical value
   - Term occurrences linked in the UI for gloss tooltips
3. Provides a **sophisticated quiz/assessment engine**:
   - Multiple question types (MCQ, short answer, file upload, etc.)
   - Item bank vs quiz instances
   - Shuffle options, “freeze position” choices, media in stems
4. Implements a configurable **Experiment Engine**:
   - Randomly assigns students to variants
   - Parameterizes aspects of the UI/UX (e.g., gloss behavior, reading mode, pacing)
   - Logs detailed events per experiment / variant
5. Has **mobile-first, fully responsive, asynchronous UI**:
   - No full-page reloads during normal interactions
   - HTMX + small JS for dynamic behavior
6. Integrates with **OpenAI** and **PostHog**:
   - OpenAI for generating readings, glossaries, quizzes
   - PostHog for analytics & dashboards
7. Uses **PostgreSQL** and is deployable on **Render**.

The user wants to do **minimal manual configuration during development**. You may **invent development credentials**, place them in a dev config file, and only ask the user when truly necessary (e.g., production API keys).

---

## 1. Tech Stack

### 1.1. Backend

- Python 3.12+
- Django 5.x
- PostgreSQL 14+ (local + Render)
- Libraries (install via `requirements.txt`):
  - `django`
  - `psycopg2-binary`
  - `django-allauth` (optional but preferred for auth/registration)
  - `django-bootstrap5`
  - `django-crispy-forms`, `crispy-bootstrap5`
  - `django-ckeditor` or `django-tinymce` (choose one) for rich text
  - `django-extensions`
  - `python-dotenv` or `django-environ`
  - `openai`
  - `posthog` (Python SDK, optional – main use via JS)
  - `textstat` (for readability metrics, optional but nice)
  - `htmx` (served as static JS)
  - Any light reordering lib if needed (e.g. `django-ordered-model` or manage manually)

### 1.2. Frontend

- Bootstrap 5 (CSS + JS)
- Bootstrap Icons
- HTMX (for async partial updates)
- Optional: Alpine.js or lightweight vanilla JS modules for:
  - Movie reader player
  - Card slideshow behavior
  - Misc dynamic UI (tabs, toggles, etc.)
- Tippy.js **or** Bootstrap Popover for gloss tooltips (Tippy preferred)

### 1.3. Deployment

- Render web service
- Render PostgreSQL
- `gunicorn` as WSGI server
- `whitenoise` for static files

---

## 2. Project Setup & Configuration

### 2.1. Project structure

- Repo root:
  - `rgx_project/` (Django project)
  - `core/` (main app)
  - `config/dev.env` (generated dev env file – **not committed**)
  - `requirements.txt`
  - `manage.py`
  - `render.yaml` (for deployment)
  - `.env` (optional) / `.env.dev` / `.gitignore`

### 2.2. Dev configuration (auto-generate)

Create `config/dev.env` with **invented dev credentials**, e.g.:

```env
# Dev environment (generated)
SECRET_KEY=dev-secret-key-change-me-123456
DEBUG=True

DATABASE_URL=postgres://rgx_dev:rgx_dev_pass@localhost:5432/rgx_experiment_dev

OPENAI_API_KEY=sk-dev-fake-replace
POSTHOG_API_KEY=phc_dev_fake_key
POSTHOG_HOST=https://app.posthog.com
```

- Add `config/` to `.gitignore`.
- In `rgx_project/settings.py`, use `python-dotenv` or `django-environ` to load this file in development.
- Assume local Postgres user/db (create if missing or provide a `setup_db.sql` snippet for user).

Only prompt the user **if**:
- `DATABASE_URL` is missing and connection fails, or
- Real API keys are needed in production.

---

## 3. Data Model (Django Models)

Use a **custom User model** and multiple logical sections. All models below live in `core/models.py` (or split into modules if desired, but keep import paths consistent).

### 3.1. Sites, Users, Rosters

**Site**

- `id`
- `name` (CharField, 200)
- `code` (CharField, 20, unique)

**User** (custom user model)

- Inherit from `AbstractUser`.
- Fields:
  - `role`: CharField, choices = {student, instructor, researcher}
  - `site`: FK → Site, nullable
- Convenience methods: `is_student()`, `is_instructor()`, `is_researcher()`.

**Roster**

- `id`
- `site`: FK → Site
- `instructor`: FK → User (role=instructor)
- `name`
- `students`: M2M → User (role=student)

### 3.2. Story, Segments, Media

**Story**

- `id`
- `instructor`: FK → User (role=instructor)
- `title`
- `text_html` (TextField)
- `source_type`: CharField, choices = {manual, ai_generated, external}
- `source_metadata`: JSONField (dict with `author`, `publisher`, `isbn`, `provider`, `external_ids`, `canonical_url`, etc.)
- `reading_level_label`: CharField (e.g. “Grade 6–7”, “B1”, “Lexile 780L”)
- `reading_level_metrics`: JSONField (optional: `{"word_count": 520, "flesch_kincaid": 7.2, ...}`)
- `created_at`: DateTime

**StorySegment**

Represents chunks of the story used for card & movie modes.

- `id`
- `story`: FK → Story
- `index`: PositiveIntegerField (order within story)
- `title`: CharField (optional; used in movie mode as scene title)
- `text_html`: TextField (text specific to segment)
- Optional mapping to full story text:
  - `start_char`, `end_char` (Integer, nullable)
- `metadata`: JSONField (e.g., `{"type":"main","difficulty":2}`)

**MediaAsset**

Generic media library.

- `id`
- `owner`: FK → User
- `file`: FileField (images, audio, video; configure media storage)
- `media_type`: CharField, choices = {image, audio, video}
- `title`: CharField (optional)
- `alt_text`: CharField / TextField (for images)
- `description`: TextField (optional)
- `created_at`

**SegmentMedia**

Links media to segments.

- `id`
- `segment`: FK → StorySegment
- `media`: FK → MediaAsset
- `role`: CharField, choices = {background_image, inline_image, audio_narration, video_clip}
- `start_offset_ms`: Integer (0 for images; start within clip for audio/video)
- `end_offset_ms`: Integer (nullable; for partial clips)
- `order`: PositiveIntegerField (for multiple media items per segment)

### 3.3. Glossary & Term Indexing

**Glossary**

- `id`
- `story`: OneToOneField → Story
- `name` (optional)
- `language_code`: CharField (L2, e.g. “en”)
- `native_language_code`: CharField (L1, e.g. “vi”)
- `created_at`

**Term**

Story-specific term (simpler than a global dictionary; can be extended later).

- `id`
- `glossary`: FK → Glossary
- `term_text`: CharField
- `lemma`: CharField (optional)
- `part_of_speech`: CharField (optional, or normalized later)
- `definition_html`: TextField (L2 definition)
- `translation`: CharField (short L1 gloss)
- `translation_lang_code`: CharField (should match `native_language_code` but not enforced here)
- `ipa`: CharField (optional)
- `difficulty_rating`: Integer or Float (1–5)
- `is_ai_suggested`: Boolean
- `is_selected_for_glossary`: Boolean (candidate vs accepted)
- `gloss_type`: CharField choices (definition, translation_only, synonym, explanation)
- `is_exam_safe`: Boolean
- `notes`: TextField (optional)
- `created_at`, `updated_at`

**TermOccurrence**

Precise location of a term in the story text.

- `id`
- `story`: FK → Story
- `term`: FK → Term
- `segment`: FK → StorySegment (nullable)
- `start_char`, `end_char`: Integer (position in a plain-text snapshot of story or segment)
- `token_index`: Integer (optional, index in token sequence)
- `sentence_index`: Integer (optional)
- `anchor_text`: CharField (the substring at that span, for sanity)
- `anchor_version`: CharField (e.g. hash of the story’s plain text at time of indexing)
- `created_at`

### 3.4. Quiz / Assessment Engine

Separate **Item Bank** and **Quiz** instances.

**ItemBankQuestion**

- `id`
- `owner`: FK → User (instructor/researcher)
- `prompt_html`
- `question_type`: CharField choices:
  - {mcq_single, mcq_multi, true_false, short_answer, long_answer, matching, ordering, cloze, file_upload}
- `default_points`: Float
- `subject`: CharField (optional)
- `grade_band`: CharField (optional)
- `metadata`: JSONField (contains difficulty, discrimination, tags, learning standard IDs)
- `status`: CharField choices {draft, active, retired}
- `created_at`, `updated_at`

**Choice** (for MCQ, ordering, etc.)

- `id`
- `item_bank_question`: FK → ItemBankQuestion
- `text_html`
- `is_correct`: Boolean
- `freeze_position`: Boolean
- `order`: Integer

**ShortAnswerKey**

- `id`
- `item_bank_question`: FK
- `acceptable_answer`: CharField or TextField
- `match_type`: CharField choices {exact, case_insensitive, regex, normalized}

**MatchingPair**

- `id`
- `item_bank_question`: FK
- `prompt_text_html`
- `target_text_html`
- `group`: CharField / Integer (to support multiple matching subgroups per question)

**OrderingElement**

- `id`
- `item_bank_question`: FK
- `text_html`
- `correct_position`: Integer

**FileUploadConfig**

- `id`
- `item_bank_question`: FK
- `allowed_mime_types`: JSONField list (`["image/*", "application/pdf"]`)
- `max_file_size_bytes`: Integer

**Quiz** (test/assessment)

- `id`
- `instructor`: FK → User
- `title`
- `description`: TextField
- `time_limit_seconds`: Integer (nullable)
- `attempt_limit`: Integer (nullable – None for unlimited)
- `shuffle_questions`: Boolean
- `show_feedback_mode`: CharField choices {none, summary_only, per_question_after_submit}
- `navigation_mode`: CharField {free, linear}
- `show_correct_answers`: Boolean
- `allow_review`: Boolean
- `metadata`: JSONField
- `created_at`, `updated_at`

**QuizQuestion**

- `id`
- `quiz`: FK → Quiz
- `item_bank_question`: FK → ItemBankQuestion
- `order`: Integer
- `points_override`: Float (nullable; fallback to ItemBankQuestion.default_points)
- `section_label`: CharField (optional, for grouping)

**QuizSession**

- `id`
- `student`: FK → User
- `quiz`: FK → Quiz (or tie to Lesson; see below)
- `lesson`: FK → Lesson (optional but recommended)
- `started_at`
- `completed_at`: nullable
- `time_limit_seconds`: integer snapshot
- `time_used_seconds`: integer (calculated)
- `attempt_number`: Integer
- `status`: CharField {in_progress, completed, expired, abandoned}
- `metadata`: JSONField (stores question/choice order, device info, etc.)

**QuizSubmission**

- `id`
- `session`: FK → QuizSession
- `score`: float
- `max_score`: float
- `submitted_at`
- `metadata`: JSONField

**ResponseLog**

- `id`
- `submission`: FK → QuizSubmission
- `question`: FK → ItemBankQuestion
- `question_type`: store again for convenience
- `selected_choice_ids`: JSONField (list of choice IDs, where applicable)
- `short_answer_text`: TextField (if short answer)
- `long_answer_text`: TextField (if long answer / essay)
- `file_upload_path`: CharField (if file upload)
- `file_metadata`: JSONField (mime type, size, etc.)
- `is_correct`: Boolean (where determinable)
- `partial_credit_ratio`: Float (0–1, where used)
- `time_spent_seconds`: Float (optional)

### 3.5. Lessons & Progress

**Lesson**

- `id`
- `instructor`: FK → User
- `site`: FK → Site
- `title`
- `introduction_html`: TextField
- `story`: FK → Story (reading)
- `quiz`: FK → Quiz
- `rosters`: M2M → Roster
- `is_active`: Boolean
- **Reading mode config**:
  - `allowed_modes`: CharField or JSON (e.g. `["continuous","cards","movie"]`)
  - `default_mode`: CharField {continuous, cards, movie}
  - `lock_mode`: Boolean (no switching)
- `created_at`

**LessonProgress**

- `id`
- `student`: FK → User
- `lesson`: FK → Lesson
- `reading_start`, `reading_end`
- `quiz_start`, `quiz_end`
- `comprehension_score`: Float (mirrors final quiz score if single quiz)
- `self_efficacy_rating`: Integer (Likert 1–5)
- `created_at`
- Derivable property: `reading_duration_seconds`

### 3.6. Instrumentation Logs

**GlossClickLog**

- `id`
- `student`: FK → User
- `lesson`: FK → Lesson
- `story`: FK → Story
- `term`: FK → Term
- `term_occurrence`: FK → TermOccurrence (nullable)
- `segment`: FK → StorySegment (nullable)
- `clicked_at`
- `client_info`: JSONField (user agent, device type, etc.)

**ReadingEvent**

- `id`
- `student`: FK → User
- `lesson`: FK → Lesson
- `story`: FK → Story
- `event_type`: CharField {start, scroll, pause, resume, finish, mode_change, segment_view}
- `event_payload`: JSONField (e.g. scroll position, from/to mode, segment index)
- `created_at`

---

## 4. Experiment Engine

### 4.1. Models

**Experiment**

- `id`
- `key`: SlugField, unique (e.g. “tooltip_placement_v1”)
- `name`
- `description`: TextField
- `status`: CharField {draft, running, paused, completed}
- `created_at`

**ExperimentVariant**

- `id`
- `experiment`: FK → Experiment
- `key`: SlugField (e.g. “margin_card”, “inline_bubble”)
- `name`
- `parameters`: JSONField (config dict – see below)
- `weight`: PositiveIntegerField (relative frequency)
- Unique constraint: (experiment, key)

**ExperimentAssignment**

- `id`
- `user`: FK → User
- `experiment`: FK → Experiment
- `variant`: FK → ExperimentVariant
- `assigned_at`
- Unique constraint: (user, experiment)

(Optional) **ExperimentScope**

- (For v1 you can omit; if implemented:)
- `id`
- `experiment`: FK
- `scope_type`: CharField {global, site, roster, lesson}
- `scope_id`: Integer (or separate FKs; decide an approach)
- Use to limit experiment to certain lessons/rosters.

### 4.2. Experiment parameters

Parameters JSON per variant might look like:

```json
{
  "default_reading_mode": "cards",
  "allowed_reading_modes": ["continuous", "cards"],
  "tooltip_position": "margin",
  "highlight_style": "underline_dotted",
  "show_gloss_icon": true,
  "gloss_open_delay_ms": 200,
  "allow_gloss_during_play": false,
  "pause_on_gloss_click": true,
  "card_auto_advance_seconds": 0
}
```

### 4.3. Helper functions

Implement a module `core/experiments.py` with:

- `get_or_assign_variant(user, experiment_key) -> ExperimentVariant | None`
  - If no assignment exists for user:
    - If experiment is `running`, pick a variant via weighted random choice.
    - Create ExperimentAssignment.
  - Return variant.

- `get_treatment_config(user, lesson) -> dict`
  - For v1: assume one global experiment key (e.g. “tooltip_placement_v1”) or a fixed list.
  - Get or assign variant.
  - Return `variant.parameters` dict (merged if multiple experiments later).
  - Include variant key itself for analytics, e.g.:

    ```python
    cfg = variant.parameters.copy()
    cfg["_experiment_key"] = experiment.key
    cfg["_variant_key"] = variant.key
    return cfg
    ```

---

## 5. Reading Engine – Modes & Behavior

### 5.1. Modes Overview

Per Lesson, student sees a **Reader** that supports:

- Mode `continuous` – full text view.
- Mode `cards` – one StorySegment per “slide”/card.
- Mode `movie` – timed, synchronized display of segment text + media.

Lesson and experiment determine:

- Which modes are allowed.
- Which mode is default.
- Mode switching rules.

### 5.2. Continuous Mode

- URL pattern: `/lessons/<lesson_id>/read/` (with mode parameter, e.g. `?mode=continuous`).
- Template:
  - Uses a `base.html`.
  - Displays:
    - Lesson title
    - Story reading_level_label
    - Mode switcher
    - Main reading area with `story.text_html` rendered, with gloss terms wrapped.

- Gloss term markup:
  - Wrap with `<span class="gloss-term" data-term-id="..." data-occurrence-id="...">word</span>`.
  - JS/Tippy to show gloss tooltip or side panel (subject to experiment config).

- Mobile:
  - Single column, large text, bottom sheet for gloss details.

### 5.3. Card Mode

- Uses `StorySegment` records.
- Template (or partial) renders:
  - Progress bar (“3 / 12 cards”).
  - Single card at a time (`segment.text_html`).
  - If segment has image: show image at top or side.
  - Previous/Next buttons (and keyboard support).
- Under the hood:
  - A small JS component manages current index.
  - For analytics:
    - On segment change, send async call to log `ReadingEvent` with `event_type="segment_view"` and `segment_index`.

- Mobile:
  - Full-screen card; navigation buttons easily tappable.
  - Optionally support swipe left/right (JS).

### 5.4. Movie Mode

- Uses `StorySegment` + `SegmentMedia` (+ durations).
- Player UI:
  - Visual area: main image/video.
  - Text area: segment text with glosses.
  - Control bar:
    - Play/Pause
    - Next/Previous scene
    - Timeline (progress bar / slider)
    - Time display

- For v1, you can implement simple auto-advance:
  - Each segment has `duration_ms` either stored in metadata or derived from word count.
  - Player uses JS `setTimeout` or `requestAnimationFrame` to move from segment to segment.
- If audio narration is present:
  - On segment change, play the assigned audio clip.
  - Basic: one audio per segment.
  - (Optionally, support single audio track + offset metadata in later versions.)

- Gloss behavior:
  - Controlled by experiment parameters:
    - `allow_gloss_during_play`, `pause_on_gloss_click`.
  - If `pause_on_gloss_click=True`: pausing when a gloss term is tapped; show tooltip/side panel.

- Logging:
  - `ReadingEvent` with `event_type` = {movie_play_started, movie_play_paused, movie_completed}.
  - Include current segment index and timestamp in `event_payload`.

---

## 6. Glossary Engine – AI & Indexing

### 6.1. Text analysis & readability

On Story save or explicitly triggered:

1. Extract **plain text** from `text_html`:
   - Use HTML parser (e.g. `BeautifulSoup`) to strip tags.
2. Use `textstat` (or similar) to compute:
   - Word count
   - Sentence count
   - Flesch-Kincaid / other readability metrics
3. Save results into `Story.reading_level_metrics` and optional `reading_level_label`.

### 6.2. AI-assisted term candidate generation

Implement function:

```python
def generate_ai_term_candidates(story: Story, level: str, l1_lang_code: str) -> list[dict]:
    ...
```

Behavior:

- Use OpenAI Chat Completions with JSON output.
- Provide:
  - Passage text (plain or HTML).
  - Target student level.
  - Native language code.
- Request JSON list:

```json
{
  "terms": [
    {
      "term_text": "photosynthesis",
      "reason": "key concept, academically important",
      "difficulty": 4,
      "definition_html": "The process by which plants...",
      "translation": "quá trình quang hợp",
      "part_of_speech": "noun"
    },
    ...
  ]
}
```

- Create `Term` objects with:
  - `is_ai_suggested=True`, `is_selected_for_glossary=False`.
  - Set difficulty, definition, translation, etc.

### 6.3. Glossary suggestions UI

For instructors:

- A **Glossary Suggestions** view:
  - Top: summary of story (title, reading level, word count).
  - Two sections:
    - **Active Terms**: accepted terms (`is_selected_for_glossary=True`).
    - **AI Suggestions**: candidate terms.
- For each candidate term:
  - Card or table row showing:
    - Term
    - Difficulty
    - Example snippet (from first occurrence; optional)
    - AI definition
    - AI translation
    - Buttons: “Accept”, “Reject”, “Edit”

All actions:
- Use HTMX for async updates:
  - Accept: set `is_selected_for_glossary=True`, move term to “Active Terms” section.
  - Reject: delete term or mark as rejected.

### 6.4. TermOccurrence indexing

Implement function:

```python
def index_term_occurrences(story: Story):
    ...
```

Behavior:

1. Clear existing `TermOccurrence` for that story (or re-anchor intelligently).
2. Work with a plain-text version of the story:
   - Option: maintain a mapping from plain-text positions to HTML positions.
3. For each `Term` where `is_selected_for_glossary=True`:
   - Search `term_text` occurrences in the plain text (case-insensitive).
   - For each match:
     - Determine `start_char`, `end_char`.
     - Determine `segment`:
       - If you maintain mapping of char ranges to `StorySegment`s, assign `segment_id`.
     - Set `anchor_text` and `anchor_version` (e.g., hash of plain text).
4. Create `TermOccurrence` entries accordingly.

Later, to apply gloss markup:

- When rendering the text in templates:
  - Either:
    - Pre-process HTML to insert `<span class="gloss-term"...>` around occurrences, OR
    - Store pre-marked HTML in a separate field (e.g., `story.text_html_with_gloss`).
- For now, prefer **runtime insertion** to keep the canonical text clean.

---

## 7. Quiz / Assessment Engine – Behavior

You’ve already defined models. Implement:

### 7.1. Authoring UI

- Quiz list: card/table with actions (Edit, Preview, Clone, Archive).
- Quiz editor:
  - Drag-and-drop question list (use JS/HTMX).
  - For each question:
    - Preview card with stem snippet and type icons.
    - “Edit” opens full editor:
      - Prompt rich text editor (with media insertion).
      - Type selection (MCQ, etc.).
      - Choices/keys editors depending on type.
      - Shuffle toggles, freeze position for choices.
  - “Generate items from reading” button:
    - For a given Story, call OpenAI to generate a set of questions and choices.
    - Insert them as `ItemBankQuestion`s and link to Quiz.

### 7.2. Delivery logic

- On starting a quiz for a student/lesson:
  - Create `QuizSession` with:
    - Randomized question order (if `shuffle_questions=True`).
    - Within each question, randomized choice order:
      - Shuffle only choices where `freeze_position=False`.
    - Store selected orders in `QuizSession.metadata`.
- Show questions page:
  - Use navigation mode:
    - `free`: allow jumping between questions.
    - `linear`: next-only navigation.
- Use asynchronous submissions:
  - For each question or final submission, send via HTMX or JS `fetch`.
  - Store answers in `ResponseLog`.

### 7.3. Scoring engine

Implement a scoring function:

```python
def score_quiz_submission(submission: QuizSubmission):
    ...
```

For each question:

- MCQ single:
  - Check if selected choice == correct; full points else 0.
- MCQ multi:
  - Use strategy defined in question metadata (e.g., all-or-nothing, partial).
- Short answer:
  - Normalize text, check patterns.
- File upload / long answer:
  - Initially 0; allow manual scoring in an instructor UI.

Store:

- `is_correct` and `partial_credit_ratio` in `ResponseLog`.
- Total sum in `QuizSubmission.score`, `max_score`.

---

## 8. Student Experience – Flows

### 8.1. My Lessons

- Route: `/lessons/` (student-only).
- Show:
  - List of assigned Lessons (via rosters).
  - Status: Not started / In progress / Completed.
  - Basic metadata (title, reading level, due date if added later).

### 8.2. Lesson flow

1. **Intro page**:
   - Lesson title, site.
   - Introduction text.
   - Reading level + estimated time.
   - Start button.
2. **Reader page** (mode determined by lesson & experiment):
   - Mode selector (if more than one mode allowed).
   - Reader container with selected mode partial.
   - Gloss behavior as per treatment config.
3. **Quiz page**:
   - After reading, button “Start Quiz”.
   - Quizzing UI as per engine.

All transitions:

- Use normal navigation for page-level (Intro → Reader → Quiz).
- Use HTMX for inner updates (switching modes, dynamic actions, logging events).

---

## 9. Instructor & Researcher UI

### 9.1. Instructor

- Dashboard:
  - Cards for:
    - Stories
    - Glossaries
    - Quizzes
    - Lessons
    - Rosters
- Story authoring:
  - Tabs: Details | Content | Segments & Media | Glossary | AI Tools
- Glossary tools:
  - AI suggestion panel, active terms panel.
- Quiz builder:
  - Drag-and-drop, AI suggestions for questions/distractors.
- Lesson builder:
  - Steps:
    1. Choose Story
    2. Choose Quiz
    3. Intro text
    4. Assign rosters
    5. Reading modes & experiment selection.

### 9.2. Researcher

- Experiments management:
  - List experiments, statuses.
  - Add/edit variants, parameters.
  - Start/pause experiments.
- Analytics dashboard:
  - For each experiment:
    - Charts (via Chart.js) for:
      - Reading duration per variant.
      - Gloss clicks per 1000 words per variant.
      - Comprehension scores per variant.
    - Filters: site, roster, reading level, date range.
- Export tools:
  - CSV for:
    - LessonProgress
    - GlossClickLog
    - QuizSession + QuizSubmission + ResponseLog
    - TermOccurrence

---

## 10. Front-End Architecture & Responsiveness

### 10.1. Base template

`base.html` should include:

- Meta viewport (`<meta name="viewport" content="width=device-width, initial-scale=1">`)
- Bootstrap 5 CSS & JS
- HTMX
- Optional Alpine.js
- PostHog JS snippet
- Global nav bar
- `<main>` container
- Toast container for async success/errors
- Dark/high-contrast mode toggle

### 10.2. Async practices

- Use HTMX for:
  - Modal forms (create/edit).
  - Table/list updates on edit/delete.
  - Wizard steps.
- Use JS only where:
  - Complex UI behavior (movie player, card slider).
  - Real-time interactions (timers, media).

### 10.3. Mobile-first design

- Layouts:
  - Default: single column, edge-to-edge with padding.
  - Use Bootstrap `container-fluid` and responsive classes.
- Avoid horizontal scrolling.
- Ensure all controls (buttons, tabs, toggles) have adequate touch area.

---

## 11. Instrumentation & Analytics (PostHog)

### 11.1. JS integration

- Load PostHog snippet in `base.html`.
- On user login (or in base template with user context), call:

  ```js
  posthog.identify('{{ request.user.id }}');
  ```

### 11.2. Events

On the front-end, capture:

- `lesson_viewed` (when student opens lesson intro)
- `reading_started` / `reading_finished`
- `reading_mode_changed` (payload: from_mode, to_mode)
- `segment_viewed` (payload: segment_index)
- `movie_play_started` / `movie_play_paused` / `movie_play_completed`
- `gloss_clicked` (payload: term_id, segment_index)
- `quiz_started` / `quiz_submitted` (payload: score, max_score)

Each event should include:

- `user_id`
- `lesson_id`
- `story_id`
- `source_type`
- `reading_level`
- `experiment_key` & `variant_key` (from treatment config)

Also log these server-side to the DB models (`ReadingEvent`, `GlossClickLog`, `QuizSession` etc.) as specified.

---

## 12. AI Integration – OpenAI

### 12.1. Config

- Read `OPENAI_API_KEY` from env (`dev.env` or Render env).
- Use `openai` Python client.

### 12.2. Use cases

Implement these helper functions/views:

1. **Generate Reading**:
   - Input: subject, topic, level, length, style, options (generate quiz, glossary).
   - Output: Story (and optionally Quiz + Terms).
2. **Generate Glossary Candidates**:
   - Input: Story, level, L1 language.
   - Output: candidate Terms saved to DB.
3. **Generate Quiz from Story**:
   - Input: Story, desired number of questions, difficulty.
   - Output: ItemBankQuestion + Choices created in DB and linked to Quiz.
4. **Generate distractors**:
   - Input: correct answer and prompt.
   - Output: 3–5 distractors to add as Choices.

All prompts should request **JSON output** for easier parsing.

---

## 13. Dev Tools & Testing

- Use `django-extensions` for shell_plus, show_urls, etc.
- Use `pytest` + `pytest-django` for tests.
- Write tests for:
  - Model integrity (unique constraints, etc.).
  - Experiment assignment logic.
  - Basic scoring logic for quizzes.
  - Glossary indexing functions.

---

## 14. Deployment (Render)

- Add `render.yaml` with:
  - Web service config:
    - `buildCommand: pip install -r requirements.txt && python manage.py collectstatic --noinput`
    - `startCommand: gunicorn rgx_project.wsgi`
  - Postgres service.
- Use environment variables in Render for:
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `OPENAI_API_KEY`
  - `POSTHOG_API_KEY`
  - `POSTHOG_HOST`
- Ensure `DEBUG=False` in production.

---

That’s the full spec.
