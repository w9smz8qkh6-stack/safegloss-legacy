# EZGloss Regeneration Guide

Blueprint for recreating the EZGloss Django app from scratch. Focuses on architecture, data model, features, endpoints, and external dependencies so an agent can rebuild without the original code.

## Stack & Core Config
- Django 4.2.26, Python 3.11+; Bootstrap 5 via crispy-forms/`django-bootstrap5`.
- Auth: `django-allauth` (Google/Microsoft/Apple providers), roles mapped to groups (`accounts/constants.py`).
- Task queue: `django-q` (Redis preferred; ORM fallback). Settings tuned for Render starter instances.
- Storage: static via WhiteNoise; media under `/media/`.
- Optional AI/TTS: OpenAI (translations + TTS), Google TTS, AWS Polly. Feature flags via env vars.
- Debug: `django-debug-toolbar` in `DEBUG`; `django-axes` for login lockout.
- Frontend JS: small vanilla modules in `static/js` (dashboard polling, media AI helpers, TOC metadata, status pollers).

## Environment Variables (key)
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- Database: `DATABASE_URL` (preferred) **or** `DB_ENGINE` (`postgresql`|`mysql`|`sqlite`), `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- Redis/queue: `REDIS_URL`, `DJANGO_Q_WORKERS`, `DJANGO_Q_TIMEOUT`, `DJANGO_Q_RETRY`, `DJANGO_Q_QUEUE_LIMIT`, `DJANGO_Q_BULK`, `DJANGO_Q_SAVE_LIMIT`, `DJANGO_Q_MAX_ATTEMPTS`.
- OpenAI: `OPENAI_API_KEY`, `OPENAI_TRANSLATION_MODEL` (default `gpt-4o-mini`), `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE`, `OPENAI_MAX_CONCURRENT_REQUESTS`, `OPENAI_RATE_LIMIT_MAX_RETRIES`, `OPENAI_RATE_LIMIT_BASE_DELAY`.
- Google TTS: `GOOGLE_*` maps (`GOOGLE_TTS_LANGUAGE_CODE_MAP`, `GOOGLE_TTS_LANGUAGE_VOICE_MAP`, `GOOGLE_TTS_DEFAULT_LANGUAGE_CODE`, etc.).
- AWS Polly: `AWS_POLLY_REGION`, `AWS_POLLY_VOICE_ID`, `AWS_POLLY_ENGINE`, `AWS_POLLY_OUTPUT_FORMAT`, `AWS_POLLY_SAMPLE_RATE`, `AWS_*` creds, `AWS_POLLY_LANGUAGE_VOICE_MAP`.
- Admin secret for sensitive endpoints: `ADMIN_SECRET_KEY`.

## Apps & Structure
- `core`: data models (DB-first, `managed=False`), views, forms, services (OpenAI/Google TTS/Polly, auto-translate, TOC consensus), admin registrations.
- `accounts`: signup/login helpers, role enforcement (`RoleRequiredMixin`/decorator), nearby school lookup, tier selection view, profile context processor.
- Project: `ezsite` with `settings.py`, `urls.py`, ASGI/WSGI.
- Templates root `templates/` with feature subfolders (`glossary`, `media`, `course`, `offering`, `dashboard`, `account`, `registration`, `socialaccount`, etc.).
- Static assets: `static/css`, `static/js`, `static/img`, `static/samples`.
- DB SQL scripts in `db/` (`glossary_database_schema.sql`, view scripts, migrations); many models rely on pre-existing tables/views.

## Data Model (summary)
> All models are unmanaged (`managed=False`) and assume the DB schema already exists.
- Lookup: `Lang` (name/endonym/ISO), `UserRole`, `PartOfSpeech`, `SchoolType`, `SchoolLevel`, `SubjectArea`, `MediaFormat`.
- User: `UserProfile` (links to `auth.User`, role, school, subject areas, timezone, avatar, points).
- Media: `Media` (format/lang/owner/urls + descriptions), `MediaMetadataDefinition`, `MediaMetadata`, `MediaToc` (hierarchical TOC nodes with parent/position/locator).
- Glossary: `Glossary` (title/description/cover, owner, optional media), `Term` (lang, text, definition, sample, IPA, image, audio byte fields + deprecated URL fields), `GlossaryTerm` (glossary ↔ term, TOC location, order), `Translation` (base term → equivalent term per glossary), `TranslationJobLog` (status per term/lang), `BatchProcessingMetrics` (timing for enhancement/translation batches).
- Courses: `Course` (school/level/subject/owner, standards), `CourseGlossary` (course ↔ glossary), `CourseMedia` (course ↔ media).
- Offerings: `CourseOffering` (course, title, dates, timezone, teacher, mode `study|exam`, M2M members/resources), `CourseOfferingResource`, `CourseOfferingMember`, `Exam` (window per offering), `CourseOfferingModeEvent` (mode change audit).
- Engagement: `UserFavorite`, `UserNote`, `UserClickLog`, `UserPointTransaction`, `UserLoginEvent`.
- DB views: `GlossaryExamModeV`, `MediaTocFlatV`, `TranslationPairsV`.
- Standards: `StandardsAuthority`, `InstructionalStandard` (code/name/subject/level), `CourseStandard` (course ↔ standard).

## URL Map (major features)
Root/home: `""` → `core.home`; `dashboard/` plus role-specific dashboards.

Auth/Accounts:
- `accounts/` (allauth), `accounts/api/schools/nearby/` (geofiltered schools), `accounts/select-tier/`.

Health/Demo:
- `health/`, `health/teacher/`; `exam/author/` demo view.

Media CRUD & TOC:
- `media/create|edit|delete|view|list/`, `media/ai-enhance/`.
- Wizard: `media/wizard/step1/`, `media/wizard/step2/<media_id>/`.
- TOC editor: `media/<media_id>/toc/` (page), `toc/data`, `toc/add|update|delete`, `toc/reorder`, `toc/ai-generate` (from TOC or from media details).

Glossary CRUD & Wizard:
- `glossary/list|school-list|create|view|edit|delete/`, `glossary/auto-create/` (AI from media), `glossary/user-notes/`.
- Wizard: `glossary/wizard/choice`, steps 1–4 (`/wizard/step1/`, `/step2/<id>/`, `/step3/<id>/`, `/step4/<id>/`).
- Bulk add terms page: `glossary/<id>/bulk-add/`.
- Context fetch: `glossary/<id>/context/`.

Term Management & AI:
- List/add/update/delete: `glossary/<gid>/term/list|add|<tid>/update|<tid>/delete`.
- AI enhance: `term/<tid>/enhance` + preview `enhance-new`; `term/fetch-definition`.
- Translation: `term/<tid>/translations/` list/add/update/delete; `term/<tid>/ai-translate`, `ai-apply`, `ai-translate/openai`.
- Audio: `term/tts-audio/`, `/term/<tid>/audio/` (main), `/definition/`, `/sample/` (binary from DB).
- TOC helpers: `glossary/<gid>/toc/options`, `/toc/tree`.
- Master/translation explorer: `term/master-list/`, `term/<tid>/translations/…`.
- Part of speech list: `part-of-speech/list/`.

Glossary Reader/Writer UX:
- Reader: `glossary/<gid>/reader`, data endpoint `/reader-data` (and legacy alias), favorites toggle, notes save, TOC consensus endpoint.
- Writer/editor: `glossary/<gid>/writer`.
- Event logging: `glossary/reader/log-event`, `clicks/log`, `clicks/card-flips/count`.
- Favorites list: `favorites/list/`.
- Search: `search/` (glossary search).
- Gamification: `points/award`, `points/total`.

Import/Export (core/views_import_export.py):
- Import UI: `glossary/<gid>/import/` (page), `import/preview`, `import/confirm`; template download at `glossary/import-template/`.
- Export: CSV/Excel/JSON/PDF at `glossary/<gid>/export/{csv|excel|json|pdf}` (PDF supports `?lang=xx&include_definitions=1&include_samples=0`).

Courses/Offerings/Enrollments:
- Courses: `course/list|create|<id>/view|edit|delete`.
- Course media: `course/<cid>/media` manage, `media/add`, `course_media_id/update|remove`, `course/<cid>/media-glossaries`.
- Offerings: `offering/list|create|<id>/view|edit|delete`, toggle mode `offering/<id>/toggle-mode`, mode status API `api/offering/<id>/mode`, toggle via API `api/offering/<id>/mode/toggle`.
- Offering resources: `offering/<id>/resources` list/add/remove, `offering/<id>/media-glossaries`.
- Offering members: `offering/<id>/members` (page), data endpoint, add, bulk add, remove.
- Offering exams: `offering/<id>/exams` list, create/edit/delete exam.
- Student enrollments/stats: `student/enrollments/students`, `student/enrollments/<profile_id>/[add|remove|]`, `student/stats/*`, `enrollment/list`.
- Reports/APIs: `api/offering/<id>/report`, `/report/export`.

Admin & Support APIs:
- Login-as (superuser-only): `api/users-list`, `api/login-as`.
- Admin glossary reset: `api/admin/glossary/<gid>/reset-terms` (guarded by `ADMIN_SECRET_KEY`).
- Queue/status: `api/translation-queue-status`, `api/qcluster/status`, `api/translation-stats`, `api/openai-quota/status`.

## Frontend Views & Templates (high level)
- Base layouts: `templates/base.html`, `base_minimal.html`.
- Home/dashboard: `home.html`, `dashboard.html`, `dashboards/` role-specific includes; JS `static/js/dashboard.js`, `status-poller.js`, `mode-poller.js`.
- Glossary screens: `templates/glossary/*.html`
  - Reader (`reader.html` + backup), Writer, Terms modal (`terms.html`), Edit/import/export pages, Wizard steps (`wizard_choice`, `wizard_step2_media`, `wizard_step2_toc`, `wizard_step4_bulk_add`, `wizard_step5_bulk_review`), partials (`partials/glossary_toc_term_template.html`), deprecated wizard copies in `glossary/deprecatred/`.
  - Term form JS inline initializes `loadTOCOptions`, `loadTermsList`, `setupTermForm`.
- Media: `templates/media/*` for CRUD and TOC tree (Fancytree), AI enhance.
- Course/Offering/School templates under `templates/course`, `templates/offering`, `templates/school`.
- Account/auth: `templates/account`, `registration`, `socialaccount`.

## Services & Background Processing
- `core/services/openai_term_service.py`: builds prompts, batches translations, handles rate limits, parses responses, concurrency limit via settings.
- `core/services/auto_translate.py`: ensures translations per student/offering, message helpers.
- TTS services: `google_tts.py`, `polly_tts.py`, OpenAI TTS via `settings.OPENAI_TTS_*`; helpers map language → voice.
- `core/services/toc_consensus.py`: aggregates TOC votes/consensus.
- `core/services/quota_tracker.py|quota_cache.py`: simple quota accounting.
- `core/tasks.py`: sample task `debug_log_connection_id` for django-q.

## Authentication & Roles
- Roles limited to Teacher/Student (plus Django superuser for admin). `ROLE_TO_GROUP` maps to groups.
- `RoleRequiredMixin`/`role_required` used in views (fallback no-op if accounts app missing).
- Allauth signup forms in `accounts/forms.py` capture role, timezone, school, subject areas; context processor exposes `user_profile`.

## Admin Interface
- Admin registrations for main models with search/filter; inlines for TOC and Glossary terms; custom forms for timezone select widgets.
- Useful for seeding Langs, Parts of Speech, Schools, etc.

## Logging & Metrics
- Logging to `logs/django.log` by default; multiple app logs in repo (`runserver.log`, `qcluster_*.log`, etc. for reference).
- `UserClickLog` + `UserPointTransaction` record engagement; endpoints to fetch counts.

## Rebuild Checklist
1. Create Django project `ezsite`, apps `core`, `accounts`; install requirements.
2. Bring in settings similar to `ezsite/settings.py` (env-driven DB, Redis/queue, OpenAI/TTS, allauth, axes, whitenoise, debug toolbar).
3. Recreate unmanaged models listed above to match DB schema (import from existing SQL in `db/`).
4. Wire URLs exactly as in `ezsite/urls.py` (see sections above).
5. Implement views:
   - `core/views.py`: dashboards, media CRUD/TOC, glossary CRUD/wizard, term CRUD + AI translate/enhance, reader/writer, favorites/notes, search, course/offering/enrollment/exam flows, gamification endpoints, health endpoints, admin reset, login-as, reporting APIs.
   - `core/views_import_export.py`: import preview/confirm, export CSV/Excel/JSON/PDF, template download.
   - `accounts/views.py`: nearby schools, tier selection.
6. Forms: `core/forms.py` (GlossaryForm, SchoolForm with Select2, Term/CourseOffering/Exam admin forms), `accounts/forms.py` (signup variants, profile edit).
7. Admin: `core/admin.py` hooking forms/inlines; ensure select2/static admin widgets.
8. Templates/static: recreate structure noted above; Bootstrap 5 styling; JS modules for dashboard polling, media AI, TOC metadata, course standards select (`static/js/course-standards.js`).
9. Task queue: configure `django-q` with Redis if available; include `core.tasks.debug_log_connection_id` sample.
10. Seed data: load SQL from `db/` (tables + views like `translation_pairs_v`, `media_toc_flat_v`, `glossary_exam_mode_v`); add Langs/Parts of Speech/School metadata.
11. Validate: `/health`, `/health/teacher` respond JSON; admin site works; basic flows—create media, TOC, glossary, add terms, run AI translate, export PDF/CSV, create course/offering, enroll students, toggle study/exam mode, reader loads cards/favorites/notes logging.

## Reference Files (in repo)
- `README.md` for quickstart; many analyses in root Markdown files (performance, batching, AI quotas).
- Logs/examples: `qcluster*.log`, `test_*` timing files.
- DB SQL: `db/glossary_database_schema.sql`, `db/views/migrate_views.sql`, migrations folder for standards/points/click logs.
