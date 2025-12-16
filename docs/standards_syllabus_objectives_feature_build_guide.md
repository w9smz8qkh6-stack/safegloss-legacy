## 16) Notes on Licensing + Compliance

Some standards bodies restrict redistribution. Your pipeline must support three modes per authority:

1. **Full text stored** (allowed)
2. **Codes + short descriptors only** (safer)
3. **Reference-only** (store code + link; teacher clicks out)

When uncertain, default to **reference-only** and store:
- objective codes,
- minimal descriptors,
- and official `source_url`.

## 17) Provenance, Source Links, and Method Reporting

You want to be able to (a) **prove how you obtained** the learning objectives, (b) **link users to the official source**, and (c) clearly report when a course’s objectives were obtained via an alternate method.

This requires two things:
1) a **provenance data model** stored alongside each `StandardsDocument`, and
2) a small, explicit **method taxonomy** (a controlled vocabulary) so every import is reportable.

### 17.1 Provenance fields (store on `StandardsDocument`)

Add the following fields to `StandardsDocument` (and populate them during import/sync). These fields are intentionally verbose; they are your audit trail.

- `source_publisher_name` (string)
  - Example: “Texas Education Agency”, “College Board”, “International Baccalaureate Organization”, “Cambridge Assessment International Education”.
- `source_publisher_type` (enum: `government`, `nonprofit`, `publisher`, `testing_org`, `other`)
- `source_title` (string)
  - Human-readable doc title, e.g., “Technology Applications TEKS, Grades 6–8”.
- `source_url` (url)
  - Primary web URL for the official objectives page/document (already in your model — keep it and treat it as authoritative).
- `source_url_canonical` (url, optional)
  - If the provider URL is messy, store a canonical “landing” page URL.
- `source_accessed_at` (datetime)
  - When the source was fetched/verified.
- `source_content_type` (enum: `html`, `pdf`, `json`, `docx`, `api`)
- `source_version_label` (string)
  - E.g., “Adopted 2022”, “Syllabus 2025–2027”, “Fall 2024 Course & Exam Description”.
- `source_effective_from` (date, optional)
- `source_license_notes` (text)
  - Freeform notes about redistribution restrictions.
- `acquisition_method` (enum; see 17.2)
- `acquisition_notes` (text)
  - Brief explanation of what was done (e.g., “Downloaded official PDF from TEA and parsed headings into nodes”).
- `evidence_artifact_id` (FK to `StandardsArtifact`, optional but recommended)
  - Points to the raw downloaded file snapshot that produced this document.
- `evidence_sha256_raw` (string, optional)
- `evidence_sha256_canonical` (string)
  - Store the checksum you already compute so you can prove the exact text/tree you imported.

> UI requirement (Teacher page): show a small “Source” panel with:
> - Publisher name
> - Version label
> - “View official source” link (`source_url`)
> - Method badge (`acquisition_method`)
> - Last verified (`source_accessed_at`)

### 17.2 Method taxonomy (controlled vocabulary)

Define a strict set of `acquisition_method` values. Every imported `StandardsDocument` MUST have exactly one.

1) `official_api`
- Objectives retrieved via an official API provided by the authority/publisher.
- Evidence: API endpoint name + timestamp; optionally store request/response hashes.

2) `official_web_page`
- Objectives extracted from an official web page maintained by the authority/publisher.
- Evidence: HTML snapshot stored as `StandardsArtifact`.

3) `official_pdf`
- Objectives extracted from an official PDF document.
- Evidence: PDF stored as `StandardsArtifact`.

4) `official_download_bundle`
- Objectives extracted from an official downloadable bundle (ZIP, dataset, etc.).
- Evidence: bundle stored as `StandardsArtifact`.

5) `publisher_portal_reference_only`
- Official objectives exist behind a portal/login or restrictive terms, so you store **codes/structure + source link** only.
- Evidence: portal URL + notes; do not store full text unless permitted.

6) `third_party_mirror_reference`
- Objectives are not reasonably accessible in official form, so you use a reputable mirror/reference site and store a clear attribution + link.
- Evidence: mirror URL + rationale in `acquisition_notes`.

