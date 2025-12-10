"""Utility functions for the core app."""
import re
import math
import logging
from html.parser import HTMLParser
from typing import Optional

import textstat
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# LEXILE ESTIMATION
# =============================================================================

# Lexile grade band reference (approximate)
LEXILE_GRADE_BANDS = {
    "K-1": (0, 300),
    "1": (190, 530),
    "2": (420, 650),
    "3": (520, 820),
    "4": (740, 940),
    "5": (830, 1010),
    "6": (925, 1070),
    "7": (970, 1120),
    "8": (1010, 1185),
    "9": (1050, 1260),
    "10": (1080, 1335),
    "11-12": (1185, 1385),
    "College": (1300, 1600),
}


def strip_html(html_text: str) -> str:
    """Remove HTML tags and decode entities for text analysis."""
    if not html_text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def estimate_lexile(text: str) -> dict:
    """
    Estimate Lexile level using textstat metrics as proxies.

    Lexile is based on:
    - Mean sentence length (syntactic complexity)
    - Word frequency (semantic difficulty)

    Since we don't have the proprietary Lexile corpus, we approximate using:
    - Flesch-Kincaid Grade Level (correlated with Lexile)
    - Dale-Chall (uses word frequency list)
    - Sentence statistics

    Returns dict with estimated Lexile and supporting metrics.
    """
    if not text or len(text.split()) < 10:
        return {
            "lexile": None,
            "lexile_label": "Insufficient text",
            "grade_level": None,
            "metrics": {}
        }

    # Ensure we're working with plain text
    plain_text = strip_html(text) if '<' in text else text

    # Get core metrics
    sentence_count = textstat.sentence_count(plain_text)
    word_count = textstat.lexicon_count(plain_text, removepunct=True)
    syllable_count = textstat.syllable_count(plain_text)

    if sentence_count == 0 or word_count == 0:
        return {
            "lexile": None,
            "lexile_label": "Unable to analyze",
            "grade_level": None,
            "metrics": {}
        }

    # Calculate derived metrics
    avg_sentence_length = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count

    # Get various readability scores
    flesch_kincaid_grade = textstat.flesch_kincaid_grade(plain_text)
    dale_chall = textstat.dale_chall_readability_score(plain_text)
    smog = textstat.smog_index(plain_text)
    ari = textstat.automated_readability_index(plain_text)
    coleman_liau = textstat.coleman_liau_index(plain_text)

    # Get difficult word percentage (proxy for word frequency)
    difficult_words = textstat.difficult_words(plain_text)
    difficult_word_pct = (difficult_words / word_count * 100) if word_count > 0 else 0

    # Estimate Lexile using grade-to-Lexile conversion
    # Average multiple grade-level estimates for robustness
    grade_estimates = [
        flesch_kincaid_grade,
        dale_chall,  # Dale-Chall is already grade-adjusted
        smog,
        ari,
        coleman_liau
    ]
    # Filter out invalid values
    valid_grades = [g for g in grade_estimates if g is not None and 0 <= g <= 20]

    if valid_grades:
        avg_grade = sum(valid_grades) / len(valid_grades)
    else:
        avg_grade = flesch_kincaid_grade or 5

    # Convert grade level to approximate Lexile
    # Formula derived from grade band correlations:
    # Lexile ≈ 200 + (grade * 100) with adjustments for difficulty
    base_lexile = 200 + (avg_grade * 100)

    # Adjust based on sentence complexity and word difficulty
    sentence_adjustment = (avg_sentence_length - 15) * 5  # Baseline ~15 words/sentence
    word_adjustment = (difficult_word_pct - 10) * 8  # Baseline ~10% difficult words

    estimated_lexile = int(base_lexile + sentence_adjustment + word_adjustment)

    # Clamp to valid Lexile range
    estimated_lexile = max(0, min(2000, estimated_lexile))

    # Determine grade band label
    lexile_label = get_lexile_label(estimated_lexile)

    return {
        "lexile": estimated_lexile,
        "lexile_label": lexile_label,
        "grade_level": round(avg_grade, 1),
        "metrics": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "difficult_word_pct": round(difficult_word_pct, 1),
            "flesch_kincaid_grade": round(flesch_kincaid_grade, 1) if flesch_kincaid_grade else None,
            "dale_chall": round(dale_chall, 1) if dale_chall else None,
            "smog_index": round(smog, 1) if smog else None,
            "flesch_reading_ease": round(textstat.flesch_reading_ease(plain_text), 1),
        }
    }


