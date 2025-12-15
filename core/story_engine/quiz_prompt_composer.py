"""
Quiz Prompt Composer

Generates AI prompts for quiz question creation based on QuizProfile.
Ensures questions align with story content, glossary terms, and pedagogical constraints.

Prompt ordering (mandatory):
1. System context and role
2. Source material (story/glossary)
3. Question type constraints
4. Bloom's taxonomy requirements
5. Category distribution
6. Age-appropriate language constraints
7. Output format requirements
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .quiz_profile_builder import QuizProfile, AlignmentSource


@dataclass
class ComposedQuizPrompt:
    """The final composed prompt for quiz generation."""
    system_message: str
    user_prompt: str
    profile_hash: str
    expected_output_format: str = "json"

    def full_prompt(self) -> str:
        """Combine system and user prompts."""
        return f"{self.system_message}\n\n---\n\n{self.user_prompt}"


@dataclass
class GeneratedQuestion:
    """A generated quiz question with metadata."""
    question_type: str
    question_text: str
    choices: list[dict] | None = None  # For MCQ types
    correct_answer: Any = None
    explanation: str | None = None
    hint: str | None = None
    bloom_level: str | None = None
    category: str | None = None
    source_reference: str | None = None  # Text excerpt the question relates to
    points: int = 1
    metadata: dict = field(default_factory=dict)


class QuizPromptComposer:
    """
    Composes prompts for quiz question generation.

    Takes a QuizProfile and source material to produce prompts that
    generate age-appropriate, pedagogically-aligned quiz questions.
    """

    SYSTEM_MESSAGE = """You are an educational assessment specialist creating reading comprehension questions.
