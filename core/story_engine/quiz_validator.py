"""
Quiz Validator

Validates generated quiz questions for structure, alignment, and pedagogical constraints.
Checks that questions conform to the QuizProfile requirements.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .quiz_profile_builder import QuizProfile


class QuizValidationSeverity(Enum):
    """Severity levels for quiz validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class QuizValidationIssue:
    """A single validation issue found in a quiz question."""
    code: str
    severity: QuizValidationSeverity
    message: str
    question_index: int | None = None
    field_name: str | None = None
    actual_value: Any = None
    expected_value: Any = None
    suggestion: str = ""


@dataclass
class ValidatedQuestion:
    """A validated quiz question with any issues found."""
    index: int
    question_type: str
    question_text: str
    is_valid: bool
    issues: list[QuizValidationIssue] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


@dataclass
class QuizValidationResult:
    """Complete validation result for a quiz."""
    valid: bool
    score: float  # 0.0 to 1.0
    total_questions: int
    valid_questions: int
    issues: list[QuizValidationIssue] = field(default_factory=list)
    questions: list[ValidatedQuestion] = field(default_factory=list)
    alignment_score: float = 1.0
    bloom_distribution: dict[str, int] = field(default_factory=dict)
    category_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "valid": self.valid,
            "score": round(self.score, 3),
            "total_questions": self.total_questions,
            "valid_questions": self.valid_questions,
            "issue_count": len(self.issues),
            "alignment_score": round(self.alignment_score, 3),
            "bloom_distribution": self.bloom_distribution,
            "category_distribution": self.category_distribution,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "message": i.message,
                    "question_index": i.question_index,
                    "field_name": i.field_name,
                }
                for i in self.issues
            ],
        }