def get_lexile_label(lexile: int) -> str:
    """Get a human-readable grade band label for a Lexile score."""
    for grade, (low, high) in LEXILE_GRADE_BANDS.items():
        if low <= lexile <= high:
            return f"Grade {grade} ({lexile}L)"
    if lexile < 200:
        return f"Beginning Reader ({lexile}L)"
    if lexile > 1400:
        return f"Advanced ({lexile}L)"
    return f"{lexile}L"


def lexile_to_grade_band(lexile: int) -> str:
    """Convert Lexile score to grade band string."""
    for grade, (low, high) in LEXILE_GRADE_BANDS.items():
        if low <= lexile <= high:
            return grade
    if lexile < 200:
        return "K"
    return "College+"


# =============================================================================
# AI STORY GENERATION
# =============================================================================

def get_openai_client():
    """Get OpenAI client if configured."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured in settings")

    from openai import OpenAI
    return OpenAI(api_key=api_key)


def get_lexile_guidelines(target_lexile: int) -> dict:
    """
    Get writing guidelines for a target Lexile level.

    Returns parameters that influence text complexity:
    - Sentence length targets
    - Vocabulary complexity hints
    - Structural guidance
    """
    if target_lexile < 400:  # K-2
        return {
            "grade_description": "early elementary (K-2)",
            "sentence_length": "5-10 words",
            "vocabulary": "simple, high-frequency words; avoid abstract concepts",
            "structure": "short paragraphs, simple sentence structures, subject-verb-object patterns",
            "content": "concrete topics, familiar situations, repetition for reinforcement"
        }
    elif target_lexile < 700:  # 2-4
        return {
            "grade_description": "elementary (grades 2-4)",
            "sentence_length": "8-15 words",
            "vocabulary": "common words with some grade-level vocabulary; define new terms in context",
            "structure": "clear paragraphs, mostly simple sentences with some compound sentences",
            "content": "relatable topics, clear cause-effect relationships"
        }
    elif target_lexile < 1000:  # 4-7
        return {
            "grade_description": "middle school (grades 4-7)",
            "sentence_length": "12-18 words",
            "vocabulary": "grade-appropriate vocabulary; can include some academic terms with context clues",
            "structure": "varied sentence structures, compound and complex sentences, clear transitions",
            "content": "can include more abstract concepts, multiple perspectives"
        }
    elif target_lexile < 1200:  # 7-10
        return {
            "grade_description": "high school (grades 7-10)",
            "sentence_length": "15-22 words",
            "vocabulary": "academic vocabulary, domain-specific terms, nuanced word choices",
            "structure": "sophisticated sentence variety, subordinate clauses, rhetorical devices",
            "content": "complex themes, analysis and inference required"
        }
    else:  # 10+
        return {
            "grade_description": "advanced high school/college (grades 11+)",
            "sentence_length": "18-30 words",
            "vocabulary": "advanced academic vocabulary, discipline-specific terminology",
            "structure": "complex syntax, embedded clauses, varied rhetorical strategies",
            "content": "sophisticated themes, multiple layers of meaning, requires synthesis"
        }


def generate_story_prompt(
    topic: str,
    target_lexile: int,
    word_count: int = 300,
    genre: str = "narrative",
    target_language: str = "English",
    additional_instructions: str = ""
) -> str:
    """
    Build the prompt for story generation with Lexile targeting.
    """
    guidelines = get_lexile_guidelines(target_lexile)

    prompt = f"""You are an expert educational content writer creating reading material for language learners.

TASK: Write a {genre} text about "{topic}" calibrated to approximately {target_lexile}L Lexile level.