You generate questions that test understanding at appropriate cognitive levels.
Questions must be directly answerable from the provided source text.
You output questions in structured JSON format only."""

    def compose(
        self,
        profile: QuizProfile,
        focus_terms: list[str] | None = None,
        focus_segments: list[str] | None = None,
    ) -> ComposedQuizPrompt:
        """
        Compose a quiz generation prompt from a QuizProfile.

        Args:
            profile: The assembled QuizProfile
            focus_terms: Specific glossary terms to prioritize
            focus_segments: Specific story segment IDs to focus on

        Returns:
            ComposedQuizPrompt ready for LLM submission
        """
        sections = []

        # Section 1: Source Material
        sections.append(self._compose_source_material(profile, focus_segments))

        # Section 2: Glossary Terms (if provided)
        if profile.glossary_source:
            sections.append(self._compose_glossary_section(profile, focus_terms))

        # Section 3: Question Generation Instructions
        sections.append(self._compose_generation_instructions(profile))

        # Section 4: Question Type Constraints
        sections.append(self._compose_question_types(profile))

        # Section 5: Bloom's Taxonomy Requirements
        sections.append(self._compose_bloom_requirements(profile))

        # Section 6: Category Distribution
        sections.append(self._compose_category_requirements(profile))

        # Section 7: Language Constraints
        sections.append(self._compose_language_constraints(profile))

        # Section 8: Output Format
        sections.append(self._compose_output_format(profile))

        user_prompt = "\n\n".join(filter(None, sections))

        return ComposedQuizPrompt(
            system_message=self.SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            profile_hash=profile.profile_hash,
            expected_output_format="json",
        )

    def _compose_source_material(
        self,
        profile: QuizProfile,
        focus_segments: list[str] | None,
    ) -> str:
        """Section 1: Source Material."""
        lines = ["## SOURCE TEXT", ""]

        if profile.story_source:
            source = profile.story_source
            if source.source_title:
                lines.append(f"Title: {source.source_title}")
                lines.append("")

            # Include full text or focused segments
            if focus_segments and source.segments:
                lines.append("### Relevant Passages")
                for seg in source.segments:
                    if seg.get("id") in focus_segments:
                        lines.append(f"[Segment {seg.get('id')}]")
                        lines.append(seg.get("text", ""))
                        lines.append("")
            elif source.text_content:
                lines.append("### Full Text")
                lines.append(source.text_content)
        else:
            lines.append("(No source text provided - generate questions about general topics)")

        return "\n".join(lines)

    def _compose_glossary_section(
        self,
        profile: QuizProfile,
        focus_terms: list[str] | None,
    ) -> str:
        """Section 2: Glossary Terms."""
        lines = ["## GLOSSARY TERMS", ""]

        if not profile.glossary_source:
            return ""

        terms = profile.glossary_source.glossary_terms

        if focus_terms:
            # Filter to focused terms
            terms = [t for t in terms if t.get("term") in focus_terms]

        if not terms:
            return ""

        lines.append("These vocabulary terms should be tested in the quiz:")
        lines.append("")

        for term in terms:
            term_word = term.get("term", "")
            definition = term.get("definition", "")
            lines.append(f"- **{term_word}**: {definition}")

        lines.append("")
        lines.append("Create vocabulary questions that test understanding of these terms in context.")

        return "\n".join(lines)

    def _compose_generation_instructions(self, profile: QuizProfile) -> str:
        """Section 3: Generation Instructions."""
        lines = [
            "## QUESTION GENERATION TASK",
            "",
            f"Generate {profile.question_count} quiz questions based on the source text above.",
            "",
        ]

        # Assessment mode affects question style
        if profile.assessment_mode == "study_mode":
            lines.extend([
                "### Study Mode Requirements",
                "- Include helpful hints for each question",
                "- Provide detailed explanations for correct answers",
                "- Reference specific text passages in explanations",
                "- Questions should help learners understand, not just test",
            ])
        else:
            lines.extend([
                "### Exam Mode Requirements",
                "- Do not include hints",
                "- Explanations should be concise",
                "- Questions should assess comprehension accurately",
            ])

        # Add profile guidance
        if profile.guidance:
            lines.append("")
            lines.append("### Additional Guidelines")
            for g in profile.guidance:
                lines.append(f"- {g}")

        return "\n".join(lines)

    def _compose_question_types(self, profile: QuizProfile) -> str:
        """Section 4: Question Type Constraints."""
        lines = ["## ALLOWED QUESTION TYPES", ""]

        type_instructions = {
            "mcq_single": self._mcq_single_instructions,
            "mcq_multi": self._mcq_multi_instructions,
            "true_false": self._true_false_instructions,
            "short_answer": self._short_answer_instructions,
            "long_answer": self._long_answer_instructions,
            "cloze": self._cloze_instructions,
            "matching": self._matching_instructions,
            "ordering": self._ordering_instructions,
        }

        for type_id in profile.allowed_question_types:
            constraints = profile.question_type_constraints.get(type_id)
            if constraints and constraints.enabled:
                if type_id in type_instructions:
                    lines.extend(type_instructions[type_id](constraints))
                    lines.append("")

        return "\n".join(lines)

    def _mcq_single_instructions(self, constraints) -> list[str]:
        """Instructions for single-answer MCQ."""
        return [
            "### Multiple Choice (Single Answer)",
            f"- Provide exactly {constraints.max_choices} answer choices",
            "- Only one choice should be correct",
            "- Distractors must be plausible but clearly incorrect",
            "- Do not use 'all of the above' or 'none of the above'",
            "- Randomize correct answer position",
        ]

    def _mcq_multi_instructions(self, constraints) -> list[str]:
        """Instructions for multiple-answer MCQ."""
        return [
            "### Multiple Choice (Multiple Answers)",
            f"- Provide {constraints.min_choices} to {constraints.max_choices} answer choices",
            f"- {constraints.min_correct} to {constraints.max_correct} choices should be correct",
            "- Clearly indicate that multiple answers are expected",
            "- Each correct answer should be independently justifiable",
        ]

    def _true_false_instructions(self, constraints) -> list[str]:
        """Instructions for true/false questions."""
        return [
            "### True / False",
            "- Statement must be unambiguously true or false based on text",
            "- Avoid double negatives",
            "- False statements should be plausibly incorrect",
        ]

    def _short_answer_instructions(self, constraints) -> list[str]:
        """Instructions for short answer questions."""
        return [
            "### Short Answer",
            f"- Expected response: 1-2 sentences (max {constraints.max_words} words)",
            "- Question should have a specific, clear answer",
            "- Provide a sample correct answer",
            "- Allow for paraphrasing in acceptable responses",
        ]

    def _long_answer_instructions(self, constraints) -> list[str]:
        """Instructions for long/extended response questions."""
        return [
            "### Extended Response",
            f"- Expected response: {constraints.max_words} words maximum",
            "- Question should require text evidence",
            "- Provide grading rubric criteria",
            "- Allow for multiple valid interpretations",
        ]

    def _cloze_instructions(self, constraints) -> list[str]:
        """Instructions for fill-in-the-blank questions."""
        lines = [
            "### Fill in the Blank (Cloze)",
            "- Target vocabulary words or key concepts",
            "- Context should make answer determinable",
            "- Blank should have a single clear answer",
        ]
        if constraints.word_bank_required:
            lines.append("- MUST provide a word bank with options")
        return lines

    def _matching_instructions(self, constraints) -> list[str]:
        """Instructions for matching questions."""
        return [
            "### Matching",
            f"- Provide {constraints.max_items} pairs to match",
            "- All items should be from same category",
            "- Include 1-2 distractor items in one column",
            "- Relationships should be unambiguous",
        ]

    def _ordering_instructions(self, constraints) -> list[str]:
        """Instructions for sequence/ordering questions."""
        return [
            "### Sequence / Ordering",
            f"- Provide {constraints.max_items} items to order",
            "- Events must have a clear, unambiguous order",
            "- Use for chronological events or logical sequences",
            "- Specify the ordering criterion clearly",
        ]

    def _compose_bloom_requirements(self, profile: QuizProfile) -> str:
        """Section 5: Bloom's Taxonomy Requirements."""
        bloom = profile.bloom_constraints
        lines = ["## COGNITIVE LEVEL REQUIREMENTS", ""]

        # Explain allowed levels
        level_descriptions = {
            "remember": "Recall facts and basic concepts (Who, What, Where, When)",
            "understand": "Explain ideas or concepts (Summarize, Describe, Explain)",
            "apply": "Use information in new situations (How would you use...)",
            "analyze": "Draw connections among ideas (Compare, Contrast, Why)",
            "evaluate": "Justify a decision or position (Do you agree, Judge)",
            "create": "Produce new or original work (Design, Predict, Write)",
        }

        lines.append("Questions must target these cognitive levels:")
        for level in bloom.allowed_levels:
            desc = level_descriptions.get(level, level)
            lines.append(f"- **{level.title()}**: {desc}")

        # Question stems
        if bloom.question_stems:
            lines.append("")
            lines.append("### Suggested Question Stems")
            for level, stems in bloom.question_stems.items():
                if stems:
                    lines.append(f"- {level.title()}: {', '.join(stems[:4])}")

        # Distribution guidance
        lines.append("")
        lines.append("### Distribution")
        lines.append("Distribute questions across these cognitive levels.")
        if "remember" in bloom.allowed_levels and "understand" in bloom.allowed_levels:
            lines.append("Prioritize 'Remember' and 'Understand' levels for foundational comprehension.")

        return "\n".join(lines)

    def _compose_category_requirements(self, profile: QuizProfile) -> str:
        """Section 6: Category Distribution."""
        cat = profile.category_constraints
        lines = ["## QUESTION CATEGORIES", ""]

        category_descriptions = {
            "literal_comprehension": "Questions about explicitly stated information",
            "inferential_comprehension": "Questions requiring conclusions from the text",
            "vocabulary": "Questions about word meaning and usage",
            "text_structure": "Questions about how the text is organized",
            "author_purpose": "Questions about why and how the author wrote",
            "critical_thinking": "Questions requiring judgment and evaluation",
        }

        lines.append("Include questions from these categories:")
        for cat_id in cat.allowed_categories:
            desc = category_descriptions.get(cat_id, cat_id)
            pct = cat.target_distribution.get(cat_id, 0)
            lines.append(f"- **{cat_id.replace('_', ' ').title()}** (~{int(pct * 100)}%): {desc}")

        return "\n".join(lines)

    def _compose_language_constraints(self, profile: QuizProfile) -> str:
        """Section 7: Language Constraints for Age Band."""
        lines = [
            "## LANGUAGE REQUIREMENTS",
            "",
            f"Target age band: {profile.age_band}",
            f"Target Lexile band: {profile.lexile_band}",
            "",
        ]

        lines.append("### Question Language")
        lines.append(f"- Maximum {profile.question_max_words} words per question")

        if profile.avoid_negatives:
            lines.append("- Do NOT use negative phrasing (NOT, EXCEPT, NEVER)")
            lines.append("- Rephrase negatives as positives")

        lines.append("- Use clear, direct language")
        lines.append("- Avoid ambiguous wording")
        lines.append("- Questions should have one clear interpretation")

        # Age-specific guidance
        if profile.age_band == "6-8":
            lines.extend([
                "",
                "### Early Reader Accommodations",
                "- Use very simple vocabulary in questions",
                "- Focus on 'who, what, where, when' questions",
                "- Keep answer choices short (1-4 words when possible)",
            ])
        elif profile.age_band == "8-10":
            lines.extend([
                "",
                "### Developing Reader Accommodations",
                "- Introduce simple 'why' and 'how' questions",
                "- Keep answer choices concise",
            ])

        return "\n".join(lines)

    def _compose_output_format(self, profile: QuizProfile) -> str:
        """Section 8: Output Format Requirements."""
        lines = [
            "## OUTPUT FORMAT",
            "",
            "Output your questions as a JSON array. Each question object must include:",
            "",
            "```json",
            "[",
            "  {",
            '    "question_type": "mcq_single",',
            '    "question_text": "What did...",',
            '    "choices": [',
            '      {"id": "a", "text": "...", "is_correct": false},',
            '      {"id": "b", "text": "...", "is_correct": true},',
            '      {"id": "c", "text": "...", "is_correct": false}',
            "    ],",
            '    "correct_answer": "b",',
            '    "explanation": "The correct answer is B because...",',
        ]

        if profile.include_hints:
            lines.append('    "hint": "Look at paragraph 2...",')

        lines.extend([
            '    "bloom_level": "understand",',
            '    "category": "literal_comprehension",',
            '    "source_reference": "paragraph 2, sentence 3",',
            '    "points": 1',
            "  }",
            "]",
            "```",
            "",
            "### Field Requirements",
            "- `question_type`: One of the allowed types",
            "- `question_text`: The question itself",
            "- `choices`: Array of choice objects (for MCQ/matching)",
            "- `correct_answer`: The correct answer(s)",
            "- `explanation`: Why the answer is correct",
        ])

        if profile.include_hints:
            lines.append("- `hint`: A helpful hint pointing to relevant text")

        lines.extend([
            "- `bloom_level`: The cognitive level",
            "- `category`: The question category",
            "- `source_reference`: Where in the text the answer can be found",
            "- `points`: Point value (usually 1)",
            "",
            "Output ONLY the JSON array. No additional text.",
        ])

        return "\n".join(lines)


