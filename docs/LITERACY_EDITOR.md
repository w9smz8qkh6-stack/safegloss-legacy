LITERACY_EDITOR.md
Excellent — this is the point where the project becomes operationally real.

Below I’ll give you three concrete deliverables, all written so your agent can immediately act:
	1.	Age × Genre Writing Rules Matrix (human-readable + canonical)
	2.	Rule files (JSON) + where they live + how they’re used
	3.	A technical task list your agent can execute end-to-end

You can paste this straight into your repo or split it into files.

⸻

1. Age × Genre Writing Rules Matrix

This matrix defines editorial constraints, not creativity hints.

Age Bands (Canonical)

Age Band	Typical Lexile
6–8	300–450L
8–10	450–650L
10–12	600–850L
12–14	800–1050L


⸻

A. Cross-Age Core Rules (Apply to All Genres)

Dimension	6–8	8–10	10–12	12–14
Main characters	1	1–2	≤3	≤4
Conflicts	1	1	1–2	2
Timeline	Linear only	Linear	Mostly linear	Nonlinear allowed
Emotions	Named explicitly	Named	Mixed	Often inferred
Inference	None	Low	Moderate	High
Moral	Stated	Clear	Implied	Implicit
Flashbacks	Never	Never	Rare	Allowed


⸻

B. Genre-Specific Rules by Age

Realistic Fiction

Age	Rules
6–8	Everyday settings, clear cause → effect, adult support visible
8–10	Small personal goals, peer interaction, clear resolution
10–12	Internal conflict allowed, realistic setbacks
12–14	Ambiguity allowed, complex motivations


⸻

Fantasy

Age	Rules
6–8	One magical element, explained immediately
8–10	Simple world rules, limited invented terms
10–12	Consistent world logic, mild lore
12–14	Complex systems, delayed exposition


⸻

Mystery

Age	Rules
6–8	Problem is obvious, solution explained step-by-step
8–10	Clues explicit, reasoning shown
10–12	Reader inference encouraged but resolved
12–14	Red herrings allowed, layered clues


⸻

Informational Fiction

Age	Rules
6–8	Facts repeated, topic stated clearly
8–10	One concept per section
10–12	Cause–effect chains
12–14	Synthesis across ideas


⸻

2. Rule Files (JSON) + How to Use Them

These files are merged dynamically to produce the final prompt.

Recommended Directory Structure

/rules/
  age_rules.json
  genre_rules.json
  lexile_rules.json
  ell_rules.json        (optional)


⸻

A. age_rules.json

{
  "6-8": {
    "max_characters": 1,
    "conflict_count": 1,
    "timeline": "linear",
    "emotion_expression": "explicit",
    "inference_level": "none",
    "moral_clarity": "stated",
    "flashbacks": false
  },
  "8-10": {
    "max_characters": 2,
    "conflict_count": 1,
    "timeline": "linear",
    "emotion_expression": "explicit",
    "inference_level": "low",
    "moral_clarity": "clear",
    "flashbacks": false
  },
  "10-12": {
    "max_characters": 3,
    "conflict_count": 2,
    "timeline": "mostly_linear",
    "emotion_expression": "mixed",
    "inference_level": "moderate",
    "moral_clarity": "implied",
    "flashbacks": "rare"
  },
  "12-14": {
    "max_characters": 4,
    "conflict_count": 2,
    "timeline": "flexible",
    "emotion_expression": "implicit",
    "inference_level": "high",
    "moral_clarity": "implicit",
    "flashbacks": true
  }
}


⸻

B. genre_rules.json

{
  "realistic_fiction": {
    "setting": "grounded",
    "magic_allowed": false,
    "cause_effect_required": true
  },
  "fantasy": {
    "setting": "invented",
    "magic_allowed": true,
    "world_rules_must_be_stated": true,
    "limit_invented_terms": true
  },
  "mystery": {
    "clues_required": true,
    "resolution_must_explain_reasoning": true
  },
  "informational_fiction": {
    "facts_must_be_accurate": true,
    "topic_sentences_required": true,
    "reinforcement_required": true
  }
}


⸻

C. lexile_rules.json

{
  "300-400L": {
    "avg_sentence_length": "6-9",
    "max_clauses": 0,
    "vocabulary_level": "very_common"
  },
  "400-500L": {
    "avg_sentence_length": "8-11",
    "max_clauses": 1,
    "vocabulary_level": "common"
  },
  "500-600L": {
    "avg_sentence_length": "10-13",
    "max_clauses": 1,
    "vocabulary_level": "mostly_common"
  },
  "600-700L": {
    "avg_sentence_length": "11-14",
    "max_clauses": 1,
    "vocabulary_level": "mixed"
  },
  "700-900L": {
    "avg_sentence_length": "13-17",
    "max_clauses": 2,
    "vocabulary_level": "academic_allowed"
  }
}


⸻

How These Files Are Used (Critical)

Prompt Assembly Pipeline
	1.	User selects:
	•	Age
	•	Genre
	•	Lexile band
	2.	Backend:
	•	Loads age_rules[age]
	•	Merges genre_rules[genre]
	•	Applies lexile_rules[band]
	3.	System converts rules into plain-English constraints
	4.	Constraints injected into prompt template

⚠️ Never expose raw JSON to the model.

⸻

3. Technical Task List for Your Agent

This is implementation-ready.

⸻

Phase 1 — Foundations
	•	Create /rules/ directory
	•	Populate age_rules.json
	•	Populate genre_rules.json
	•	Populate lexile_rules.json
	•	Validate schemas (required keys present)

⸻

Phase 2 — Writing Profile Builder
	•	Create WritingProfile object
	•	Inputs:
	•	age_band
	•	genre
	•	lexile_band
	•	optional flags (ELL, study_mode)
	•	Merge rule files into one profile
	•	Output normalized constraints

⸻

Phase 3 — Prompt Composer
	•	Convert profile rules into natural language
	•	Enforce layering order:
	1.	Reader profile
	2.	Developmental rules
	3.	Genre rules
	4.	Lexile constraints
	5.	Story parameters
	•	Plug into existing Lexile prompt template

⸻

Phase 4 — Validation Pipeline
	•	Sentence length analyzer
	•	Clause counter (heuristic)
	•	Passive voice detector
	•	Vocabulary frequency checker
	•	Auto-rewrite loop if out of bounds

⸻

Phase 5 — UI Integration
	•	Story Creation page:
	•	Age selector
	•	Genre selector
	•	Lexile band selector
	•	Tooltips:
	•	Explain “Lexile-aligned”
	•	Explain age-appropriate constraints
	•	Teacher preview metadata:
	•	“Designed for ages X–Y”
	•	“Approx. 600–700L”

⸻

Phase 6 — Safety & Compliance
	•	Ensure no copyrighted exemplars
	•	Add wording guardrails
	•	Prevent “write like [author]” prompts

⸻

Final Insight (Important)

What you’ve built here is not a story generator.