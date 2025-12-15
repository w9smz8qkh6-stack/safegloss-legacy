ROADMAP.md


# Safegloss Story Engine Roadmap

This roadmap describes how to operationalize the knowledge captured in our supporting docs into a **sophisticated, configurable story generation system** that is:
- **Lexile-aligned** (constraint-based)
- **Corpora-aware** (rules derived from open/public-domain texts)
- **Age + genre adaptive** (developmentally appropriate writing)
- **Writing-style adaptive** (rule-driven, not “vibes-driven”)
- **Auditable and testable** (deterministic rule assembly + validation)

## Documentation Reference Index

This roadmap is implemented using the following specification documents. Each milestone below explicitly depends on one or more of these files.

### Story Generation
- `docs/LEXILE_STORY_GENERATION.md` — Lexile‑aligned story prompting & validation
- `docs/LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md` — Pedagogical, developmental, and corpus‑derived writing rules
- `docs/NATURAL_LANGUAGE_RULE_PHRASES.md` — Deterministic rule‑to‑language mappings used by the Prompt Composer

### Quiz & Assessment System
- `docs/AI_QUIZ_GENERATION_AND_VALIDATION.md` — Quiz prompt template, Bloom alignment, psychometric constraints
- `docs/QUIZ_TO_LEARNING_OBJECTIVES_AND_STANDARDS.md` — Learning objective and standards mapping model
- `docs/STANDARDS_ALIGNED_ASSESSMENT_CORPORA.md` — Assessment‑style corpora extraction and modeling
- `docs/QUIZ_VALIDATION_AND_ANALYTICS.md` — Validation, reliability heuristics, analytics, telemetry

### Platform & Integration
- `docs/ROADMAP.md` — System‑level implementation plan (this document)

## 0. Source Docs (Inputs to the Roadmap)

These documents are treated as “spec sources” for implementation:

- `docs/LEXILE_STORY_GENERATION.md`
  - Prompt template + Lexile proxy constraints + validation expectations
- `docs/LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md`
  - Corpus strategy + pedagogy + genre craft + legal constraints
- `docs/NATURAL_LANGUAGE_RULE_PHRASES.md`
  - Deterministic rule-to-phrase mappings for the prompt composer

The **implementation** should treat these as canonical references.

---

## 1. Product Goals

### 1.1 Teacher-Facing Outcomes
- Teachers can generate stories by:
  - Lexile band (approx.)
  - Age band
  - Genre
  - Theme/topic
  - Word count
  - Tone
  - Study vs Exam mode
  - Optional vocabulary restrictions (glossary-locked)
- Teachers can preview:
  - The story
  - The applied constraints (why it’s leveled this way)
  - Metrics summary (sentence length, dialogue ratio, etc.)

### 1.2 System Outcomes
- Stable generation via **rule-driven prompting**.
- Repeatable results with transparent configuration.
- Automated post-generation validation + iterative fixes.

---

## 2. Architecture Overview

### 2.1 Key Components
1. **Rules Library** (`/rules/*.json`)
   - Age rules
   - Genre rules
   - Lexile rules
   - Optional ELL rules
2. **Writing Profile Builder**
   - Merges rule files into a single normalized “writing profile” per request
3. **Prompt Composer**
   - Emits natural-language constraints in the mandatory layered order
4. **Generation Service**
   - Calls the LLM with the composed prompt
5. **Validation & Rewrite Loop**
   - Computes proxies (sentence length, clause heuristics, passive voice)
   - Rewrites or regenerates until within target band
6. **Audit + Telemetry**
   - Stores applied rules + measured metrics + final output
7. **Safegloss Integration Layer**
   - Auth & identity bridging between safegloss and safegloss-legacy
   - Shared access to glossaries, vocabulary, and user roles
   - Cross-app content linking (stories ↔ glossaries)

### 2.2 Data Flow
Story Request → Writing Profile → Prompt → Draft Story → Validation → (Fix Loop) → Final Story + Metrics + Audit Record

---

## 3. Milestones

---

## Milestone A — Foundations (Rules + Prompting) ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**
- `rules/` directory with age_rules.json, genre_rules.json, lexile_rules.json, ell_rules.json, style_profiles.json
- `core/story_engine/rules.py` - RulesLoader with schema validation
- `core/story_engine/guardrails.py` - ContentGuardrails for legal/ethical constraints
- `core/story_engine/profile_builder.py` - WritingProfileBuilder merges rules into profiles
- `core/story_engine/prompt_composer.py` - PromptComposer generates deterministic prompts

