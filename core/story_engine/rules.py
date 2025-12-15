"""
Rules Loader with Schema Validation

Loads and validates rule files from /rules/ directory.
Ensures all required keys exist and values are within allowed ranges.
"""

import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass


# Schema definitions for validation
AGE_BANDS = ["6-8", "8-10", "10-12", "12-14"]
GENRES = ["realistic_fiction", "fantasy", "mystery", "informational_fiction"]
LEXILE_BANDS = ["300-400L", "400-500L", "500-600L", "600-700L", "700-900L", "900-1100L"]
STYLE_PROFILES = ["minimalist", "cinematic", "humorous", "sel_focused", "adventure"]
ELL_LEVELS = ["beginner", "intermediate", "advanced"]

# Enum values for validation
TIMELINE_VALUES = ["linear", "mostly_linear", "flexible"]
EMOTION_EXPRESSION_VALUES = ["explicit", "mixed", "implicit"]
INFERENCE_LEVEL_VALUES = ["none", "low", "moderate", "high"]
MORAL_CLARITY_VALUES = ["stated", "clear", "implied", "implicit"]
VOCABULARY_LEVEL_VALUES = ["very_common", "common", "mostly_common", "mixed", "academic_allowed"]


class RulesValidationError(Exception):
    """Raised when rule validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of rule validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]


class RulesLoader:
    """
    Loads and validates rule files from the rules directory.

    Rule files are cached at startup for performance.
    """

    def __init__(self, rules_dir: str | Path | None = None):
        if rules_dir is None:
            # Default to /rules/ in project root
            self.rules_dir = Path(__file__).parent.parent.parent / "rules"
        else:
            self.rules_dir = Path(rules_dir)

        self._cache: dict[str, dict] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load and validate all rule files."""
        if self._loaded:
            return

        rule_files = [
            ("age_rules", "age_rules.json"),
            ("genre_rules", "genre_rules.json"),
            ("lexile_rules", "lexile_rules.json"),
            ("ell_rules", "ell_rules.json"),
            ("style_profiles", "style_profiles.json"),
        ]

        for key, filename in rule_files:
            filepath = self.rules_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self._cache[key] = data
            else:
                self._cache[key] = {}

        self._loaded = True

        # Validate all loaded rules
        result = self.validate_all()
        if not result.valid:
            raise RulesValidationError(
                f"Rule validation failed: {'; '.join(result.errors)}"
            )

    def get_age_rules(self, age_band: str) -> dict:
        """Get rules for a specific age band."""
        self.load_all()
        rules = self._cache.get("age_rules", {}).get("rules", {})
        if age_band not in rules:
            raise ValueError(f"Unknown age band: {age_band}. Valid bands: {AGE_BANDS}")
        return rules[age_band]

    def get_genre_rules(self, genre: str) -> dict:
        """Get rules for a specific genre."""
        self.load_all()
        rules = self._cache.get("genre_rules", {}).get("rules", {})
        if genre not in rules:
            raise ValueError(f"Unknown genre: {genre}. Valid genres: {GENRES}")
        return rules[genre]

    def get_lexile_rules(self, lexile_band: str) -> dict:
        """Get rules for a specific Lexile band."""
        self.load_all()
        bands = self._cache.get("lexile_rules", {}).get("bands", {})
        if lexile_band not in bands:
            raise ValueError(f"Unknown Lexile band: {lexile_band}. Valid bands: {LEXILE_BANDS}")
        return bands[lexile_band]

    def get_ell_rules(self, level: str) -> dict:
        """Get ELL rules for a specific level."""
        self.load_all()
        levels = self._cache.get("ell_rules", {}).get("levels", {})
        if level not in levels:
            raise ValueError(f"Unknown ELL level: {level}. Valid levels: {ELL_LEVELS}")
        return levels[level]

    def get_style_profile(self, profile: str) -> dict:
        """Get a style profile."""
        self.load_all()
        profiles = self._cache.get("style_profiles", {}).get("profiles", {})
        if profile not in profiles:
            raise ValueError(f"Unknown style profile: {profile}. Valid profiles: {STYLE_PROFILES}")
        return profiles[profile]

    def get_approved_lexile_phrasing(self) -> list[str]:
        """Get approved Lexile-related phrasing."""
        self.load_all()
        return self._cache.get("lexile_rules", {}).get("approved_phrasing", [])

    def get_prohibited_lexile_phrasing(self) -> list[str]:
        """Get prohibited Lexile-related phrasing."""
        self.load_all()
        return self._cache.get("lexile_rules", {}).get("prohibited_phrasing", [])

    def validate_all(self) -> ValidationResult:
        """Validate all loaded rules against schemas."""
        errors = []
        warnings = []

        # Validate age rules
        age_rules = self._cache.get("age_rules", {}).get("rules", {})
        for band in AGE_BANDS:
            if band not in age_rules:
                warnings.append(f"Missing age band: {band}")
            else:
                errs = self._validate_age_band(band, age_rules[band])
                errors.extend(errs)

        # Validate genre rules
        genre_rules = self._cache.get("genre_rules", {}).get("rules", {})
        for genre in GENRES:
            if genre not in genre_rules:
                warnings.append(f"Missing genre: {genre}")
            else:
                errs = self._validate_genre(genre, genre_rules[genre])
                errors.extend(errs)

        # Validate lexile rules
        lexile_bands = self._cache.get("lexile_rules", {}).get("bands", {})
        for band in LEXILE_BANDS:
            if band not in lexile_bands:
                warnings.append(f"Missing Lexile band: {band}")
            else:
                errs = self._validate_lexile_band(band, lexile_bands[band])
                errors.extend(errs)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_age_band(self, band: str, rules: dict) -> list[str]:
        """Validate a single age band's rules."""
        errors = []

        # Check required keys
        required = ["narrative", "cognitive", "guidance"]
        for key in required:
            if key not in rules:
                errors.append(f"Age band {band} missing required key: {key}")

        # Validate narrative rules
        narrative = rules.get("narrative", {})

        if "timeline" in narrative:
            if narrative["timeline"] not in TIMELINE_VALUES:
                errors.append(
                    f"Age band {band}: invalid timeline value '{narrative['timeline']}'. "
                    f"Must be one of {TIMELINE_VALUES}"
                )

        if "emotion_expression" in narrative:
            if narrative["emotion_expression"] not in EMOTION_EXPRESSION_VALUES:
                errors.append(
                    f"Age band {band}: invalid emotion_expression value. "
                    f"Must be one of {EMOTION_EXPRESSION_VALUES}"
                )

        if "inference_level" in narrative:
            if narrative["inference_level"] not in INFERENCE_LEVEL_VALUES:
                errors.append(
                    f"Age band {band}: invalid inference_level value. "
                    f"Must be one of {INFERENCE_LEVEL_VALUES}"
                )

        if "moral_clarity" in narrative:
            if narrative["moral_clarity"] not in MORAL_CLARITY_VALUES:
                errors.append(
                    f"Age band {band}: invalid moral_clarity value. "
                    f"Must be one of {MORAL_CLARITY_VALUES}"
                )

        if "max_characters" in narrative:
            if not isinstance(narrative["max_characters"], int) or narrative["max_characters"] < 1:
                errors.append(f"Age band {band}: max_characters must be a positive integer")

        return errors

    def _validate_genre(self, genre: str, rules: dict) -> list[str]:
        """Validate a single genre's rules."""
        errors = []

        required = ["requirements", "guidance"]
        for key in required:
            if key not in rules:
                errors.append(f"Genre {genre} missing required key: {key}")

        return errors

    def _validate_lexile_band(self, band: str, rules: dict) -> list[str]:
        """Validate a single Lexile band's rules."""
        errors = []

        required = ["sentence", "vocabulary", "grammar", "guidance"]
        for key in required:
            if key not in rules:
                errors.append(f"Lexile band {band} missing required key: {key}")

        # Validate sentence rules
        sentence = rules.get("sentence", {})
        if "avg_length" in sentence:
            avg = sentence["avg_length"]
            if not isinstance(avg, dict) or "min" not in avg or "max" not in avg:
                errors.append(f"Lexile band {band}: avg_length must have min and max")
            elif avg["min"] > avg["max"]:
                errors.append(f"Lexile band {band}: avg_length min cannot exceed max")

        # Validate vocabulary level
        vocab = rules.get("vocabulary", {})
        if "level" in vocab:
            if vocab["level"] not in VOCABULARY_LEVEL_VALUES:
                errors.append(
                    f"Lexile band {band}: invalid vocabulary level. "
                    f"Must be one of {VOCABULARY_LEVEL_VALUES}"
                )

        return errors


# Singleton instance for convenience
_default_loader: RulesLoader | None = None


def get_rules_loader() -> RulesLoader:
    """Get the default rules loader singleton."""
    global _default_loader
    if _default_loader is None:
        _default_loader = RulesLoader()
    return _default_loader
