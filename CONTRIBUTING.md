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
python scripts/check_documentation_updates.py
```

## Documentation completion

Documentation is part of the implementation. Every change to code,
reconstructed behavior, interfaces, tests, scripts, dependencies,
configuration, security, deployment, operations, architecture, research
interpretation, or user-visible output must update the relevant durable
documentation during the same task. Follow
[`docs/DOCUMENTATION_MAINTENANCE.md`](docs/DOCUMENTATION_MAINTENANCE.md) and
compare the finished work semantically with the reconstruction specification,
repository audit, cited evidence, setup, security, rights, and user guidance.
The path check above is evidence only; it cannot establish historical or
explanatory accuracy.

Keep credentials, user data, database exports, uploaded media, and generated
artifacts out of commits. Use `.env.example` to document configuration names
with placeholders only.

Pull requests should explain the behavior changed, any migrations or deployment
impact, documentation updated, and checks that were run. Keep changes focused
and add regression coverage when practical.