### A1. Establish Rules Directory
- Create directory:
  - `/rules/`
- Add initial rule files:
  - `age_rules.json`
  - `genre_rules.json`
  - `lexile_rules.json`
  - `ell_rules.json` (optional)

### A2. Define Schemas and Guardrails
- Add lightweight schema validation (runtime checks):
  - Required keys exist
  - Values are in allowed enums/ranges
- Add guardrails:
  - Disallow “write like [living author]” requests
  - Prevent claims of “Lexile certified”
  - Approved phrasing: “Lexile-aligned”, “Designed for readers around …”

### A3. Implement Writing Profile Builder
- Input:
  - `age_band`, `genre`, `lexile_band`, optional flags (`study_mode`, `ell_mode`, `allowed_vocab`, `restricted_vocab`)
- Output:
  - Normalized profile object:
    - Narrative rules
    - Style rules
    - Lexile proxy rules
    - Vocabulary constraints

**Acceptance Criteria**
- For any valid combination, profile is deterministic and logged.

### A4. Implement Prompt Composer (v1)
- Use `docs/NATURAL_LANGUAGE_RULE_PHRASES.md` to generate:
  - Age rules phrasing
  - Genre rules phrasing
  - Lexile rules phrasing
- Enforce prompt ordering:
  1) Reader & Age Profile
  2) Developmental Rules
  3) Genre Rules
  4) Lexile/Language Constraints
  5) Story Parameters
  6) Output constraints

**Acceptance Criteria**
- Given identical input, prompt text is identical (stable).

---

(Primary references: LEXILE_STORY_GENERATION.md, NATURAL_LANGUAGE_RULE_PHRASES.md)

---

## Milestone B — Validation & Rewrite Loop (Lexile Proxy Compliance) ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**
- `core/story_engine/text_metrics.py` - TextMetricsExtractor with sentence segmentation, word count, avg length, dialogue ratio, passive voice detection, clause complexity
- `core/story_engine/validator.py` - StoryValidator with per-Lexile-band thresholds and scoring
- `core/story_engine/rewrite_loop.py` - RewriteLoop with SentenceSplitter, PassiveVoiceRewriter, auto-fix strategies, and regeneration hints

### B1. Metrics Extraction
Implement text analyzers:
- Sentence segmentation
- Word count
- Average sentence length + variance
- Long sentence detector
- Dialogue ratio (quote-based heuristics)
- Passive voice heuristic detector
- Clause complexity heuristic (simple approximate)

### B2. Validation Rules
- Define per-lexile-band thresholds based on `lexile_rules.json`:
  - avg sentence length range
  - max clauses
  - vocabulary level policy (heuristic)

### B3. Auto-Fix Loop
Strategy:
1. If word count off: trim/expand deterministically
2. If sentences too long: split sentences
3. If passive voice detected: rewrite to active voice
4. If vocabulary too difficult: replace with simpler synonyms (use safe substitution)
5. Re-run metrics

Loop policy:
- Max iterations: 2–4
- If still failing: regenerate with stricter prompt emphasis

**Acceptance Criteria**
- ≥80% of stories land within band thresholds without manual edits.

---

(Primary references: LEXILE_STORY_GENERATION.md, QUIZ_VALIDATION_AND_ANALYTICS.md)

## Milestone C — Corpora-Aware Rules (Operationalizing "Writing Expertise") ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**
- `core/story_engine/corpus_analyzer.py` - CorpusAnalyzer class for analyzing texts and computing statistics
- `rules/corpus_stats.json` - Aggregated statistics from 127 public-domain texts by age bucket and genre
- `rules/age_rules.json` (v1.1.0) - Updated with corpus_metrics including sentence length, dialogue ratio, word count ranges
- `rules/lexile_rules.json` (v1.1.0) - Updated with validation_thresholds derived from corpus analysis
- `core/story_engine/validator.py` - Updated to use corpus-derived validation_thresholds

### C1. Build a Public-Domain Corpus Set (Curated)
- Select open/public-domain sources (e.g., Project Gutenberg, ICDL where permissible)
- Build a dataset of representative texts:
  - Age buckets: 6–8, 8–10, 10–12, 12–14
  - Genres: realistic fiction, fantasy, mystery, informational fiction
- Target: 20–50 texts per bucket

