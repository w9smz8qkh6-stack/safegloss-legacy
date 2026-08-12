"""Tests for prompt composition, including golden tests for stability."""

import pytest
from ..prompt_composer import PromptComposer, ComposedPrompt, compose_story_prompt
from ..profile_builder import WritingProfileBuilder


class TestPromptComposer:
    """Test suite for PromptComposer."""

    @pytest.fixture
    def composer(self):
        """Get a fresh prompt composer."""
        return PromptComposer()

    @pytest.fixture
    def builder(self):
        """Get a fresh profile builder."""
        return WritingProfileBuilder()

    def test_composer_initialization(self, composer):
        """Test that composer initializes without errors."""
        assert composer is not None
        assert composer.SYSTEM_MESSAGE_FICTION is not None
        assert composer.SYSTEM_MESSAGE_NONFICTION is not None

    def test_compose_returns_prompt(self, composer, builder):
        """Test that compose returns a ComposedPrompt."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            theme="friendship",
        )
        result = composer.compose(profile, theme="friendship")
        assert isinstance(result, ComposedPrompt)
        assert result.system_message is not None
        assert result.user_prompt is not None
        assert result.profile_hash is not None

    def test_prompt_contains_required_sections(self, composer, builder):
        """Test that prompt contains all required sections."""
        profile = builder.build(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            theme="magic",
        )
        result = composer.compose(profile, theme="magic")
        prompt = result.user_prompt

        assert "## READER PROFILE" in prompt
        assert "## DEVELOPMENTAL WRITING RULES" in prompt
        assert "## GENRE RULES" in prompt
        assert "## LANGUAGE CONSTRAINTS" in prompt
        assert "## STORY PARAMETERS" in prompt
        assert "## OUTPUT REQUIREMENTS" in prompt

    def test_prompt_contains_age_info(self, composer, builder):
        """Test that prompt includes age-specific information."""
        profile = builder.build(
            age_band="6-8",
            genre="realistic_fiction",
            lexile_band="400-500L",
            theme="helping",
        )
        result = composer.compose(profile, theme="helping")
        assert "6-8" in result.user_prompt

    def test_prompt_contains_lexile_constraints(self, composer, builder):
        """Test that prompt includes Lexile constraints."""
        profile = builder.build(
            age_band="10-12",
            genre="mystery",
            lexile_band="700-900L",
            theme="detective",
        )
        result = composer.compose(profile, theme="detective")
        assert "700-900L" in result.user_prompt

    def test_style_profile_adds_section(self, composer, builder):
        """Test that style profile adds a style section."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            style_profile="cinematic",
            theme="adventure",
        )
        result = composer.compose(profile, theme="adventure")
        assert "## WRITING STYLE" in result.user_prompt
        assert "Cinematic" in result.user_prompt

    def test_vocabulary_control_adds_section(self, composer, builder):
        """Test that vocabulary control adds a section."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            allowed_vocabulary=["friend", "help", "share"],
            vocabulary_mode="strict",
            theme="friendship",
        )
        result = composer.compose(profile, theme="friendship")
        assert "## VOCABULARY CONTROL" in result.user_prompt
        assert "friend" in result.user_prompt

    def test_study_mode_mentioned(self, composer, builder):
        """Test that study mode is mentioned in prompt."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            study_mode=True,
            theme="learning",
        )
        result = composer.compose(profile, theme="learning")
        assert "Study Mode" in result.user_prompt


