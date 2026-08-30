# SafeGloss Legacy

SafeGloss Legacy is a living replication of the PHP/MySQL Web application used
for Brendan O. Downey's 2014 doctoral study of digital vocabulary annotations
and reading comprehension among university English-language learners.

The original application was lost after the study. The dissertation preserves
enough description, screenshots, study materials, and instrumentation details
to reconstruct it. This repository exists to make that research platform
replicable again while retaining its historically specific architecture and
workflow.

## Preservation status

The repository currently contains a later Django reconstruction that drifted
into a broader literacy product. That implementation is being audited against
the dissertation before replacement with a faithful, deployable PHP/MySQL
replica. Until that work is complete, the current code should not be treated as
an accurate reproduction of the 2014 application or as a supported production
release.

The evidence-based target is documented in
[`docs/RECONSTRUCTION_SPEC.md`](docs/RECONSTRUCTION_SPEC.md), and the current
repository drift is summarized in
[`docs/REPOSITORY_AUDIT.md`](docs/REPOSITORY_AUDIT.md).

## Intended character

- **Living:** it should run from a clean checkout and permit new replications.
- **Archival:** original roles, screens, workflows, treatments, and measures
  govern the product rather than present-day SafeGloss requirements.
- **Transparent:** reconstructed details and unresolved ambiguities are labeled
  rather than presented as recovered source code.
- **Safe to operate:** supported runtimes, secure authentication, isolated local
  mail, and reproducible deployment may be used without redesigning the study.

Newer SafeGloss products may reference this project as a research artifact, but
Legacy is not their codebase, upstream, or architectural template.

## Rights and data

The dissertation includes a study passage and assessment adapted from
third-party instructional material. Those materials are evidence about the
original study but are not automatically redistributable as application seed
data. Demonstration fixtures must use synthetic or clearly licensed content
unless separate permission is established.

Never commit participant data, credentials, mail-server secrets, database
exports, or production configuration.

## License

Original code in this repository is available under the [MIT License](LICENSE).
The license does not grant rights to the dissertation, third-party readings,
assessments, trademarks, or datasets.