### C2. Corpus Analytics Pipeline
Compute per-bucket aggregate stats:
- avg sentence length distribution
- paragraph length distribution
- dialogue ratio distribution
- vocabulary reuse rate
- pronoun density
- temporal markers frequency

Store results as:
- `rules/corpus_stats.json` (aggregated, not raw text)

### C3. Convert Corpus Stats → Rule Enhancements
- Use corpus distributions to refine:
  - sentence targets
  - dialogue ratio defaults
  - paragraph length guidance
  - max character norms

**Acceptance Criteria**
- Rule files reflect empirical distributions (not guesswork).

---

(Primary references: LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md, STANDARDS_ALIGNED_ASSESSMENT_CORPORA.md)

## Milestone D — Writing-Style Adaptive System ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**
- `rules/style_profiles.json` (v1.1.0) - Enhanced with 6 style profiles: minimalist, cinematic, humorous, sel_focused, adventure, lyrical
- Each profile includes: adjustments (dialogue_ratio_target, sentence_length_modifier, sensory_detail, figurative_language), writing_voice (pacing, description_style, emotional_showing), age-specific restrictions, guidance, and avoid lists
- `core/story_engine/profile_builder.py` - Updated StyleRules dataclass with numeric dialogue ratios, writing_voice, pacing, style_avoid; enhanced _apply_style_profile() method
- `core/story_engine/prompt_composer.py` - Added _compose_style_rules() section with voice/pacing guidance, sensory detail levels, figurative language rules
- `core/forms.py` - Added lyrical style to STYLE_PROFILE_CHOICES

### D1. Style Profiles (Reusable "Editorial Packs")
Introduce optional `style_profile` that overlays rules:
- "Minimalist" (short sentences, low figurative language)
- "Cinematic" (more sensory detail, still age-safe)
- "Humorous" (concrete humor, avoids sarcasm for younger)
- "SEL-focused" (explicit emotion labeling)
- "Adventure" (fast-paced, action-oriented)
- "Lyrical" (poetic, musical prose)

Represent as:
- `rules/style_profiles.json`

### D2. Adaptation Logic
- Style profiles may adjust:
  - dialogue ratio (with numeric min/max targets)
  - sensory adjectives frequency guidance
  - emotional explicitness
  - figurative language allowance
  - pacing and voice characteristics
  - age-specific humor types and techniques

**Acceptance Criteria**
- Same story parameters produce noticeably different styles while staying within Lexile constraints.

---

(Primary references: LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md)

## Milestone E — Vocabulary Control (Glossary-Locked Stories) ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**

- `core/story_engine/profile_builder.py` - Added VocabularyConstraints dataclass with modes (none, prefer, strict), max_stretch_words, and frequency_threshold
- `core/story_engine/prompt_composer.py` - Added _compose_vocabulary_control() section for glossary-locked prompting
- `core/forms.py` - Added vocabulary_mode dropdown, max_stretch_words field to StoryGeneratorForm

### E1. Allowed Vocabulary Mode
- Accept `allowed_vocabulary_list` (from a teacher glossary)
- Add prompting constraints:
  - "prefer" mode: Prioritize allowed words, permit common words within frequency tier
  - "strict" mode: Require allowed words with limited stretch word allowance
  - Avoid outside terms beyond frequency threshold

### E2. "Stretch Words" Feature

- Allow up to N stretch words per story (configurable, default 5)
- In Study Mode:
  - Inline simple definition required for stretch words
  - Example: "The bird was resilient—it kept trying even when things were hard."
- Stretch words tracked via study_mode + vocabulary constraints

**Acceptance Criteria**
- Stories reliably include glossary terms without lexical drift.

---

(Primary references: LEXILE_STORY_GENERATION.md, LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md)

---

## Milestone F — UI & Teacher Experience ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**
- `core/forms.py` - StoryGeneratorForm with all generation inputs (age, lexile, genre, theme, word count, tone, style, ELL mode, vocabulary controls)
- `core/views.py` - story_generate, story_generate_preview, story_generate_save, story_export views
- `core/templates/core/instructor/story_generate.html` - Generation form with transparency panel
- `core/templates/core/instructor/story_generate_preview.html` - Preview with validation metrics
- `core/templates/core/instructor/story_export.html` - Print-friendly export view
- Dashboard and story list updated with AI Generate buttons

