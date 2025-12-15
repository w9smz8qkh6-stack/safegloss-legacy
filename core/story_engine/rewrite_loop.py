"""
Rewrite Loop

Implements auto-fix strategies for stories that fail validation.
Iteratively corrects issues until the story passes or max iterations reached.

Strategies:
1. Word count adjustment (trim/expand)
2. Long sentence splitting
3. Passive voice rewriting
4. Vocabulary simplification
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

from .text_metrics import TextMetrics, extract_metrics
from .validator import (
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    StoryValidator,
)
from .rules import get_rules_loader


class FixStrategy(Enum):
    """Available fix strategies."""
    SPLIT_SENTENCES = "split_sentences"
    SIMPLIFY_PASSIVE = "simplify_passive"
    TRIM_CONTENT = "trim_content"
    EXPAND_CONTENT = "expand_content"
    SIMPLIFY_VOCABULARY = "simplify_vocabulary"
    REDUCE_CLAUSES = "reduce_clauses"


@dataclass
class FixAttempt:
    """Record of a single fix attempt."""
    strategy: FixStrategy
    original_value: Any
    new_value: Any
    success: bool
    details: str = ""


@dataclass
class RewriteIteration:
    """Record of a single rewrite iteration."""
    iteration: int
    validation_before: ValidationResult
    fixes_applied: list[FixAttempt] = field(default_factory=list)
    validation_after: ValidationResult | None = None
    text_before: str = ""
    text_after: str = ""


@dataclass
class RewriteResult:
    """Complete result of the rewrite loop."""
    success: bool
    final_text: str
    final_validation: ValidationResult
    iterations: list[RewriteIteration] = field(default_factory=list)
    total_fixes_applied: int = 0
    requires_regeneration: bool = False
    regeneration_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "success": self.success,
            "total_iterations": len(self.iterations),
            "total_fixes_applied": self.total_fixes_applied,
            "requires_regeneration": self.requires_regeneration,
            "regeneration_hints": self.regeneration_hints,
            "final_score": self.final_validation.score,
            "final_valid": self.final_validation.valid,
        }


class SentenceSplitter:
    """Deterministic sentence splitting utility."""

    # Patterns for finding split points in long sentences (order matters - try most specific first)
    SPLIT_PATTERNS = [
        # Split on "because" + clause
        (re.compile(r'\s+because\s+', re.IGNORECASE), '. This was because '),
        # Split on "and he/she/they/it" (new independent clause)
        (re.compile(r'\s+and\s+(he|she|it|they|we)\s+', re.IGNORECASE), r'. \1 '),
        # Split on "but he/she/they/it"
        (re.compile(r'\s+but\s+(he|she|it|they|we)\s+', re.IGNORECASE), r'. But \1 '),
        # Split on "so he/she/they/it"
        (re.compile(r'\s+so\s+(he|she|it|they|we)\s+', re.IGNORECASE), r'. So \1 '),
        # Split on semicolons
        (re.compile(r';\s+'), '. '),
        # Split on ", which" relative clauses
        (re.compile(r',\s+which\s+', re.IGNORECASE), '. It '),
        # Split on ", where" relative clauses
        (re.compile(r',\s+where\s+', re.IGNORECASE), '. There '),
        # Split on ", when"
        (re.compile(r',\s+when\s+', re.IGNORECASE), '. When '),
        # Split on ", after"
        (re.compile(r',\s+after\s+', re.IGNORECASE), '. After '),
        # Split on ", before"
        (re.compile(r',\s+before\s+', re.IGNORECASE), '. Before '),
    ]

    @classmethod
    def split_if_long(cls, sentence: str, max_words: int = 20, _depth: int = 0) -> list[str]:
        """
        Split a sentence if it exceeds max_words.

        Returns list of resulting sentences (may be 1 if no split possible).
        """
        # Prevent infinite recursion
        if _depth > 5:
            return [sentence]

        words = sentence.split()
        if len(words) <= max_words:
            return [sentence]

        original_word_count = len(words)

        # Try each split pattern
        for pattern, replacement in cls.SPLIT_PATTERNS:
            if pattern.search(sentence):
                result = pattern.sub(replacement, sentence, count=1)
                # Check if we successfully created multiple sentences
                parts = cls._split_on_sentence_boundary(result)
                if len(parts) > 1:
                    # Verify we actually made progress (each part is shorter)
                    all_shorter = all(len(p.split()) < original_word_count for p in parts)
                    if not all_shorter:
                        continue  # Try next pattern

                    # Ensure each part has proper punctuation
                    final_parts = []
                    for part in parts:
                        part = part.strip()
                        # Capitalize first letter
                        if part and part[0].islower():
                            part = part[0].upper() + part[1:]
                        # Add period if missing
                        if part and part[-1] not in '.!?':
                            part = part + '.'
                        # Recursively split if still too long (with depth limit)
                        final_parts.extend(cls.split_if_long(part, max_words, _depth + 1))
                    return final_parts

        # If no pattern worked, try splitting at comma near middle
        if ',' in sentence:
            # Find comma in middle third of sentence
            start = len(sentence) // 3
            end = len(sentence) * 2 // 3
            comma_pos = sentence.find(',', start)
            if comma_pos > 0 and comma_pos < end:
                part1 = sentence[:comma_pos].strip()
                part2 = sentence[comma_pos + 1:].strip()

                # Verify both parts are shorter than original
                if len(part1.split()) < original_word_count and len(part2.split()) < original_word_count:
                    # Capitalize second part
                    if part2 and part2[0].islower():
                        part2 = part2[0].upper() + part2[1:]
                    # Add periods
                    if not part1.endswith('.'):
                        part1 += '.'
                    if not part2.endswith('.'):
                        part2 += '.'
                    return [part1, part2]

        return [sentence]

    @classmethod
    def _split_on_sentence_boundary(cls, text: str) -> list[str]:
        """Split text on sentence boundaries."""
        # Split on period/exclamation/question followed by space and capital
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [p.strip() for p in parts if p.strip()]


class PassiveVoiceRewriter:
    """
    Attempts to convert passive voice to active voice.

    This is heuristic-based and handles only simple, unambiguous cases.
    Complex rewrites are left unchanged and flagged for AI assistance.
    """

    # Pattern: "The X was verbed by the Y." -> "The Y verbed the X."
    # Only match very simple structures to avoid mangling complex sentences
    SIMPLE_PATTERN = re.compile(
        r'^(The\s+)?(\w+)\s+was\s+(\w+ed)\s+by\s+(the\s+)?(\w+)([.,!?])$',
        re.IGNORECASE
    )

    @classmethod
    def rewrite_simple(cls, sentence: str) -> tuple[str, bool]:
        """
        Attempt simple passive-to-active conversion.

        Only handles clear "X was verbed by Y" patterns that end the sentence.
        Returns (rewritten_sentence, was_changed).
        Complex cases return the original sentence unchanged.
        """
        stripped = sentence.strip()
        match = cls.SIMPLE_PATTERN.match(stripped)

        if match:
            # Groups: 1="The ", 2=object, 3=verb, 4="the ", 5=subject, 6=punctuation
            article1 = match.group(1) or ""
            obj = match.group(2)
            verb = match.group(3)
            article2 = match.group(4) or ""
            subj = match.group(5)
            punct = match.group(6)

            # Construct: "The subject verbed the object."
            new_article = article2.capitalize() if article2 else ""
            new_subj = subj.capitalize() if not new_article else subj
            new_obj_article = article1.lower().strip() + " " if article1 else ""

            result = f"{new_article}{new_subj} {verb} {new_obj_article}{obj}{punct}"
            result = re.sub(r'\s+', ' ', result).strip()

            return result, True

        # Complex passive constructions are not rewritten deterministically
        return sentence, False


class RewriteLoop:
    """
    Implements the validation-fix loop for story refinement.

    Process:
    1. Validate story
    2. If invalid, apply deterministic fixes
    3. Re-validate
    4. Repeat up to max_iterations
    5. If still failing, provide regeneration hints
    """

    DEFAULT_MAX_ITERATIONS = 3

    def __init__(
        self,
        validator: StoryValidator | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ):
        self.validator = validator or StoryValidator()
        self.max_iterations = max_iterations
        self.rules = get_rules_loader()

    def process(
        self,
        text: str,
        lexile_band: str,
        target_word_count: int | None = None,
    ) -> RewriteResult:
        """
        Process a story through the validation-fix loop.

        Args:
            text: The story text to process
            lexile_band: Target Lexile band
            target_word_count: Optional target word count

        Returns:
            RewriteResult with final text and iteration history
        """
        iterations = []
        current_text = text
        total_fixes = 0

        for i in range(self.max_iterations):
            # Validate current text
            validation = self.validator.validate(
                current_text, lexile_band, target_word_count
            )

            iteration = RewriteIteration(
                iteration=i + 1,
                validation_before=validation,
                text_before=current_text,
            )

            # If valid, we're done
            if validation.valid:
                iteration.validation_after = validation
                iteration.text_after = current_text
                iterations.append(iteration)

                return RewriteResult(
                    success=True,
                    final_text=current_text,
                    final_validation=validation,
                    iterations=iterations,
                    total_fixes_applied=total_fixes,
                )

            # Apply fixes
            fixed_text, fixes = self._apply_fixes(
                current_text, validation, lexile_band
            )

            iteration.fixes_applied = fixes
            iteration.text_after = fixed_text
            total_fixes += len([f for f in fixes if f.success])

            # Re-validate after fixes
            validation_after = self.validator.validate(
                fixed_text, lexile_band, target_word_count
            )
            iteration.validation_after = validation_after

            iterations.append(iteration)

            # Update current text for next iteration
            current_text = fixed_text

            # If no successful fixes were applied, stop iterating
            if not any(f.success for f in fixes):
                break

        # Final validation
        final_validation = self.validator.validate(
            current_text, lexile_band, target_word_count
        )

        # Generate regeneration hints if still failing
        requires_regen = not final_validation.valid
        hints = self._generate_regeneration_hints(final_validation) if requires_regen else []

        return RewriteResult(
            success=final_validation.valid,
            final_text=current_text,
            final_validation=final_validation,
            iterations=iterations,
            total_fixes_applied=total_fixes,
            requires_regeneration=requires_regen,
            regeneration_hints=hints,
        )

    def _apply_fixes(
        self,
        text: str,
        validation: ValidationResult,
        lexile_band: str,
    ) -> tuple[str, list[FixAttempt]]:
        """
        Apply deterministic fixes based on validation issues.

        Returns (fixed_text, list_of_fix_attempts).
        """
        fixes = []
        current_text = text

        for issue in validation.issues:
            if issue.severity == ValidationSeverity.INFO:
                continue  # Skip informational issues

            fix_result = self._apply_fix_for_issue(
                current_text, issue, validation.metrics, lexile_band
            )

            if fix_result:
                current_text, attempt = fix_result
                fixes.append(attempt)

        return current_text, fixes

    def _apply_fix_for_issue(
        self,
        text: str,
        issue: ValidationIssue,
        metrics: TextMetrics,
        lexile_band: str,
    ) -> tuple[str, FixAttempt] | None:
        """
        Apply a fix for a specific issue.

        Returns (new_text, fix_attempt) or None if no fix possible.
        """
        code = issue.code

        if code in ["SENTENCE_TOO_LONG", "TOO_MANY_LONG_SENTENCES"]:
            return self._fix_long_sentences(text, metrics, lexile_band)

        elif code == "TOO_MUCH_PASSIVE_VOICE":
            return self._fix_passive_voice(text, metrics)

        elif code in ["TOO_MANY_CLAUSES", "TOO_MANY_COMPLEX_SENTENCES"]:
            return self._fix_complex_sentences(text, metrics, lexile_band)

        elif code == "WORD_COUNT_HIGH":
            return self._fix_word_count_high(text, metrics, issue.expected_range)

        elif code == "WORD_COUNT_LOW":
            # Cannot expand content deterministically
            return None

        return None

    def _fix_long_sentences(
        self,
        text: str,
        metrics: TextMetrics,
        lexile_band: str,
    ) -> tuple[str, FixAttempt] | None:
        """Split long sentences."""
        if not metrics or not metrics.sentences:
            return None

        # Get max sentence length for this band
        try:
            rules = self.rules.get_lexile_rules(lexile_band)
            max_len = rules.get("sentence", {}).get("avg_length", {}).get("max", 15)
            threshold = max_len + 5  # Allow some buffer
        except ValueError:
            threshold = 20

        # Find and split long sentences
        new_sentences = []
        changes_made = 0

        for sent in metrics.sentences:
            if sent.word_count > threshold:
                split = SentenceSplitter.split_if_long(sent.text, threshold)
                if len(split) > 1:
                    new_sentences.extend(split)
                    changes_made += 1
                else:
                    new_sentences.append(sent.text)
            else:
                new_sentences.append(sent.text)

        if changes_made == 0:
            return None

        # Reconstruct text (preserve paragraph structure approximately)
        new_text = ' '.join(new_sentences)

        return new_text, FixAttempt(
            strategy=FixStrategy.SPLIT_SENTENCES,
            original_value=metrics.long_sentence_count,
            new_value=metrics.long_sentence_count - changes_made,
            success=True,
            details=f"Split {changes_made} long sentences",
        )

    def _fix_passive_voice(
        self,
        text: str,
        metrics: TextMetrics,
    ) -> tuple[str, FixAttempt] | None:
        """Attempt to convert passive voice to active."""
        if not metrics or not metrics.sentences:
            return None

        new_sentences = []
        changes_made = 0

        for sent in metrics.sentences:
            if sent.has_passive_voice:
                rewritten, changed = PassiveVoiceRewriter.rewrite_simple(sent.text)
                new_sentences.append(rewritten)
                if changed:
                    changes_made += 1
            else:
                new_sentences.append(sent.text)

        if changes_made == 0:
            return None

        new_text = ' '.join(new_sentences)

        return new_text, FixAttempt(
            strategy=FixStrategy.SIMPLIFY_PASSIVE,
            original_value=metrics.passive_voice_count,
            new_value=metrics.passive_voice_count - changes_made,
            success=True,
            details=f"Rewrote {changes_made} passive constructions",
        )

    def _fix_complex_sentences(
        self,
        text: str,
        metrics: TextMetrics,
        lexile_band: str,
    ) -> tuple[str, FixAttempt] | None:
        """
        Attempt to simplify complex sentences.

        Uses sentence splitting as the primary strategy.
        """
        # For now, delegate to long sentence fixer which will split
        return self._fix_long_sentences(text, metrics, lexile_band)

    def _fix_word_count_high(
        self,
        text: str,
        metrics: TextMetrics,
        expected_range: tuple[int, int] | None,
    ) -> tuple[str, FixAttempt] | None:
        """
        Trim text to meet word count target.

        Strategy: Remove sentences from the end while maintaining coherence.
        """
        if not expected_range or not metrics or not metrics.sentences:
            return None

        target_max = expected_range[1]
        current_count = metrics.total_words

        if current_count <= target_max:
            return None

        # Calculate how many words to remove
        excess = current_count - target_max

        # Try removing sentences from the end (before any closing/moral)
        sentences = [s.text for s in metrics.sentences]

        # Don't remove the last sentence (usually conclusion)
        # Remove from second-to-last backwards
        removed = 0
        words_removed = 0

        # Work backwards but skip the last sentence
        for i in range(len(sentences) - 2, max(0, len(sentences) - 5), -1):
            sent_words = len(sentences[i].split())
            if words_removed < excess and sent_words < excess * 1.5:
                sentences.pop(i)
                words_removed += sent_words
                removed += 1
                if words_removed >= excess:
                    break

        if removed == 0:
            return None

        new_text = ' '.join(sentences)

        return new_text, FixAttempt(
            strategy=FixStrategy.TRIM_CONTENT,
            original_value=current_count,
            new_value=current_count - words_removed,
            success=True,
            details=f"Removed {removed} sentences ({words_removed} words)",
        )

    def _generate_regeneration_hints(
        self,
        validation: ValidationResult,
    ) -> list[str]:
        """
        Generate hints for prompt modification if regeneration is needed.
        """
        hints = []

        for issue in validation.issues:
            if issue.severity != ValidationSeverity.ERROR:
                continue

            code = issue.code

            if code == "SENTENCE_TOO_LONG":
                hints.append(
                    "EMPHASIZE: Write shorter sentences. "
                    f"Target {issue.expected_range[0]}-{issue.expected_range[1]} words per sentence."
                )

            elif code == "SENTENCE_TOO_SHORT":
                hints.append(
                    "EMPHASIZE: Sentences are too short. "
                    f"Target {issue.expected_range[0]}-{issue.expected_range[1]} words per sentence."
                )

            elif code == "TOO_MUCH_PASSIVE_VOICE":
                hints.append(
                    "STRICT REQUIREMENT: Use only active voice. "
                    "Every sentence should have a clear subject performing the action."
                )

            elif code == "TOO_MANY_CLAUSES":
                hints.append(
                    "STRICT REQUIREMENT: Use simple sentences only. "
                    "Avoid 'because', 'although', 'which', 'when', 'while'."
                )

            elif code == "WORD_COUNT_LOW":
                hints.append(
                    f"EMPHASIZE: Story is too short. "
                    f"Expand to at least {issue.expected_range[0]} words."
                )

            elif code == "WORD_COUNT_HIGH":
                hints.append(
                    f"EMPHASIZE: Story is too long. "
                    f"Keep under {issue.expected_range[1]} words."
                )

        return hints


def process_story(
    text: str,
    lexile_band: str,
    target_word_count: int | None = None,
    max_iterations: int = 3,
) -> RewriteResult:
    """
    Convenience function to process a story through the rewrite loop.

    Args:
        text: The story text to process
        lexile_band: Target Lexile band
        target_word_count: Optional target word count
        max_iterations: Maximum fix iterations

    Returns:
        RewriteResult with final text and iteration history
    """
    loop = RewriteLoop(max_iterations=max_iterations)
    return loop.process(text, lexile_band, target_word_count)
