# Text Acquisition Planning

This document describes how Safegloss can discover, acquire (legally), and link required course texts and alternative materials from libraries, publisher platforms, and open repositories.

> Design principle: **link-first, license-respecting acquisition**.
> Safegloss should prefer official APIs and authenticated library lending mechanisms; it should not attempt to bypass DRM, paywalls, or access controls.

## Goals

- Allow teachers/admins to define **Required Texts** and **Alternatives** for each course.
- Provide an **Acquire Text** page where a user can:
  - See required texts for the selected course.
  - See legitimate acquisition options and availability (borrow / read online / download where licensed).
  - Connect their accounts (NYPL, UVA, etc.) to enable one-click actions.
- Store **provenance** for every linked text (source, access method, license/terms signal, timestamp).
- Initially, **Acquire Text** is an **admin-only** workflow that augments Course; teachers consume the populated results. During early development (until admin roles exist), **teachers will be temporarily granted full access** to this feature.

## Non-Goals

- Circumvent paywalls/DRM.
- Scrape or redistribute unauthorized copies.
- Store full copyrighted textbooks in Safegloss unless a license explicitly permits it.
- Automatically bypass DRM, paywalls, bot protections, or terms-of-service restrictions via scripted logins.

---

# Acquire Text Page

## User Experience

### Access Control (MVP)

- Target steady state: **Admin-only** access.
  - Admins curate required texts/alternatives and run acquisition searches to populate course tables.
  - Teachers and students **do not run acquisition**; they only see the populated links/statuses on the course.

- Temporary dev mode (until admin permissions are implemented):
  - **Teacher users have full access** to Acquire Text so development/testing can proceed.
  - Mark all teacher-triggered actions in logs as `actor_role=teacher_dev_override`.

### Entry Points

- **Course → Required Texts** section includes an **Acquire** button.
- Global navigation: **Acquire Text**.

### Acquire Text Page Layout

**Header**
- Course selector (dropdown / search)
- Optional filters: Language, Edition, Format (PDF/ePub/HTML/Print), “Free only”, “Borrow only”, “Has API”, “Institutional access only”

**Main Panel**
- **Required Texts** (cards)
  - Title, authors, publisher, edition/year, ISBN-10/ISBN-13, OCLC (if known)
  - Status badges: Found / Not Found / Borrowable / Restricted / Purchase Only
  - Best match result (if any) + action buttons
- **Alternatives** (cards)
  - Open or lower-friction substitutes (OER, older editions, publicly accessible syllabi/handbooks, examiner reports, etc.)

**Result Drawer (per text)**
- Ranked sources list with:
  - Source name (NYPL, UVA Libraries, WorldCat, OpenAlex, etc.)
  - Access type: Borrow (CDL/DRM), Read Online, Chapter PDF, Download (open), Purchase (last resort)
  - Requirements: login needed, campus VPN, limited seats, waitlist/hold
  - “Confidence” score + match signals (ISBN match, title/author similarity)
  - Provenance metadata

### Actions

- **Connect account** (if required)
- **Check availability** (refresh)
- **Borrow / Place Hold / Open in Provider** (deep-link)
- **Save Link to Course** (stores a TextLocation/URL + access method)
- **Request purchase** (admin workflow) / “Ask librarian” (template email)

---

## Data Model Additions (High-Level)

### Entities

- **Text**
  - title, subtitle, authors, publisher, edition, year
  - identifiers: ISBN-10/13, DOI (rare for textbooks), OCLC, LCCN, internal slug
  - language/variant (optional)

- **CourseText** (junction)
  - course_id, text_id
  - requirement_level: Required | Recommended | Alternative
  - notes (teacher/admin)

- **TextSource** (catalog of providers)
  - name, type: Library | Publisher | OER | Index
  - supports_api (bool)
  - auth_method: None | OAuth | SAML | LibraryCard+PIN | Proxy/VPN | APIKey
  - discovery_methods (array)

- **UserTextSourceCredential** (per user per provider)
  - user_id, text_source_id
  - encrypted credentials / token refs
  - fields vary by provider (see “Credential Vault”)

- **AcquisitionCandidate**
  - text_id, text_source_id
  - match_score, match_signals (JSON)
  - access_type, url, availability snapshot
  - fetched_at, expires_at

- **AcquisitionLog**
  - user_id, course_id, text_id
  - actor_role (admin | teacher_dev_override)
  - action: searched | opened | borrowed | hold_placed | saved_link
  - timestamp, status, error_code

