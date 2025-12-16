# Text Analysis Pipeline (Post‑Acquisition)

This document defines the **Text Analysis** phase that occurs after a text has been acquired and linked to a course. The goal is to transform raw or semi‑structured full text into a **normalized, auditable, AI‑ready representation** that supports curriculum alignment, glossary extraction, exam mapping, and future generative reconstruction.

---

## 1. Purpose & Vision

After acquisition, a text is no longer treated as a monolithic book or PDF. Instead, it becomes a **structured knowledge artifact** whose internal components can be inspected, aligned, audited, and recomposed.

The long‑term vision is:
- Click any textbook → instantly view a **reliable, auditable glossary of terms**
- Each term linked to:
  - exact location in the text (section / page / paragraph)
  - relevant learning objective(s)
  - relevant past exam item(s), where available
- Definitions are:
  - pulled directly from the text when present, or
  - aligned against authoritative definitions in the text
- Over time, accumulated analysis enables **AI‑assisted textbook synthesis** that is standards‑aligned and exam‑informed

---

## 2. Input Assumptions

The analysis pipeline operates on a **full‑text source** that may originate from:
- HTML (preferred)
- ePub
- PDF (OCR or text‑layer)
- Vendor‑hosted readers (via extracted text segments where permitted)

Each source must be associated with:
- a `Text` record
- one or more `TextLocation` references (page, section, paragraph, offset, etc.)

---

## 3. Normalized Text Representation (Core Output)

The first responsibility of the pipeline is to produce a **normalized internal text model** suitable for AI and deterministic analysis.

### 3.1 Canonical Segmentation

The text is segmented hierarchically:

- Text
  - Part / Unit (if present)
    - Chapter
      - Section
        - Subsection
          - Paragraph / Block

Each segment receives:
- a stable internal ID
- hierarchical path label (e.g. `3.2.1 Variables and Constants`)
- location metadata (page, offset, etc.)

This structure must be preserved even when the source format is flat (e.g. PDF).

### 3.2 AI-Generated Structural Summary

After canonical segmentation is complete, the system generates a **concise AI-authored structural summary** of the text.

This summary:
- Describes the overall organization of the text
- Progresses hierarchically from the highest level (book / part / unit) down to the smallest child sections
- Uses neutral, descriptive language (not evaluative)

Example outputs include:
- “This book is organized into 6 units, each containing 3–5 chapters focused on…”
- “Chapter 4 is divided into sections covering…, with subsections that emphasize…”

The structural summary is:
- stored as metadata on the `Text` record
- regenerated when the structural model changes
- used to give educators rapid orientation to unfamiliar textbooks

---

## 4. Structural Feature Detection

The pipeline analyzes the normalized text to detect and record structural and semantic features.

### 4.1 Table of Contents (TOC)

- Detect explicit TOC if provided
- Infer implicit TOC from heading patterns
- Normalize into a hierarchical index

### 4.2 Index Detection

- Detect publisher‑provided index if present
- Normalize index terms → referenced locations
- Store as a first‑class searchable structure

### 4.3 Glossary Detection

If the text provides its own glossary:
- Detect glossary section(s)
- Extract terms and definitions
- Link each term back to its definition location

These definitions are treated as **authoritative for that text**.

### 4.4 Insets, Pull Quotes, Sidebars

Detect and classify:
- callout boxes
- sidebars
- pull quotes
- worked examples
- notes / warnings / tips

Each is stored with:
- type
- parent section
- full text

### 4.5 Figures, Tables, Images

- Detect references to figures/tables/images
- Record captions and nearby explanatory text
- Link figures to surrounding sections

---

## 5. Learning Objective & Syllabus Alignment

Once structure is established, content is aligned against curricular requirements.

### 5.1 Objective Matching

For each text segment:
- Compare semantic content to learning objectives / syllabus statements
- Record:
  - matched objective(s)
  - confidence score
  - directionality:
    - fully aligned
    - partially aligned
    - content exceeds objective scope
    - content falls short of objective scope

This allows detection of **over‑teaching** and **under‑coverage**.

### 5.2 Objective Coverage Map

Produce a coverage matrix:
- objectives × text sections
- supports gap analysis and curriculum review

---

## 6. Past Exam Alignment (When Available)

If past exam items are indexed for the course:

- Compare text segments to exam items
- Record:
  - which sections support which exam items
  - cognitive level alignment (Bloom / publisher verbs)
  - frequency / weight of exam relevance

This enables:
- exam‑informed glossaries
- exam‑weighted term prioritization

---

## 7. High‑Confidence Glossary Extraction

### 7.1 Term Candidate Identification

From the normalized text:
- extract candidate terms via:
  - headings
  - emphasized text
  - repeated noun phrases
  - index/glossary terms

### 7.2 Definition Resolution

For each term:
1) Prefer **explicit in‑text definitions**
2) Otherwise, infer definition from nearby explanatory text
3) Cross‑check against authoritative glossary (if provided)

### 7.3 Auditable Term Records

Each glossary term record stores:
- term text
- definition text
- text location(s): section, page, paragraph
- linked learning objective(s)
- linked exam item(s)
- confidence score
- provenance flags (direct quote vs inferred)

This produces a **textbook‑specific, auditable glossary**.

---

## 7A. Readability & Lexile Analysis

The system analyzes the normalized text to estimate **reading difficulty and grade-band alignment**.

### Lexile & Readability Estimation

- Compute an estimated Lexile measure (or Lexile-equivalent proxy where licensing prevents official scoring)
- Support additional readability metrics as secondary signals (e.g. Flesch–Kincaid, Dale–Chall)

### Granularity

Readability analysis is performed at multiple levels:
- whole text / book
- chapter
- section or subsection (where text length permits)

### Outputs

For each analyzed level, store:
- estimated Lexile range
- confidence score
- notes on variability across sections

### Uses

Lexile/readability data supports:
- course–text fit analysis
- differentiation for student cohorts
- adaptive reconstruction prompts (e.g. “rewrite at Lexile X”) 

Readability analysis is **advisory**, not prescriptive, and is always presented with uncertainty ranges.

---

## 8. Reverse‑Engineering Prompts (Recomposition Layer)

For each atomic text segment (e.g. section or subsection), generate a **reconstruction prompt**:

> “Write an explanation of ___ suitable for ___ students, covering the following objectives, using examples comparable to those found in the original text.”

Prompt inputs include:
- section topic
- key terms
- learning objectives
- exam relevance
- detected examples / figures

These prompts allow:
- controlled regeneration of content
- adaptation to different reading levels
- future textbook synthesis

---

## 9. Toward AI‑Authored, Standards‑Aligned Textbooks (Future)

With sufficient accumulated data:
- syllabus + objectives
- past exams
- multiple analyzed textbooks
- real course delivery feedback

Safegloss can:
- detect the *canonical content shape* of a topic
- identify unnecessary or missing material
- generate a **new, standards‑aligned textbook**:
  - auditable
  - exam‑informed
  - locally adaptable

This is not simple summarization; it is **curriculum‑aware reconstruction**.

---

## 10. Non‑Goals & Guardrails

- Do not replace licensed textbooks without permission
- Do not redistribute copyrighted content
- Maintain traceability from generated artifacts back to source texts

---

## 11. Outputs of the Text Analysis Phase

Primary outputs:
- Normalized text structure
- TOC + index + glossary structures
- Objective coverage map
- Exam‑linked glossary
- Reconstruction prompts per section

These outputs feed:
- Course views
- Glossary builder
- Exam enhancement features
- Future authoring tools