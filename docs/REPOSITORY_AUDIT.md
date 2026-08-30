# Current repository audit

Documentation maintenance is now an explicit completion requirement. Any task
that changes the reconstruction, its evidence interpretation, implementation,
operation, or user-visible behavior must update this audit and the other
governing records when their claims are affected; see
`docs/DOCUMENTATION_MAINTENANCE.md`.

Validated, task-owned Legacy changes now follow the suite's standing cadence:
commit and push at cohesive green checkpoints and task completion. Legacy has
no production deployment target unless a current runbook establishes one.
Protected default-branch changes use scoped task branches and required-check
pull requests rather than administrator bypass.

## Conclusion

The checked-in application is not a faithful replica of the system described in
the dissertation. It began in December 2025 as a Django reading-experiment
reconstruction, then quickly became a broader literacy generator. Its Git
history remains valuable evidence of that reconstruction attempt, but its
current architecture and product scope should not govern the archival target.

## What can inform the reconstruction

Several Django concepts correspond to documented original behavior and may be
used as secondary implementation clues after checking them against the
dissertation:

- sites, users, roles, rosters, and roster membership;
- stories, glossaries, terms, and language equivalents;
- lessons that combine a story and quiz and are assigned to rosters;
- multiple-choice questions, randomized choices, submissions, and scores;
- lesson progress, reading events, and gloss-click records; and
- student, instructor/teacher, and researcher-oriented screens.

The templates may also help interpret screenshot details, but they are not
historical source artifacts.

## Drift to remove from the archival product

The following additions are not supported by the dissertation and materially
changed the application's identity:

- Django 5, django-allauth, PostgreSQL, HTMX, Bootstrap, and Render-specific
  Django deployment;
- Google OAuth and the renaming of the documented instructor role to teacher;
- AI and rule-driven story, glossary, and quiz generation;
- reading-level analysis and multiple reader modes;
- external-book acquisition and bookmarks;
- courses, units, standards catalogs, learning objectives, publisher resources,
  provider adapters, and background jobs;
- PostHog-oriented analytics and newer product telemetry; and
- the duplicate `rgx/` Django snapshot.

These features should not be ported into the PHP reconstruction. Git history is
the recovery mechanism for anyone studying the abandoned Django phase.

## Missing or incomplete historical behavior

The current repository does not fully reproduce several central documented
properties:

- the monolithic PHP/MySQL/LAMP deployment model;
- the original registration survey and informed-consent flow;
- explicit balanced treatment assignment and configurable A/B mapping;
- separate open and close events for calculating each gloss duration;
- the original researcher system-log and score-log reports;
- per-submission SMTP session reports;
- Adobe Captivate-compatible glossary XML exchange;
- lesson XML sharing; and
- the original compact dashboard and manager interface shown in the figures.

## Replacement boundary

The reconstruction should replace the executable Django product rather than
wrap or incrementally refactor it. The existing Git history already preserves
the Django phase. Before deletion, the replacement must establish a clean
PHP/MySQL boot path, schema, representative research workflow, and tests so the
repository never passes through an undocumented or irreproducible state.