7) `teacher_provided_upload`
- Teacher/admin uploads a standards file for private use (PDF/DOCX). You parse it and store results under that user/org.
- Evidence: uploaded file as artifact + uploader identity.

8) `manual_curated`
- Objectives were entered or curated manually by you/admin from an official source (used only when automation fails).
- Evidence: explicit citation in `acquisition_notes` + link.

9) `hybrid`
- Combination of the above for a single document (e.g., structure from web page + objective text from PDF). In this case, list both sources in `acquisition_notes` and store multiple artifacts.

**Hard rule:** If `acquisition_method` is not one of the above, the import should fail validation.

### 17.3 Provider output must include provenance

Update your provider contract so `fetch_objectives()` returns:
- canonical nodes, AND
- a `provenance` object, e.g.:

```json
{
  "authority": "TX_TEKS",
  "subject": "TECH_APPS",
  "grade": "G6",
  "version": "Adopted 2022",
  "source_url": "https://...",
  "provenance": {
    "source_publisher_name": "Texas Education Agency",
    "source_publisher_type": "government",
    "source_title": "Technology Applications TEKS",
    "source_accessed_at": "2025-12-16T09:00:00+07:00",
    "source_content_type": "pdf",
    "acquisition_method": "official_pdf",
    "acquisition_notes": "Downloaded TEA PDF and parsed headings/objectives into canonical nodes.",
    "evidence_sha256_raw": "...",
    "evidence_sha256_canonical": "..."
  },
  "nodes": [
    {"id":"n1","parent":null,"type":"strand","code":"CT","text":"Computational Thinking","order":1}
  ]
}
```

During import/sync, map `provenance.*` fields onto `StandardsDocument`.

### 17.4 Validation checks (must pass before DB import)

Add validation rules:
- `source_url` is present and begins with `https://`.
- `source_publisher_name` is present.
- `acquisition_method` is one of the controlled values.
- If `acquisition_method` is `publisher_portal_reference_only` or `third_party_mirror_reference`, then:
  - you must store a link and the `acquisition_notes` must explain why.
  - consider storing only codes/structure if licensing is unclear.

### 17.5 Reporting exports

Add a small admin export that produces a provenance report (CSV or JSON) per authority:
- authority, subject, grade
- version label
- acquisition method
- publisher name
- source_url
- source_accessed_at
- checksums

This becomes your “how we got it” compliance/audit artifact.

### 17.6 Implementation Checklist (Required)

This checklist turns the provenance design into **enforceable code changes**. These steps are mandatory for this feature to be considered complete.

#### Step 1 — Extend the Data Model
- Add all provenance fields listed in **17.1** to `StandardsDocument`.
- Add FK support to `StandardsArtifact` for raw evidence snapshots.
- Run migrations and verify existing documents either:
  - backfill provenance, or
  - are marked legacy/unverified.

#### Step 2 — Enforce Provenance at Import Time
- Update `sync_document()` and `import_standards_json` so that:
  - every import **requires** a `provenance` object
  - missing or invalid provenance **fails the import**
- Validate:
  - `source_url` is present and HTTPS
  - `source_publisher_name` is present
  - `acquisition_method` ∈ controlled vocabulary

#### Step 3 — Update Provider Contract
- Modify provider interface so `fetch_objectives()` returns:
  - canonical nodes
  - version metadata
  - **provenance object** (required)
- Providers that do not supply provenance must raise an error.

#### Step 4 — Map Provenance to Database Fields
- During import/sync, map `provenance.*` fields onto `StandardsDocument`.
- Store:
  - `evidence_sha256_raw`
  - `evidence_sha256_canonical`
- Link `evidence_artifact_id` when available.

#### Step 5 — Teacher UI: Source Transparency
- Add a “Source” panel to the teacher standards view showing:
  - Publisher name
  - Version label
  - Acquisition method (badge)
  - Last verified date
  - Clickable official source URL

