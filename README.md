# Safegloss Legacy

Safegloss Legacy is a Django application for creating and delivering leveled
reading material, glossaries, quizzes, and standards-aligned learning content.
It also contains an older reading-experiment implementation under `rgx/` for
historical reference.

This repository is a legacy, in-development codebase. It is suitable for
review and experimentation, but it should not be treated as a supported or
production-ready release without an independent security and deployment
review.

## What is here

- `core/` — the current Django app, including authoring, reading, quiz,
  standards, background-job, and story-generation features.
- `acquire/` — external text discovery and acquisition integrations.
- `rgx_project/` — current Django project settings and URLs.
- `rgx/` — an older self-contained snapshot retained for reference.
- `rules/` — versioned JSON constraints used by the story and quiz engines.
- `data/` — local-only standards source material and derived datasets. These
  files are intentionally excluded from the public repository; see
  [`data/README.md`](data/README.md).
- `docs/` — architecture notes, product specifications, and implementation
  guides of varying age.

For a more detailed system summary, see
[`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md). Some design documents describe
planned behavior and may be ahead of the implementation.

## Local setup

Prerequisites:

- Python 3.12+
- PostgreSQL 14+

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example config/dev.env
```

Edit `config/dev.env`, create the configured PostgreSQL database, and then run:

```bash
python manage.py migrate
python manage.py runserver
```

The application can start without optional AI and analytics keys, but the
corresponding integrations will be unavailable.

## Verification

```bash
python manage.py check
pytest -q core/story_engine/tests
```

The current automated suite covers the story-engine utilities. Broader Django
integration coverage is incomplete.

## Security and sensitive data

Configuration belongs in environment variables or the ignored
`config/dev.env`; never commit credentials or production data. See
[`SECURITY.md`](SECURITY.md) for reporting guidance and the repository's
security limitations.

## License

The original Safegloss source code in this repository is available under the
[MIT License](LICENSE). The license does not grant rights to third-party
standards, books, assessment materials, trademarks, or datasets, which are not
included in the public repository.
