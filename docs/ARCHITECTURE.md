# Architecture and operations

## Shape

SafeGloss Legacy is deliberately a small LAMP-style monolith. Apache serves
`public/index.php`, which dispatches all page and form actions. Shared bootstrap,
domain, mail, and rendering functions live in `src/`. MySQL owns accounts,
content, assignments, attempts, instrumentation, scores, and captured reports.

```text
Browser
  ├─ index.php: role workflows and forms
  ├─ event.php: gloss open/close JSON endpoint
  └─ assets/: archival visual treatment and interaction JavaScript
          │
          ▼
PHP 8.4 / Apache ── PDO prepared statements ── MySQL 8.4
          │
          └─ database capture (default) or explicit TLS SMTP
```

This is an intentionally direct reconstruction, not a framework starter. Newer
SafeGloss repositories may reference concepts but should not inherit this
architecture.

## Data and research invariants

- `treatment_mode` is the authoritative semantic value. `contiguous` means the
  near-word popover; `margin` means the non-contiguous right-margin panel.
- `treatment_label` preserves A/B reporting, and `sites.label_a_mode` records
  which conflicting dissertation mapping a replication selected.
- Treatment values are copied onto each lesson attempt and event so later site
  changes cannot rewrite historical sessions.
- `system_events.server_recorded_at` is authoritative UTC MySQL time with six
  fractional digits. Validated client time is supplementary.
- Quiz choices are shuffled only for display; correctness is stored on the
  authored choice and never exposed in the student's score detail.
- Mail delivery failures never roll back the completed attempt. Every report is
  stored in `mail_outbox` as captured, sent, or failed.

## Trust boundaries

Public registration requires a site code and can create only student or
instructor accounts. Researcher accounts require the CLI. Every manager query is
scoped to the signed-in instructor/site, and student lessons and attempts are
checked through roster membership and ownership.

Rich content passes through an allowlist sanitizer. JavaScript receives only
sanitized definition markup encoded in data attributes. Forms and the event
endpoint require a session CSRF token. Security headers prohibit third-party
scripts, framing, and broad browser permissions.

## Containers and persistence

`compose.yaml` builds the application image and uses a pinned MySQL image. The
web root and application source are owned by root and the container runs as
`www-data` with a read-only filesystem. Only temporary Apache/session paths are
writable. MySQL persists in the named `legacy_mysql` volume and runs the initial
schema only when that volume is empty.

There is no documented production deployment target. A deployment must add
HTTPS termination, secret management, backups/restores, monitoring, retention,
and an institutionally approved research-data plan.

## Current reconstruction boundary

The runnable slice covers all three roles, the treatment and lesson lifecycle,
instrumentation, scoring, logs, and report capture/SMTP. Historical XML
import/export remains unimplemented because the dissertation does not reproduce
the Captivate or lesson schema. Manager screens currently add and list records;
full edit/delete parity and the historical rich editor/word counter remain
fidelity work. These limitations are explicit so deployability is not mistaken
for perfect recovery.