#### Step 6 — Admin Audit Export
- Implement a CSV/JSON export for admins including:
  - authority, subject, grade
  - version label
  - acquisition method
  - publisher name
  - source_url
  - source_accessed_at
  - checksums

This export is the authoritative answer to:
> “How were these learning objectives obtained?”

#### Step 7 — Validation Gate (Non-Negotiable)
- If provenance is missing, incomplete, or invalid:
  - **do not import** the standards document
  - surface a clear error in logs/admin UI

This gate prevents undocumented or legally ambiguous curriculum data from entering the system.


## 18) Definition of Done

- Teacher-only Standards page exists and works.
- Teacher can choose Authority → Program → Subject → Grade and view objectives as a tree.
- Teacher can save selection to their library.
- Teacher can re-sync and see updated version timestamps.
- Pipeline phases 0–3 exist and can run end-to-end for at least one authority.
- At least one authority is ingested with real data and passes validation.
- Teacher can toggle between native codes and internal numbering in the objectives tree, and search by either format.


## Data Model (Normalized, Versioned, Sync-Friendly)

**Authority**
- `name` (e.g., “International Baccalaureate”, “Cambridge Assessment International Education”, “College Board”)
- `code` (stable key: `IB`, `CAMBRIDGE`, `COLLEGE_BOARD`, `ETS`, `ACT`, `US_STATES`)
- `description`
- `is_active`

**AuthorityProgram** (sub-category / framework)
- FK `authority`
- `name` (e.g., “PYP”, “MYP”, “Diploma”, “IGCSE”, “Starters”, “SAT”, “TOEFL”, “ACT”, “Texas”, “New York”)
- `code` (stable key, e.g., `IB_PYP`, `IB_MYP`, `IB_DP`, `CAM_IGCSE`, `ETS_TOEFL`, `CB_SAT`, `STATE_TX`)
- `description`
- `provider_key` (maps to provider/parser implementation)
- `is_active`
- unique constraint: `(authority, code)`

> Design note: All downstream entities (Subject, GradeLevel, StandardsDocument) MUST reference `AuthorityProgram`, not `Authority` directly. This allows a single authority (e.g., IB, Cambridge, U.S. States) to support multiple independent curricula with different structures, licensing rules, and acquisition methods.

### Standards Authority Hierarchy (Authority → Program)

The standards data model is hierarchical:
- **Authority**: The parent organization (e.g., IB, Cambridge, College Board, U.S. States)
- **AuthorityProgram**: The specific program, framework, or state (e.g., “MYP”, “IGCSE”, “SAT”, “Texas”)
- **Subject**
- **GradeLevel**
- **StandardsDocument**

All references to standards in catalogs, curriculum, and teacher selection workflows must use the Authority → Program → Subject → Grade hierarchy.

**StandardsDocument**
- FK `authority_program`
- `subject`
- `grade_level`
- `version_label`
- `source_url`
- (plus all provenance fields from section 17.1)

**ObjectiveNode** (tree)
- FK `document` (to `StandardsDocument`)
- `parent` self‑FK (nullable)
- `node_type` (enum: `strand`, `substrand`, `objective`, `note`)
- `code` (native authority code, stored exactly as published; e.g., `(6)(1)(A)`, `CCSS.MATH.CONTENT.6.RP.A.1`)
- `text` (objective wording; may be blank/short if reference-only)
- `sort_order`

**Internal numbering fields (cross-authority)**
- `internal_code` (string; e.g., `1`, `1.1`, `1.1.1`)
- `internal_path` (string; e.g., `1/1.1/1.1.1`)
- `internal_sort_key` (string/int; stable ordering across nodes)

Indexes:
- `(document_id, parent_id, sort_order)`
- `(document_id, code)`
- `(document_id, internal_code)`

**ObjectiveCodeMap** (audit mapping between native and internal codes)
- FK `objective_node`
- `native_code` (copied from `ObjectiveNode.code`)
- `internal_code` (copied from `ObjectiveNode.internal_code`)
- `mapping_method` (enum: `algorithmic`, `manual_curated`, `hybrid`)
- `mapped_by` (FK to user/admin, nullable)
- `mapped_at` (datetime)
- `notes` (text)