TARGET AUDIENCE: {guidelines['grade_description']} readers (approximately {target_lexile}L Lexile)

LEXILE CALIBRATION REQUIREMENTS:
- Sentence length: Average {guidelines['sentence_length']} per sentence
- Vocabulary: {guidelines['vocabulary']}
- Structure: {guidelines['structure']}
- Content approach: {guidelines['content']}

SPECIFICATIONS:
- Length: Approximately {word_count} words
- Language: {target_language}
- Format: Return ONLY the story text, formatted with HTML paragraphs (<p> tags)
- Do NOT include titles, headers, or meta-commentary

WRITING GUIDELINES FOR LEXILE {target_lexile}L:
1. Count your sentences and ensure they average the target length
2. Choose vocabulary appropriate for the reading level
3. Use clear topic sentences and logical flow
4. Include context clues for any challenging vocabulary
5. Create engaging content while maintaining readability constraints

{f"ADDITIONAL INSTRUCTIONS: {additional_instructions}" if additional_instructions else ""}

Write the text now:"""

    return prompt


async def generate_story_async(
    topic: str,
    target_lexile: int,
    word_count: int = 300,
    genre: str = "narrative",
    target_language: str = "English",
    additional_instructions: str = "",
    model: str = "gpt-4o"
) -> dict:
    """
    Generate a story using OpenAI with Lexile targeting.

    Returns dict with generated text and metadata.
    """
    client = get_openai_client()

    prompt = generate_story_prompt(
        topic=topic,
        target_lexile=target_lexile,
        word_count=word_count,
        genre=genre,
        target_language=target_language,
        additional_instructions=additional_instructions
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educational content writer specializing in creating reading materials calibrated to specific Lexile levels. You understand the relationship between sentence length, word frequency, and text complexity."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=word_count * 3,  # Allow for variation
        )

        generated_text = response.choices[0].message.content.strip()

        # Analyze the generated text
        analysis = estimate_lexile(generated_text)

        return {
            "success": True,
            "text_html": generated_text,
            "target_lexile": target_lexile,
            "actual_lexile": analysis["lexile"],
            "lexile_label": analysis["lexile_label"],
            "metrics": analysis["metrics"],
            "generation_params": {
                "topic": topic,
                "target_lexile": target_lexile,
                "word_count": word_count,
                "genre": genre,
                "model": model,
            }
        }

    except Exception as e:
        logger.error(f"Story generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "text_html": None
        }


def generate_story_sync(
    topic: str,
    target_lexile: int,
    word_count: int = 300,
    genre: str = "narrative",
    target_language: str = "English",
    additional_instructions: str = "",
    model: str = "gpt-4o"
) -> dict:
    """
    Synchronous version of story generation for use in Django views.
    """
    client = get_openai_client()

    prompt = generate_story_prompt(
        topic=topic,
        target_lexile=target_lexile,
        word_count=word_count,
        genre=genre,
        target_language=target_language,
        additional_instructions=additional_instructions
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educational content writer specializing in creating reading materials calibrated to specific Lexile levels. You understand the relationship between sentence length, word frequency, and text complexity."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=word_count * 3,
        )

        generated_text = response.choices[0].message.content.strip()

        # Ensure proper HTML wrapping
        if not generated_text.startswith('<p>'):
            paragraphs = generated_text.split('\n\n')
            generated_text = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())

        # Analyze the generated text
        analysis = estimate_lexile(generated_text)

        return {
            "success": True,
            "text_html": generated_text,
            "target_lexile": target_lexile,
            "actual_lexile": analysis["lexile"],
            "lexile_label": analysis["lexile_label"],
            "grade_level": analysis["grade_level"],
            "metrics": analysis["metrics"],
            "generation_params": {
                "topic": topic,
                "target_lexile": target_lexile,
                "word_count": word_count,
                "genre": genre,
                "model": model,
            }
        }

    except Exception as e:
        logger.error(f"Story generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "text_html": None
        }


def regenerate_for_lexile(
    text: str,
    target_lexile: int,
    current_lexile: int,
    model: str = "gpt-4o"
) -> dict:
    """
    Adjust existing text to better match target Lexile level.
    """
    client = get_openai_client()

    direction = "simpler" if target_lexile < current_lexile else "more complex"
    difference = abs(target_lexile - current_lexile)

    guidelines = get_lexile_guidelines(target_lexile)

    prompt = f"""Rewrite the following text to be {direction}, targeting approximately {target_lexile}L Lexile level.

