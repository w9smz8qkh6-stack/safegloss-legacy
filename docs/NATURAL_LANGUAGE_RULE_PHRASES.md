NATURAL_LANGUAGE_RULE_PHRASES.md
Great—this is the last critical layer between your rule engine and high-quality output.

Below is a canonical set of natural-language rule phrasings that your Prompt Composer should emit, derived directly from the rule files you’ve already defined.

This is written so your agent can:
	•	map JSON keys → phrasing templates
	•	assemble clean, human-readable constraints
	•	keep prompts consistent and auditable

You can save this as:

docs/NATURAL_LANGUAGE_RULE_PHRASES.md


⸻


# Natural-Language Rule Phrasing  
## Prompt Composer Output Reference

---

## Purpose

This document defines the **exact natural-language phrasing** that the Prompt Composer should generate from structured rule data.

The goal is to:
- Translate rules into **clear editorial instructions**
- Avoid ambiguity for the model
- Maintain consistency across prompts
- Prevent “creative drift”

These phrases are **not shown to users**, only injected into prompts.

---

## Prompt Section Ordering (Mandatory)

The Prompt Composer MUST emit rules in this order:

1. Reader & Age Profile
2. Developmental Writing Rules
3. Genre-Specific Rules
4. Lexile & Language Constraints
5. Story-Specific Parameters

---

## 1. Reader & Age Profile

### Template

You are writing for readers aged {{age_band}}.

These readers are still developing reading comprehension and require writing
that matches their cognitive and emotional stage.

### Examples
- “You are writing for readers aged 6–8.”
- “You are writing for readers aged 10–12.”

---

## 2. Developmental Writing Rules (Age-Based)

These phrases come from `age_rules.json`.

---

### Character & Plot Rules

#### `max_characters`
- **1**

Use only one main character.
Do not introduce additional named characters.

- **2**

Use no more than two main characters.
Keep their roles clearly distinct.

- **3+**

Limit the story to {{max_characters}} main characters.
Avoid unnecessary minor characters.

---

#### `conflict_count`
- **1**

Focus on a single, clear problem or challenge.
Do not introduce multiple conflicts.

- **2**

The story may include up to two related challenges.
Ensure both are resolved clearly.

---

#### `timeline`
- **linear**

The story must move forward in time without flashbacks.
Events should occur in the order they happen.

- **mostly_linear**

The story should be mostly linear in time.
Avoid complex time shifts.

- **flexible**

Nonlinear storytelling is allowed if it remains clear.

---

### Emotional & Cognitive Rules

#### `emotion_expression`
- **explicit**

Characters’ emotions must be named directly.
Do not rely on the reader to infer feelings.

- **mixed**

Some emotions may be shown through actions, but key feelings should still be stated.

- **implicit**

Emotions may be implied through actions and dialogue.

---

#### `inference_level`
- **none**

Do not require the reader to infer meaning.
Explain all important ideas directly.

- **low**

Keep inference minimal.
Important meanings should be explained.

- **moderate**

Allow some inference, but ensure understanding by the end.

- **high**

Readers may infer meaning without explicit explanation.

---

#### `moral_clarity`
- **stated**

State the lesson or moral of the story clearly.

- **clear**

Make the lesson clear through the outcome of the story.

- **implied**

The lesson may be implied but should be understandable.

- **implicit**

Do not state the lesson explicitly.

---

#### `flashbacks`
- **false**

Do not use flashbacks or references to past events outside the main timeline.

- **rare**

Flashbacks should be avoided unless absolutely necessary.

- **true**

Flashbacks are allowed if clearly signposted.

---

## 3. Genre-Specific Rules

These phrases come from `genre_rules.json`.

---

### Realistic Fiction

The story should be set in a realistic, everyday environment.
All events must be believable.
Clear cause-and-effect relationships are required.

---

### Fantasy

The story may include magical or imaginary elements.
The rules of the world must be explained clearly.
Limit the number of invented terms.
Do not assume prior knowledge of the fantasy setting.

---

### Mystery

The story must include clear clues.
The solution must be explained step-by-step.
Do not hide essential information from the reader.

---

### Informational Fiction

All factual information must be accurate.
Each section should focus on one main idea.
Key information should be reinforced through repetition.

---

## 4. Lexile & Language Constraints

These phrases come from `lexile_rules.json`.

---

### Sentence Length

#### Example: `avg_sentence_length: 10–13`

Aim for an average sentence length of 10 to 13 words.
Avoid long or complex sentences.

---

### Clause Limits

#### `max_clauses: 0`

Use only simple sentences.
Do not use dependent clauses.

#### `max_clauses: 1`

Limit sentences to one clause.
Avoid nested or layered clauses.

#### `max_clauses: 2`

Limit sentences to no more than two clauses.

---

### Vocabulary Level

#### `very_common`

Use only very common, everyday words.
Avoid academic or abstract vocabulary.

#### `common`

Use common spoken English words.
Avoid rare or specialized vocabulary.

#### `mostly_common`

Use mostly common words.
Introduce new words sparingly and clearly.

#### `mixed`

Some academic words are allowed if clearly supported by context.

#### `academic_allowed`

Academic vocabulary is allowed.
Ensure meaning is clear from context.

---

### Grammar Rules (Always Included)

Use active voice.
Avoid passive constructions.
Use clear subject–verb–object sentence order.

---

## 5. Story-Specific Parameters

These are injected last.

Theme: {{theme}}
Setting: {{setting}}
Main character: {{main_character}}
Tone: {{tone}}
Target length: {{word_count}} words
Dialogue level: {{dialogue_ratio}}

---

## Study Mode (Optional)

If `study_mode = true`:

When a potentially difficult word appears,
define it immediately using simple language within the sentence.

---

## Output Constraints (Always Final)

Output plain text only.
Do not include headings, bullet points, or explanations.
Do not mention rules or constraints in the output.

---

## Summary for the Agent

Each rule:
- Maps directly from JSON
- Emits deterministic phrasing
- Is composable and auditable
- Avoids stylistic ambiguity

This ensures **repeatable, pedagogically sound story generation**.