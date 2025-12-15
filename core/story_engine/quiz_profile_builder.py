"""
Quiz Profile Builder

Assembles a QuizProfile from quiz rules, age constraints, and alignment sources.
The profile determines question types, Bloom's levels, and pedagogical constraints.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .rules import get_rules_loader, RulesLoader


@dataclass
class QuestionTypeConstraints:
    """Constraints for a specific question type."""
    type_id: str
    label: str
    enabled: bool = True
    min_choices: int = 3
    max_choices: int = 4
    min_correct: int = 1
    max_correct: int = 1
    word_bank_required: bool = False
    max_items: int = 6
    max_words: int = 50


@dataclass
class BloomConstraints:
    """Constraints for Bloom's taxonomy levels."""
    allowed_levels: list[str] = field(default_factory=lambda: ["remember", "understand"])
    target_distribution: dict[str, float] = field(default_factory=dict)
    question_stems: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class CategoryConstraints:
    """Constraints for question categories."""
    allowed_categories: list[str] = field(default_factory=list)
    target_distribution: dict[str, float] = field(default_factory=dict)


@dataclass
class AlignmentSource:
    """Source material for quiz alignment."""
    source_type: str  # "story", "glossary", "lesson"
    source_id: str = ""
    source_title: str = ""
    text_content: str = ""
    glossary_terms: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)


@dataclass
class QuizProfile:
    """
    Complete quiz generation profile.

    Assembled from quiz rules with age/Lexile/mode constraints.
    Passed to the Quiz Prompt Composer for question generation.
    """
    # Input parameters
    age_band: str
    lexile_band: str
    assessment_mode: str = "study_mode"  # study_mode or exam_mode
    question_count: int = 5

    # Alignment sources
    story_source: AlignmentSource | None = None
    glossary_source: AlignmentSource | None = None

    # Question type constraints
    allowed_question_types: list[str] = field(default_factory=list)
    question_type_constraints: dict[str, QuestionTypeConstraints] = field(default_factory=dict)

    # Bloom's taxonomy constraints
    bloom_constraints: BloomConstraints = field(default_factory=BloomConstraints)

    # Category constraints
    category_constraints: CategoryConstraints = field(default_factory=CategoryConstraints)

    # General constraints
    max_questions: int = 10
    question_max_words: int = 20
    avoid_negatives: bool = True
    include_hints: bool = True
    include_explanations: bool = True

    # Assessment mode features
    show_answers_immediately: bool = True
    allow_retries: bool = True
    show_text_references: bool = True

    # Assembled guidance
    guidance: list[str] = field(default_factory=list)

    # Audit fields
    profile_hash: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """Convert profile to dictionary for serialization."""
        d = asdict(self)
        # Convert nested dataclasses
        if self.story_source:
            d["story_source"] = asdict(self.story_source)
        if self.glossary_source:
            d["glossary_source"] = asdict(self.glossary_source)
        return d

    def compute_hash(self) -> str:
        """Compute deterministic hash for auditability."""
        data = self.to_dict()
        data.pop("profile_hash", None)
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class QuizRulesLoader:
    """Loads and provides access to quiz rules."""

    def __init__(self, rules_dir: str | Path | None = None):
        if rules_dir is None:
            # Default to rules/ directory relative to project root
            rules_dir = Path(__file__).parent.parent.parent / "rules"
        self.rules_dir = Path(rules_dir)
        self._cache: dict[str, Any] = {}

    def _load_json(self, filename: str) -> dict:
        """Load and cache a JSON file."""
        if filename not in self._cache:
            path = self.rules_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Quiz rules file not found: {path}")
            with open(path) as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    def get_quiz_rules(self) -> dict:
        """Get all quiz rules."""
        return self._load_json("quiz_rules.json")

    def get_question_types(self) -> dict:
        """Get question type definitions."""
        rules = self.get_quiz_rules()
        return rules.get("question_types", {})

    def get_bloom_taxonomy(self) -> dict:
        """Get Bloom's taxonomy definitions."""
        rules = self.get_quiz_rules()
        return rules.get("bloom_taxonomy", {})

    def get_question_categories(self) -> dict:
        """Get question category definitions."""
        rules = self.get_quiz_rules()
        return rules.get("question_categories", {})

    def get_age_band_rules(self, age_band: str) -> dict:
        """Get quiz rules for a specific age band."""
        rules = self.get_quiz_rules()
        age_rules = rules.get("age_band_rules", {})
        if age_band not in age_rules:
            raise ValueError(f"Unknown age band: {age_band}")
        return age_rules[age_band]

    def get_assessment_mode(self, mode: str) -> dict:
        """Get assessment mode configuration."""
        rules = self.get_quiz_rules()
        modes = rules.get("assessment_modes", {})
        if mode not in modes:
            raise ValueError(f"Unknown assessment mode: {mode}")
        return modes[mode]

    def get_alignment_rules(self) -> dict:
        """Get alignment rules for story/glossary integration."""
        rules = self.get_quiz_rules()
        return rules.get("alignment_rules", {})