Current Lexile: ~{current_lexile}L
Target Lexile: {target_lexile}L
Difference: {difference}L ({direction})

ADJUSTMENT GUIDELINES:
- Target sentence length: {guidelines['sentence_length']}
- Vocabulary level: {guidelines['vocabulary']}
- Structure: {guidelines['structure']}

{"SIMPLIFICATION STRATEGIES:" if target_lexile < current_lexile else "COMPLEXITY STRATEGIES:"}
{"- Break long sentences into shorter ones" if target_lexile < current_lexile else "- Combine simple sentences with conjunctions and subordinate clauses"}
{"- Replace difficult words with simpler synonyms" if target_lexile < current_lexile else "- Use more precise, academic vocabulary"}
{"- Add context and explanations" if target_lexile < current_lexile else "- Remove redundant explanations"}
{"- Use more concrete examples" if target_lexile < current_lexile else "- Add nuance and abstract concepts"}

ORIGINAL TEXT:
{text}

REWRITTEN TEXT (maintain the same meaning and key information, format with <p> tags):"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at adapting text complexity while preserving meaning. You understand Lexile measures and how sentence length and word frequency affect readability."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,  # Lower temp for more faithful rewrites
        )

        rewritten_text = response.choices[0].message.content.strip()

        # Ensure proper HTML wrapping
        if not rewritten_text.startswith('<p>'):
            paragraphs = rewritten_text.split('\n\n')
            rewritten_text = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())

        analysis = estimate_lexile(rewritten_text)

        return {
            "success": True,
            "text_html": rewritten_text,
            "target_lexile": target_lexile,
            "actual_lexile": analysis["lexile"],
            "lexile_label": analysis["lexile_label"],
            "grade_level": analysis["grade_level"],
            "metrics": analysis["metrics"],
            "adjustment": direction,
        }

    except Exception as e:
        logger.error(f"Text regeneration failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "text_html": None
        }


