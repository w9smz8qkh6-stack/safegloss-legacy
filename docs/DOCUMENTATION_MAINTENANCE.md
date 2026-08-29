# Documentation maintenance

Documentation is part of completion for SafeGloss Legacy. Every task that
changes source code, reconstructed behavior, interfaces, tests, scripts,
dependencies, configuration, security, deployment, operations, architecture,
research interpretation, or user-visible output must review and update the
relevant durable documentation during the same task.

## Documentation map

- `README.md` and `CONTRIBUTING.md` govern repository purpose, safe setup, and
  contributor workflow.
- `docs/RECONSTRUCTION_SPEC.md` is the evidence-based target. Behavior derived
  from the dissertation must cite the relevant chapter, section, figure,
  table, or appendix and distinguish facts, reconstruction choices, and
  unresolved ambiguity.
- `docs/REPOSITORY_AUDIT.md` records current drift, reusable evidence, missing
  behavior, and the replacement boundary.
- `PROJECT_OVERVIEW.md`, `SAFEGLOSS_PROJECT_OVERVIEW.md`, and older feature
  plans are historical or transitional unless the reconstruction documents
  explicitly make them current. Do not let them override archival evidence.
- `SECURITY.md`, `.env.example`, setup/deployment guidance, data documentation,
  and user-facing help govern operational, privacy, rights, and interface
  claims.
- Active project-state, capability, workstream, decision, or changelog records
  must be updated when their claims or status change.

## Completion procedure

Inspect the finished implementation and compare every governing document by
meaning. Update affected setup instructions, architecture, operational
runbooks, public contracts, security and rights guidance, user documentation,
reconstruction decisions, project state, and changelog material. Preserve
citations and clearly label inferences.

Use repository-owned tooling to regenerate facts, inventories, or indexes when
available and safe, then review the diff. A passing generator, freshness, link,
or path check is evidence only and does not prove that explanatory text or
historical interpretation is accurate.

Run `python scripts/check_documentation_updates.py` and the affected repository
checks before handoff. If another canonical SafeGloss repository depends on an
archival fact changed here, update its affected documentation in the original
task while keeping histories and verification separate.

If an affected repository or source is unavailable, overlapping work prevents
a safe update, redistribution rights are unresolved, or a necessary fact
cannot be verified, the task is incomplete. Name the exact repository,
document, unresolved claim, and blocker.

Documentation completion is a prerequisite for Legacy's standing delivery
cadence. After relevant checks pass, commit task-owned changes and push the
current branch to its existing configured upstream at a cohesive green
checkpoint and task completion. Local edits, commits, pushes, and any future
deployment remain distinct checked steps. Never include unrelated dirty work,
force-push, rewrite history, bypass branch protection, expose secrets or
restricted materials, or proceed past failed checks. Legacy has no production
deployment target unless a current repository runbook establishes one.
Protected branches use scoped task branches and pull requests; merge only after
all required checks pass and no required human approval is outstanding.
