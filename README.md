# SafeGloss Legacy

SafeGloss Legacy is a living reconstruction of the PHP/MySQL web application
used for Brendan O. Downey's 2014 doctoral research on digital vocabulary
annotations and reading comprehension among university English-language
learners. The original source and deployment were lost; the dissertation's
descriptions and screenshots are the primary reconstruction evidence.

This repository is intentionally a software museum artifact: runnable and safe
enough for new replications, but governed by the original research workflow
rather than the architecture or feature set of newer SafeGloss products.

## What runs now

The executable application is a compact PHP 8.4/Apache monolith backed by MySQL
8.4. It implements:

- student, instructor, and researcher roles;
- site-code registration, consent acknowledgement, proficiency survey, and
  balanced treatment assignment;
- an explicit semantic treatment mode where **near gloss is contiguous** and
  right-margin gloss is non-contiguous;
- configurable historical A/B label mappings because Chapter 3 and Table 3 of
  the dissertation conflict;
- story, glossary, quiz, roster, and lesson authoring;
- the introduction → reading → quiz → score student sequence;
- UTC microsecond event logging for reading and gloss open/close actions;
- derived reading/gloss durations, scoring, researcher logs, and gradebook; and
- detailed post-quiz reports captured in MySQL by default, with optional
  verified-TLS SMTP delivery.

The earlier Django/PostgreSQL literacy-product reconstruction was removed from
the current tree. Git history preserves it for study. It is not part of the
Legacy runtime.

## Run locally

Requirements: Docker Engine with Docker Compose v2.

```bash
cp .env.example .env
# Replace every placeholder in .env, especially APP_KEY and database passwords.
docker compose up -d --build
docker compose exec web php /var/www/safegloss/bin/setup.php site \
  "Example University" 4821 chapter3
docker compose exec web php /var/www/safegloss/bin/setup.php user \
  instructor instructor instructor@example.invalid 4821
```

Open <http://localhost:8088>. Students and additional instructors can register
with the four-digit site code. Create a researcher account with the same setup
command but omit the site code:

```bash
docker compose exec web php /var/www/safegloss/bin/setup.php user \
  researcher researcher researcher@example.invalid
```

`chapter3` maps A to margin and B to contiguous. `table3` maps A to contiguous
and B to margin. Both profiles persist the semantic treatment separately from
the historical label.

MySQL initializes `database/migrations/001_initial.sql` only when its named
volume is empty. Do not remove a volume that contains needed research data.

## Verify

```bash
docker compose config --quiet
docker build --tag safegloss-legacy:verification .
docker run --rm safegloss-legacy:verification \
  php /var/www/safegloss/tests/domain_test.php
docker run --rm --entrypoint sh safegloss-legacy:verification -c \
  'find /var/www/html /var/www/safegloss -name "*.php" -print0 | xargs -0 -n1 php -l'
python3 scripts/check_documentation_updates.py
```

The evidence and remaining fidelity gaps are recorded in
[`docs/RECONSTRUCTION_SPEC.md`](docs/RECONSTRUCTION_SPEC.md). The code layout
and trust boundaries are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Preservation and rights

- No participant data, credentials, database exports, mail secrets, or
  production configuration belong in Git.
- The study passage and quiz adapted third-party instructional material. They
  are evidence, not redistributable seed content. Use synthetic or clearly
  licensed materials unless rights are independently established.
- Database mail capture is deliberately non-delivering. Real SMTP is an
  explicit deployment decision.
- This reconstruction is not recovered original source code. Inferred and
  safety-adapted behavior is labeled in the specification.

Original repository code is available under the [MIT License](LICENSE). That
license does not grant rights to the dissertation, third-party readings,
assessments, trademarks, or datasets.