class TextExtractor(HTMLParser):
    """Extract plain text positions from HTML while preserving tag locations."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)


def markup_glossary_terms(html_content, terms):
    """
    Process HTML content and wrap glossary terms with clickable spans.

    Args:
        html_content: The HTML string to process
        terms: QuerySet or list of Term objects with term_text and pk

    Returns:
        HTML string with glossary terms wrapped in <span class="gloss-term" data-term-id="...">
    """
    if not html_content or not terms:
        return html_content

    # Build a lookup of term_text -> term for efficient matching
    # Sort by length descending to match longer phrases first
    term_lookup = {}
    for term in terms:
        # Store both the original and lowercase versions for matching
        term_text = term.term_text.strip()
        if term_text:
            term_lookup[term_text.lower()] = term

    if not term_lookup:
        return html_content

    # Sort terms by length (longest first) to handle overlapping matches correctly
    sorted_terms = sorted(term_lookup.keys(), key=len, reverse=True)

    # Build a regex pattern that matches any of the terms (case-insensitive, word boundaries)
    # Escape special regex characters in term text
    escaped_terms = [re.escape(term) for term in sorted_terms]
    pattern = r'\b(' + '|'.join(escaped_terms) + r')\b'

    def replace_term(match):
        """Replace matched term with wrapped span, preserving original case."""
        matched_text = match.group(0)
        term = term_lookup.get(matched_text.lower())
        if term:
            return f'<span class="gloss-term" data-term-id="{term.pk}">{matched_text}</span>'
        return matched_text

    # Process the HTML carefully - only replace in text nodes, not in tags
    result = []
    last_end = 0

    # Find all HTML tags to skip them during replacement
    tag_pattern = re.compile(r'<[^>]+>')

    # Split by tags and process text between them
    parts = tag_pattern.split(html_content)
    tags = tag_pattern.findall(html_content)

    for i, text_part in enumerate(parts):
        if text_part:
            # Apply term replacement to this text part
            processed_text = re.sub(pattern, replace_term, text_part, flags=re.IGNORECASE)
            result.append(processed_text)
        if i < len(tags):
            result.append(tags[i])

    return ''.join(result)


def get_story_terms(story):
    """
    Get all active glossary terms for a story.

    Args:
        story: Story model instance

    Returns:
        QuerySet of Term objects or empty list
    """
    try:
        glossary = story.glossary
        return glossary.terms.filter(is_selected_for_glossary=True)
    except Exception:
        return []


# =============================================================================
# AI GLOSSARY GENERATION
# =============================================================================

def generate_glossary_terms(
    text: str,
    target_lexile: int = None,
    num_terms: int = 10,
    native_language: str = None,
    model: str = "gpt-4o"
) -> dict:
    """
    Use AI to identify challenging vocabulary and generate glossary terms.

    Args:
        text: The story text to analyze
        target_lexile: Lexile level of the text (for context)
        num_terms: Maximum number of terms to suggest
        native_language: L1 for translations (e.g., "Vietnamese", "Spanish")
        model: OpenAI model to use

    Returns:
        dict with success status and list of suggested terms
    """
    client = get_openai_client()

    # Strip HTML for analysis
    plain_text = strip_html(text) if '<' in text else text

    # Get reading level context
    if target_lexile:
        level_context = f"This text is at approximately {target_lexile}L Lexile level."
        guidelines = get_lexile_guidelines(target_lexile)
        audience = guidelines['grade_description']
    else:
        analysis = estimate_lexile(plain_text)
        target_lexile = analysis.get('lexile', 700)
        level_context = f"Estimated reading level: {target_lexile}L"
        audience = "language learners"

    translation_instruction = ""
    if native_language:
        translation_instruction = f"""
- translation: Translation in {native_language}"""

    prompt = f"""Analyze this text and identify the {num_terms} most important vocabulary terms for a glossary.

{level_context}
Target audience: {audience}

SELECTION CRITERIA:
1. Academic vocabulary and domain-specific terms
2. Words that are crucial for comprehension
3. Multi-syllable words that may be unfamiliar
4. Words with meanings specific to this context
5. Phrasal verbs or idiomatic expressions

EXCLUDE:
- Very common high-frequency words (the, is, and, etc.)
- Proper nouns (unless they need explanation)
- Words already defined in context

For each term, provide:
- term: The exact word or phrase as it appears in the text
- definition: A clear, learner-friendly definition (appropriate for {audience})
- part_of_speech: noun, verb, adjective, adverb, etc.
- example_sentence: A simple example sentence using the word{translation_instruction}
- difficulty: A rating from 1-5 (1=easy, 5=very difficult)

TEXT TO ANALYZE:
{plain_text[:3000]}

Return your response as a JSON array of term objects. Only return the JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ESL/EFL vocabulary instructor who identifies key vocabulary for language learners. You provide clear, learner-appropriate definitions and helpful context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        import json
        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            data = json.loads(response_text)
            # Handle both {terms: [...]} and direct array format
            if isinstance(data, dict) and 'terms' in data:
                terms = data['terms']
            elif isinstance(data, list):
                terms = data
            else:
                # Try to find an array in the response
                for key, value in data.items():
                    if isinstance(value, list):
                        terms = value
                        break
                else:
                    terms = []
        except json.JSONDecodeError:
            # Try to extract JSON array from response
            import re
            match = re.search(r'\[[\s\S]*\]', response_text)
            if match:
                terms = json.loads(match.group())
            else:
                terms = []

        return {
            "success": True,
            "terms": terms,
            "text_lexile": target_lexile,
            "count": len(terms)
        }

    except Exception as e:
        logger.error(f"Glossary generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "terms": []
        }


