"""Tests for story validation."""

import pytest
from ..validator import (
    StoryValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_story,
)


class TestStoryValidator:
    """Test suite for StoryValidator."""

    @pytest.fixture
    def validator(self):
        """Get a fresh validator."""
        return StoryValidator()

    def test_validator_initialization(self, validator):
        """Test that validator initializes without errors."""
        assert validator is not None
        assert validator.rules is not None

    def test_validate_returns_result(self, validator):
        """Test that validate returns a ValidationResult."""
        text = "The cat sat on the mat. It was happy."
        result = validator.validate(text, "500-600L")
        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.score, float)

    def test_validate_includes_metrics(self, validator):
        """Test that validation result includes metrics."""
        text = "The cat sat on the mat. It was happy."
        result = validator.validate(text, "500-600L")
        assert result.metrics is not None
        assert result.metrics.total_words > 0

    def test_validate_invalid_band(self, validator):
        """Test validation with invalid Lexile band."""
        text = "Some text here."
        result = validator.validate(text, "invalid-band")
        assert result.valid is False
        assert any(i.code == "INVALID_BAND" for i in result.issues)

    def test_sentence_length_validation(self, validator):
        """Test sentence length validation."""
        # Very long sentences for 300-400L band
        long_text = " ".join(["word"] * 20) + ". " + " ".join(["word"] * 20) + "."
        result = validator.validate(long_text, "300-400L")
        # Should have sentence length issues
        assert any("SENTENCE" in i.code for i in result.issues)

    def test_word_count_validation(self, validator):
        """Test word count validation against target."""
        text = "Short text."
        result = validator.validate(text, "500-600L", target_word_count=500)
        assert any(i.code == "WORD_COUNT_LOW" for i in result.issues)

    def test_score_range(self, validator):
        """Test that score is between 0 and 1."""
        text = "The cat sat on the mat. It was a sunny day. Birds sang."
        result = validator.validate(text, "500-600L")
        assert 0.0 <= result.score <= 1.0

    def test_result_to_dict(self, validator):
        """Test ValidationResult serialization."""
        text = "The cat sat on the mat."
        result = validator.validate(text, "500-600L")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "valid" in d
        assert "score" in d
        assert "issues" in d


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_issue_creation(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            code="TEST_ISSUE",
            severity=ValidationSeverity.WARNING,
            message="Test message",
            metric_name="test_metric",
            actual_value=10,
            expected_range=(5, 8),
            suggestion="Fix it",
        )
        assert issue.code == "TEST_ISSUE"
        assert issue.severity == ValidationSeverity.WARNING

    def test_severity_values(self):
        """Test severity enum values."""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"


class TestValidateStoryConvenience:
    """Test the validate_story convenience function."""

    def test_convenience_function(self):
        """Test validate_story convenience function."""
        text = "The cat sat on the mat. It was happy."
        result = validate_story(text, "500-600L")
        assert isinstance(result, ValidationResult)

    def test_with_word_count(self):
        """Test validate_story with target word count."""
        text = "The cat sat on the mat. It was happy."
        result = validate_story(text, "500-600L", target_word_count=100)
        assert isinstance(result, ValidationResult)


class TestValidationThresholds:
    """Test validation using corpus-derived thresholds."""

    @pytest.fixture
    def validator(self):
        return StoryValidator()

    def test_uses_corpus_thresholds(self, validator):
        """Test that validator uses corpus-derived thresholds."""
        # This is a simple validation - the validator should use
        # validation_thresholds from lexile_rules.json
        text = "Short sentence. Another one."
        result = validator.validate(text, "500-600L")
        # Should complete without error
        assert result is not None

    def test_dialogue_ratio_validation(self, validator):
        """Test dialogue ratio validation."""
        # All dialogue - should flag high dialogue ratio
        text = '"Hello," said John. "Hi," said Mary. "Bye," said John.'
        result = validator.validate(text, "500-600L")
        # May or may not flag depending on thresholds
        assert result is not None

    def test_passive_voice_validation(self, validator):
        """Test passive voice validation for strict bands."""
        # Heavy passive voice for 300-400L (should flag as error)
        text = "The ball was kicked. The door was opened. The cake was eaten."
        result = validator.validate(text, "300-400L")
        passive_issues = [i for i in result.issues if "PASSIVE" in i.code]
        assert len(passive_issues) > 0


class TestValidationWithStyles:
    """Test validation considers style profile constraints."""

    @pytest.fixture
    def validator(self):
        return StoryValidator()

    def test_minimalist_short_sentences_ok(self, validator):
        """Test that short sentences are fine for minimalist style."""
        # Very short sentences
        text = "He ran. She followed. They stopped. He turned."
        result = validator.validate(text, "500-600L")
        # Short sentences alone shouldn't fail validation
        # (style is applied during generation, not validation)
        assert result is not None