> Design note: `ObjectiveCodeMap` is an audit log of how internal numbering was derived. Mapping provenance is distinct from standards provenance and must be exportable in admin reports.


## Standards Authorities and Programs (Seed Specification)

This section defines the **canonical seed data** for Standards Authorities and their sub-categories (programs/frameworks). These MUST be seeded before catalogs or curriculum ingestion begins.

### International Authorities

**International Baccalaureate (IB)**
- Authority code: `IB`
- Programs:
  - `IB_PYP` — Primary Years Programme (PYP)
  - `IB_MYP` — Middle Years Programme (MYP)
  - `IB_DP` — Diploma Programme

**Cambridge Assessment International Education**
- Authority code: `CAMBRIDGE`
- Programs:
  - `CAM_IGCSE` — IGCSE
  - `CAM_STARTERS` — Cambridge Starters

**British Council**
- Authority code: `BC`
- Programs:
  - `BC_IELTS` — IELTS (International English Language Testing System)

---

### Testing & Assessment Organizations

**Educational Testing Service (ETS)**
- Authority code: `ETS`
- Programs:
  - `ETS_TOEFL` — TOEFL

**College Board**
- Authority code: `COLLEGE_BOARD`
- Programs:
  - `CB_SAT` — SAT

**ACT, Inc.**
- Authority code: `ACT`
- Programs:
  - `ACT_EXAM` — ACT

---

### United States — State Standards

**U.S. States**
- Authority code: `US_STATES`
- Programs:
  - `STATE_NY` — New York
  - `STATE_TX` — Texas
  - `STATE_IL` — Illinois
  - `STATE_FL` — Florida

> Design note: Each state program behaves like an independent standards authority from a curriculum perspective (different publishers, update cycles, and licensing), but is grouped under a single parent for UI clarity.

---

### UI Behavior (Authority → Program → Subject → Grade)

Teacher selection flow MUST be:
1. Authority (e.g., IB, Cambridge, U.S. States)
2. Program / Framework (e.g., MYP, IGCSE, Texas)
3. Subject Area
4. Grade / Course

Programs are not optional. If an authority has only one program, it should still be represented explicitly to keep the model uniform.

## Teacher Filtering UI (Single-Page, Cascading Multi-Select)

This feature requires a **single teacher-only page** that acts as a filtering tool for learning objectives across many standards systems.

### Requirements

**1) Single-page dynamic form**
- The teacher sees one form with **cascading, dynamic multi-select controls**.
- Controls must support both:
  - **single-select** (simple workflow), and
  - **multi-select** (compare across programs/grades/subjects).

**2) Cascading dependency rules**
The selection order and dependency rules are:
1. **Authority** (multi-select)
2. **Program / Framework** (multi-select; filtered by selected authorities)
3. **Grade band / Grade level** (multi-select; filtered by authority+program)
4. **Subject** (multi-select; filtered by authority+program)
5. **Course** (optional multi-select; filtered by subject; used when the authority has explicit courses)
6. **Document version** (optional; default to latest; allow selecting historical versions)

**3) Query result output**
Submitting the form must render:
- A **tree of objectives** grouped as:
  - Authority → Program → Subject → Grade/Course → Strands → Objectives
- A compact **results header** summarizing:
  - number of objectives returned
  - selected filters
  - time to fetch (optional)

**4) Source transparency panel (required)**
Above each authority/program’s tree, display a “Source” panel populated from `StandardsDocument` provenance:
- Publisher name
- Version label
- **Published date / Effective date** (if known)
- **Expiry / Superseded date** (if known)
- Acquisition method badge
- Last verified (source_accessed_at)
- Clickable official URL (`source_url`)

> If the system cannot determine published/effective/expiry dates reliably, it must display “Unknown” rather than guessing.