def suggest_additional_terms(
    text: str,
    existing_terms: list,
    num_suggestions: int = 5,
    model: str = "gpt-4o"
) -> dict:
    """
    Suggest additional glossary terms not already in the glossary.

    Args:
        text: The story text
        existing_terms: List of term strings already in glossary
        num_suggestions: Number of additional terms to suggest

    Returns:
        dict with suggested terms
    """
    client = get_openai_client()

    plain_text = strip_html(text) if '<' in text else text
    existing_list = ", ".join(existing_terms) if existing_terms else "none"

    prompt = f"""Analyze this text and suggest {num_suggestions} additional vocabulary terms for a glossary.

ALREADY IN GLOSSARY (do not suggest these):
{existing_list}

Suggest terms that:
1. Are NOT in the existing list above
2. Would help comprehension
3. Are challenging for language learners

TEXT:
{plain_text[:2000]}

Return a JSON array with term objects containing: term, definition, part_of_speech, difficulty (1-5)"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a vocabulary expert. Return only a JSON array of term objects."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        import json
        data = json.loads(response.choices[0].message.content.strip())
        terms = data.get('terms', data) if isinstance(data, dict) else data

        return {
            "success": True,
            "terms": terms if isinstance(terms, list) else [],
            "count": len(terms) if isinstance(terms, list) else 0
        }

    except Exception as e:
        logger.error(f"Additional term suggestion failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "terms": []
        }


# =============================================================================
# AI QUIZ GENERATION
# =============================================================================

def generate_quiz_questions(
    text: str,
    num_questions: int = 5,
    question_types: list = None,
    target_lexile: int = None,
    focus_area: str = None,
    model: str = "gpt-4o"
) -> dict:
    """
    Generate comprehension quiz questions based on story text.

    Args:
        text: The story text to generate questions from
        num_questions: Number of questions to generate
        question_types: List of types to include (mcq_single, true_false, short_answer)
        target_lexile: Reading level for question difficulty
        focus_area: Optional focus (main_idea, details, vocabulary, inference)
        model: OpenAI model to use

    Returns:
        dict with success status and list of generated questions
    """
    client = get_openai_client()

    # Default question types
    if not question_types:
        question_types = ["mcq_single", "true_false", "short_answer"]

    # Strip HTML for analysis
    plain_text = strip_html(text) if '<' in text else text

    # Get reading level context
    if target_lexile:
        guidelines = get_lexile_guidelines(target_lexile)
        level_context = f"Questions should be appropriate for {guidelines['grade_description']} readers ({target_lexile}L)."
    else:
        analysis = estimate_lexile(plain_text)
        target_lexile = analysis.get('lexile', 700)
        guidelines = get_lexile_guidelines(target_lexile)
        level_context = f"Estimated text level: {target_lexile}L. Questions for {guidelines['grade_description']} readers."

    # Build question type instructions
    type_instructions = []
    if "mcq_single" in question_types:
        type_instructions.append("""
MULTIPLE CHOICE (mcq_single):
- 4 answer choices (A, B, C, D)
- One clearly correct answer
- Plausible distractors based on the text
- Format: {"type": "mcq_single", "prompt": "...", "choices": [{"label": "A", "text": "...", "is_correct": true/false}, ...]}""")

    if "true_false" in question_types:
        type_instructions.append("""
TRUE/FALSE (true_false):
- Statement that is clearly true or false based on the text
- Avoid ambiguous statements
- Format: {"type": "true_false", "prompt": "...", "choices": [{"label": "True", "text": "True", "is_correct": true/false}, {"label": "False", "text": "False", "is_correct": true/false}]}""")

    if "short_answer" in question_types:
        type_instructions.append("""
