# Quiz Rules & Bloom Mapping
## Deterministic Constraints for AI Quiz Generation

---

## Purpose

This document defines **rule-based constraints** that govern quiz item generation,
mapping **age band, Bloom level, and question type** to allowable forms.

These rules prevent:
- cognitively inappropriate questions
- misaligned difficulty
- invalid assessment constructs

---

## Bloom Level → Question Type Matrix

| Bloom Level | Allowed Question Types | Notes |
|------------|-----------------------|------|
| Remember | MCQ, Matching | Fact recall only |
| Understand | MCQ, Short Answer | Meaning, paraphrase |
| Apply | MCQ, Cloze | Context-based use |
| Analyze | Short Answer | Relationships, motives |
| Evaluate | Short Answer | Judgments with evidence |
| Create | Short Answer | Optional, older students only |

---

## Age Band → Bloom Constraints (Enforced)

| Age Band | Max Bloom Level | Disallowed |
|--------|---------------|------------|
| 6–8 | Understand | Analyze+ |
| 8–10 | Apply | Evaluate+ |
| 10–12 | Analyze | Create |
| 12–14 | Evaluate | None (Create optional) |

---

## Age Band → Item Complexity Rules

### Ages 6–8
- One idea per question
- Concrete wording only
- No abstract reasoning
- Answers directly stated in text

### Ages 8–10
- Simple inference allowed
- Clear textual evidence
- Minimal distractor subtlety

### Ages 10–12
- Multi-sentence reasoning allowed
- Character motivation questions allowed
- Cause-effect chains permitted

### Ages 12–14
- Implicit themes allowed
- Evidence-based judgment
- Comparative reasoning allowed

---

## Distractor Design Rules (MCQ)

- Exactly one correct answer
- Distractors must be:
  - plausible
  - text-related
  - clearly incorrect
- Distractors must not:
  - be humorous
  - use trick wording
  - rely on outside knowledge

---

## Cloze Item Rules

- Blank must target:
  - glossary vocabulary OR
  - key comprehension word
- Sentence must remain grammatical
- Only one unambiguous correct fill

---

## Matching Item Rules

- Maximum 6 pairs
- Terms must appear in the story
- Definitions must reflect story usage

---

## Enforcement Policy

If a generated item violates any rule:
1. Lower Bloom level
2. Simplify question type
3. Regenerate item only

Max attempts per item: 2

---

## Summary

These rules ensure:
- Cognitive appropriateness
- Predictable difficulty
- Valid assessment constructs