**5) Partial availability handling**
When multiple selections are requested (e.g., multiple programs/grades):
- If some items are available and others are missing, return what is available and show a clear per-item message:
  - “Not available (reference-only)”
  - “Not ingested yet”
  - “Restricted/licensing (link only)”
  - “Provider error (last attempted: …)”

**6) UX must support fast iterative filtering**
- Changing a parent filter must clear invalid downstream selections.
- Dependent lists should load via lightweight JSON endpoints (HTMX/fetch).
- The page should preserve the selected filters in the URL querystring (shareable teacher link).

### Endpoints (minimum)
- `GET /teacher/standards/` (page)
- `GET /teacher/standards/api/authorities`
- `GET /teacher/standards/api/programs?authorities=...`
- `GET /teacher/standards/api/grades?programs=...`
- `GET /teacher/standards/api/subjects?programs=...&grades=...`
- `GET /teacher/standards/api/courses?programs=...&subjects=...&grades=...` (optional)
- `GET /teacher/standards/api/results?...` (returns tree + provenance summary)

> Note on authorities without published objectives: Some authorities provide only a syllabus/scheme of work (topics, pacing, exemplar exam questions) without explicit learning objectives. For these, add an extra inference step:
> - Ingest syllabus topics and past exam question metadata.
> - Derive candidate objectives (structured nodes) from topics/question patterns.
> - Mark inferred objectives with `acquisition_method=hybrid` and capture provenance notes explaining the inference sources.
> - Surface these as inferred in the UI and exports so teachers understand the origin.

---

## Standards Code Mapping and Internal Numbering

Different authorities use different codes (e.g., TEKS `(6)(1)(A)`, Common Core `CCSS.MATH.CONTENT.6.RP.A.1`, IB statements without stable codes, etc.). To enable **cross-authority sorting/searching** and consistent UI, implement a mapping layer that supports:

- Displaying either **native authority codes** *or* an **internal superimposed numbering** (`1.0`, `1.1`, `1.1.1`, …)
- Searching by either numbering system
- Stable internal ordering even when native codes are missing or non-hierarchical

### Requirements

**1) Store native codes as-is**
- Keep `ObjectiveNode.code` as the native code when present.
- Never “normalize” native codes by rewriting them; store the exact official code string.

**2) Add internal numbering fields on ObjectiveNode**
Add fields (or equivalent computed fields) to `ObjectiveNode`:
- `internal_code` (string; e.g., `1`, `1.1`, `1.1.1`)
- `internal_path` (string; e.g., `1/1.1/1.1.1` or similar)
- `internal_sort_key` (string/int) to guarantee stable ordering

**3) Add a mapping table for auditability**
Create `ObjectiveCodeMap` (or similar) to explicitly map:
- FK `objective_node`
- `native_code` (copied from ObjectiveNode.code)
- `internal_code`
- `mapping_method` (enum: `algorithmic`, `manual_curated`, `hybrid`)
- `mapped_by` (user/admin, nullable)
- `mapped_at` (datetime)
- `notes` (text)

**4) Mapping generation rules**
- If the authority provides a hierarchical code system, prefer algorithmic mapping that preserves hierarchy.
- If the authority lacks stable codes (common in narrative standards), generate internal codes from the canonical tree order.
- Any manual overrides must be tracked via `mapping_method=manual_curated`.

**5) UI toggle**
In the teacher standards page, provide a toggle:
- “Show native codes” (default)
- “Show internal numbering”

When internal numbering is enabled, show both formats when available:
- `1.1.1 (CCSS.MATH.CONTENT.6.RP.A.1)`

**6) Search behavior**
Objective search must support:
- `q=` keyword search across objective text
- code search across both `native_code` and `internal_code`

**7) Provenance for mapping**
Mapping is not the same as standards provenance. It must be reported separately.
- Include mapping method + timestamp in admin audit export.

---

## 19) Official Media and Endorsed Courses Catalog

Authorities often cite official media (textbooks, guides, exam prep books) and endorse courses hosted elsewhere. Add a catalog so teachers can see authoritative resources and feature tags for alignment.