### F1. Story Creation Page Inputs
Add/selectors:
- Age band
- Lexile band
- Genre
- Theme/topic
- Word count
- Dialogue level
- Tone
- Style profile
- Study vs Exam mode
- Vocabulary mode (none / glossary-locked / restricted list)

### F2. Transparency Panel
Show teachers:
- Applied rules summary (human-readable)
- Metrics summary (computed)
- “Lexile-aligned” disclaimer language

### F3. Export & Classroom Use
- Export formats:
  - Print PDF
  - Web view
  - Optional: slide story (image placeholders)

---

## Milestone H — Safegloss Auth & Glossary Integration

### H1. Auth Integration (Safegloss ↔ Safegloss-Legacy)
```
- Implement shared authentication or SSO between safegloss and safegloss-legacy
- Ensure consistent user identities (teacher, student, admin) across both apps
- Support token-based auth (JWT or session bridge)
- Enforce permission checks consistently in both systems
```

### H2. Story as Media Type in Safegloss
```
- Add a new media format: "AI-Generated Story"
- Allow stories generated in safegloss-legacy to appear as selectable media in Safegloss
- Treat stories as first-class learning texts (similar to books, articles, videos)
- Store story metadata:
  - age band
  - Lexile band (approx.)
  - genre
  - theme
  - generation timestamp
```

### H3. Glossary ↔ Story Linking
```
- Allow a Safegloss glossary to be explicitly linked to one or more stories
- Enable story generation using glossary-controlled vocabulary
- Support bidirectional navigation:
  - From a story → view linked glossary terms
  - From a glossary → view related stories
```

### H4. Unified Authoring Flow
```
- Allow glossary creation/editing workflows in safegloss-legacy to reuse Safegloss glossary infrastructure
- Centralize glossary management logic in Safegloss
- safegloss-legacy becomes a consumer of glossary authoring APIs
- Ensure versioning and ownership rules remain consistent
```

**Acceptance Criteria**
```
- A teacher logged into either app can access their glossaries and stories seamlessly
- Stories generated in safegloss-legacy can be attached to glossaries in Safegloss
- Vocabulary constraints flow cleanly from Safegloss → story generation
```

 (Primary references: QUIZ_TO_LEARNING_OBJECTIVES_AND_STANDARDS.md, ROADMAP.md)

## Milestone I — AI Quiz Generation & Assessment ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**

- `rules/quiz_rules.json` - Comprehensive quiz rules with:
  - Question type definitions (mcq_single, mcq_multi, true_false, short_answer, long_answer, cloze, matching, ordering)
  - Bloom's taxonomy alignment (remember through create)
  - Question categories (literal_comprehension, inferential_comprehension, vocabulary, text_structure, author_purpose, critical_thinking)
  - Age-band specific constraints and question distributions
  - Assessment modes (study_mode, exam_mode)
  - Story and glossary alignment rules
- `core/story_engine/quiz_profile_builder.py` - QuizProfileBuilder with:
  - QuizProfile dataclass with pedagogical constraints
  - BloomConstraints and CategoryConstraints
  - AlignmentSource for story/glossary linking
  - QuestionTypeConstraints per question type
  - QuizRulesLoader for quiz rules access
