# SafeGloss Legacy preservation guidance

## Repository mission

SafeGloss Legacy is a living replication of the PHP/MySQL research application
described in Brendan O. Downey's 2014 doctoral dissertation, *The Effects of the
Variable Spatial Contiguity of Digital Vocabulary Annotations on Reading
Comprehension by English Language Learners at American Universities*.

Treat the repository as a working software museum artifact. Its purpose is to
preserve and reproduce the original application's research design, participant
experience, content-management workflow, analytics, and instrumentation. It is
not an upstream implementation or architectural template for newer SafeGloss
products.

## Governing principles

- Prefer historical fidelity over feature expansion or architectural
  modernization.
- Use the dissertation as the primary source for original behavior. Distinguish
  documented facts from reconstruction choices and unresolved ambiguities.
- Preserve the monolithic, database-driven PHP/MySQL application model and the
  three original roles: student, instructor, and researcher.
- Modern runtime, security, testing, and container support may surround the
  replica when needed to keep it safe and deployable, but must not silently
  alter the research treatment, measurements, or user workflow.
- Do not add newer SafeGloss features such as AI generation, standards catalogs,
  curriculum hierarchies, external-book discovery, PWA behavior, or hosted
  product integrations unless an archival source establishes that they belonged
  to the original application.
- Newer SafeGloss repositories may study or deliberately port concepts from
  Legacy. Do not reshape Legacy to make such porting easier.
- Do not bundle dissertation study materials or third-party textbook content
  unless redistribution rights are established. Use synthetic or clearly
  licensed fixtures for reproducible demonstrations.
- External integrations, especially email, must default to non-delivering local
  behavior. Enabling real delivery requires explicit configuration.

## Required verification

For behavior derived from the dissertation, cite the relevant chapter, section,
figure, table, or appendix in the reconstruction documentation. Record any
necessary inference in `docs/RECONSTRUCTION_SPEC.md`.

Keep the application runnable from a clean checkout with documented PHP/MySQL
requirements and a reproducible local environment. Verify schema creation,
authentication and role boundaries, treatment assignment, lesson progression,
event timestamps, quiz scoring, derived session measures, and non-delivering
mail defaults before calling a reconstruction complete.

## Documentation is part of completion

Every task that changes source code, reconstructed behavior, interfaces, tests,
scripts, dependencies, configuration, security, deployment, operations,
architecture, research interpretation, or user-visible output must review and
update the relevant durable documentation in the same task. Follow
`docs/DOCUMENTATION_MAINTENANCE.md`. In particular, compare the finished work
semantically with the reconstruction specification, repository audit, setup
and security guidance, and cited dissertation evidence. Generated freshness or
path checks are evidence only.

If accurate documentation cannot be updated because a repository or source is
unavailable, overlapping work conflicts, rights are unresolved, or a required
fact cannot be verified, report the task incomplete with the exact document,
claim, and blocker. Run `python3 scripts/check_documentation_updates.py` before
handoff.

After checks pass, commit task-owned changes and push the current branch to its
existing configured upstream at a cohesive green checkpoint and task
completion. Verify branch, remote, divergence, diff, and secret and rights
safety; never force-push, rewrite history, bypass branch protection, or include
unrelated work. Legacy has no production deployment target unless a current
repository runbook establishes one.
If repository rules require a pull request, use a scoped task branch, wait for
required checks, and merge only after every gate passes and no required human
approval remains.