class TestPromptStability:
    """Golden tests for prompt stability - same input should produce same output."""

    @pytest.fixture
    def builder(self):
        return WritingProfileBuilder()

    @pytest.fixture
    def composer(self):
        return PromptComposer()

    def test_deterministic_output(self, builder, composer):
        """Test that identical inputs produce identical prompts."""
        kwargs = {
            "age_band": "8-10",
            "genre": "fantasy",
            "lexile_band": "500-600L",
            "theme": "magic",
        }
        profile1 = builder.build(**kwargs)
        profile2 = builder.build(**kwargs)

        prompt1 = composer.compose(profile1, theme="magic")
        prompt2 = composer.compose(profile2, theme="magic")

        assert prompt1.user_prompt == prompt2.user_prompt
        assert prompt1.profile_hash == prompt2.profile_hash

    def test_deterministic_with_style(self, builder, composer):
        """Test determinism with style profile."""
        kwargs = {
            "age_band": "10-12",
            "genre": "mystery",
            "lexile_band": "700-900L",
            "style_profile": "adventure",
            "theme": "detective",
        }
        profile1 = builder.build(**kwargs)
        profile2 = builder.build(**kwargs)

        prompt1 = composer.compose(profile1, theme="detective")
        prompt2 = composer.compose(profile2, theme="detective")

        assert prompt1.user_prompt == prompt2.user_prompt

    def test_deterministic_with_vocabulary(self, builder, composer):
        """Test determinism with vocabulary control."""
        kwargs = {
            "age_band": "8-10",
            "genre": "realistic_fiction",
            "lexile_band": "500-600L",
            "allowed_vocabulary": ["apple", "banana", "cherry"],
            "vocabulary_mode": "prefer",
            "theme": "fruit",
        }
        profile1 = builder.build(**kwargs)
        profile2 = builder.build(**kwargs)

        prompt1 = composer.compose(profile1, theme="fruit")
        prompt2 = composer.compose(profile2, theme="fruit")

        assert prompt1.user_prompt == prompt2.user_prompt


class TestComposeStoryPromptConvenience:
    """Test the compose_story_prompt convenience function."""

    def test_convenience_function(self):
        """Test compose_story_prompt convenience function."""
        result = compose_story_prompt(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            theme="magic",
        )
        assert isinstance(result, ComposedPrompt)

    def test_with_all_options(self):
        """Test compose_story_prompt with all options."""
        result = compose_story_prompt(
            age_band="10-12",
            genre="mystery",
            lexile_band="700-900L",
            theme="detective",
            word_count=600,
            setting="old mansion",
            main_character="young detective",
            tone="suspenseful",
            style_profile="adventure",
            ell_mode="intermediate",
            study_mode=True,
            allowed_vocabulary=["clue", "mystery", "solve"],
            restricted_vocabulary=["death", "blood"],
            vocabulary_mode="prefer",
            max_stretch_words=3,
        )
        assert isinstance(result, ComposedPrompt)
        assert "detective" in result.user_prompt
        assert "old mansion" in result.user_prompt


class TestPromptSections:
    """Test individual prompt section composition."""

    @pytest.fixture
    def builder(self):
        return WritingProfileBuilder()

    @pytest.fixture
    def composer(self):
        return PromptComposer()

    def test_narrative_rules_for_young_readers(self, builder, composer):
        """Test narrative rules for young readers (6-8)."""
        profile = builder.build(
            age_band="6-8",
            genre="realistic_fiction",
            lexile_band="400-500L",
            theme="helping",
        )
        result = composer.compose(profile, theme="helping")
        prompt = result.user_prompt

        assert "one main character" in prompt.lower()
        assert "single" in prompt.lower() and "problem" in prompt.lower()

    def test_narrative_rules_for_older_readers(self, builder, composer):
        """Test narrative rules for older readers (12-14)."""
        profile = builder.build(
            age_band="12-14",
            genre="mystery",
            lexile_band="900-1100L",
            theme="investigation",
        )
        result = composer.compose(profile, theme="investigation")
        prompt = result.user_prompt

        # Should allow more complexity
        assert "3" in prompt or "three" in prompt.lower()

    def test_genre_specific_rules(self, builder, composer):
        """Test genre-specific rules in prompt."""
        profile = builder.build(
            age_band="10-12",
            genre="fantasy",
            lexile_band="700-900L",
            theme="dragons",
        )
        result = composer.compose(profile, theme="dragons")
        prompt = result.user_prompt

        assert "magic" in prompt.lower() or "imaginary" in prompt.lower()

    def test_lexile_constraints_in_prompt(self, builder, composer):
        """Test Lexile constraints appear in prompt."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            theme="sports",
        )
        result = composer.compose(profile, theme="sports")
        prompt = result.user_prompt

        # Should mention sentence length targets
        assert "9" in prompt and "12" in prompt  # 9-12 word avg