# Global quiz rules loader
_quiz_rules_loader: QuizRulesLoader | None = None


def get_quiz_rules_loader() -> QuizRulesLoader:
    """Get the global quiz rules loader instance."""
    global _quiz_rules_loader
    if _quiz_rules_loader is None:
        _quiz_rules_loader = QuizRulesLoader()
    return _quiz_rules_loader


class QuizProfileBuilder:
    """
    Builds a QuizProfile from quiz rules and alignment sources.

    The profile constrains:
    - Which question types can be generated
    - Which Bloom's taxonomy levels are appropriate
    - Question category distribution
    - Assessment mode features
    """

    def __init__(self, rules_loader: QuizRulesLoader | None = None):
        self.rules = rules_loader or get_quiz_rules_loader()

    def build(
        self,
        age_band: str,
        lexile_band: str,
        question_count: int = 5,
        assessment_mode: str = "study_mode",
        story_id: str | None = None,
        story_text: str | None = None,
        story_title: str | None = None,
        story_segments: list[dict] | None = None,
        glossary_terms: list[dict] | None = None,
        requested_types: list[str] | None = None,
        requested_categories: list[str] | None = None,
        requested_bloom_levels: list[str] | None = None,
    ) -> QuizProfile:
        """
        Build a complete quiz profile.

        Args:
            age_band: Target age band (e.g., "8-10")
            lexile_band: Target Lexile band (e.g., "500-600L")
            question_count: Number of questions to generate
            assessment_mode: "study_mode" or "exam_mode"
            story_id: ID of source story for alignment
            story_text: Full text of source story
            story_title: Title of source story
            story_segments: Story segments with IDs
            glossary_terms: List of glossary term dicts with id, term, definition
            requested_types: Specific question types to include
            requested_categories: Specific categories to focus on
            requested_bloom_levels: Specific Bloom's levels to target

        Returns:
            QuizProfile ready for prompt composition
        """
        # Get age band rules
        age_rules = self.rules.get_age_band_rules(age_band)

        # Get assessment mode config
        mode_config = self.rules.get_assessment_mode(assessment_mode)

        # Build base profile
        profile = QuizProfile(
            age_band=age_band,
            lexile_band=lexile_band,
            assessment_mode=assessment_mode,
            question_count=min(question_count, age_rules["constraints"]["max_questions_per_quiz"]),
        )

        # Build alignment sources
        if story_text or story_id:
            profile.story_source = AlignmentSource(
                source_type="story",
                source_id=story_id or "",
                source_title=story_title or "",
                text_content=story_text or "",
                segments=story_segments or [],
            )

        if glossary_terms:
            profile.glossary_source = AlignmentSource(
                source_type="glossary",
                glossary_terms=glossary_terms,
            )

        # Apply age band constraints
        self._apply_age_constraints(profile, age_rules, requested_types, requested_categories, requested_bloom_levels)

        # Apply assessment mode features
        self._apply_assessment_mode(profile, mode_config)

        # Build question type constraints
        self._build_question_type_constraints(profile, age_rules)

        # Build Bloom's constraints
        self._build_bloom_constraints(profile, age_rules, requested_bloom_levels)

        # Build category constraints
        self._build_category_constraints(profile, age_rules, requested_categories)

        # Compute audit hash
        profile.profile_hash = profile.compute_hash()

        return profile

    def _apply_age_constraints(
        self,
        profile: QuizProfile,
        age_rules: dict,
        requested_types: list[str] | None,
        requested_categories: list[str] | None,
        requested_bloom_levels: list[str] | None,
    ) -> None:
        """Apply age-band specific constraints."""
        constraints = age_rules.get("constraints", {})

        # Set general constraints
        profile.max_questions = constraints.get("max_questions_per_quiz", 10)
        profile.question_max_words = constraints.get("question_max_words", 20)
        profile.avoid_negatives = constraints.get("avoid_negatives", True)

        # Filter allowed question types
        allowed_types = age_rules.get("allowed_question_types", [])
        if requested_types:
            # Intersect requested with allowed
            profile.allowed_question_types = [t for t in requested_types if t in allowed_types]
        else:
            profile.allowed_question_types = allowed_types

        # Add guidance
        profile.guidance.extend(age_rules.get("guidance", []))

    def _apply_assessment_mode(self, profile: QuizProfile, mode_config: dict) -> None:
        """Apply assessment mode features."""
        features = mode_config.get("features", {})

        profile.show_answers_immediately = features.get("show_answers_immediately", True)
        profile.allow_retries = features.get("allow_retries", True)
        profile.include_explanations = features.get("show_explanations", True)
        profile.show_text_references = features.get("show_text_references", True)

        # Question selection preferences
        selection = mode_config.get("question_selection", {})
        profile.include_hints = selection.get("include_hints", True)

    def _build_question_type_constraints(self, profile: QuizProfile, age_rules: dict) -> None:
        """Build constraints for each allowed question type."""
        question_types = self.rules.get_question_types()
        constraints = age_rules.get("constraints", {})

        for type_id in profile.allowed_question_types:
            type_def = question_types.get(type_id, {})

            type_constraints = QuestionTypeConstraints(
                type_id=type_id,
                label=type_def.get("label", type_id),
                enabled=True,
            )

            # Apply type-specific defaults
            if "min_choices" in type_def:
                type_constraints.min_choices = type_def["min_choices"]
            if "max_choices" in type_def:
                type_constraints.max_choices = type_def["max_choices"]
            if "min_correct" in type_def:
                type_constraints.min_correct = type_def["min_correct"]
            if "max_correct" in type_def:
                type_constraints.max_correct = type_def["max_correct"]
            if "max_words" in type_def:
                type_constraints.max_words = type_def["max_words"]

            # Apply age-band overrides
            if type_id == "mcq_single" or type_id == "mcq_multi":
                type_constraints.max_choices = constraints.get("mcq_choices", 4)
            if type_id == "cloze":
                type_constraints.word_bank_required = constraints.get("cloze_word_bank", False)
            if type_id == "ordering":
                type_constraints.max_items = constraints.get("ordering_max_items", 6)
            if type_id == "short_answer":
                type_constraints.max_words = constraints.get("short_answer_max_words", 50)
            if type_id == "long_answer":
                type_constraints.max_words = constraints.get("long_answer_max_words", 200)

            profile.question_type_constraints[type_id] = type_constraints

    def _build_bloom_constraints(
        self,
        profile: QuizProfile,
        age_rules: dict,
        requested_levels: list[str] | None,
    ) -> None:
        """Build Bloom's taxonomy constraints."""
        bloom_taxonomy = self.rules.get_bloom_taxonomy()

        # Get allowed levels from age rules
        allowed = age_rules.get("allowed_bloom_levels", ["remember", "understand"])
        if requested_levels:
            # Intersect with allowed
            allowed = [l for l in requested_levels if l in allowed]

        # Build question stems for allowed levels
        stems = {}
        for level in allowed:
            level_def = bloom_taxonomy.get(level, {})
            stems[level] = level_def.get("question_stems", [])

        # Calculate target distribution (equal by default)
        distribution = {level: 1.0 / len(allowed) for level in allowed}

        profile.bloom_constraints = BloomConstraints(
            allowed_levels=allowed,
            target_distribution=distribution,
            question_stems=stems,
        )

    def _build_category_constraints(
        self,
        profile: QuizProfile,
        age_rules: dict,
        requested_categories: list[str] | None,
    ) -> None:
        """Build question category constraints."""
        # Get allowed categories from age rules
        allowed = age_rules.get("allowed_categories", [])
        if requested_categories:
            # Intersect with allowed
            allowed = [c for c in requested_categories if c in allowed]

        # Get target distribution from age rules
        distribution = age_rules.get("question_distribution", {})

        # Normalize distribution to allowed categories
        if allowed:
            total = sum(distribution.get(c, 0) for c in allowed)
            if total > 0:
                distribution = {c: distribution.get(c, 0) / total for c in allowed}
            else:
                distribution = {c: 1.0 / len(allowed) for c in allowed}

        profile.category_constraints = CategoryConstraints(
            allowed_categories=allowed,
            target_distribution=distribution,
        )


def build_quiz_profile(
    age_band: str,
    lexile_band: str,
    question_count: int = 5,
    assessment_mode: str = "study_mode",
    story_text: str | None = None,
    glossary_terms: list[dict] | None = None,
    **kwargs,
) -> QuizProfile:
    """
    Convenience function to build a quiz profile.

    Args:
        age_band: Target age band
        lexile_band: Target Lexile band
        question_count: Number of questions
        assessment_mode: "study_mode" or "exam_mode"
        story_text: Source story text for alignment
        glossary_terms: Glossary terms for vocabulary questions
        **kwargs: Additional arguments passed to builder

    Returns:
        QuizProfile ready for prompt composition
    """
    builder = QuizProfileBuilder()
    return builder.build(
        age_band=age_band,
        lexile_band=lexile_band,
        question_count=question_count,
        assessment_mode=assessment_mode,
        story_text=story_text,
        glossary_terms=glossary_terms,
        **kwargs,
    )