class QuizValidator:
    """
    Validates generated quiz questions against profile constraints.

    Checks:
    - JSON structure validity
    - Required fields presence
    - Question type constraints
    - Bloom's taxonomy alignment
    - Category distribution
    - Story/glossary alignment
    - Language appropriateness
    """

    REQUIRED_FIELDS = ["question_type", "question_text", "correct_answer"]

    MCQ_REQUIRED_FIELDS = ["choices"]

    def __init__(self):
        pass

    def validate(
        self,
        quiz_json: str | list[dict],
        profile: QuizProfile,
    ) -> QuizValidationResult:
        """
        Validate quiz questions against profile constraints.

        Args:
            quiz_json: JSON string or list of question dicts
            profile: QuizProfile with constraints

        Returns:
            QuizValidationResult with issues and scores
        """
        issues = []
        questions = []
        score_deductions = 0.0

        # Parse JSON if string
        if isinstance(quiz_json, str):
            try:
                quiz_data = self._parse_json(quiz_json)
            except json.JSONDecodeError as e:
                return QuizValidationResult(
                    valid=False,
                    score=0.0,
                    total_questions=0,
                    valid_questions=0,
                    issues=[QuizValidationIssue(
                        code="INVALID_JSON",
                        severity=QuizValidationSeverity.ERROR,
                        message=f"Failed to parse quiz JSON: {str(e)}",
                        suggestion="Ensure output is valid JSON array",
                    )],
                )
        else:
            quiz_data = quiz_json

        # Ensure it's a list
        if not isinstance(quiz_data, list):
            quiz_data = [quiz_data]

        # Validate each question
        bloom_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        valid_count = 0

        for idx, q_data in enumerate(quiz_data):
            q_issues = []

            # Validate structure
            struct_issues = self._validate_structure(idx, q_data, profile)
            q_issues.extend(struct_issues)

            # Validate question type constraints
            type_issues = self._validate_question_type(idx, q_data, profile)
            q_issues.extend(type_issues)

            # Validate language
            lang_issues = self._validate_language(idx, q_data, profile)
            q_issues.extend(lang_issues)

            # Validate alignment (if source text provided)
            if profile.story_source and profile.story_source.text_content:
                align_issues = self._validate_alignment(idx, q_data, profile)
                q_issues.extend(align_issues)

            # Track Bloom's level
            bloom = q_data.get("bloom_level", "unknown")
            bloom_counts[bloom] = bloom_counts.get(bloom, 0) + 1

            # Track category
            category = q_data.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

            # Create validated question
            is_valid = not any(i.severity == QuizValidationSeverity.ERROR for i in q_issues)
            if is_valid:
                valid_count += 1

            questions.append(ValidatedQuestion(
                index=idx,
                question_type=q_data.get("question_type", "unknown"),
                question_text=q_data.get("question_text", ""),
                is_valid=is_valid,
                issues=q_issues,
                raw_data=q_data,
            ))

            issues.extend(q_issues)

        # Validate overall distribution
        dist_issues, dist_deduction = self._validate_distribution(
            bloom_counts, category_counts, profile
        )
        issues.extend(dist_issues)
        score_deductions += dist_deduction

        # Calculate alignment score
        alignment_score = self._calculate_alignment_score(questions, profile)

        # Calculate score deduction from issues
        for issue in issues:
            if issue.severity == QuizValidationSeverity.ERROR:
                score_deductions += 0.15
            elif issue.severity == QuizValidationSeverity.WARNING:
                score_deductions += 0.05

        # Cap deductions
        score_deductions = min(score_deductions, 1.0)
        final_score = max(0.0, 1.0 - score_deductions)

        # Overall validity
        has_errors = any(i.severity == QuizValidationSeverity.ERROR for i in issues)
        is_valid = not has_errors and valid_count >= len(quiz_data) * 0.8

        return QuizValidationResult(
            valid=is_valid,
            score=final_score,
            total_questions=len(quiz_data),
            valid_questions=valid_count,
            issues=issues,
            questions=questions,
            alignment_score=alignment_score,
            bloom_distribution=bloom_counts,
            category_distribution=category_counts,
        )

    def _parse_json(self, json_str: str) -> list[dict]:
        """Parse JSON string, handling common formatting issues."""
        # Try direct parse first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find array in text
        array_match = re.search(r'\[[\s\S]*\]', json_str)
        if array_match:
            return json.loads(array_match.group())

        raise json.JSONDecodeError("No valid JSON found", json_str, 0)

    def _validate_structure(
        self,
        idx: int,
        q_data: dict,
        profile: QuizProfile,
    ) -> list[QuizValidationIssue]:
        """Validate question structure and required fields."""
        issues = []

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in q_data or not q_data[field]:
                issues.append(QuizValidationIssue(
                    code="MISSING_FIELD",
                    severity=QuizValidationSeverity.ERROR,
                    message=f"Missing required field: {field}",
                    question_index=idx,
                    field_name=field,
                    suggestion=f"Add '{field}' to the question",
                ))

        # Check MCQ-specific fields
        q_type = q_data.get("question_type", "")
        if q_type in ["mcq_single", "mcq_multi"]:
            for field in self.MCQ_REQUIRED_FIELDS:
                if field not in q_data or not q_data[field]:
                    issues.append(QuizValidationIssue(
                        code="MISSING_MCQ_FIELD",
                        severity=QuizValidationSeverity.ERROR,
                        message=f"MCQ question missing '{field}'",
                        question_index=idx,
                        field_name=field,
                    ))

        # Check explanation (required for study mode)
        if profile.include_explanations and "explanation" not in q_data:
            issues.append(QuizValidationIssue(
                code="MISSING_EXPLANATION",
                severity=QuizValidationSeverity.WARNING,
                message="Question missing explanation (required for study mode)",
                question_index=idx,
                field_name="explanation",
            ))

        # Check hint (required for study mode)
        if profile.include_hints and "hint" not in q_data:
            issues.append(QuizValidationIssue(
                code="MISSING_HINT",
                severity=QuizValidationSeverity.INFO,
                message="Question missing hint",
                question_index=idx,
                field_name="hint",
            ))

        return issues

    def _validate_question_type(
        self,
        idx: int,
        q_data: dict,
        profile: QuizProfile,
    ) -> list[QuizValidationIssue]:
        """Validate question type constraints."""
        issues = []

        q_type = q_data.get("question_type", "")

        # Check if type is allowed
        if q_type not in profile.allowed_question_types:
            issues.append(QuizValidationIssue(
                code="INVALID_QUESTION_TYPE",
                severity=QuizValidationSeverity.ERROR,
                message=f"Question type '{q_type}' not allowed for this age band",
                question_index=idx,
                field_name="question_type",
                actual_value=q_type,
                expected_value=profile.allowed_question_types,
            ))
            return issues

        # Get type constraints
        constraints = profile.question_type_constraints.get(q_type)
        if not constraints:
            return issues

        # Validate MCQ choices
        if q_type in ["mcq_single", "mcq_multi"]:
            choices = q_data.get("choices", [])
            if len(choices) < constraints.min_choices:
                issues.append(QuizValidationIssue(
                    code="TOO_FEW_CHOICES",
                    severity=QuizValidationSeverity.WARNING,
                    message=f"Only {len(choices)} choices, minimum is {constraints.min_choices}",
                    question_index=idx,
                    field_name="choices",
                    actual_value=len(choices),
                    expected_value=constraints.min_choices,
                ))
            elif len(choices) > constraints.max_choices:
                issues.append(QuizValidationIssue(
                    code="TOO_MANY_CHOICES",
                    severity=QuizValidationSeverity.WARNING,
                    message=f"{len(choices)} choices exceeds maximum of {constraints.max_choices}",
                    question_index=idx,
                    field_name="choices",
                    actual_value=len(choices),
                    expected_value=constraints.max_choices,
                ))

            # Check for correct answer
            correct_count = sum(1 for c in choices if c.get("is_correct"))
            if q_type == "mcq_single" and correct_count != 1:
                issues.append(QuizValidationIssue(
                    code="INVALID_CORRECT_COUNT",
                    severity=QuizValidationSeverity.ERROR,
                    message=f"MCQ single must have exactly 1 correct answer, found {correct_count}",
                    question_index=idx,
                    field_name="choices",
                    actual_value=correct_count,
                    expected_value=1,
                ))
            elif q_type == "mcq_multi":
                if correct_count < constraints.min_correct:
                    issues.append(QuizValidationIssue(
                        code="TOO_FEW_CORRECT",
                        severity=QuizValidationSeverity.ERROR,
                        message=f"MCQ multi needs at least {constraints.min_correct} correct answers",
                        question_index=idx,
                        actual_value=correct_count,
                        expected_value=constraints.min_correct,
                    ))

        # Validate cloze word bank
        if q_type == "cloze" and constraints.word_bank_required:
            if "word_bank" not in q_data and "choices" not in q_data:
                issues.append(QuizValidationIssue(
                    code="MISSING_WORD_BANK",
                    severity=QuizValidationSeverity.WARNING,
                    message="Cloze question requires word bank for this age band",
                    question_index=idx,
                    field_name="word_bank",
                ))

        # Validate ordering item count
        if q_type == "ordering":
            items = q_data.get("items", q_data.get("choices", []))
            if len(items) > constraints.max_items:
                issues.append(QuizValidationIssue(
                    code="TOO_MANY_ORDERING_ITEMS",
                    severity=QuizValidationSeverity.WARNING,
                    message=f"Ordering has {len(items)} items, max is {constraints.max_items}",
                    question_index=idx,
                    actual_value=len(items),
                    expected_value=constraints.max_items,
                ))

        return issues

    def _validate_language(
        self,
        idx: int,
        q_data: dict,
        profile: QuizProfile,
    ) -> list[QuizValidationIssue]:
        """Validate question language constraints."""
        issues = []

        question_text = q_data.get("question_text", "")
        word_count = len(question_text.split())

        # Check question length
        if word_count > profile.question_max_words:
            issues.append(QuizValidationIssue(
                code="QUESTION_TOO_LONG",
                severity=QuizValidationSeverity.WARNING,
                message=f"Question has {word_count} words (max: {profile.question_max_words})",
                question_index=idx,
                field_name="question_text",
                actual_value=word_count,
                expected_value=profile.question_max_words,
            ))

        # Check for negative phrasing
        if profile.avoid_negatives:
            negative_patterns = [
                r'\bnot\b', r'\bexcept\b', r'\bnever\b',
                r'\bwithout\b', r'\bun\w+\b', r'\bnone\b',
            ]
            for pattern in negative_patterns:
                if re.search(pattern, question_text, re.IGNORECASE):
                    issues.append(QuizValidationIssue(
                        code="NEGATIVE_PHRASING",
                        severity=QuizValidationSeverity.WARNING,
                        message="Question contains negative phrasing (avoid for young readers)",
                        question_index=idx,
                        field_name="question_text",
                        suggestion="Rephrase using positive language",
                    ))
                    break

        return issues

    def _validate_alignment(
        self,
        idx: int,
        q_data: dict,
        profile: QuizProfile,
    ) -> list[QuizValidationIssue]:
        """Validate question alignment with source text."""
        issues = []

        if not profile.story_source:
            return issues

        source_text = profile.story_source.text_content.lower()
        question_text = q_data.get("question_text", "").lower()
        correct_answer = str(q_data.get("correct_answer", "")).lower()

        # Check if answer relates to source text
        # For literal comprehension, correct answer should be findable in text
        category = q_data.get("category", "")
        if category == "literal_comprehension":
            # Simple check: some key words from answer should appear in text
            answer_words = set(re.findall(r'\b\w{4,}\b', correct_answer))
            text_words = set(re.findall(r'\b\w{4,}\b', source_text))

            if answer_words and not answer_words & text_words:
                issues.append(QuizValidationIssue(
                    code="ANSWER_NOT_IN_TEXT",
                    severity=QuizValidationSeverity.WARNING,
                    message="Literal comprehension answer doesn't appear in source text",
                    question_index=idx,
                    field_name="correct_answer",
                    suggestion="Ensure answer is directly from the text",
                ))

        # Check source reference
        source_ref = q_data.get("source_reference", "")
        if not source_ref and category in ["literal_comprehension", "vocabulary"]:
            issues.append(QuizValidationIssue(
                code="MISSING_SOURCE_REFERENCE",
                severity=QuizValidationSeverity.INFO,
                message="Question should reference specific text location",
                question_index=idx,
                field_name="source_reference",
            ))

        return issues

    def _validate_distribution(
        self,
        bloom_counts: dict[str, int],
        category_counts: dict[str, int],
        profile: QuizProfile,
    ) -> tuple[list[QuizValidationIssue], float]:
        """Validate Bloom's and category distribution."""
        issues = []
        deduction = 0.0

        # Check Bloom's level validity
        allowed_bloom = set(profile.bloom_constraints.allowed_levels)
        for level, count in bloom_counts.items():
            if level != "unknown" and level not in allowed_bloom:
                issues.append(QuizValidationIssue(
                    code="INVALID_BLOOM_LEVEL",
                    severity=QuizValidationSeverity.WARNING,
                    message=f"Bloom level '{level}' not appropriate for this age band",
                    field_name="bloom_level",
                    actual_value=level,
                    expected_value=list(allowed_bloom),
                ))
                deduction += 0.05

        # Check category validity
        allowed_categories = set(profile.category_constraints.allowed_categories)
        for category, count in category_counts.items():
            if category != "unknown" and category not in allowed_categories:
                issues.append(QuizValidationIssue(
                    code="INVALID_CATEGORY",
                    severity=QuizValidationSeverity.WARNING,
                    message=f"Category '{category}' not appropriate for this age band",
                    field_name="category",
                    actual_value=category,
                    expected_value=list(allowed_categories),
                ))
                deduction += 0.05

        return issues, deduction

    def _calculate_alignment_score(
        self,
        questions: list[ValidatedQuestion],
        profile: QuizProfile,
    ) -> float:
        """Calculate overall alignment score."""
        if not questions:
            return 0.0

        valid_count = sum(1 for q in questions if q.is_valid)
        return valid_count / len(questions)


def validate_quiz(
    quiz_json: str | list[dict],
    profile: QuizProfile,
) -> QuizValidationResult:
    """
    Convenience function to validate a quiz.

    Args:
        quiz_json: JSON string or list of question dicts
        profile: QuizProfile with constraints

    Returns:
        QuizValidationResult with issues and scores
    """
    validator = QuizValidator()
    return validator.validate(quiz_json, profile)
