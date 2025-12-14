# Lexile-Controlled Story Generation  
**Implementation & Prompt Template Guide**

## Purpose

This document defines how to generate AI stories that are **Lexile-aligned** (approximate) using explicit linguistic constraints rather than relying on proprietary Lexile scoring.

The goal is to:
- Generate predictable, leveled stories
- Integrate cleanly with the Story Creation page
- Support iteration and validation
- Avoid Lexile® trademark misuse

---

## Important Constraints & Definitions

### Lexile Reality Check
- Lexile is a **proprietary algorithm** (MetaMetrics)
- We cannot compute or claim exact Lexile scores
- We *can* generate **Lexile-aligned** or **Lexile-banded** content

All outputs should be described as:
> “Designed for readers around 600–700L”

---

## Core Strategy

Lexile alignment is achieved by controlling **proxies**:

1. Average sentence length
2. Sentence structure complexity
3. Vocabulary frequency
4. Clause depth
5. Passive voice usage
6. Abstract vs concrete language

The AI must be guided **explicitly** on these dimensions.

---

## Story Generation Inputs (from Story Creation Page)

These values should be passed into the prompt dynamically.

### Required Inputs
- `target_lexile_band` (e.g. 500–600L)
- `word_count`
- `theme_or_topic`
- `audience_age_range`

### Optional Inputs (Highly Recommended)
- `allowed_vocabulary_list` (glossary-based)
- `restricted_words_list`
- `tone` (adventure, calm, humorous, etc.)
- `setting`
- `main_character_profile`
- `dialogue_ratio` (low / medium / high)
- `study_mode` (true/false)

---

## Lexile Band Constraint Table

Use this table to convert Lexile bands into **explicit linguistic rules**.

| Lexile Band | Avg Sentence Length | Sentence Types | Vocabulary | Clauses |
|------------|--------------------|---------------|------------|--------|
| 300–400L | 6–9 words | Simple | Very common | None |
| 400–500L | 8–11 words | Simple | Common | Occasional |
| 500–600L | 10–13 words | Simple + compound | Mostly common | Limited |
| 600–700L | 11–14 words | Simple + compound | Some academic | Few |
| 700–900L | 13–17 words | Compound | Mixed | Moderate |
| 900–1100L | 16–20 words | Complex allowed | Academic | Regular |

---

## Prompt Construction Rules (Non-Negotiable)

### Always Include
- Explicit sentence length target
- Explicit sentence structure guidance
- Vocabulary guidance
- Passive voice instruction
- Clause limitation instruction

### Never Rely On
- “Write at a 600L level” alone
- Grade-level labels without constraints

---

## Canonical Prompt Template

This is the **base template** your agent should implement.

### System Message

You are an educational content generator specializing in leveled reading texts.
You strictly follow linguistic constraints related to sentence length,
syntax complexity, and vocabulary usage.

---

### User Prompt Template

Generate a short story using the following constraints.

TARGET READING BAND
Lexile target: {{target_lexile_band}}
(This is approximate and must be achieved using linguistic constraints below.)

LENGTH
Total length: {{word_count}} words (±5%)

SENTENCE CONSTRAINTS
	•	Average sentence length: {{avg_sentence_length}} words
	•	Prefer simple and compound sentences
	•	Limit dependent clauses to {{max_clauses_per_sentence}} per sentence
	•	Avoid nested clauses
	•	Avoid parentheticals and appositives

VOCABULARY CONSTRAINTS
	•	Use mostly high-frequency, everyday English words
	•	Avoid rare or abstract academic vocabulary unless explicitly allowed
	•	Prefer concrete nouns and verbs
{{#if allowed_vocabulary_list}}
	•	Allowed vocabulary list:
{{allowed_vocabulary_list}}
{{/if}}
{{#if restricted_words_list}}
	•	Avoid using the following words:
{{restricted_words_list}}
{{/if}}

GRAMMAR & STYLE
	•	Avoid passive voice
	•	Use active, direct sentence construction
	•	Use clear subject-verb-object order
	•	Avoid figurative language unless simple and explicit

DIALOGUE
Dialogue level: {{dialogue_ratio}}
	•	Keep dialogue sentences short and direct

CONTENT
	•	Theme: {{theme_or_topic}}
	•	Setting: {{setting}}
	•	Main character: {{main_character_profile}}
	•	Audience age range: {{audience_age_range}}

STUDY MODE
{{#if study_mode}}
	•	When a potentially difficult word appears, immediately define it in simple language within the sentence
{{/if}}

OUTPUT FORMAT
	•	Plain text only
	•	No headings
	•	No bullet points
	•	No explanations

---

## Example Filled Prompt (600–700L)

Lexile target: 600–700L
Total length: 450 words
Average sentence length: 12–14 words
Max clauses per sentence: 1
Dialogue level: medium
Theme: curiosity and problem-solving
Audience: ages 10–12

---

## Post-Generation Validation (Required)

After generation, the system should run:

1. Average sentence length calculation
2. Long sentence detection (>18 words)
3. Vocabulary frequency scan
4. Passive voice detection

If out of range:
- Simplify sentences
- Replace rare words
- Re-run generation

---

## Legal & Branding Notes

- Do NOT label output as “Lexile® certified”
- Approved wording:
  - “Lexile-aligned”
  - “Designed for readers around 600–700L”
  - “Reading difficulty approximately equivalent to…”

---

## Future Enhancements

- Adaptive Lexile increase based on student mastery
- Glossary-locked vocabulary stories
- Term highlighting linked to glossary entries
- Dual-mode output (Study vs Exam)

---

## Summary

Lexile control is achieved through:
- Explicit constraints
- Predictable sentence structure
- Vocabulary discipline
- Iterative validation

This prompt template is the **foundation** for reliable, scalable leveled story generation.