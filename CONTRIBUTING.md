# Contributing

SafeGloss Legacy is a bounded historical reconstruction. Changes should improve
reproducibility, safety, or fidelity to the dissertation—not turn Legacy into a
general literacy platform or a template for newer SafeGloss products.

Before implementing a behavioral change:

1. identify its dissertation chapter, section, figure, table, or appendix;
2. label undocumented implementation details as inferred or safety adaptations;
3. preserve the semantic rule that near gloss is contiguous;
4. use synthetic or clearly licensed test content; and
5. update the reconstruction and operational documentation in the same change.

Run the checks documented in [README.md](README.md). For database-facing
changes, also initialize a fresh MySQL volume and exercise the affected role and
lesson workflow. Pull requests should explain the evidence, behavior, schema or
operational impact, documentation changes, and exact checks run.

Do not commit `.env`, credentials, participant records, database exports,
captured mail reports, copyrighted study content, or generated deployment data.
Do not add AI generation, standards catalogs, external-book discovery, PWA
behavior, hosted integrations, or newer SafeGloss architecture without primary
historical evidence.