- `core/story_engine/quiz_prompt_composer.py` - QuizPromptComposer with:
  - Structured prompt sections (source material, glossary, question types, Bloom's, categories, language, output format)
  - ComposedQuizPrompt with JSON output specification
  - Age-appropriate language constraints
  - Assessment mode feature configuration
- `core/story_engine/quiz_validator.py` - QuizValidator with:
  - JSON parsing and structure validation
  - Question type constraint validation
  - Bloom's taxonomy and category distribution checking
  - Story/glossary alignment verification
  - Language appropriateness checks
  - QuizValidationResult with scoring and detailed issues

### I1. Quiz Generator Service

- Build an AI-powered quiz generator that operates on:
  - AI-generated stories
  - Linked glossaries
- Support multiple question types:
  - multiple choice (single and multi-answer)
  - short answer
  - long answer / extended response
  - vocabulary matching
  - cloze (fill-in-the-blank)
  - ordering / sequencing

### I2. Quiz Pedagogical Constraints

- Align quiz difficulty with:
  - story age band
  - Lexile band
  - glossary vocabulary level
- Ensure questions test:
  - literal comprehension
  - vocabulary understanding
  - basic inference (where age-appropriate)
  - text structure
  - author's purpose (older readers)
  - critical thinking (older readers)

### I3. Quiz ↔ Story ↔ Glossary Alignment

- Each quiz question should reference:
  - a specific part of the story
  - or a specific glossary term
- Store traceability metadata for each question

### I4. Assessment Modes

- Study Mode:
  - hints allowed
  - glossary access allowed
  - immediate feedback
  - detailed explanations
- Exam Mode:
  - no hints
  - limited glossary access (configurable)
  - delayed feedback

### I5. Storage & Reuse

- Persist quizzes so teachers can:
  - reuse
  - edit
  - regenerate variants
- Allow quizzes to be shared across classes

### Acceptance Criteria

- A teacher can generate a quiz directly from an AI-generated story ✅
- Quiz difficulty matches the story's constraints ✅
- Each quiz question is explainable and traceable ✅
- Quiz validation ensures pedagogical alignment ✅

(Primary references: AI_QUIZ_GENERATION_AND_VALIDATION.md, QUIZ_TO_LEARNING_OBJECTIVES_AND_STANDARDS.md, QUIZ_VALIDATION_AND_ANALYTICS.md, STANDARDS_ALIGNED_ASSESSMENT_CORPORA.md)

## Milestone G — Quality, Testing, and Observability ✅ COMPLETE

**Completed:** 2025-12-15

**Implementation:**

- `core/story_engine/tests/` - Comprehensive test suite:
  - `test_rules.py` - Unit tests for rules loading and validation
  - `test_profile_builder.py` - Tests for profile building and rule merging
  - `test_text_metrics.py` - Tests for metric extraction
  - `test_validator.py` - Tests for story validation
  - `test_prompt_composer.py` - Tests including golden tests for prompt stability
- `core/story_engine/telemetry.py` - TelemetryLogger with GenerationRecord, context manager support
- `core/story_engine/evaluation.py` - EvaluationHarness for batch testing with EvaluationReport

### G1. Automated Tests

- Unit tests for:
  - rule merging (profile builder)
  - prompt composer output stability (golden tests)
  - metric extractors (text_metrics)
  - validator (corpus-derived thresholds)
- Golden tests:
  - Known inputs → identical prompt output verified

### G2. Telemetry

Log per story via TelemetryLogger:

- request params (age_band, genre, lexile_band, theme, etc.)
- merged profile (profile_hash, profile_version)
- prompt hash
- validation metrics (score, issues)
- iteration count
- final metrics (word_count, avg_sentence_length, dialogue_ratio)

### G3. Evaluation Harness

- EvaluationHarness with test matrix generation
- Batch evaluation across bands/genres/styles
- EvaluationReport with pass rate distributions
- Prompt-only and full story evaluation modes

### Acceptance Criteria

- Tests verify rule merging and prompt stability ✅
- Telemetry captures complete generation records ✅
- Evaluation harness can batch-test across all parameter combinations ✅

---

## 4. Backlog & Stretch Goals

### S1. Multi-lingual Story Generation
- Generate story in target language with separate level constraints
- Ensure culturally appropriate content

### S2. Student Personalization
- Use student interests to set theme/setting (with safe filtering)

### S3. “Digital Story” Output
- Produce scene prompts from paragraphs
- Generate images per scene
- Create a slideshow-style animation with narration (where available)

---

## 5. Implementation Notes (Practical Guidance)

### Where Rules Live
- Store JSON rule files in `/rules/`
- Keep them versioned in git
- Changes to rules should be reviewed like code

### How to Use the Rule Files
- Backend loads rule files at startup (cache)
- Request merges:
  - age → genre → lexile → optional style → optional ELL → vocab overlays
- Prompt composer emits deterministic phrasing from the merged profile

### Auditing
- Store the merged profile and computed metrics with each story so results are explainable and debuggable.

---

## 6. Suggested Development Order

1) Milestone A (Rules + Prompt Composer)
2) Milestone B (Validation loop)
3) Milestone F (UI integration)
4) Milestone C (Corpora analytics)
5) Milestone D/E (Style + Vocabulary control)
6) Milestone G (Eval harness + telemetry)
7) Milestone H (Safegloss integration)
8) Milestone I (AI quizzes & assessment)

---

## Definition of Done

The system is “done” when:
- A teacher can generate a story with chosen age, genre, and Lexile band
- The system validates and corrects to stay within band proxies
- The applied rules are transparent to the teacher
- The system is auditable, testable, and stable across runs

---