SHORT ANSWER (short_answer):
- Open-ended question requiring 1-3 sentence response
- Include expected_answer for grading reference
- Format: {"type": "short_answer", "prompt": "...", "expected_answer": "..."}""")

    focus_instruction = ""
    if focus_area:
        focus_map = {
            "main_idea": "Focus on questions about the main idea, central theme, and overall message.",
            "details": "Focus on questions about specific details, facts, and supporting information.",
            "vocabulary": "Focus on questions about word meanings, context clues, and vocabulary usage.",
            "inference": "Focus on questions requiring inference, drawing conclusions, and reading between the lines.",
            "sequence": "Focus on questions about the order of events, cause and effect, and chronology.",
        }
        focus_instruction = f"\nFOCUS AREA: {focus_map.get(focus_area, focus_area)}"

    prompt = f"""Generate {num_questions} reading comprehension questions for the following text.

{level_context}
{focus_instruction}

QUESTION TYPES TO INCLUDE:
{chr(10).join(type_instructions)}

GUIDELINES:
1. Questions should test genuine comprehension, not just word recognition
2. Include a mix of literal and inferential questions
3. Ensure questions can be answered from the text alone
4. Make questions progressively harder if generating multiple
5. For MCQ, make distractors plausible but clearly wrong based on text

TEXT:
{plain_text[:4000]}

Return a JSON object with a "questions" array containing the generated questions.
Each question should have: type, prompt, points (default 1), and either choices array or expected_answer."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert reading assessment designer who creates comprehension questions that effectively measure reading understanding. You create questions appropriate for the reading level of the text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        import json
        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            data = json.loads(response_text)
            questions = data.get('questions', data) if isinstance(data, dict) else data
            if not isinstance(questions, list):
                for key, value in data.items():
                    if isinstance(value, list):
                        questions = value
                        break
                else:
                    questions = []
        except json.JSONDecodeError:
            questions = []

        return {
            "success": True,
            "questions": questions,
            "count": len(questions),
            "text_lexile": target_lexile,
        }

    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "questions": []
        }


def generate_vocabulary_quiz(
    terms: list,
    quiz_type: str = "definition_match",
    num_questions: int = None,
    model: str = "gpt-4o"
) -> dict:
    """
    Generate a vocabulary quiz from glossary terms.

    Args:
        terms: List of term dicts with term_text and definition_html
        quiz_type: Type of vocabulary quiz (definition_match, fill_blank, context_clue)
        num_questions: Number of questions (defaults to len(terms))

    Returns:
        dict with generated vocabulary questions
    """
    client = get_openai_client()

    if not terms:
        return {"success": False, "error": "No terms provided", "questions": []}

    num_questions = num_questions or len(terms)
    term_list = "\n".join([
        f"- {t.get('term_text', t.get('term', ''))}: {t.get('definition_html', t.get('definition', ''))}"
        for t in terms[:20]  # Limit to 20 terms
    ])

    quiz_type_instructions = {
        "definition_match": """Create multiple choice questions where students match terms to their definitions.
Format: {"type": "mcq_single", "prompt": "What does [TERM] mean?", "choices": [...], "term": "..."}""",

        "fill_blank": """Create fill-in-the-blank sentences where students choose the correct vocabulary word.
Format: {"type": "mcq_single", "prompt": "Complete the sentence: _____ means...", "choices": [...], "term": "..."}""",

        "context_clue": """Create questions where students identify the meaning of a term from context.
Format: {"type": "mcq_single", "prompt": "In the sentence '...', what does [TERM] mean?", "choices": [...], "term": "..."}"""
    }

    prompt = f"""Generate {num_questions} vocabulary quiz questions from these terms:

{term_list}

QUIZ TYPE: {quiz_type}
{quiz_type_instructions.get(quiz_type, quiz_type_instructions['definition_match'])}

GUIDELINES:
1. Each question tests one vocabulary term
2. Include 4 choices with one correct answer
3. Distractors should be plausible but clearly different meanings
4. Questions should be clear and unambiguous

Return a JSON object with a "questions" array."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a vocabulary assessment expert who creates effective questions to test word knowledge."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        import json
        data = json.loads(response.choices[0].message.content.strip())
        questions = data.get('questions', [])

        return {
            "success": True,
            "questions": questions,
            "count": len(questions),
            "quiz_type": quiz_type,
        }

    except Exception as e:
        logger.error(f"Vocabulary quiz generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "questions": []
        }
