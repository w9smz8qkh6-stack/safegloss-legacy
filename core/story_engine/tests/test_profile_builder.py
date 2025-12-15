"""Tests for WritingProfileBuilder and rule merging."""

import pytest
from ..profile_builder import (
    WritingProfileBuilder,
    WritingProfile,
    NarrativeRules,
    StyleRules,
    VocabularyRules,
    VocabularyConstraints,
)


class TestWritingProfileBuilder:
    """Test suite for WritingProfileBuilder."""

    @pytest.fixture
    def builder(self):
        """Get a fresh profile builder."""
        return WritingProfileBuilder()

    def test_builder_initialization(self, builder):
        """Test that builder initializes without errors."""
        assert builder is not None
        assert builder.rules is not None
        assert builder.guardrails is not None

    def test_build_basic_profile(self, builder):
        """Test building a basic profile."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            theme="friendship",
        )
        assert isinstance(profile, WritingProfile)
        assert profile.age_band == "8-10"
        assert profile.genre == "realistic_fiction"
        assert profile.lexile_band == "500-600L"

    def test_profile_has_narrative_rules(self, builder):
        """Test that profile includes narrative rules from age band."""
        profile = builder.build(
            age_band="6-8",
            genre="realistic_fiction",
            lexile_band="400-500L",
            theme="helping others",
        )
        assert profile.narrative.max_characters == 1
        assert profile.narrative.timeline == "linear"
        assert profile.narrative.flashbacks is False

    def test_profile_has_lexile_constraints(self, builder):
        """Test that profile includes Lexile constraints."""
        profile = builder.build(
            age_band="10-12",
            genre="mystery",
            lexile_band="700-900L",
            theme="solving a puzzle",
        )
        assert profile.style.avg_sentence_length_min == 12
        assert profile.style.avg_sentence_length_max == 17
        assert profile.style.max_clauses == 2

    def test_profile_hash_deterministic(self, builder):
        """Test that profile hash is deterministic."""
        kwargs = {
            "age_band": "8-10",
            "genre": "fantasy",
            "lexile_band": "500-600L",
            "theme": "courage",
        }
        profile1 = builder.build(**kwargs)
        profile2 = builder.build(**kwargs)
        assert profile1.profile_hash == profile2.profile_hash

    def test_profile_hash_changes_with_input(self, builder):
        """Test that profile hash changes with different inputs."""
        profile1 = builder.build(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            theme="courage",
        )
        profile2 = builder.build(
            age_band="10-12",  # Different age
            genre="fantasy",
            lexile_band="500-600L",
            theme="courage",
        )
        assert profile1.profile_hash != profile2.profile_hash

    def test_style_profile_applies_adjustments(self, builder):
        """Test that style profile modifies base rules."""
        profile_without_style = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            theme="friendship",
        )
        profile_with_style = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            style_profile="minimalist",
            theme="friendship",
        )
        # Minimalist has sentence_length_modifier: -2
        assert profile_with_style.style.avg_sentence_length_min < profile_without_style.style.avg_sentence_length_min

    def test_style_profile_sets_dialogue_ratio(self, builder):
        """Test that style profile sets dialogue ratio targets."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            style_profile="humorous",
            theme="funny situation",
        )
        # Humorous has dialogue_ratio_target: min 0.35, max 0.55
        assert profile.style.dialogue_ratio_min == 0.35
        assert profile.style.dialogue_ratio_max == 0.55

    def test_vocabulary_mode_auto_detection(self, builder):
        """Test that vocabulary mode auto-enables when words provided."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            allowed_vocabulary=["friend", "help", "share"],
            theme="friendship",
        )
        assert profile.vocab_constraints.mode == "prefer"

    def test_vocabulary_mode_explicit_strict(self, builder):
        """Test explicit strict vocabulary mode."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            allowed_vocabulary=["friend", "help", "share"],
            vocabulary_mode="strict",
            max_stretch_words=3,
            theme="friendship",
        )
        assert profile.vocab_constraints.mode == "strict"
        assert profile.vocab_constraints.max_stretch_words == 3

    def test_study_mode_enables_stretch_definitions(self, builder):
        """Test that study mode enables stretch word definitions."""
        profile = builder.build(
            age_band="8-10",
            genre="realistic_fiction",
            lexile_band="500-600L",
            allowed_vocabulary=["friend", "help"],
            vocabulary_mode="strict",
            study_mode=True,
            theme="friendship",
        )
        assert profile.vocab_constraints.stretch_words_require_definition is True

    def test_ell_mode_applies_constraints(self, builder):
        """Test that ELL mode applies additional constraints."""
        profile_without_ell = builder.build(
            age_band="10-12",
            genre="realistic_fiction",
            lexile_band="700-900L",
            theme="adventure",
        )
        profile_with_ell = builder.build(
            age_band="10-12",
            genre="realistic_fiction",
            lexile_band="700-900L",
            ell_mode="beginner",
            theme="adventure",
        )
        # ELL should add more guidance
        assert len(profile_with_ell.guidance) > len(profile_without_ell.guidance)

    def test_guidance_accumulates(self, builder):
        """Test that guidance accumulates from all rule sources."""
        profile = builder.build(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            style_profile="adventure",
            theme="quest",
        )
        # Should have guidance from age, genre, lexile, and style
        assert len(profile.guidance) > 5


class TestVocabularyConstraints:
    """Test suite for VocabularyConstraints dataclass."""

    def test_default_values(self):
        """Test default vocabulary constraint values."""
        vc = VocabularyConstraints()
        assert vc.mode == "none"
        assert vc.allowed_words == []
        assert vc.restricted_words == []
        assert vc.max_stretch_words == 5
        assert vc.stretch_words_require_definition is True

    def test_custom_values(self):
        """Test custom vocabulary constraint values."""
        vc = VocabularyConstraints(
            mode="strict",
            allowed_words=["hello", "world"],
            max_stretch_words=3,
        )
        assert vc.mode == "strict"
        assert vc.allowed_words == ["hello", "world"]
        assert vc.max_stretch_words == 3


class TestProfileSerialization:
    """Test profile serialization and hashing."""

    @pytest.fixture
    def builder(self):
        return WritingProfileBuilder()

    def test_to_dict(self, builder):
        """Test profile serialization to dictionary."""
        profile = builder.build(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            theme="magic",
        )
        d = profile.to_dict()
        assert isinstance(d, dict)
        assert d["age_band"] == "8-10"
        assert d["genre"] == "fantasy"
        assert "narrative" in d
        assert "style" in d

    def test_compute_hash(self, builder):
        """Test hash computation."""
        profile = builder.build(
            age_band="8-10",
            genre="fantasy",
            lexile_band="500-600L",
            theme="magic",
        )
        hash1 = profile.compute_hash()
        assert isinstance(hash1, str)
        assert len(hash1) == 16  # SHA256 truncated to 16 chars
