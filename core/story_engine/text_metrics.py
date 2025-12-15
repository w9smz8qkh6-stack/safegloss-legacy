"""
Text Metrics Extraction

Implements text analyzers for Lexile proxy compliance validation:
- Sentence segmentation
- Word count
- Average sentence length + variance
- Long sentence detection
- Dialogue ratio (quote-based heuristics)
- Passive voice heuristic detection
- Clause complexity heuristic
"""

import re
import statistics
from dataclasses import dataclass, field


@dataclass
class SentenceMetrics:
    """Metrics for a single sentence."""
    text: str
    word_count: int
    clause_count: int
    is_dialogue: bool
    has_passive_voice: bool
    is_complex: bool


@dataclass
class TextMetrics:
    """Complete metrics for a text sample."""
    # Basic counts
    total_words: int = 0
    total_sentences: int = 0
    total_paragraphs: int = 0

    # Sentence length metrics
    avg_sentence_length: float = 0.0
    sentence_length_variance: float = 0.0
    sentence_length_std_dev: float = 0.0
    min_sentence_length: int = 0
    max_sentence_length: int = 0

    # Long sentence detection
    long_sentence_count: int = 0
    long_sentence_threshold: int = 20  # configurable
    long_sentence_ratio: float = 0.0

    # Dialogue metrics
    dialogue_sentence_count: int = 0
    dialogue_ratio: float = 0.0

    # Passive voice metrics
    passive_voice_count: int = 0
    passive_voice_ratio: float = 0.0

    # Clause complexity
    avg_clause_count: float = 0.0
    complex_sentence_count: int = 0
    complex_sentence_ratio: float = 0.0

    # Individual sentence data
    sentences: list[SentenceMetrics] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding individual sentences for brevity)."""
        return {
            "total_words": self.total_words,
            "total_sentences": self.total_sentences,
            "total_paragraphs": self.total_paragraphs,
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "sentence_length_variance": round(self.sentence_length_variance, 2),
            "sentence_length_std_dev": round(self.sentence_length_std_dev, 2),
            "min_sentence_length": self.min_sentence_length,
            "max_sentence_length": self.max_sentence_length,
            "long_sentence_count": self.long_sentence_count,
            "long_sentence_ratio": round(self.long_sentence_ratio, 3),
            "dialogue_sentence_count": self.dialogue_sentence_count,
            "dialogue_ratio": round(self.dialogue_ratio, 3),
            "passive_voice_count": self.passive_voice_count,
            "passive_voice_ratio": round(self.passive_voice_ratio, 3),
            "avg_clause_count": round(self.avg_clause_count, 2),
            "complex_sentence_count": self.complex_sentence_count,
            "complex_sentence_ratio": round(self.complex_sentence_ratio, 3),
        }


class TextMetricsExtractor:
    """
    Extracts linguistic metrics from text for Lexile proxy validation.

    Provides heuristic-based analysis suitable for leveled reading validation.
    """

    # Sentence-ending punctuation (accounts for dialogue)
    SENTENCE_ENDINGS = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z"])|'  # Standard sentence break
        r'(?<=[.!?])"?\s+(?=[A-Z])|'  # After closing quote
        r'(?<=[.!?])"\s*$'  # End of text with quote
    )

    # Simple sentence splitter (handles common cases)
    SENTENCE_SPLIT = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z"])|(?<=[.!?]")(?=\s+[A-Z])'
    )

    # Dialogue detection (text within quotes)
    DIALOGUE_PATTERN = re.compile(r'["""\'].*?["""\']')

    # Passive voice indicators (common patterns)
    PASSIVE_PATTERNS = [
        re.compile(r'\b(was|were|is|are|been|being)\s+\w+ed\b', re.IGNORECASE),
        re.compile(r'\b(was|were|is|are|been|being)\s+\w+en\b', re.IGNORECASE),
        re.compile(r'\b(got|get|gets|getting)\s+\w+ed\b', re.IGNORECASE),
    ]

    # Clause indicators
    CLAUSE_MARKERS = [
        "who", "whom", "whose", "which", "that",  # Relative
        "because", "since", "although", "though", "while",  # Subordinating
        "if", "unless", "when", "whenever", "where", "whereas",
        "before", "after", "until", "as", "even though",
    ]

    # Coordinating conjunctions (for compound sentences)
    COORD_CONJUNCTIONS = ["and", "but", "or", "nor", "for", "yet", "so"]

    def __init__(self, long_sentence_threshold: int = 20):
        """
        Initialize the extractor.

        Args:
            long_sentence_threshold: Word count above which sentences are "long"
        """
        self.long_sentence_threshold = long_sentence_threshold

    def extract(self, text: str) -> TextMetrics:
        """
        Extract all metrics from a text sample.

        Args:
            text: The text to analyze

        Returns:
            TextMetrics with all computed values
        """
        metrics = TextMetrics(long_sentence_threshold=self.long_sentence_threshold)

        if not text or not text.strip():
            return metrics

        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        metrics.total_paragraphs = len(paragraphs) if paragraphs else 1

        # Segment sentences
        sentences = self._segment_sentences(text)
        metrics.total_sentences = len(sentences)

        if not sentences:
            return metrics

        # Analyze each sentence
        sentence_lengths = []
        clause_counts = []

        for sentence_text in sentences:
            sentence_metrics = self._analyze_sentence(sentence_text)
            metrics.sentences.append(sentence_metrics)

            sentence_lengths.append(sentence_metrics.word_count)
            clause_counts.append(sentence_metrics.clause_count)

            if sentence_metrics.is_dialogue:
                metrics.dialogue_sentence_count += 1
            if sentence_metrics.has_passive_voice:
                metrics.passive_voice_count += 1
            if sentence_metrics.is_complex:
                metrics.complex_sentence_count += 1
            if sentence_metrics.word_count > self.long_sentence_threshold:
                metrics.long_sentence_count += 1

        # Compute aggregate metrics
        metrics.total_words = sum(sentence_lengths)
        metrics.avg_sentence_length = statistics.mean(sentence_lengths)
        metrics.min_sentence_length = min(sentence_lengths)
        metrics.max_sentence_length = max(sentence_lengths)

        if len(sentence_lengths) > 1:
            metrics.sentence_length_variance = statistics.variance(sentence_lengths)
            metrics.sentence_length_std_dev = statistics.stdev(sentence_lengths)

        metrics.avg_clause_count = statistics.mean(clause_counts)

        # Compute ratios
        n = metrics.total_sentences
        metrics.long_sentence_ratio = metrics.long_sentence_count / n
        metrics.dialogue_ratio = metrics.dialogue_sentence_count / n
        metrics.passive_voice_ratio = metrics.passive_voice_count / n
        metrics.complex_sentence_ratio = metrics.complex_sentence_count / n

        return metrics

    def _segment_sentences(self, text: str) -> list[str]:
        """
        Segment text into sentences.

        Handles:
        - Standard punctuation
        - Dialogue with embedded punctuation
        - Abbreviations (basic handling)
        """
        # Normalize whitespace
        text = ' '.join(text.split())

        # Protect common abbreviations
        protected = text
        abbrevs = ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Jr.', 'Sr.',
                   'Inc.', 'Ltd.', 'vs.', 'etc.', 'e.g.', 'i.e.']
        for abbrev in abbrevs:
            protected = protected.replace(abbrev, abbrev.replace('.', '<DOT>'))

        # Split on sentence boundaries
        # Use a more robust approach: split on .!? followed by space and capital
        sentences = []
        current = []
        words = protected.split()

        for i, word in enumerate(words):
            current.append(word)

            # Check if this word ends a sentence
            if self._is_sentence_end(word, words, i):
                sentence = ' '.join(current).replace('<DOT>', '.')
                if sentence.strip():
                    sentences.append(sentence.strip())
                current = []

        # Don't forget the last sentence if it doesn't end with punctuation
        if current:
            sentence = ' '.join(current).replace('<DOT>', '.')
            if sentence.strip():
                sentences.append(sentence.strip())

        return sentences

    def _is_sentence_end(self, word: str, words: list[str], index: int) -> bool:
        """Check if a word marks the end of a sentence."""
        if not word:
            return False

        # Check for sentence-ending punctuation
        ends_with_punct = word.rstrip('"\'""').endswith(('.', '!', '?'))
        if not ends_with_punct:
            return False

        # If it's the last word, it's a sentence end
        if index >= len(words) - 1:
            return True

        # Check if next word starts with capital (new sentence)
        next_word = words[index + 1].lstrip('"\'""')
        if next_word and next_word[0].isupper():
            return True

        # Check if next word starts with opening quote + capital
        if next_word.startswith(('"', '"', "'")):
            inner = next_word.lstrip('"\'""')
            if inner and inner[0].isupper():
                return True

        return False

    def _analyze_sentence(self, sentence: str) -> SentenceMetrics:
        """Analyze a single sentence."""
        # Word count
        words = self._tokenize_words(sentence)
        word_count = len(words)

        # Check for dialogue
        is_dialogue = self._has_dialogue(sentence)

        # Check for passive voice
        has_passive = self._has_passive_voice(sentence)

        # Count clauses
        clause_count = self._count_clauses(sentence)

        # Determine complexity (more than 1 clause = complex)
        is_complex = clause_count > 1

        return SentenceMetrics(
            text=sentence,
            word_count=word_count,
            clause_count=clause_count,
            is_dialogue=is_dialogue,
            has_passive_voice=has_passive,
            is_complex=is_complex
        )

    def _tokenize_words(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Remove punctuation for word counting
        cleaned = re.sub(r'[^\w\s\'-]', ' ', text)
        words = [w for w in cleaned.split() if w and not w.isspace()]
        return words

    def _has_dialogue(self, sentence: str) -> bool:
        """Check if sentence contains dialogue."""
        return bool(self.DIALOGUE_PATTERN.search(sentence))

    def _has_passive_voice(self, sentence: str) -> bool:
        """
        Heuristic passive voice detection.

        Looks for patterns like:
        - "was/were/is/are + past participle"
        - "been/being + past participle"
        - "got/get + past participle"
        """
        for pattern in self.PASSIVE_PATTERNS:
            if pattern.search(sentence):
                return True
        return False

    def _count_clauses(self, sentence: str) -> int:
        """
        Estimate clause count in a sentence.

        Counts:
        - Base clause (1)
        - Additional clauses from subordinating conjunctions
        - Semi-independent clauses from coordinating conjunctions
        """
        clause_count = 1  # Every sentence has at least one clause

        sentence_lower = sentence.lower()
        words = sentence_lower.split()

        # Count subordinating clause markers
        for marker in self.CLAUSE_MARKERS:
            # Match whole words only
            if marker in words:
                clause_count += 1

        # Count coordinating conjunctions that introduce new clauses
        # Only count if followed by subject-verb pattern (simplified)
        for conj in self.COORD_CONJUNCTIONS:
            # Simple heuristic: conjunction at word boundary
            pattern = re.compile(rf'\b{conj}\b', re.IGNORECASE)
            matches = pattern.findall(sentence)
            # Don't count 'and' in lists, only when it might introduce a clause
            if conj == "and":
                # Heuristic: 'and' followed by pronoun or article suggests new clause
                and_clause = re.compile(
                    r'\band\s+(he|she|it|they|we|i|the|a|an)\s+\w+',
                    re.IGNORECASE
                )
                clause_count += len(and_clause.findall(sentence))
            elif conj in ["but", "yet", "so"]:
                clause_count += len(matches)

        return clause_count


def extract_metrics(text: str, long_sentence_threshold: int = 20) -> TextMetrics:
    """
    Convenience function to extract metrics from text.

    Args:
        text: The text to analyze
        long_sentence_threshold: Word count above which sentences are "long"

    Returns:
        TextMetrics with all computed values
    """
    extractor = TextMetricsExtractor(long_sentence_threshold=long_sentence_threshold)
    return extractor.extract(text)