### Provenance Requirements

For every saved link:
- provider/source name
- canonical URL
- access method label (e.g., “NYPL Borrow via SimplyE”, “UVA Ebook Central access”)
- date/time checked
- match basis (ISBN exact / title-author similarity)

---

## Credential Vault in User Profile

Add a **User Profile → Acquire Text Accounts** section.

### Where credentials live (MVP)

- **Steady state:** credentials belong to the **admin user** who curates acquisition for the institution.
- **Current dev constraint:** until admin roles exist, store credentials on the **teacher user record** (dev override) so API development can proceed.
- Implementation detail: credentials should be stored in a separate table (`UserTextSourceCredential`) and **referenced** from the user record; do not add provider-specific columns directly onto `User`.

### UX Requirements

- List of providers with:
  - Connect/Disconnect button
  - Last validated timestamp
  - Scope summary (what Safegloss can do)
- “Test connection” per provider
- Clear explanation: Safegloss stores tokens securely; it does not store plaintext passwords when OAuth is available.

### Storage & Security

- Prefer OAuth / SSO tokens; avoid passwords.
- Encrypt secrets at rest (app-level encryption + KMS/secret manager in production).
- Store only the minimum needed fields.
- Support token refresh and revocation.
- Audit trail of credential changes.

## Authentication & Automated Access

> Requirement update: the Acquire Text feature will make **real API calls** and (where permitted) perform **authenticated catalog access**, not just provide deep links.

### Allowed approaches (prefer in this order)

1) **Official APIs with tokens/keys**
   - Best for reliability and compliance.
   - Examples: vendor APIs (Ex Libris Primo/Alma), open metadata APIs.

2) **OAuth / SSO flows (user-mediated)**
   - Redirect the user to the provider login and store a refreshable token.
   - Best practice for any provider that supports it.

3) **Library card + PIN (credential-based) through an official interface**
   - Only if the provider exposes an API or supported integration for programmatic availability/holds.
   - Avoid storing plaintext PINs; encrypt at rest and allow revocation.

4) **Browser automation (last resort; opt-in; terms-aware)**
   - Use a headless browser (e.g., Playwright) only when:
     - There is **no official API**, and
     - The provider’s terms allow automated access (or we have written permission), and
     - We are mimicking a user session (not breaking access controls), and
     - We rate-limit and do not bypass CAPTCHAs/bot protections.
   - Output should still be **link-first**: primarily capture stable links and availability states, not bulk-download files.

### Hard constraints

- Do not attempt to defeat DRM, CAPTCHAs, or bot mitigation.
- Do not store or transmit credentials insecurely.
- Always record provenance (what method, what account, when checked).

### Credential scopes per provider

For each provider connector, define a `capabilities` list:
- `search_catalog`
- `check_availability`
- `place_hold`
- `borrow`
- `open_reader`
- `download_open_access` (only for explicitly open content)

### Research checklist per provider (what we must discover)

- Official API availability + docs (or formal partner program)
- Authentication method (OAuth, SAML/SSO, card+PIN, API key)
- Login entry points/URLs and post-login cookies/session lifetime
- Whether programmatic holds/borrows are allowed
- Rate limits and acceptable use requirements
- Terms-of-service constraints for automated access
- Data we can legally store (links vs full-text)

---

## Source Coverage Strategy

Safegloss should support **multiple acquisition pathways**:

1) **Official library lending platforms** (OverDrive/Libby, SimplyE, Hoopla, etc.)
2) **University library vendor platforms** (Ebook Central, EBSCOhost eBooks, JSTOR, SpringerLink, Cambridge Core, Oxford Academic)
3) **Open repositories** (OpenStax, LibreTexts, OER Commons, DOAB)
4) **Indexes/metadata APIs** (WorldCat Search API (if licensed), Crossref, OpenAlex, Google Books metadata)

Safegloss should also record **“purchase-only”** options as a last resort, but acquisition should remain link-based.

---

## Initial Provider List (Phase 1)

### Public Libraries

- **New York Public Library (NYPL)**
  - Typical access: library card + PIN; borrowing often via **SimplyE** and/or **OverDrive/Libby** depending on title/format.
  - Implementation approach:
    - Start with **discovery** via public catalog search + deep links.
    - Add optional “account connection” for availability checks where supported.
  - Auth/Automation note: NYPL e-book lending commonly routes through vendor platforms (e.g., OverDrive/Libby, cloudLibrary). Prefer vendor-supported APIs/partner programs for authenticated actions; otherwise fall back to catalog deep links + user-mediated flows.

