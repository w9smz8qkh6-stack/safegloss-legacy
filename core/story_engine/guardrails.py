"""
Content Guardrails

Enforces safety and legal constraints on story generation requests.
Prevents prohibited content and ensures compliance with guidelines.
"""

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    allowed: bool
    violations: list[str]
    warnings: list[str]


class ContentGuardrails:
    """
    Enforces content safety and legal guardrails.

    Checks:
    - No "write like [living author]" requests
    - No claims of "Lexile certified"
    - Appropriate themes for age bands
    - No prohibited content types
    """

    # Living authors that cannot be imitated
    PROTECTED_AUTHORS = [
        "j.k. rowling",
        "jk rowling",
        "stephen king",
        "rick riordan",
        "jeff kinney",
        "dav pilkey",
        "roald dahl",  # Estate actively enforces
        "dr. seuss",
        "dr seuss",
        "mo willems",
        "kate dicamillo",
        "r.l. stine",
        "rl stine",
    ]

    # Prohibited Lexile-related phrases
    PROHIBITED_LEXILE_PHRASES = [
        "lexile certified",
        "official lexile",
        "lexile score of",
        "lexile rated",
        "lexile level:",
        "certified lexile",
    ]

    # Approved Lexile-related phrases
    APPROVED_LEXILE_PHRASES = [
        "lexile-aligned",
        "lexile aligned",
        "designed for readers around",
        "reading difficulty approximately",
        "approximate lexile band",
    ]

    # Prohibited themes by age band
    AGE_PROHIBITED_THEMES = {
        "6-8": [
            "death of parent",
            "violence",
            "weapons",
            "romantic relationships",
            "divorce",
            "substance abuse",
            "mental illness",
            "abuse",
            "war",
            "terrorism",
        ],
        "8-10": [
            "graphic violence",
            "weapons in detail",
            "romantic relationships",
            "substance abuse",
            "detailed mental illness",
            "abuse",
            "war violence",
        ],
        "10-12": [
            "graphic violence",
            "romantic physical content",
            "substance abuse glorified",
            "detailed abuse",
            "self-harm",
        ],
        "12-14": [
            "graphic violence",
            "explicit content",
            "substance abuse glorified",
            "self-harm glorified",
        ],
    }

    # Always prohibited regardless of age
    ALWAYS_PROHIBITED = [
        "explicit sexual content",
        "graphic gore",
        "torture",
        "hate speech",
        "discrimination",
        "self-harm instructions",
        "suicide methods",
        "illegal activities instructions",
        "real children by name",
        "real schools by name",
    ]

    def __init__(self):
        self._author_pattern = self._build_author_pattern()

    def _build_author_pattern(self) -> re.Pattern:
        """Build regex pattern for detecting author imitation requests."""
        patterns = []
        for author in self.PROTECTED_AUTHORS:
            # Match "write like", "in the style of", "similar to", etc.
            escaped = re.escape(author)
            patterns.append(f"(?:write|writing)\\s+(?:like|as)\\s+{escaped}")
            patterns.append(f"(?:in\\s+the\\s+)?style\\s+of\\s+{escaped}")
            patterns.append(f"similar\\s+to\\s+{escaped}")
            patterns.append(f"imitat(?:e|ing)\\s+{escaped}")
            patterns.append(f"channel(?:ing)?\\s+{escaped}")

        return re.compile("|".join(patterns), re.IGNORECASE)

    def check_request(
        self,
        theme: str | None = None,
        style_request: str | None = None,
        age_band: str | None = None,
        full_prompt: str | None = None,
    ) -> GuardrailResult:
        """
        Check a story generation request against all guardrails.

        Args:
            theme: The requested story theme
            style_request: Any style/author-related request
            age_band: Target age band (e.g., "6-8")
            full_prompt: The complete prompt text to check

        Returns:
            GuardrailResult with allowed status and any violations
        """
        violations = []
        warnings = []

        # Check for author imitation
        if style_request:
            if self._author_pattern.search(style_request):
                violations.append(
                    "Cannot imitate living or estate-protected authors. "
                    "Use style profiles instead (minimalist, cinematic, etc.)"
                )

        if full_prompt:
            if self._author_pattern.search(full_prompt):
                violations.append(
                    "Prompt contains request to imitate protected author"
                )

        # Check for prohibited Lexile phrases
        text_to_check = " ".join(filter(None, [theme, style_request, full_prompt]))
        for phrase in self.PROHIBITED_LEXILE_PHRASES:
            if phrase.lower() in text_to_check.lower():
                violations.append(
                    f"Prohibited phrase '{phrase}' detected. "
                    f"Use 'Lexile-aligned' or 'designed for readers around X-YL' instead."
                )

        # Check for always-prohibited content
        for prohibited in self.ALWAYS_PROHIBITED:
            if prohibited.lower() in text_to_check.lower():
                violations.append(f"Prohibited content type: {prohibited}")

        # Check age-appropriate themes
        if theme and age_band:
            prohibited_for_age = self.AGE_PROHIBITED_THEMES.get(age_band, [])
            theme_lower = theme.lower()
            for prohibited in prohibited_for_age:
                if prohibited.lower() in theme_lower:
                    violations.append(
                        f"Theme '{prohibited}' is not appropriate for age band {age_band}"
                    )

        # Add warnings for borderline content
        if theme:
            theme_lower = theme.lower()
            borderline_themes = ["conflict", "danger", "scary", "dark"]
            for borderline in borderline_themes:
                if borderline in theme_lower and age_band in ["6-8", "8-10"]:
                    warnings.append(
                        f"Theme '{borderline}' may need careful handling for {age_band}"
                    )

        return GuardrailResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )

    def check_output(self, generated_text: str, age_band: str) -> GuardrailResult:
        """
        Check generated story output for prohibited content.

        Args:
            generated_text: The AI-generated story text
            age_band: Target age band

        Returns:
            GuardrailResult with any detected issues
        """
        violations = []
        warnings = []

        text_lower = generated_text.lower()

        # Check for always-prohibited content in output
        for prohibited in self.ALWAYS_PROHIBITED:
            if prohibited.lower() in text_lower:
                violations.append(f"Generated text contains prohibited content: {prohibited}")

        # Check for prohibited Lexile claims in output
        for phrase in self.PROHIBITED_LEXILE_PHRASES:
            if phrase.lower() in text_lower:
                violations.append(f"Generated text contains prohibited Lexile claim: {phrase}")

        # Age-specific checks
        if age_band in ["6-8", "8-10"]:
            # Check for potentially scary words
            scary_words = ["death", "killed", "blood", "scream", "terror"]
            for word in scary_words:
                if word in text_lower:
                    warnings.append(f"Word '{word}' may be intense for {age_band}")

        return GuardrailResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )

    def sanitize_prompt(self, prompt: str) -> str:
        """
        Remove or replace prohibited content from a prompt.

        This is a fallback - ideally check_request should catch issues first.
        """
        result = prompt

        # Remove author imitation requests
        result = self._author_pattern.sub("[REMOVED: author imitation request]", result)

        # Replace prohibited Lexile phrases
        for phrase in self.PROHIBITED_LEXILE_PHRASES:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            result = pattern.sub("Lexile-aligned", result)

        return result


# Singleton instance
_guardrails: ContentGuardrails | None = None


def get_guardrails() -> ContentGuardrails:
    """Get the default guardrails singleton."""
    global _guardrails
    if _guardrails is None:
        _guardrails = ContentGuardrails()
    return _guardrails
