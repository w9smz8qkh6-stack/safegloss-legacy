Perfect — below is a single, agent-ready Markdown file that captures the expertise, sources, extraction process, and operational prompting strategy you asked for.

This is written so an agent can:
	•	turn it into code,
	•	build rule libraries,
	•	assemble prompts dynamically,
	•	and remain legally safe.

You can save this as:

docs/LEXILE_YOUNG_READERS_WRITING_EXPERTISE.md


⸻


# Writing for Young Readers  
## Capturing Educational Expertise for Lexile-Controlled AI Story Generation

---

## Purpose

This document defines **how to acquire, encode, and operationalize expert knowledge** about writing stories for young readers in an educational context.

It complements the Lexile-controlled prompt system by adding:
- Age-appropriate pedagogy
- Genre-specific narrative rules
- Empirically derived language patterns
- Legal and ethical safeguards

The goal is **not to train a new model**, but to **systematically guide prompting** so AI-generated stories resemble professionally edited children’s literature.

---

## Core Principle

> Children’s literature quality comes from **constraints**, not creativity alone.

Professional publishers encode expertise through:
- Developmental rules
- Genre conventions
- Linguistic limits
- Editorial heuristics

This document explains how to capture those rules.

---

## A. Sources of Expertise

We rely on **three complementary knowledge sources**.

---

### 1. Open & Public-Domain Children’s Corpora (Empirical Evidence)

These sources provide **measurable linguistic patterns**.

#### Recommended Sources
| Source | Value |
|---|---|
| Project Gutenberg | Public-domain children’s fiction |
| International Children’s Digital Library (ICDL) | Age-tagged texts |
| Open Library | Metadata-rich editions |
| British National Corpus (subset) | Language usage patterns |
| Curated leveled readers (public domain) | Sentence & pacing norms |

#### What We Extract
- Average sentence length by age
- Sentence length variance
- Dialogue percentage
- Paragraph length
- Vocabulary reuse frequency
- Narrative pacing markers

> These metrics are descriptive, not copied text.

---

### 2. Educational & Pedagogical Frameworks (Best Practice)

These sources define **what children can cognitively process**.

#### Authoritative Frameworks
- Reading Recovery
- Fountas & Pinnell
- CEFR (A1–B2, young learner interpretation)
- NAEP Reading Framework
- Cambridge Primary English
- IB PYP Language Scope & Sequence

#### What We Capture
- Appropriate abstraction levels
- Inference expectations by age
- Emotional explicitness requirements
- Cognitive load limits
- Moral and thematic complexity

---

### 3. Genre Craft Knowledge (Editorial Wisdom)

This is the **tacit knowledge** used by editors and teachers.

Examples:
- Younger readers need explicit cause-and-effect
- Fantasy requires extra grounding
- Mystery requires clarity of clues
- Informational fiction prioritizes cohesion
- Humor must be concrete for younger ages

Sources include:
- Teacher guides
- Writing handbooks
- Publisher submission rubrics
- Curriculum-aligned writing guides

---

## B. Building a Reference Corpus

### Minimum Viable Corpus

For each combination of:
- Age band
- Genre

Collect:
- 20–50 representative public-domain texts

Example buckets:
- Ages 6–8 × Realistic Fiction
- Ages 8–10 × Fantasy
- Ages 10–12 × Mystery
- Ages 10–12 × Informational Fiction

---

### Corpus Tagging

Each text should be tagged with:
- Intended age range
- Genre
- Approximate Lexile band (if known)
- Word count

---

## C. Extracting Patterns from the Corpus

Your agent should compute **statistics**, not store text.

---

### 1. Structural Metrics

- Average sentence length
- Sentence length variance
- Paragraph length
- Dialogue ratio
- Number of sentences per paragraph

---

### 2. Linguistic Metrics

- Vocabulary reuse rate
- Pronoun density
- Abstract noun frequency
- Verb concreteness
- Temporal markers:
  - then
  - after
  - suddenly
  - finally

