STANDARDS_VERSIONING_MODEL_DESIGN.md
# Standards Versioning Model – Implementation Design

## Purpose
This document defines a **versioned standards architecture** for Safegloss, intended to support long-lived curricula such as TEKS, SOL, NGSS, IB, and Cambridge. It is written for an **implementation agent** and focuses on correctness, auditability, and downstream alignment (courses, textbooks, exams).

The core principle is:
> **Standards change over time; learning artifacts must remain referenceable to the version in force when they were created or used.**

---

## Design Goals

1. Support **multiple versions** of the same standards authority (e.g., TEKS 2012 vs TEKS 2023)
2. Preserve **historical integrity** (old textbooks/exams still map correctly)
3. Enable **side-by-side comparisons** and drift analysis
4. Allow **downstream mappings** (courses, objectives, exams, textbooks) to pin to a specific version
5. Be **idempotent and seed-friendly**
6. Avoid hard deletes; favor temporal validity

---

## Core Concepts

### 1. Authority (Who owns the standards)
Represents the issuing body.

Examples:
- Texas Education Agency (TEA)
- Virginia Department of Education (VDOE)
- International Baccalaureate (IBO)
- Cambridge Assessment

Authority is **stable across time**.

---

### 2. Standards Framework (What family of standards)
A named standards system under an authority.

Examples:
- TEKS – Mathematics
- TEKS – English Language Arts and Reading
- IB MYP Sciences
- Cambridge IGCSE ICT

Frameworks change slowly; versions change frequently.

---

### 3. Standards Version (When / which revision)
Represents a specific published revision.

This is the **critical versioning boundary**.

Attributes:
- Official publication year
- Effective start date
- Optional end-of-validity date
- Status (draft | active | deprecated | superseded)

---

### 4. Standards Nodes (The actual learning standards)
Individual standards/objectives, typically hierarchical.

Examples:
- TEKS §111.7(b)(1)(A)
- IB MYP Sci 3-2

Nodes are **always version-scoped**.

---

## Proposed Data Model (Logical)

### Authority
```
authority
- id (PK)
- name
- short_code (e.g., TEKS, SOL, IB)
- jurisdiction
- website_url
```

---

### Standards Framework
```
standards_framework
- id (PK)
- authority_id (FK → authority)
- name
- subject
- grade_band
- description
```

Examples:
- authority=TEA, name="TEKS Mathematics", grade_band="K–12"

---

### Standards Version
```
standards_version
- id (PK)
- framework_id (FK → standards_framework)
- version_label (e.g., "2012", "2023")
- publication_year
- effective_from (date)
- effective_to (date, nullable)
- status (draft | active | deprecated)
- source_url
- notes
```

Rules:
- Only **one ACTIVE version per framework at a time**
- Older versions remain queryable

---

### Standards Node
```
standards_node
- id (PK)
- standards_version_id (FK → standards_version)
- parent_id (FK → standards_node, nullable)
- code (official code / label)
- title
- description
- level (integer, depth in hierarchy)
- sort_order
```

Notes:
- Hierarchy uses an **adjacency list**
- Nodes are immutable once published; corrections = new version

---

## Versioning Rules (Critical)

1. **Never edit a published node**
   - Text changes → new standards_version

2. **Deprecation is temporal, not destructive**
   - Use `effective_to` + `status=deprecated`

3. **Downstream artifacts pin to versions**
   - Courses, exams, textbooks reference `standards_version_id`

4. **Cross-version mapping is explicit**
   - No implicit inheritance

---

## Cross-Version Mapping (Optional but Powerful)

Used for drift analysis and continuity.

### Standards Node Mapping
```
standards_node_map
- id (PK)
- from_node_id (FK → standards_node)
- to_node_id (FK → standards_node)
- relationship_type (unchanged | split | merged | revised | deprecated)
- confidence (0.0–1.0)
```

This table is populated manually or via AI-assisted tooling.

---

## Course Alignment Model

### Course
Courses are **not versioned**, but their alignment is.

```
course
- id (PK)
- authority_id (FK → authority)
- grade_level
- subject
- name
```

### Course ↔ Standards Version
```
course_standards_version
- course_id (FK → course)
- standards_version_id (FK → standards_version)
- is_primary (bool)
```

This allows:
- Same course taught under different standards revisions
- Historical replay ("What standards applied in 2018?")

---

## Textbooks, Exams, and Materials

All learning artifacts must pin to a **standards_version_id**.

Example:
```
textbook
- id
- title
- publisher
- publication_year
- standards_version_id
```

Same pattern applies to:
- Exam specifications
- Past exam items
- Sample responses

---

## Seeding Strategy (Agent Instructions)

### Phase 1: Authorities
- Seed TEA, VDOE, IBO, Cambridge
- Idempotent by `short_code`

### Phase 2: Frameworks
- One row per subject × grade band
- Idempotent by `(authority_id, name)`

### Phase 3: Versions
- One row per official revision
- Populate dates + status

### Phase 4: Nodes
- Import hierarchy from CSV/JSON
- Validate parent-child integrity
- Compute `level` and `sort_order`

### Phase 5: Courses
- Seed grade-level course shells
- Link to correct standards_version

---

## Query Patterns (Expected)

- Current standards for a course
- Standards at a historical date
- Compare two versions of a framework
- Find textbooks misaligned to current standards

---

## Anti-Patterns to Avoid

- Editing nodes in place
- Using display names as keys
- Assuming one-to-one mapping across versions
- Deleting deprecated standards

---

## Why This Matters

This model allows Safegloss to:
- Explain *why* textbooks differ
- Track curricular drift
- Support legacy classrooms
- Align AI-generated materials responsibly

It also mirrors how real educational systems actually behave.

---

## Next Implementation Steps

1. Confirm table names vs current schema
2. Decide ENUM vs lookup tables for `status`
3. Implement idempotent seeders
4. Build admin tooling for version comparison
5. Add AI-assisted node mapping (future)

---

**End of design document.**