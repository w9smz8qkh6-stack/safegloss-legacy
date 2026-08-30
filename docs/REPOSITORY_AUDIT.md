# Current repository audit

## Conclusion

The active tree is now a PHP/MySQL reconstruction of the dissertation platform,
not the later Django literacy product. It is reproducible, deployable for local
study, and implements the representative research workflow. Git history remains
the archive of the removed Django phase and its unrelated AI, standards,
acquisition, PWA, and product experiments.

This is reconstructed software, not recovered original source. The dissertation
governs factual claims; `docs/RECONSTRUCTION_SPEC.md` labels conflicts,
inferences, and safety adaptations.

## Established replacement boundary

- `public/` contains the Apache entry points, period-informed responsive CSS,
  and the two gloss interactions.
- `src/` contains configuration, PDO access, security/session handling, domain
  calculations, SMTP/database reporting, and shared UI.
- `database/migrations/001_initial.sql` defines the MySQL research/content
  schema and UTC microsecond instrumentation.
- `bin/setup.php` provisions sites and non-public researcher/instructor
  accounts.
- `compose.yaml` and `Dockerfile` provide pinned PHP/Apache and MySQL execution.
- `tests/domain_test.php` protects semantic treatment mapping, alternating
  assignment, scoring, microsecond durations, and gloss event pairing.

The current tree deliberately excludes Django, PostgreSQL, Google OAuth, AI
generation, external book acquisition, standards and course catalogs, reading
level rules, background jobs, analytics products, and offline/PWA behavior.

## Verified representative workflow

Against a fresh MySQL volume, the reconstruction has been exercised through its
HTTP interfaces for:

- site provisioning and instructor registration/login;
- story, glossary, quiz, and roster-assigned lesson creation;
- two student registrations receiving both alternating semantic treatments;
- the contiguous student's near-word gloss rendering and separate open/close
  event capture;
- reading-to-quiz progression, randomized choices, a scored submission, and
  student score display; and
- a detailed session report stored with `captured` status under the default
  non-delivering mail transport.

Browser review at desktop and mobile widths found no horizontal overflow,
confirmed responsive stacking and 44-pixel primary targets, verified keyboard
Escape dismissal/focus return for the near gloss, and produced no console
warnings or errors.

## Remaining fidelity work

The following dissertation-described behavior is not yet complete:

- Captivate-compatible glossary XML and lesson XML import/export; the exact
  historical schemas are not reproduced in the dissertation;
- full edit/delete parity in authoring managers;
- the historical reduced CKEditor controls, live word counter, language
  equivalent authoring UI, and multimedia inputs;
- formal load evidence for the documented 50–60-user target; and
- broader automated HTTP authorization and lifecycle coverage.

These gaps do not change the implemented treatment or measurement semantics and
must remain visible until primary evidence or additional reconstruction work
resolves them.

## Delivery state

Legacy has no production deployment target. Cohesive verified changes are
committed and pushed under the suite's standing delivery cadence, but running a
local Compose stack is verification rather than production publication.