### University Libraries

- **University of Virginia (UVA) Libraries**
  - Typical access: UVA NetBadge / SSO; off-campus via proxy/VPN; content via vendor platforms (varies by title).
  - Implementation approach:
    - Provide catalog deep links + OpenURL resolver support.
    - Allow user to store “institution selector” + resolver base URL.
  - Auth/Automation note: UVA catalog (Virgo) and licensed full-text access commonly rely on SSO/proxy + vendor platforms. Prefer OpenURL resolver links and Ex Libris APIs where available; avoid scripted SSO automation unless explicitly permitted.

### Metadata & Discovery

- Google Books (metadata + preview links)
- Open Library / Internet Archive (controlled digital lending where available)
- Crossref / OpenAlex (metadata enrichment)

> Note: API details vary by provider; implement connectors incrementally and prioritize the ones with stable APIs.

---

## Matching & Ranking Logic

### Matching Inputs

- Exact identifiers first: ISBN-13 → ISBN-10 → OCLC
- Fallback: normalized title + primary author + edition/year

### Ranking Heuristics

1) Exact ISBN match + borrowable/read-online
2) Exact ISBN match + login required
3) Title/author match (high similarity) + borrowable
4) Open alternatives (OER) that satisfy course objectives
5) Purchase-only (last resort)

### “Alternatives” Logic

If required text is unavailable:
- Offer:
  - Earlier editions (clearly labeled)
  - OER equivalents
  - Publisher free companion excerpts
  - Syllabus/examiner reports/official course guides

---

## Technical Architecture

### Connector Pattern

- `acquire/connectors/base.py`
  - Standard interface:
    - `search(text_query, identifiers)`
    - `get_availability(candidate)`
    - `get_deep_link(candidate)`
    - `normalize_result(raw)`

### Execution Model

- Async background tasks for searching providers (rate limits + caching)
- Cache acquisition candidates per text/source for a short TTL (e.g., 24 hours)

### Compliance Guardrails

- Respect robots.txt where applicable.
- Prefer APIs; avoid brittle scraping.
- Store only links + metadata unless content is explicitly licensed for download.

---

## Phased Delivery

### Phase A — Course Texts + Link Aggregation (No Logins)

- Admin-only: Course → Required Texts / Alternatives UI (curation + acquisition controls)
- Acquire Text page that:
  - Searches public catalogs and metadata APIs
  - Presents deep links to providers
- Save selected provider link to the course
- Teachers: read-only visibility of populated course text links/statuses (no acquisition controls)

### Phase B — Account Connections (NYPL + UVA)

- Admin-only: User Profile → Acquire Text Accounts (connectors + credential vault)
- Add provider connectors:
  - NYPL: catalog + deep links; optional availability checks where possible
  - UVA: resolver links; guidance for SSO/proxy; optional availability checks if supported

### Phase C — Vendor Platforms + OpenURL Resolver

- Add connectors for Ebook Central, EBSCO eBooks, JSTOR, SpringerLink, Cambridge Core, Oxford Academic
- Institution “resolver configuration” model to support multiple universities

### Phase D — Admin Workflows

- “Request purchase” / “Ask librarian” templates
- Course-level dashboards for missing texts

---

## UI Copy (Draft)

- **Acquire Text**: “Find legitimate ways to access the materials for this course. Connect library accounts to speed up borrowing and access checks.”
- **Disclaimer**: “Safegloss only links to authorized sources and does not bypass paywalls or DRM.”

---

## Open Questions

- Do we support multiple institutions per user (e.g., adjunct + personal library)?
- Do we allow per-course institution overrides (useful for shared courses)?
- What is the minimum set of identifiers we require for a ‘Required Text’ entry (ISBN strongly recommended)?

---

# Implementation Roadmap (From Plan to Code)

This section translates the planning decisions into a concrete, buildable execution plan.

## Guiding Operating Assumption

Safegloss performs **authenticated discovery and availability actions** where permitted, but **does not directly download or redistribute DRM-protected full text**. The system is link-first and vendor-aware.

This keeps the platform:
- legally defensible
- compatible with library/vendor ecosystems
- extensible across institutions

