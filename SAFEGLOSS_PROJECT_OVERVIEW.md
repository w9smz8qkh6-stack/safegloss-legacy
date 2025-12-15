# Safegloss Project Overview

This overview summarizes the `/safegloss` Django project (Safegloss v2) and its operational docs for quick onboarding.

## What the app does
- Teacher-facing glossary authoring with student-facing readers; supports study vs exam modes (see `docs/SAFEGLOSS_REFACTOR.MD` for reader mode refactor).
- AI-assisted term translation/definition generation (OpenAI), plus optional Google TTS/translation; background tasks run via Django-Q.
- Rostering and enrollment flows including OneRoster v1.1 LMS import (`docs/OneRoster_LMS_Integration.md`).
- Payments and auth: Django-Allauth (Google OAuth setup in `docs/DJANGO_SAFEGLOSS_CONFIG.md`), Stripe keys defined in Render env group.
- Print/export and accessibility improvements tracked in `docs/PROJECT_ROADMAP.MD`.

## Tech stack & services
- Django 5.x, PostgreSQL 15, Redis (Django-Q broker), Gunicorn + WhiteNoise.
- Key deps: `django-allauth`, `django-q2`, `django-axes`, `openai`, `stripe`, `redis`, `python-dotenv`, `dj-database-url`.
- Two Render services per `render.yaml`: web (`gunicorn safeglossv2.wsgi`) and worker (`python manage.py qcluster`), both sharing Postgres + Redis.

## Data model snapshot
- `core/models.py` declares mostly `managed = False` models mapped to an existing schema (courses, standards, media, glossary terms, roles, subscription tiers, etc.). Schema SQL lives in `db/schema_v3_15.sql` with lookup seeds in `db/seed_lookup_data.sql`.
- Migration directory is present but tables come from the loaded schema; run core Django migrations for auth/allauth/axes, then load schema SQL.

## Key docs
- Local dev: `docs/LOCAL_DEV.md` (Postgres URL, Redis, how to load schema/seed and run server + qcluster).
- Deployment: `docs/RENDER_DEPLOY.md` and `render.yaml` (env vars, health checks, worker tuning).
- Domain/Google OAuth setup: `docs/DJANGO_SAFEGLOSS_CONFIG.md`.
- Reader mode refactor: `docs/SAFEGLOSS_REFACTOR.MD`.
- LMS import: `docs/OneRoster_LMS_Integration.md`.
- Roadmap/security/print/export guidance: `docs/PROJECT_ROADMAP.MD`.

## Getting started (summary)
1) Copy `.env.example` to `.env`, set DB/Redis URLs (see `docs/LOCAL_DEV.md`).  
2) `pip install -r requirements.txt` (Python 3.11+).  
3) `python manage.py migrate` (built-in apps), then load `db/schema_v3_15.sql` and `db/seed_lookup_data.sql`.  
4) Run services: `python manage.py runserver` and `python manage.py qcluster`.  
5) For Render: ensure env group `safegloss-env` includes secret keys (DJANGO_SECRET_KEY, OPENAI_API_KEY, Stripe, SendGrid, etc.) and deploy web + worker.
