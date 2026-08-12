"""Tests for text metrics extraction."""

import pytest
from ..text_metrics import TextMetrics, extract_metrics


class TestExtractMetrics:
    """Test suite for extract_metrics function."""

    def test_basic_extraction(self):
        """Test basic metric extraction."""
        text = "The cat sat on the mat. It was a sunny day."
        metrics = extract_metrics(text)
        assert isinstance(metrics, TextMetrics)
        assert metrics.total_words > 0
        assert metrics.total_sentences == 2

    def test_word_count(self):
        """Test accurate word counting."""
        text = "One two three four five."
        metrics = extract_metrics(text)
        assert metrics.total_words == 5

    def test_sentence_count(self):
        """Test accurate sentence counting."""
        text = "First sentence. Second sentence! Third sentence?"
        metrics = extract_metrics(text)
        assert metrics.total_sentences == 3

    def test_avg_sentence_length(self):
        """Test average sentence length calculation."""
        # Two sentences: 4 words each = avg 4
        text = "One two three four. Five six seven eight."
        metrics = extract_metrics(text)
        assert metrics.avg_sentence_length == 4.0

    def test_dialogue_detection_double_quotes(self):
        """Test dialogue detection with double quotes."""
        text = '"Hello," said John. "How are you?" asked Mary.'
        metrics = extract_metrics(text)
        assert metrics.dialogue_sentence_count > 0
        assert metrics.dialogue_ratio > 0

    def test_dialogue_detection_single_quotes(self):
        """Test dialogue detection with single quotes."""
        text = "'Hello,' said John. 'How are you?' asked Mary."
        metrics = extract_metrics(text)
        assert metrics.dialogue_sentence_count > 0

    def test_no_dialogue(self):
        """Test text without dialogue."""
        text = "The sun rose over the hills. Birds began to sing."
        metrics = extract_metrics(text)
        assert metrics.dialogue_ratio == 0.0

    def test_passive_voice_detection(self):
        """Test passive voice detection."""
        text = "The ball was kicked. The window was broken. John ran."
        metrics = extract_metrics(text)
        assert metrics.passive_voice_count >= 2
        assert metrics.passive_voice_ratio > 0

    def test_no_passive_voice(self):
        """Test text without passive voice."""
        text = "John kicked the ball. Mary broke the window."
        metrics = extract_metrics(text)
        assert metrics.passive_voice_ratio == 0.0

    def test_long_sentence_detection(self):
        """Test long sentence detection."""
        short = "Short sentence here."
        long_text = " ".join(["word"] * 30) + "."  # 30 word sentence
        text = f"{short} {long_text}"
        metrics = extract_metrics(text)
        assert metrics.long_sentence_count >= 1

    def test_clause_complexity(self):
        """Test clause complexity calculation."""
        simple = "The cat sat."
        complex_sentence = "The cat, which was black, sat on the mat that was red."
        text = f"{simple} {complex_sentence}"
        metrics = extract_metrics(text)
        assert metrics.avg_clause_count > 1.0

    def test_sentence_length_std_dev(self):
        """Test sentence length standard deviation."""
        # Varied sentence lengths
        text = "Short. This is a medium length sentence here. A tiny bit."
        metrics = extract_metrics(text)
        assert metrics.sentence_length_std_dev > 0

    def test_empty_text(self):
        """Test handling of empty text."""
        metrics = extract_metrics("")
        assert metrics.total_words == 0
        assert metrics.total_sentences == 0
        assert metrics.avg_sentence_length == 0

    def test_single_sentence(self):
        """Test handling of single sentence."""
        text = "Just one sentence here."
        metrics = extract_metrics(text)
        assert metrics.total_sentences == 1
        assert metrics.sentence_length_std_dev == 0


class TestTextMetricsDataclass:
    """Test TextMetrics dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = TextMetrics(
            total_words=100,
            total_sentences=10,
            avg_sentence_length=10.0,
            sentence_length_std_dev=2.0,
            long_sentence_count=1,
            long_sentence_ratio=0.1,
            long_sentence_threshold=20,
            dialogue_sentence_count=3,
            dialogue_ratio=0.3,
            passive_voice_count=2,
            passive_voice_ratio=0.2,
            avg_clause_count=1.5,
            complex_sentence_ratio=0.2,
        )
        d = metrics.to_dict()
        assert isinstance(d, dict)
        assert d["total_words"] == 100
        assert d["avg_sentence_length"] == 10.0


class TestMetricsEdgeCases:
    """Test edge cases in metrics extraction."""

    def test_punctuation_handling(self):
        """Test handling of various punctuation."""
        text = "Hello! How are you? I'm fine... Great!"
        metrics = extract_metrics(text)
        assert metrics.total_sentences >= 3

    def test_abbreviations(self):
        """Test handling of abbreviations."""
        text = "Dr. Smith went to the U.S.A. for a conference."
        metrics = extract_metrics(text)
        # Should not over-count sentences due to periods in abbreviations
        assert metrics.total_sentences <= 2

    def test_numbers_in_text(self):
        """Test handling of numbers."""
        text = "There were 100 people. About 50 stayed."
        metrics = extract_metrics(text)
        assert metrics.total_words == 7

    def test_contractions(self):
        """Test handling of contractions."""
        text = "I'm going to the store. She's coming too."
        metrics = extract_metrics(text)
        # Contractions should count appropriately
        assert metrics.total_words >= 8