---

## Connector-First Architecture (Non-Negotiable)

All providers (NYPL, UVA, vendors, metadata services) must implement a common connector interface. Provider-specific logic must never leak into Course, UI, or workflow code.

### Canonical Connector Interface (Conceptual)

```python
class TextSourceConnector:
    capabilities = set()

    def search(self, text):
        """Return ranked AcquisitionCandidate objects."""

    def check_availability(self, candidate):
        """Return availability/hold/borrow state."""

    def place_hold(self, candidate, credential):
        """Optional: place a hold if supported."""

    def borrow(self, candidate, credential):
        """Optional: borrow if supported."""

    def open_reader_url(self, candidate):
        """Return the canonical reader/deep-link URL."""
```

Capabilities are explicitly declared per connector (e.g. `search_catalog`, `check_availability`, `borrow`).

---

## Credential Ownership & Lifecycle

### Ownership Model

- **Steady state:** credentials belong to **admin users** acting on behalf of an institution.
- **Current development mode:** credentials are stored on **teacher user records** (temporary override) so API development can proceed.
- No provider-specific fields are added to `User`; all secrets live in `UserTextSourceCredential`.

### Lifecycle Rules

- Credentials are encrypted at rest.
- Each credential stores:
  - auth method
  - allowed scopes/capabilities
  - last validated timestamp
- Credentials can be revoked at any time by the user.
- All authenticated actions are logged with role attribution.

---

## Authentication Strategy (Strict Priority Order)

1) **Official APIs (API keys / tokens)**
   - Preferred and default whenever available.
   - Examples: Ex Libris Primo/Alma APIs, vendor partner APIs.

2) **OAuth / SSO (user-mediated)**
   - User completes login on provider site.
   - Safegloss stores refreshable tokens where allowed.

3) **Library card + PIN via supported interfaces**
   - Used only when providers explicitly support programmatic access.
   - Stored securely; never logged.

4) **Browser automation (disabled by default)**
   - Feature-flagged.
   - Only used if:
     - no official API exists
     - provider terms explicitly allow automation
     - no CAPTCHA/bot mitigation is bypassed
   - Output is still link-first; no bulk file capture.

---

## Provider-Specific Reality Notes

### University of Virginia (UVA) Libraries

- Catalog: **Virgo**
- Typical stack: **Ex Libris Primo + Alma**
- Access pattern:
  - public catalog discovery
  - OpenURL resolver for full text
  - vendor platforms for licensed content

**Implementation priority:**
- Use Primo search APIs where available.
- Generate and store resolver links.
- Do not script NetBadge SSO.

### New York Public Library (NYPL)

- NYPL acts as an **access broker**, not a single lending platform.
- Current textbook lending routes through vendors such as:
  - OverDrive / Libby
  - cloudLibrary
  - EBSCO (occasionally)

**Implementation priority:**
- NYPL connector handles catalog discovery + vendor detection.
- Vendor connectors handle authentication and availability.
- Avoid attempting to automate NYPL login directly.

---

## Phased Build Plan (Concrete)

### Phase 1 — Metadata & Discovery Backbone

**Goal:** Populate Course → Required Texts with high-confidence matches.

- Implement connectors:
  - Google Books (metadata only)
  - Open Library
- Normalize ISBNs, editions, authorship.
- Generate confidence scores.
- Enable alternative suggestions (older editions, OER).

_No authentication required._

---

### Phase 2 — Academic Library Access (UVA First)

**Goal:** Prove authenticated academic access without credentials.

- Implement UVA Primo / catalog connector.
- Generate OpenURL resolver links.
- Store provider + access notes on CourseText.

_Result:_ Teachers see “Available via UVA Libraries (login required)” on courses.

---

### Phase 3 — Public Library Access (NYPL via Vendors)

**Goal:** Enable availability checks and user-mediated borrowing paths.

- Implement NYPL catalog connector.
- Detect downstream vendor platform.
- Implement vendor connectors incrementally (OverDrive first).
- Support availability + hold placement where APIs allow.

---

### Phase 4 — Credentialed Actions

**Goal:** Enable real authenticated workflows.

- User Profile → Acquire Text Accounts UI.
- Credential testing + revocation.
- Background jobs perform authenticated checks.
- Full audit logging enabled.

---

## Course Augmentation Flow (End-to-End)

