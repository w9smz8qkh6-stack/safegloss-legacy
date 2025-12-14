# Mapping Quizzes to Learning Objectives & Standards

---

## Purpose

This document defines how Safegloss maps **AI‑generated quiz items** to:
- explicit **learning objectives (LOs)**
- **Bloom’s taxonomy** (cognitive demand)
- optional **curriculum standards** (Cambridge, IB, Common Core, etc.)

The goal is to ensure quizzes are:
- instructionally intentional
- standards‑aware (when required)
- explainable to teachers and administrators
- suitable for reporting and analytics

---

## Core Principle

> **Quiz items assess learning objectives, not content in isolation.**

Every quiz item must clearly answer:
- What skill is being assessed?
- At what cognitive level?
- Using which part of the story or glossary?

---

## Conceptual Model

Story
└── Learning Objectives
    └── Quiz Items
        └── Standards (optional attachment)

Key idea:
- Quiz items map **directly to learning objectives**
- Standards attach **to objectives**, not to raw questions

---

## Learning Objectives (LOs)

### Definition

A learning objective is a **clear, assessable statement** describing what a learner should be able to do after reading a story.

### Required Properties

Each learning objective must specify:
- **Action verb** (Bloom‑aligned)
- **Content focus** (story detail, vocabulary, structure, inference)
- **Bloom level**
- **Age band**

### Example Learning Objectives

- LO‑1: Identify key details in a narrative text. *(Remember)*
- LO‑2: Determine the meaning of a word using context clues. *(Apply)*
- LO‑3: Explain why a character acted in a certain way. *(Understand)*
- LO‑4: Analyze cause‑and‑effect relationships in a story. *(Analyze)*

---

## Bloom’s Taxonomy as the Bridge

Bloom’s taxonomy is the **primary connector** between:
- learning objectives
- quiz item difficulty
- validation logic

### Bloom‑Aligned Verb Reference

| Bloom Level | Example Verbs |
|-----------|---------------|
| Remember | identify, list, recall |
| Understand | explain, summarize |
| Apply | determine, infer |
| Analyze | compare, examine |
| Evaluate | judge, justify |
| Create | propose, rewrite |

Rules:
- Each learning objective declares one Bloom level
- Quiz items **must not exceed** the objective’s Bloom level

---

## Objective → Quiz Item Mapping Rules

### Rule 1 — One Objective, Many Items
- One learning objective may generate multiple quiz items
- Each quiz item maps to **exactly one primary objective**

### Rule 2 — Cognitive Consistency
- Quiz item Bloom level must match the objective Bloom level
- Downgrading Bloom level is allowed; upgrading is not

### Rule 3 — Text Dependency
- The objective must be fully supported by:
  - the story text, and/or
  - linked glossary terms

No outside knowledge allowed.

---

## Standards Mapping Layer (Optional)

### Why Standards Are Optional

Standards:
- vary by country and curriculum
- change over time
- often overlap

Learning objectives remain **stable**; standards are **attached later**.

---

## Supported Standards (Initial Targets)

Safegloss should support pluggable frameworks, including:
- Cambridge Primary English
- IB PYP / MYP Language & Literature
- Common Core ELA
- Custom school‑defined standards

---

## Standards Mapping Model (Conceptual)

```json
{
  "learning_objective_id": "LO‑2",
  "bloom_level": "Apply",
  "standards": [
    {
      "framework": "Common Core",
      "code": "CCSS.ELA‑LITERACY.RL.4.4",
      "description": "Determine the meaning of words and phrases as they are used in a text"
    }
  ]
}
```

---

## Quiz Item Metadata (Extended)

Each quiz item must store:
- learning_objective_id
- bloom_level
- comprehension_type
- story_reference (paragraph / sentence range)
- glossary_reference (optional)
- standards_refs (optional list)

This enables:
- reporting
- curriculum alignment
- mastery analytics

---

## Authoring & Generation Flow

### Option A — System‑Generated Objectives (Default)
1. System extracts candidate objectives from the story:
   - literal comprehension
   - vocabulary usage
   - inference
   - structure
2. Objectives filtered by age band and Lexile band
3. Quiz items generated per objective

### Option B — Teacher‑Defined Objectives (Advanced)
- Teacher selects or edits objectives
- Quiz generator targets selected objectives only

---

## Validation Rules

### Structural Validation
- Each quiz item references a valid learning objective

### Cognitive Validation
- Quiz item Bloom level == objective Bloom level
- Objective Bloom level allowed for age band

### Content Validation
- Objective is supported by story/glossary evidence

---

## Why This Matters

This mapping makes quizzes:
- defensible
- standards‑ready
- explainable
- future‑proof for analytics

Without objectives, quizzes are opaque.
With objectives, quizzes become **instructional instruments**.

---

## Summary

Safegloss quizzes:
- assess learning objectives
- objectives align to Bloom’s taxonomy
- standards attach cleanly as metadata
- everything is traceable and auditable

---


# Quiz Validation, Reliability & Analytics

---

## Purpose

This document defines how Safegloss ensures AI‑generated quizzes are:
- valid
- reliable
- age‑appropriate
- analytically useful

Validation is applied **after generation** and **before delivery**.

---

## Validation Layers

### 1. Structural Validation
- JSON schema correctness
- Required fields present
- Valid references (story, objective, glossary)

---

### 2. Cognitive Validation
- Bloom level allowed for age band
- Question type appropriate for Bloom level
- Objective → item Bloom match

---

### 3. Linguistic Validation
- Question stem sentence length within band
- Vocabulary within Lexile proxy limits
- No ambiguous pronouns
- Neutral assessment language

---

### 4. Psychometric Heuristics

Each item must satisfy:
- One clearly correct answer
- Distractors are plausible but incorrect
- No trick wording
- No double negatives
- No overlapping answer choices

---

## Auto‑Repair Strategies

If an item fails validation:
1. Simplify wording
2. Reduce Bloom level
3. Replace distractors
4. Regenerate item only

Max retries per item: 2

---

## Reliability Checks (Heuristic)

Across a quiz:
- Consistent difficulty for same Bloom level
- Balanced comprehension categories
- No duplicate skill assessment

---

## Analytics & Telemetry

Persist per quiz:
- story_id
- learning objectives assessed
- Bloom distribution
- validation pass/fail metrics
- regeneration counts

---

## Reporting Possibilities (Future)

- Objective mastery tracking
- Bloom‑level performance trends
- Story vs quiz difficulty alignment
- Glossary term mastery

---

## Definition of Done

The quiz system is reliable when:
- ≥90% of items pass validation on first or second attempt
- Teachers can explain what each question assesses
- Analytics support instructional decisions

---
