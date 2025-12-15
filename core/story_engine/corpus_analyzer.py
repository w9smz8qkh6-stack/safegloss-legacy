"""
Corpus Analyzer

Analyzes texts to extract statistical distributions for rule enhancement.
Supports building empirical rules from public-domain corpus analysis.

Usage:
1. Add texts to the corpus via add_text()
2. Run compute_statistics() to generate aggregates
3. Export to corpus_stats.json for rule enhancement
"""

import json
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .text_metrics import TextMetricsExtractor, TextMetrics


@dataclass
class CorpusText:
    """Metadata and metrics for a single corpus text."""
    id: str
    title: str
    source: str  # e.g., "Project Gutenberg", "ICDL", "Public Domain"
    age_bucket: str  # "6-8", "8-10", "10-12", "12-14"
    genre: str  # "realistic_fiction", "fantasy", "mystery", "informational_fiction"
    word_count: int = 0
    metrics: dict = field(default_factory=dict)


@dataclass
class BucketStatistics:
    """Aggregated statistics for an age/genre bucket."""
    age_bucket: str
    genre: str
    text_count: int = 0

    # Sentence length statistics
    avg_sentence_length_mean: float = 0.0
    avg_sentence_length_std: float = 0.0
    avg_sentence_length_min: float = 0.0
    avg_sentence_length_max: float = 0.0

    # Paragraph statistics
    avg_paragraph_length_mean: float = 0.0
    avg_paragraph_length_std: float = 0.0

    # Dialogue statistics
    dialogue_ratio_mean: float = 0.0
    dialogue_ratio_std: float = 0.0

    # Complexity statistics
    passive_voice_ratio_mean: float = 0.0
    complex_sentence_ratio_mean: float = 0.0
    avg_clause_count_mean: float = 0.0

    # Word statistics
    avg_word_count: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "age_bucket": self.age_bucket,
            "genre": self.genre,
            "text_count": self.text_count,
            "sentence_length": {
                "mean": round(self.avg_sentence_length_mean, 2),
                "std": round(self.avg_sentence_length_std, 2),
                "min": round(self.avg_sentence_length_min, 2),
                "max": round(self.avg_sentence_length_max, 2),
            },
            "paragraph_length": {
                "mean": round(self.avg_paragraph_length_mean, 2),
                "std": round(self.avg_paragraph_length_std, 2),
            },
            "dialogue_ratio": {
                "mean": round(self.dialogue_ratio_mean, 3),
                "std": round(self.dialogue_ratio_std, 3),
            },
            "complexity": {
                "passive_voice_ratio": round(self.passive_voice_ratio_mean, 3),
                "complex_sentence_ratio": round(self.complex_sentence_ratio_mean, 3),
                "avg_clause_count": round(self.avg_clause_count_mean, 2),
            },
            "word_count": {
                "mean": round(self.avg_word_count, 0),
            },
        }