1. Admin (or teacher in dev override) defines Required Texts for a Course.
2. Acquire Text background jobs run:
   - discovery
   - ranking
   - availability checks
3. Best candidates are saved to `CourseText`.
4. Teachers viewing the course see:
   - provider badges
   - access notes (borrow / login required / open)
   - alternative options when unavailable.

Teachers **do not manage acquisition** in steady state.

---

## Logging, Audit & Compliance

Every authenticated or semi-authenticated action records:

```json
{
  "actor_role": "admin | teacher_dev_override",
  "provider": "NYPL | UVA | VendorName",
  "method": "api | oauth | card_pin | automation",
  "action": "search | availability | hold | borrow",
  "result": "success | blocked | error",
  "timestamp": "..."
}
```

This supports:
- debugging
- institutional compliance
- future transparency documentation

---

## Immediate Developer Next Steps

1. Create `acquire/connectors/base.py`.
2. Stub initial connectors:
   - `google_books.py`
   - `open_library.py`
   - `uva_primo.py`
   - `nypl_catalog.py`
3. Implement `Text`, `CourseText`, `AcquisitionCandidate` models.
4. Populate one real course end-to-end to validate the flow.

---

## Long-Term Optional Extensions

- Institution-level credential pooling (admin-managed).
- Library purchase request APIs.
- Analytics: % of courses with full-text access.
- Policy-based preferences (prefer OER, prefer local library).


Got it — here’s Option 3: an agent-ready task list to implement Phase 1 → Phase 2 MVP (metadata discovery + UVA resolver links), with clear acceptance criteria.

Note: I attempted to append this into docs/TEXT_ACQUISITION_PLANNING.md, but the file-edit tool failed on my side. You can paste this section at the end of that doc as-is, or tell me to try again and I’ll re-apply it.

⸻

Agent Task List (Phase 1 → Phase 2 MVP)

This checklist is designed to be handed to a coding agent. It covers:
	•	Phase 1: metadata + discovery backbone (no auth)
	•	Phase 2: UVA catalog + resolver links (no scripted SSO)

Until admin permissions exist, treat the teacher account as teacher_dev_override for testing.

⸻

A. Scaffolding: create an acquire Django app
	1.	Create app

	•	python manage.py startapp acquire

	2.	Add to INSTALLED_APPS

	•	Add acquire to settings.

	3.	Create module structure
Create:

	•	acquire/connectors/__init__.py
	•	acquire/connectors/base.py
	•	acquire/connectors/google_books.py
	•	acquire/connectors/open_library.py
	•	acquire/connectors/uva_primo.py
	•	acquire/connectors/nypl_catalog.py (stub only for now)
	•	acquire/services/__init__.py
	•	acquire/services/matching.py
	•	acquire/services/ranking.py
	•	acquire/services/acquire_text.py

Acceptance criteria
	•	App imports cleanly
	•	python manage.py check passes

⸻

B. Data models (MVP)

Implement in acquire/models.py (or core/models.py if you prefer, but keep names consistent).
	1.	Text

	•	title, subtitle (optional)
	•	authors (string or JSON list)
	•	publisher, edition, publication_year
	•	isbn10, isbn13, oclc, lccn (nullable)
	•	language_code (nullable)

	2.	CourseText

	•	FK: course (your Course model) and FK: text
	•	requirement_level (Required/Recommended/Alternative)
	•	notes

	3.	TextSource

	•	name, source_type (Library/Publisher/OER/Index)
	•	auth_method (None/OAuth/SAML/LibraryCardPIN/ProxyVPN/APIKey)
	•	supports_api boolean

	4.	UserTextSourceCredential

	•	FK: user, FK: text_source
	•	auth_method
	•	encrypted_secret_blob (TextField)
	•	scopes (JSON)
	•	last_validated_at datetime

	5.	AcquisitionCandidate

	•	FK: text, FK: text_source
	•	match_score float
	•	match_signals JSON
	•	access_type (Borrow/ReadOnline/DownloadOpen/PurchaseOnly/LoginRequired)
	•	url (TextField)
	•	availability_snapshot JSON
	•	fetched_at, expires_at

	6.	AcquisitionLog

	•	FK: user, course, text
	•	actor_role (admin/teacher_dev_override)
	•	provider (TextSource name)
	•	method (api/oauth/card_pin/automation)
	•	action (search/availability/hold/borrow/save_link/open)
	•	result (success/blocked/error)
	•	error_code (nullable)
	•	created_at

