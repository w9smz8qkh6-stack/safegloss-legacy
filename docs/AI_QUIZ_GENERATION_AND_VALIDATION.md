

# AI Quiz Generation & Validation Specification

## Purpose

This document defines the **prompting, generation, and validation framework** for AI‑generated quizzes in the Safegloss ecosystem.

The quiz system is designed to:
- Align tightly with **AI‑generated stories** and **linked glossaries**
- Respect **reading level (Lexile‑aligned)** constraints
- Encode **cognitive demand** using **Bloom’s Taxonomy**
- Follow **psychometric best practices** for validity and reliability
- Model the **style and rigor of standards‑aligned assessments**

The goal is not to generate “fun questions,” but to generate **instructionally sound, explainable, and reusable assessment items**.

---

## Core Design Principles

1. **Assessment First, AI Second**  
   Item quality is governed by learning theory, not model creativity.

2. **Traceability**  
   Every quiz item must be traceable to:
   - a specific story segment, and/or
   - a specific glossary term

3. **Constraint‑Driven Generation**  
   Quiz items are produced using explicit constraints, not generic prompts.

4. **Explainability**  
   Each item must be explainable to a teacher: *what it tests and why*.

---

## Inputs to Quiz Generation

### Required Inputs
- `story_id`
- `story_text`
- `age_band`
- `lexile_band`
- `linked_glossary_terms`

### Optional Inputs
- `quiz_length`
- `question_type_mix`
- `bloom_distribution`
- `assessment_mode` (study | exam)
- `standards_context` (optional future)

---

## Cognitive Framework — Bloom’s Taxonomy

Quiz items are classified and generated according to **Bloom’s cognitive levels**.

| Bloom Level | Description | Example Reading Skill |
|------------|-------------|-----------------------|
| Remember | Recall facts | Identify a detail |
| Understand | Explain meaning | Summarize a paragraph |
| Apply | Use information | Use context to infer meaning |
| Analyze | Break down | Compare motivations |
| Evaluate | Judge | Assess a character’s choice |
| Create | Synthesize | Propose an alternative ending |

### Age‑Appropriate Bloom Constraints

| Age Band | Allowed Bloom Levels |
|--------|---------------------|
| 6–8 | Remember, Understand |
| 8–10 | Remember, Understand, Apply |
| 10–12 | Remember → Analyze |
| 12–14 | Remember → Evaluate (Create optional) |

---

## Reading Comprehension Focus Areas

All quiz items must fall into at least one of the following categories:

1. **Literal Comprehension**
   - Who, what, when, where
2. **Vocabulary in Context**
   - Meaning of glossary terms as used in the story
3. **Inferential Comprehension**
   - Why events happened (age‑appropriate)
4. **Structural Understanding**
   - Sequence, cause‑effect
5. **Author’s Purpose / Theme** (older bands)

Items must **not** test background knowledge unrelated to the story.

---

## Psychometric Design Guidelines

### Validity
Each item must:
- Measure the intended construct (reading comprehension)
- Avoid construct‑irrelevant difficulty (e.g. tricky wording)
- Align with the declared Bloom level

### Reliability
Across items:
- Similar difficulty for same Bloom level
- Consistent wording patterns
- Clear, unambiguous correct answers

### Bias & Fairness
- Avoid cultural or idiomatic assumptions
- Avoid unnecessary figurative language
- Prefer concrete phrasing

---

## Reference Corpora (Modeling Assessment Style)

The system should model the *style* (not copy content) of:
- NAEP reading items
- Cambridge Primary English assessments
- IB PYP / MYP reading comprehension tasks
- Publicly released standardized test questions

### What We Extract (Not Store)
- Question stem patterns
- Distractor design strategies
- Cognitive load pacing
- Language formality level

---

## Quiz Item Types

### Supported Types
- Multiple Choice (MCQ)
- Short Answer
- Vocabulary Matching
- Cloze (Fill‑in‑the‑Blank)

Each item must include:
- Correct answer
- Distractor rationale (MCQ)
- Bloom level tag
- Comprehension category

---

## Canonical Quiz Prompt Template

### System Message
```
You are an educational assessment designer.
You generate reading comprehension quiz items that follow
explicit cognitive, linguistic, and psychometric constraints.
```

### User Prompt Template
```
Generate a quiz based on the following story.

STORY CONTEXT
Age band: {{age_band}}
Lexile band: {{lexile_band}}
Assessment mode: {{assessment_mode}}

COGNITIVE CONSTRAINTS
Allowed Bloom levels: {{allowed_bloom_levels}}
Target Bloom distribution: {{bloom_distribution}}

CONTENT RULES
- All questions must be answerable from the text alone
- Questions must focus on reading comprehension
- Avoid background knowledge

VOCABULARY RULES
- Use linked glossary terms when appropriate
- Vocabulary difficulty must match the Lexile band

QUESTION REQUIREMENTS
For each question provide:
- Question text
- Question type
- Bloom level
- Correct answer
- Explanation of why the answer is correct

OUTPUT FORMAT
Return structured JSON only.
```

---

## Output Schema (Quiz Item)

```json
{
  "question_id": "uuid",
  "question_type": "multiple_choice",
  "bloom_level": "Understand",
  "comprehension_type": "Literal",
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "B",
  "explanation": "...",
  "story_reference": "paragraph_3",
  "glossary_reference": "term_id_optional"
}
```

---

## Validation Pipeline

### Structural Validation
- Required fields present
- JSON schema valid

### Cognitive Validation
- Bloom level allowed for age band
- Question type appropriate to Bloom level

### Linguistic Validation
- Question stem sentence length within bounds
- Vocabulary within Lexile proxy limits

### Psychometric Heuristics
- Distractors plausible but incorrect
- One unambiguous correct answer
- No trick wording

---

## Auto‑Repair Strategies

If validation fails:
1. Simplify wording
2. Reduce cognitive level
3. Replace distractors
4. Regenerate item only (not full quiz)

Max retries per item: 2

---

## Study vs Exam Mode Differences

### Study Mode
- Explanations shown
- Glossary access allowed
- Hints permitted

### Exam Mode
- No explanations shown
- Glossary access configurable
- Neutral wording only

---

## Storage & Reuse

Persist:
- Quiz metadata
- Item metadata
- Bloom distribution
- Story + glossary linkage

Enable:
- Editing
- Regeneration variants
- Reuse across classes

---

## Definition of Done

The quiz system is complete when:
- Quizzes are aligned to stories and glossaries
- Items respect Bloom and Lexile constraints
- Items are explainable and auditable
- Teachers trust the results for instruction or assessment

---