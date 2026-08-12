# Contributing

This is a legacy, in-development project. Before opening a substantial change,
use a GitHub issue to confirm that the work fits the intended direction.

## Development checks

Create an isolated environment and install both dependency sets:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Before submitting a pull request, run:

```bash
python manage.py check
pytest -q core/story_engine/tests
```

Keep credentials, user data, database exports, uploaded media, and generated
artifacts out of commits. Use `.env.example` to document configuration names
with placeholders only.

Pull requests should explain the behavior changed, any migrations or deployment
impact, and the checks that were run. Keep changes focused and add regression
coverage when practical.
