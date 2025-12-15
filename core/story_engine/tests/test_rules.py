"""Tests for rules loading and validation."""

import pytest
from ..rules import get_rules_loader, RulesLoader


class TestRulesLoader:
    """Test suite for RulesLoader."""

    @pytest.fixture
    def loader(self):
        """Get a fresh rules loader."""
        return get_rules_loader()

    def test_loader_initialization(self, loader):
        """Test that loader initializes without errors."""
        assert loader is not None
        assert isinstance(loader, RulesLoader)

    def test_get_age_rules_valid(self, loader):
        """Test retrieving valid age rules."""
        for age_band in ["6-8", "8-10", "10-12", "12-14"]:
            rules = loader.get_age_rules(age_band)
            assert rules is not None
            assert "narrative" in rules
            assert "guidance" in rules

    def test_get_age_rules_invalid(self, loader):
        """Test that invalid age band raises ValueError."""
        with pytest.raises(ValueError):
            loader.get_age_rules("invalid")

    def test_get_lexile_rules_valid(self, loader):
        """Test retrieving valid Lexile rules."""
        bands = ["300-400L", "400-500L", "500-600L", "600-700L", "700-900L", "900-1100L"]
        for band in bands:
            rules = loader.get_lexile_rules(band)
            assert rules is not None
            assert "sentence" in rules
            assert "vocabulary" in rules
            assert "validation_thresholds" in rules

    def test_get_lexile_rules_invalid(self, loader):
        """Test that invalid Lexile band raises ValueError."""
        with pytest.raises(ValueError):
            loader.get_lexile_rules("invalid")

    def test_get_genre_rules_valid(self, loader):
        """Test retrieving valid genre rules."""
        genres = ["realistic_fiction", "fantasy", "mystery", "informational_fiction"]
        for genre in genres:
            rules = loader.get_genre_rules(genre)
            assert rules is not None

    def test_get_genre_rules_invalid(self, loader):
        """Test that invalid genre raises ValueError."""
        with pytest.raises(ValueError):
            loader.get_genre_rules("invalid")

    def test_get_style_profile_valid(self, loader):
        """Test retrieving valid style profiles."""
        profiles = ["minimalist", "cinematic", "humorous", "sel_focused", "adventure", "lyrical"]
        for profile in profiles:
            style = loader.get_style_profile(profile)
            assert style is not None
            assert "adjustments" in style
            assert "guidance" in style

    def test_get_style_profile_invalid(self, loader):
        """Test that invalid style profile raises ValueError."""
        with pytest.raises(ValueError):
            loader.get_style_profile("invalid")

    def test_age_rules_have_corpus_metrics(self, loader):
        """Test that age rules include corpus metrics."""
        for age_band in ["6-8", "8-10", "10-12", "12-14"]:
            rules = loader.get_age_rules(age_band)
            assert "corpus_metrics" in rules
            metrics = rules["corpus_metrics"]
            assert "sentence_length" in metrics
            assert "dialogue_ratio" in metrics

    def test_lexile_rules_have_validation_thresholds(self, loader):
        """Test that Lexile rules include validation thresholds."""
        rules = loader.get_lexile_rules("500-600L")
        thresholds = rules["validation_thresholds"]
        assert "avg_sentence_length" in thresholds
        assert "max_passive_ratio" in thresholds
        assert "dialogue_ratio" in thresholds

    def test_style_profiles_have_writing_voice(self, loader):
        """Test that style profiles include writing voice settings."""
        style = loader.get_style_profile("cinematic")
        assert "writing_voice" in style
        voice = style["writing_voice"]
        assert "pacing" in voice
        assert "description_style" in voice