Acceptance criteria
	•	Migrations generated and applied
	•	Optional: models registered in Django admin for easy inspection

⸻

C. Connector interface + registry
	1.	Implement TextSourceConnector in acquire/connectors/base.py

	•	search(text)
	•	check_availability(candidate) (can be no-op for Phase 1)
	•	open_reader_url(candidate)

	2.	Add a registry in acquire/connectors/__init__.py

	•	Export dict like:
	•	{"google_books": GoogleBooksConnector(), "open_library": OpenLibraryConnector(), ...}

Acceptance criteria
	•	A management command can import registry and iterate connectors

⸻

D. Phase 1 connectors (no auth)

D1) Google Books connector (metadata)
	•	Query by ISBN first, fallback to title+author
	•	Parse:
	•	title/subtitle, authors, publisher, year
	•	identifiers (ISBN10/13)
	•	preview/info links

Acceptance criteria
	•	Given an ISBN-13, returns ≥1 candidate with a stable URL

D2) Open Library connector
	•	Query by ISBN
	•	Parse:
	•	title/authors, publish year
	•	Open Library edition/work URL

Acceptance criteria
	•	Given an ISBN, returns a candidate when Open Library has it

⸻

E. Matching + ranking services

Implement in acquire/services/matching.py and acquire/services/ranking.py:
	1.	ISBN normalization

	•	strip hyphens/spaces
	•	prefer ISBN-13

	2.	Match signals

	•	isbn_exact (bool)
	•	title_similarity (float)
	•	author_similarity (float)
	•	edition_match (bool)
	•	year_delta (int)

	3.	Ranking heuristic (initial)

	•	1st: exact ISBN
	•	2nd: title+author similarity
	•	3rd: prefer open/read/borrow over purchase-only

Acceptance criteria
	•	Deterministic ordering for a given input set

⸻

F. AcquireText service (orchestration)

Implement in acquire/services/acquire_text.py:
	1.	run_acquire_for_course(course_id, actor_user_id, actor_role, force=False)

	•	For each required CourseText:
	•	call each connector’s search(text)
	•	compute match_signals
	•	rank
	•	store top N AcquisitionCandidate rows (e.g., 10)
	•	create AcquisitionLog rows for each provider queried

	2.	Caching

	•	If candidates exist and fetched_at < 24h, skip unless force=True

Acceptance criteria
	•	Running service creates candidates + logs

⸻

G. Management command (developer MVP)

Create acquire/management/commands/acquire_text.py
	•	Example usage:
	•	python manage.py acquire_text --course <id> --actor <user_id> --role teacher_dev_override --force

Acceptance criteria
	•	Runs end-to-end without any UI

⸻

H. Phase 2 UVA connector (resolver-link MVP)

Goal: discovery + OpenURL resolver links without scripted SSO.
	1.	Implement uva_primo.py with two modes:

	•	Mode A: if a Primo public search endpoint is configured, use it
	•	Mode B: fallback — generate OpenURL resolver links from ISBN + resolver base URL

	2.	(Optional but recommended) InstitutionResolverConfig

	•	store resolver_base_url, institution_code, notes

	3.	Candidate output

	•	access_type = LoginRequired
	•	url = resolver_link

Acceptance criteria
	•	Given a test ISBN, UVA returns a candidate with a resolver URL

⸻

I. Minimal “Teacher Course View” (read-only)

Add a read-only table on Course detail:
	•	required text → top 3 candidates
	•	show provider name, access badge, and “Open” link

No acquisition controls in Course UI.

Acceptance criteria
	•	After running the command, teachers can view links/statuses on the course page

⸻

J. Security checklist (MVP)
	•	Don’t store plaintext secrets; encrypt encrypted_secret_blob
	•	Never log secrets
	•	Add setting flag:
	•	ACQUIRE_TEXT_ENABLE_AUTOMATION = False (reserved for later Playwright, keep off)

Acceptance criteria
	•	Credentials table exists even if unused in Phase 1

⸻

Definition of Done (MVP)
	•	One course has:
	•	required texts with ISBNs
	•	candidates populated from Google Books + Open Library
	•	UVA resolver candidate for ≥1 text
	•	Teachers can open best links from the Course page
	•	All runs logged with actor_role=teacher_dev_override

⸻

If you want, I can convert this into a GitHub Issues checklist format (each section as an issue with subtasks) so your agent can work through it systematically.