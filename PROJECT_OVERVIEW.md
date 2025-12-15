# Project Overview

Safegloss Legacy is a Django 5 + PostgreSQL reading experiment platform that delivers leveled stories in multiple reader modes, overlays glossary tooling, runs assessments, and measures the impact of UI/UX variants. The implementation follows two primary sources of truth:
- `docs/reading_experiment_spec.md` — architecture, models, flows, AI/analytics integration
- `docs/reading_experiment_wireframes.md` — UI structure and naming for student, instructor, and researcher views

## Core Capabilities
- Reading engine: continuous text, card slideshow, and movie mode (timed segments + media) with mode controls per lesson and experiment treatment.
- Glossary engine: per-story glossary with AI candidate generation, instructor curation, and term occurrence indexing for inline gloss spans/tooltips.
- Quiz/assessment engine: item bank, quiz assembly, randomized sessions, per-question logging, scoring, and review/feedback modes.
- Experiment engine: weighted variant assignment with JSON parameters controlling reader/gloss behavior and logged into events for analysis.
- AI integrations: OpenAI-backed story, glossary, and quiz generation; PostHog analytics on both client and server events.
- Telemetry: Reading events, gloss clicks, quiz sessions/submissions, and experiment keys/variants recorded for dashboards and exports.

## Tech Stack
- Backend: Python 3.12+, Django 5.x, PostgreSQL 14+, django-allauth, django-extensions, django-environ, gunicorn, whitenoise.
- Frontend: Bootstrap 5, HTMX-first partial updates; optional lightweight JS for card slider and movie player.
- Tooling: OpenAI SDK, PostHog JS/Python, textstat for readability metrics; crispy-forms + bootstrap5 helpers.

## Repository Layout (high level)
- `core/` — Django app (models, views, templates, static assets, story_engine utilities).
- `rgx_project/` — Django project settings and URLs.
- `docs/` — specifications, wireframes, AI prompting guides, roadmap, and VS Code agent prompt context.
- `rules/` — JSON rule libraries (age, lexile, genre, ELL, style profiles) consumed by the prompt composer.
- `templates/` and `staticfiles/` — collected/static assets and auth templates.
- `render.yaml` — Render deployment definition (web service + Postgres).
- `requirements.txt` — Python dependencies.

## Development Quickstart
Create a virtualenv, install dependencies, and add a dev env file (not tracked) to load settings via `django-environ` or `python-dotenv`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p config
cat > config/dev.env <<'EOF'
SECRET_KEY=dev-secret-key
DEBUG=True
DATABASE_URL=postgres://rgx_dev:rgx_dev_pass@localhost:5432/rgx_experiment_dev
OPENAI_API_KEY=dev-placeholder
POSTHOG_API_KEY=dev-placeholder
POSTHOG_HOST=https://app.posthog.com
EOF
python manage.py migrate
python manage.py runserver
```

## Deployment (Render)
- `render.yaml` builds with `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`, serves via `gunicorn rgx_project.wsgi:application`, and provisions a Postgres instance with `DATABASE_URL` injected.
- Production env vars to set: `SECRET_KEY`, `DATABASE_URL`, `OPENAI_API_KEY`, `POSTHOG_API_KEY`, `POSTHOG_HOST`, and `DEBUG=0`.

## Key Documents to Reference
- Product & UX: `docs/reading_experiment_spec.md`, `docs/reading_experiment_wireframes.md`
- Roadmap: `docs/ROADMAP.md`
- AI prompting & rules: `docs/LEXILE_STORY_GENERATION.md`, `docs/LEXILE_YOUNG_READERS_EXPERTISE.md`, `docs/NATURAL_LANGUAGE_RULE_PHRASES.md`, `docs/AI_QUIZ_GENERATION_AND_VALIDATION.md`
- Rule data: `rules/*.json`

## Suggested Next Steps
- Align any new code to the spec/wireframes naming and flows.
- Implement env loading from `config/dev.env` in `rgx_project/settings.py` if not already wired.
- Add sanity tests for experiment assignment, glossary indexing, and quiz scoring per spec.
