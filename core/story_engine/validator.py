"""
Story Validator

Validates generated stories against Lexile band thresholds.
Uses metrics from text_metrics.py and rules from lexile_rules.json.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .text_metrics import TextMetrics, extract_metrics
from .rules import get_rules_loader, RulesLoader


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single validation issue found in the text."""
    code: str
    severity: ValidationSeverity
    message: str
    metric_name: str
    actual_value: Any
    expected_range: tuple[Any, Any] | None = None
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Complete validation result for a story."""
    valid: bool
    score: float  # 0.0 to 1.0, higher is better
    issues: list[ValidationIssue] = field(default_factory=list)
    metrics: TextMetrics | None = None
    lexile_band: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "valid": self.valid,
            "score": round(self.score, 3),
            "lexile_band": self.lexile_band,
            "issue_count": len(self.issues),
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "message": i.message,
                    "metric": i.metric_name,
                    "actual": i.actual_value,
                    "expected_range": i.expected_range,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "metrics": self.metrics.to_dict() if self.metrics else None,
        }


class StoryValidator:
    """
    Validates stories against Lexile band constraints.

    Uses thresholds from lexile_rules.json to check:
    - Average sentence length
    - Maximum clause count
    - Passive voice usage
    - Dialogue ratio
    - Overall complexity
    """

    # Tolerance for "close enough" validation (percentage)
    TOLERANCE = 0.15  # 15% tolerance

    def __init__(self, rules_loader: RulesLoader | None = None):
        self.rules = rules_loader or get_rules_loader()

    def validate(
        self,
        text: str,
        lexile_band: str,
        target_word_count: int | None = None,
    ) -> ValidationResult:
        """
        Validate a story against Lexile band thresholds.

        Args:
            text: The story text to validate
            lexile_band: Target Lexile band (e.g., "500-600L")
            target_word_count: Optional target word count

        Returns:
            ValidationResult with issues and score
        """
        issues = []
        score_deductions = 0.0

        # Extract metrics
        metrics = extract_metrics(text)

        # Get rules for this Lexile band
        try:
            band_rules = self.rules.get_lexile_rules(lexile_band)
        except ValueError as e:
            return ValidationResult(
                valid=False,
                score=0.0,
                issues=[ValidationIssue(
                    code="INVALID_BAND",
                    severity=ValidationSeverity.ERROR,
                    message=str(e),
                    metric_name="lexile_band",
                    actual_value=lexile_band,
                )],
                metrics=metrics,
                lexile_band=lexile_band,
            )

        # Validate sentence length
        sentence_issues, sentence_deduction = self._validate_sentence_length(
            metrics, band_rules
        )
        issues.extend(sentence_issues)
        score_deductions += sentence_deduction

        # Validate clause complexity
        clause_issues, clause_deduction = self._validate_clause_complexity(
            metrics, band_rules
        )
        issues.extend(clause_issues)
        score_deductions += clause_deduction

        # Validate passive voice
        passive_issues, passive_deduction = self._validate_passive_voice(
            metrics, band_rules
        )
        issues.extend(passive_issues)
        score_deductions += passive_deduction

        # Validate word count if target provided
        if target_word_count:
            wc_issues, wc_deduction = self._validate_word_count(
                metrics, target_word_count
            )
            issues.extend(wc_issues)
            score_deductions += wc_deduction

        # Validate dialogue ratio (informational)
        dialogue_issues, dialogue_deduction = self._validate_dialogue_ratio(
            metrics, band_rules
        )
        issues.extend(dialogue_issues)
        score_deductions += dialogue_deduction

        # Compute final score (1.0 - deductions, minimum 0.0)
        final_score = max(0.0, 1.0 - score_deductions)

        # Determine validity (no errors, score above threshold)
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        is_valid = not has_errors and final_score >= 0.6

        return ValidationResult(
            valid=is_valid,
            score=final_score,
            issues=issues,
            metrics=metrics,
            lexile_band=lexile_band,
        )

    def _validate_sentence_length(
        self,
        metrics: TextMetrics,
        rules: dict,
    ) -> tuple[list[ValidationIssue], float]:
        """Validate average sentence length against band rules."""
        issues = []
        deduction = 0.0

        sentence_rules = rules.get("sentence", {})
        avg_length = sentence_rules.get("avg_length", {"min": 10, "max": 15})
        min_len = avg_length["min"]
        max_len = avg_length["max"]

        actual = metrics.avg_sentence_length

        # Check if within range (with tolerance)
        min_with_tolerance = min_len * (1 - self.TOLERANCE)
        max_with_tolerance = max_len * (1 + self.TOLERANCE)

        if actual < min_with_tolerance:
            severity = ValidationSeverity.WARNING if actual >= min_len * 0.7 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="SENTENCE_TOO_SHORT",
                severity=severity,
                message=f"Average sentence length ({actual:.1f}) is below target ({min_len}-{max_len})",
                metric_name="avg_sentence_length",
                actual_value=round(actual, 1),
                expected_range=(min_len, max_len),
                suggestion="Expand sentences by adding detail or combining related ideas",
            ))
            deduction = 0.15 if severity == ValidationSeverity.WARNING else 0.3

        elif actual > max_with_tolerance:
            severity = ValidationSeverity.WARNING if actual <= max_len * 1.3 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="SENTENCE_TOO_LONG",
                severity=severity,
                message=f"Average sentence length ({actual:.1f}) exceeds target ({min_len}-{max_len})",
                metric_name="avg_sentence_length",
                actual_value=round(actual, 1),
                expected_range=(min_len, max_len),
                suggestion="Split long sentences or simplify complex constructions",
            ))
            deduction = 0.15 if severity == ValidationSeverity.WARNING else 0.3

        # Check variance (high variance indicates inconsistent sentence length)
        if metrics.sentence_length_std_dev > max_len * 0.8:
            issues.append(ValidationIssue(
                code="HIGH_LENGTH_VARIANCE",
                severity=ValidationSeverity.INFO,
                message=f"High variation in sentence length (std dev: {metrics.sentence_length_std_dev:.1f})",
                metric_name="sentence_length_std_dev",
                actual_value=round(metrics.sentence_length_std_dev, 1),
                suggestion="Aim for more consistent sentence lengths",
            ))
            deduction += 0.05

        # Check for too many long sentences
        if metrics.long_sentence_ratio > 0.2:
            severity = ValidationSeverity.WARNING if metrics.long_sentence_ratio < 0.3 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="TOO_MANY_LONG_SENTENCES",
                severity=severity,
                message=f"{metrics.long_sentence_count} sentences exceed {metrics.long_sentence_threshold} words ({metrics.long_sentence_ratio:.0%})",
                metric_name="long_sentence_ratio",
                actual_value=round(metrics.long_sentence_ratio, 2),
                expected_range=(0, 0.2),
                suggestion="Break up long sentences into shorter ones",
            ))
            deduction += 0.1 if severity == ValidationSeverity.WARNING else 0.2

        return issues, deduction

    def _validate_clause_complexity(
        self,
        metrics: TextMetrics,
        rules: dict,
    ) -> tuple[list[ValidationIssue], float]:
        """Validate clause complexity against band rules."""
        issues = []
        deduction = 0.0

        sentence_rules = rules.get("sentence", {})
        max_clauses = sentence_rules.get("max_clauses", 1)

        # Check average clause count
        if metrics.avg_clause_count > max_clauses + 0.5:
            severity = ValidationSeverity.WARNING if metrics.avg_clause_count < max_clauses + 1 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="TOO_MANY_CLAUSES",
                severity=severity,
                message=f"Average clause count ({metrics.avg_clause_count:.1f}) exceeds target ({max_clauses})",
                metric_name="avg_clause_count",
                actual_value=round(metrics.avg_clause_count, 1),
                expected_range=(1, max_clauses),
                suggestion="Simplify sentences by removing subordinate clauses",
            ))
            deduction = 0.1 if severity == ValidationSeverity.WARNING else 0.25

        # Check complex sentence ratio - use corpus-derived thresholds
        validation_thresholds = rules.get("validation_thresholds", {})
        max_complex_ratio = validation_thresholds.get("max_complex_ratio", 0.3 if max_clauses <= 1 else 0.5)

        if metrics.complex_sentence_ratio > max_complex_ratio:
            issues.append(ValidationIssue(
                code="TOO_MANY_COMPLEX_SENTENCES",
                severity=ValidationSeverity.WARNING,
                message=f"{metrics.complex_sentence_ratio:.0%} of sentences are complex (target: <{max_complex_ratio:.0%})",
                metric_name="complex_sentence_ratio",
                actual_value=round(metrics.complex_sentence_ratio, 2),
                expected_range=(0, max_complex_ratio),
                suggestion="Use more simple sentences",
            ))
            deduction += 0.1

        return issues, deduction

    def _validate_passive_voice(
        self,
        metrics: TextMetrics,
        rules: dict,
    ) -> tuple[list[ValidationIssue], float]:
        """Validate passive voice usage against band rules."""
        issues = []
        deduction = 0.0

        grammar_rules = rules.get("grammar", {})
        passive_allowed = grammar_rules.get("passive_voice", "avoid")

        # Use corpus-derived threshold if available
        validation_thresholds = rules.get("validation_thresholds", {})
        max_passive_ratio = validation_thresholds.get("max_passive_ratio")

        # Fall back to rule-based thresholds if no corpus data
        if max_passive_ratio is None:
            if passive_allowed in [False, "avoid", "never"]:
                max_passive_ratio = 0.05
            elif passive_allowed == "rare":
                max_passive_ratio = 0.1
            elif passive_allowed == "occasional":
                max_passive_ratio = 0.2
            else:  # allowed
                max_passive_ratio = 0.3

        if metrics.passive_voice_ratio > max_passive_ratio:
            if passive_allowed in [False, "avoid", "never"]:
                severity = ValidationSeverity.ERROR if metrics.passive_voice_ratio > 0.15 else ValidationSeverity.WARNING
            else:
                severity = ValidationSeverity.WARNING

            issues.append(ValidationIssue(
                code="TOO_MUCH_PASSIVE_VOICE",
                severity=severity,
                message=f"Passive voice detected in {metrics.passive_voice_ratio:.0%} of sentences",
                metric_name="passive_voice_ratio",
                actual_value=round(metrics.passive_voice_ratio, 2),
                expected_range=(0, max_passive_ratio),
                suggestion="Rewrite passive constructions to active voice",
            ))
            deduction = 0.1 if severity == ValidationSeverity.WARNING else 0.2

        return issues, deduction

    def _validate_word_count(
        self,
        metrics: TextMetrics,
        target: int,
    ) -> tuple[list[ValidationIssue], float]:
        """Validate word count against target."""
        issues = []
        deduction = 0.0

        actual = metrics.total_words
        min_words = int(target * 0.9)  # 10% under is acceptable
        max_words = int(target * 1.1)  # 10% over is acceptable

        if actual < min_words:
            diff_pct = (target - actual) / target * 100
            severity = ValidationSeverity.WARNING if diff_pct < 20 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="WORD_COUNT_LOW",
                severity=severity,
                message=f"Word count ({actual}) is {diff_pct:.0f}% below target ({target})",
                metric_name="total_words",
                actual_value=actual,
                expected_range=(min_words, max_words),
                suggestion="Expand the story with more detail or additional scenes",
            ))
            deduction = 0.1 if severity == ValidationSeverity.WARNING else 0.2

        elif actual > max_words:
            diff_pct = (actual - target) / target * 100
            severity = ValidationSeverity.WARNING if diff_pct < 20 else ValidationSeverity.ERROR
            issues.append(ValidationIssue(
                code="WORD_COUNT_HIGH",
                severity=severity,
                message=f"Word count ({actual}) is {diff_pct:.0f}% above target ({target})",
                metric_name="total_words",
                actual_value=actual,
                expected_range=(min_words, max_words),
                suggestion="Trim unnecessary details or combine sentences",
            ))
            deduction = 0.1 if severity == ValidationSeverity.WARNING else 0.2

        return issues, deduction

    def _validate_dialogue_ratio(
        self,
        metrics: TextMetrics,
        rules: dict,
    ) -> tuple[list[ValidationIssue], float]:
        """Validate dialogue ratio using corpus-derived thresholds."""
        issues = []
        deduction = 0.0

        # Use corpus-derived thresholds if available
        validation_thresholds = rules.get("validation_thresholds", {})
        dialogue_range = validation_thresholds.get("dialogue_ratio", {"min": 0.15, "max": 0.45})
        min_dialogue = dialogue_range.get("min", 0.15)
        max_dialogue = dialogue_range.get("max", 0.45)

        # Check for excessive dialogue
        if metrics.dialogue_ratio > max_dialogue + 0.15:  # 15% tolerance above max
            issues.append(ValidationIssue(
                code="HIGH_DIALOGUE_RATIO",
                severity=ValidationSeverity.WARNING if metrics.dialogue_ratio < 0.7 else ValidationSeverity.INFO,
                message=f"Dialogue comprises {metrics.dialogue_ratio:.0%} of sentences (target: {min_dialogue:.0%}-{max_dialogue:.0%})",
                metric_name="dialogue_ratio",
                actual_value=round(metrics.dialogue_ratio, 2),
                expected_range=(min_dialogue, max_dialogue),
                suggestion="Balance dialogue with narrative description",
            ))
            deduction = 0.05

        # Check for low dialogue
        elif metrics.dialogue_ratio < min_dialogue - 0.05 and metrics.total_sentences > 10:
            issues.append(ValidationIssue(
                code="LOW_DIALOGUE_RATIO",
                severity=ValidationSeverity.INFO,
                message=f"Minimal dialogue ({metrics.dialogue_ratio:.0%}, target: {min_dialogue:.0%}-{max_dialogue:.0%})",
                metric_name="dialogue_ratio",
                actual_value=round(metrics.dialogue_ratio, 2),
                expected_range=(min_dialogue, max_dialogue),
                suggestion="Consider adding dialogue for engagement",
            ))
            # No deduction for low dialogue - it's just a suggestion

        return issues, deduction


def validate_story(
    text: str,
    lexile_band: str,
    target_word_count: int | None = None,
) -> ValidationResult:
    """
    Convenience function to validate a story.

    Args:
        text: The story text to validate
        lexile_band: Target Lexile band (e.g., "500-600L")
        target_word_count: Optional target word count

    Returns:
        ValidationResult with issues and score
    """
    validator = StoryValidator()
    return validator.validate(text, lexile_band, target_word_count)