---

### 3. Narrative Heuristics (Rule-Based)

Heuristics inferred from analysis:
- Number of named characters
- Explicit vs implicit goals
- Conflict count
- Resolution explicitness
- Moral stated vs inferred

These are encoded as **rules**, not learned weights.

---

## D. Encoding Expertise as Writing Rules

### Example: Age 6–8

	•	One main character
	•	One problem at a time
	•	Events occur in linear order
	•	Emotions must be named explicitly
	•	Cause and effect stated directly
	•	No flashbacks
	•	No implied motives

---

### Example: Age 8–10

	•	One or two main characters
	•	Clear external goal
	•	Limited internal thoughts allowed
	•	One main conflict
	•	Dialogue advances plot
	•	Minimal inference required

---

### Example: Age 10–12

	•	Two main characters allowed
	•	Internal thoughts permitted
	•	Mild inference allowed but resolved
	•	Subplots minimal
	•	Dialogue carries meaning
	•	Moral may be implied but clarified

---

## E. Genre-Specific Writing Rules

### Realistic Fiction
- Grounded settings
- Cause-and-effect clarity
- Emotional realism

### Fantasy
- Extra grounding early
- Limit invented terminology
- Rules of the world stated clearly

### Mystery
- Explicit clues
- No red herrings for younger ages
- Resolution explains reasoning

### Informational Fiction
- Strong cohesion
- Repetition for reinforcement
- Clear topic sentences

---

## F. Operationalizing Expertise in Prompting

### 1. Build a “Writing Profile” Object

This object is assembled **before prompting**.

```json
{
  "age_band": "8–10",
  "genre": "realistic fiction",
  "lexile_band": "500–600L",
  "narrative_rules": {
    "max_characters": 2,
    "conflict_count": 1,
    "emotion_expression": "explicit",
    "inference_level": "low",
    "moral_clarity": "explicit"
  },
  "style_rules": {
    "avg_sentence_length": "10–12",
    "dialogue_ratio": "medium",
    "paragraph_length": "short"
  }
}


⸻

2. Inject Rules, Not Examples

Never prompt with:

“Write like a children’s book.”

Always prompt with:

You are writing for readers aged 8–10.

Writing rules:
- Use explicit emotional language
- Keep events in linear time
- State cause and effect clearly
- Resolve the main problem explicitly


⸻

3. Prompt Layering Order (Critical)

Prompts must be layered in this order:
	1.	Reader profile (age)
	2.	Developmental rules
	3.	Genre rules
	4.	Lexile constraints
	5.	Story-specific parameters

This mirrors professional editorial workflows.

⸻

G. Rules Library Architecture

Maintain a modular rules library:
	•	age_rules.json
	•	genre_rules.json
	•	lexile_rules.json
	•	ell_rules.json (optional)

Rules are merged dynamically to build the final prompt.

⸻

H. Legal & Ethical Safeguards

Allowed
	•	Analyze public-domain texts
	•	Extract statistics
	•	Encode heuristics
	•	Generate original stories

Prohibited
	•	Mimicking living authors
	•	Reproducing copyrighted passages
	•	Claiming official Lexile certification

Approved phrasing:
	•	“Lexile-aligned”
	•	“Designed for readers around 600–700L”

⸻

I. Why This Matters

This approach transforms AI from:

“creative generator”

into:

editorially constrained literacy tool

It enables:
	•	Predictable leveling
	•	Pedagogical integrity
	•	Personalization
	•	Curriculum alignment

⸻

J. Next Implementation Steps

Recommended next artifacts:
	1.	Age × Genre Writing Rules Matrix
	2.	Writing Profile Builder schema
	3.	Corpus analysis script outline
	4.	Prompt composer service
	5.	Teacher-facing explanation UI text

⸻

Summary

High-quality children’s stories are the result of:
	•	Developmental awareness
	•	Genre discipline
	•	Linguistic control
	•	Editorial heuristics

This document defines how to capture that expertise and make it executable.