class CorpusAnalyzer:
    """
    Analyzes a corpus of texts to extract statistical distributions.

    Used to derive empirical rules for story generation based on
    actual children's literature patterns.
    """

    AGE_BUCKETS = ["6-8", "8-10", "10-12", "12-14"]
    GENRES = ["realistic_fiction", "fantasy", "mystery", "informational_fiction"]

    def __init__(self):
        self.texts: list[CorpusText] = []
        self.metrics_extractor = TextMetricsExtractor()
        self._statistics_cache: dict[str, BucketStatistics] = {}

    def add_text(
        self,
        text_id: str,
        title: str,
        content: str,
        source: str,
        age_bucket: str,
        genre: str,
    ) -> CorpusText:
        """
        Add a text to the corpus and compute its metrics.

        Args:
            text_id: Unique identifier
            title: Text title
            content: Full text content
            source: Source attribution
            age_bucket: Target age group ("6-8", "8-10", etc.)
            genre: Genre classification

        Returns:
            CorpusText with computed metrics
        """
        if age_bucket not in self.AGE_BUCKETS:
            raise ValueError(f"Invalid age_bucket: {age_bucket}")
        if genre not in self.GENRES:
            raise ValueError(f"Invalid genre: {genre}")

        # Compute metrics
        metrics = self.metrics_extractor.extract(content)

        corpus_text = CorpusText(
            id=text_id,
            title=title,
            source=source,
            age_bucket=age_bucket,
            genre=genre,
            word_count=metrics.total_words,
            metrics=metrics.to_dict(),
        )

        self.texts.append(corpus_text)
        self._statistics_cache.clear()  # Invalidate cache

        return corpus_text

    def get_texts_for_bucket(
        self,
        age_bucket: str | None = None,
        genre: str | None = None,
    ) -> list[CorpusText]:
        """Get texts matching the specified bucket criteria."""
        result = self.texts

        if age_bucket:
            result = [t for t in result if t.age_bucket == age_bucket]
        if genre:
            result = [t for t in result if t.genre == genre]

        return result

    def compute_bucket_statistics(
        self,
        age_bucket: str,
        genre: str,
    ) -> BucketStatistics:
        """
        Compute aggregated statistics for a specific age/genre bucket.

        Returns:
            BucketStatistics with means and standard deviations
        """
        cache_key = f"{age_bucket}:{genre}"
        if cache_key in self._statistics_cache:
            return self._statistics_cache[cache_key]

        texts = self.get_texts_for_bucket(age_bucket, genre)

        if not texts:
            return BucketStatistics(age_bucket=age_bucket, genre=genre)

        # Collect metrics from all texts
        sentence_lengths = []
        dialogue_ratios = []
        passive_ratios = []
        complex_ratios = []
        clause_counts = []
        word_counts = []

        for text in texts:
            m = text.metrics
            if m.get("avg_sentence_length"):
                sentence_lengths.append(m["avg_sentence_length"])
            if "dialogue_ratio" in m:
                dialogue_ratios.append(m["dialogue_ratio"])
            if "passive_voice_ratio" in m:
                passive_ratios.append(m["passive_voice_ratio"])
            if "complex_sentence_ratio" in m:
                complex_ratios.append(m["complex_sentence_ratio"])
            if "avg_clause_count" in m:
                clause_counts.append(m["avg_clause_count"])
            word_counts.append(text.word_count)

        stats = BucketStatistics(
            age_bucket=age_bucket,
            genre=genre,
            text_count=len(texts),
        )

        # Compute statistics
        if sentence_lengths:
            stats.avg_sentence_length_mean = statistics.mean(sentence_lengths)
            stats.avg_sentence_length_min = min(sentence_lengths)
            stats.avg_sentence_length_max = max(sentence_lengths)
            if len(sentence_lengths) > 1:
                stats.avg_sentence_length_std = statistics.stdev(sentence_lengths)

        if dialogue_ratios:
            stats.dialogue_ratio_mean = statistics.mean(dialogue_ratios)
            if len(dialogue_ratios) > 1:
                stats.dialogue_ratio_std = statistics.stdev(dialogue_ratios)

        if passive_ratios:
            stats.passive_voice_ratio_mean = statistics.mean(passive_ratios)

        if complex_ratios:
            stats.complex_sentence_ratio_mean = statistics.mean(complex_ratios)

        if clause_counts:
            stats.avg_clause_count_mean = statistics.mean(clause_counts)

        if word_counts:
            stats.avg_word_count = statistics.mean(word_counts)

        self._statistics_cache[cache_key] = stats
        return stats

    def compute_all_statistics(self) -> dict[str, BucketStatistics]:
        """Compute statistics for all age/genre combinations."""
        results = {}

        for age in self.AGE_BUCKETS:
            for genre in self.GENRES:
                key = f"{age}:{genre}"
                results[key] = self.compute_bucket_statistics(age, genre)

        return results

    def export_corpus_stats(self, output_path: str | Path) -> dict:
        """
        Export corpus statistics to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            The exported statistics dictionary
        """
        all_stats = self.compute_all_statistics()

        output = {
            "$schema": "corpus_stats_schema.json",
            "version": "1.0.0",
            "description": "Aggregated corpus statistics for rule enhancement",
            "total_texts": len(self.texts),
            "buckets": {},
        }

        for key, stats in all_stats.items():
            if stats.text_count > 0:
                output["buckets"][key] = stats.to_dict()

        # Also compute overall statistics by age bucket only
        output["by_age"] = {}
        for age in self.AGE_BUCKETS:
            texts = self.get_texts_for_bucket(age_bucket=age)
            if texts:
                # Aggregate across genres
                all_sentence_lengths = [
                    t.metrics.get("avg_sentence_length", 0)
                    for t in texts
                    if t.metrics.get("avg_sentence_length")
                ]
                all_dialogue_ratios = [
                    t.metrics.get("dialogue_ratio", 0)
                    for t in texts
                    if "dialogue_ratio" in t.metrics
                ]

                output["by_age"][age] = {
                    "text_count": len(texts),
                    "sentence_length_mean": round(
                        statistics.mean(all_sentence_lengths), 2
                    ) if all_sentence_lengths else 0,
                    "dialogue_ratio_mean": round(
                        statistics.mean(all_dialogue_ratios), 3
                    ) if all_dialogue_ratios else 0,
                }

        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        return output

    def load_corpus_stats(self, input_path: str | Path) -> dict:
        """Load corpus statistics from JSON file."""
        with open(input_path) as f:
            return json.load(f)


def get_corpus_analyzer() -> CorpusAnalyzer:
    """Get a corpus analyzer instance."""
    return CorpusAnalyzer()
