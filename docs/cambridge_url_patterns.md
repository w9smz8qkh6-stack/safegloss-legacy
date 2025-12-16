# Cambridge International URL Patterns

This document describes the URL patterns used by Cambridge Assessment International Education for their syllabus pages.

## Base URL

```
https://www.cambridgeinternational.org/programmes-and-qualifications/
```

## Programme-Specific Patterns

### Cambridge Primary (Ages 5-11)

**Pattern:**
```
/cambridge-primary/curriculum/{subject-slug}/
```

**Examples:**
- Mathematics (0096): `/cambridge-primary/curriculum/mathematics/`
- English (0058): `/cambridge-primary/curriculum/english/`
- Global Perspectives (0838): `/cambridge-primary/curriculum/cambridge-primary-global-perspectives/`

**Notes:**
- Subject slug is the lowercase, hyphenated subject name
- Global Perspectives has a special prefix

---

### Cambridge Lower Secondary (Ages 11-14)

**Pattern:**
```
/cambridge-lower-secondary/curriculum/{subject-slug}/
```

**Examples:**
- Mathematics (0862): `/cambridge-lower-secondary/curriculum/mathematics/`
- Science (0893): `/cambridge-lower-secondary/curriculum/science/`
- Global Perspectives (1129): `/cambridge-lower-secondary/curriculum/cambridge-lower-secondary-global-perspectives/`

**Notes:**
- Same structure as Primary
- Global Perspectives has programme-specific prefix

---

### Cambridge IGCSE (Ages 14-16)

**Standard Pattern:**
```
/cambridge-igcse-{subject-slug}-{syllabus-code}/
```

**Examples:**
- Mathematics (0580): `/cambridge-igcse-mathematics-0580/`
- Biology (0610): `/cambridge-igcse-biology-0610/`
- English - First Language (0500): `/cambridge-igcse-english-first-language-0500/`

**9-1 Grading Variants:**

Most 9-1 variants follow: `/cambridge-igcse-{subject-slug}-9-1-{code}/`

However, some have non-standard patterns:
| Syllabus | Name | URL Pattern |
|----------|------|-------------|
| 0990 | First Language English (9-1) | `/cambridge-igcse-9-1-first-language-english-0990/` |
| 0991 | ESL Count-in Speaking (9-1) | `/cambridge-igcse-english-second-language-9-1-count-in-speaking/` |
| 0992 | Literature in English (9-1) | `/cambridge-igcse-english-literature-0992/` |
| 0993 | ESL Speaking Endorsement (9-1) | `/cambridge-igcse-english-second-language-speaking-endorsement-9-1-0993/` |
| 0973 | Co-ordinated Sciences (9-1) | `/cambridge-igcse-sciences-9-1-only-0973/` |
| 0984 | Computer Science (9-1) | `/cambridge-igcse-9-1-computer-science-0984/` |

**Special Cases:**
| Syllabus | Name | URL Pattern |
|----------|------|-------------|
| 0475 | Literature in English | `/english-literature-0475/` (no prefix!) |
| 0510 | ESL Speaking Endorsement | `/cambridge-igcse-english-second-language-oral-endorsement-0510/` |
| 0511 | ESL Count-in Speaking | `/cambridge-igcse-english-second-language-count-in-oral-0511/` |
| 0538 | Indonesian (Bahasa) | `/cambridge-igcse-bahasa-indonesia-0538/` |
| 0607 | International Mathematics | `/cambridge-igcse-international-mathematics-0607/` |

---

### Cambridge O Level (Ages 14-16)

**Pattern:**
```
/cambridge-o-level-{subject-slug}-{syllabus-code}/
```

**Examples:**
- Accounting (7707): `/cambridge-o-level-accounting-7707/`
- Biology (5090): `/cambridge-o-level-biology-5090/`
- Mathematics Syllabus D (4024): `/cambridge-o-level-mathematics-d-4024/`

**Notes:**
- Consistent pattern across all subjects
- "Syllabus D" becomes "d" in slug

---

### Cambridge International AS & A Level (Ages 16-19)

**Pattern:**
```
/cambridge-international-as-and-a-level-{subject-slug}-{syllabus-code}/
```

**Examples:**
- Mathematics (9709): `/cambridge-international-as-and-a-level-mathematics-9709/`
- Biology (9700): `/cambridge-international-as-and-a-level-biology-9700/`
- Physics (9702): `/cambridge-international-as-and-a-level-physics-9702/`

**Special Cases:**
| Syllabus | Name | URL Pattern |
|----------|------|-------------|
| 9981 | European History | `/cambridge-international-as-and-a-level-history-9981/` |
| 9982 | International History | `/cambridge-international-as-and-a-level-history-9982/` |
| 9481 | Digital Media & Design | `/cambridge-international-as-and-a-level-digital-media-design-9481/` |
| 9897 | German Language & Literature | `/cambridge-international-as-and-a-level-german-9897/` |
| 9898 | French Language & Literature | Shares page with 9716: `/cambridge-international-as-and-a-level-french-9716/` |

---

## Slug Generation Rules

1. Convert to lowercase
2. Replace ` & ` with `-and-`
3. Replace ` - ` with `-`
4. Remove parentheses
5. Replace spaces with hyphens
6. Remove consecutive hyphens

**Example transformations:**
- "Art & Design" → `art-and-design`
- "English - First Language" → `english-first-language`
- "Mathematics (US)" → `mathematics-us`
- "English as a Second Language - Count-in Speaking" → `english-as-a-second-language-count-in-speaking`

---

## Shared Pages

Some 9-1 grading variants share pages with their A*-G counterparts:
- 7184 (Arabic First Language 9-1) shares with 0508
- 0995 (Physical Education 9-1) shares with 0413
- 9898 (French Language & Literature) shares with 9716

---

## Verification

All 214 URLs in the Cambridge course catalog have been verified as returning HTTP 200 status codes as of December 2024.

## Related Files

- Course catalog: `data/seeds/cambridge_international_course_catalog.json`
- Seeder command: `core/management/commands/seed_cambridge_course_catalog.py`