def compose_quiz_prompt(
    age_band: str,
    lexile_band: str,
    question_count: int = 5,
    assessment_mode: str = "study_mode",
    story_text: str | None = None,
    story_title: str | None = None,
    glossary_terms: list[dict] | None = None,
    requested_types: list[str] | None = None,
    requested_categories: list[str] | None = None,
    requested_bloom_levels: list[str] | None = None,
) -> ComposedQuizPrompt:
    """
    Convenience function to build profile and compose quiz prompt in one step.

    Args:
        age_band: Target age band (e.g., "8-10")
        lexile_band: Target Lexile band (e.g., "500-600L")
        question_count: Number of questions to generate
        assessment_mode: "study_mode" or "exam_mode"
        story_text: Source story text
        story_title: Source story title
        glossary_terms: List of glossary term dicts
        requested_types: Specific question types to include
        requested_categories: Specific categories to focus on
        requested_bloom_levels: Specific Bloom's levels to target

    Returns:
        ComposedQuizPrompt ready for LLM submission
    """
    from .quiz_profile_builder import QuizProfileBuilder

    builder = QuizProfileBuilder()
    profile = builder.build(
        age_band=age_band,
        lexile_band=lexile_band,
        question_count=question_count,
        assessment_mode=assessment_mode,
        story_text=story_text,
        story_title=story_title,
        glossary_terms=glossary_terms,
        requested_types=requested_types,
        requested_categories=requested_categories,
        requested_bloom_levels=requested_bloom_levels,
    )

    composer = QuizPromptComposer()
    return composer.compose(profile)