### 19.1 Data model
- **AuthorityProgramMedia** (new)
  - FK `authority_program`
  - `title`, `author`, `publisher`
  - `isbn_10`, `isbn_13`
  - `source_url` (canonical link; prefer official or publisher)
  - `cover_image_url`
  - `description` (text)
  - `media_type` (enum: `book`, `guide`, `practice_tests`, `video_series`, `course`)
  - `is_official` (boolean; true if published/endorsed by authority)
  - `endorsement_notes` (text; how it is referenced/endorsed)
  - `platform` (enum: `print`, `google_books`, `amazon`, `khan_academy`, `udemy`, `coursera`, `youtube`, `other`)
  - `features` (JSON: e.g., `{ "online_text": true, "practice_tests": 5, "video_hours": 12, "assignments": true, "certificates": false, "language": "en" }`)
  - `retrieved_from` (enum: `google_books`, `amazon`, `manual`, `platform_scrape`)
  - `retrieved_at` (datetime)
  - `metadata_raw` (JSON; raw API payload for audit)
  - `is_unofficial` (boolean; for platform courses not endorsed but relevant)
  - Timestamps
- **AuthorityProgramMediaTag** (optional)  
  - FK `media`
  - `label` (e.g., `official`, `exam_prep`, `beginner`, `video`, `open_course`, `with_online_text`, `interactive`)

### 19.2 Ingestion rules
- Support **multiple official media** per authority/program; never overwrite—append with provenance.
- Use **Google Books** and/or **Amazon** lookups by ISBN/title to hydrate metadata (title, authors, publisher, page count, published date, description, cover).
- For **platform courses**:
  - Identify **endorsed** courses (authority links to Khan/Udemy/etc.) and mark `is_official=true`, `platform` set accordingly.
  - Catalog **unofficial but relevant** courses with `is_unofficial=true` and `endorsement_notes` explaining rationale.
- Store **raw API payloads** in `metadata_raw` for transparency; normalize into top-level fields and `features`.
- Feature extraction guidance:
  - `online_text` (bool) when the course includes full text/materials.
  - `practice_tests` (int), `quizzes` (int), `assignments` (bool), `video_hours` (float), `downloadables` (bool), `mobile_access` (bool), `certificate` (bool), `languages` (list), `skill_level` (enum).

### 19.3 UI/UX
- On teacher standards page or program detail, show an **Official Media & Courses** panel:
  - Official items first (badge), then endorsed courses, then unofficial relevant courses.
  - Display cover/thumb, title, platform, key features (chips), and a “View” link.
  - Allow filtering by `media_type` and `platform`; search by title/author/ISBN.
- Link from media entries to the relevant **AuthorityProgram** so teachers know the alignment context.

### 19.4 API contracts
- `GET /teacher/standards/api/media?programs=...&official_only=...&platform=...`
- `POST /admin/standards/media/import` to import by ISBN/title/platform URL (admin-only).
- Background task to hydrate metadata from Google Books/Amazon and platform scrapes; retry with rate limits.

### 19.5 Definition of done (media)
- Media model and migrations exist with Google Books/Amazon hydration wired.
- Teachers can view official/endorsed media per authority/program with feature chips.
- Admins can import by ISBN/title/URL; raw payloads stored; fields normalized.
- Platform courses (Khan/Udemy/YouTube/etc.) are cataloged with `is_official`/`is_unofficial` and feature descriptors.

### 19.6 Background processing (all ingestion)
- **Run all ingestion routines in workers/queue jobs** to avoid blocking requests:
  - Standards/provider fetch + provenance validation + import/save.
  - Media hydration (Google Books/Amazon) and platform course metadata pulls.
  - Re-sync jobs (version updates) and retry flows.
- **Job contracts**:
  - Idempotent by authority/program + version key; safe to retry.
  - Respect provider/API rate limits; exponential backoff on transient errors.
  - Emit progress/log records (queued/started/succeeded/failed with reason).
  - Enforce provenance validation inside the job; fail closed on missing/invalid provenance.
- **Admin triggers**: allow enqueueing imports/re-syncs via admin UI; surface job status and last run timestamps.
