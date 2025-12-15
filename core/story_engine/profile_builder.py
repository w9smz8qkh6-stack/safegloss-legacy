"""
Writing Profile Builder

Merges rule files into a single normalized "writing profile" per request.
The profile is deterministic and logged for auditability.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any

from .rules import get_rules_loader, RulesLoader
from .guardrails import get_guardrails, ContentGuardrails


@dataclass
class NarrativeRules:
    """Narrative structure rules."""
    max_characters: int = 2
    conflict_count: int = 1
    timeline: str = "linear"
    emotion_expression: str = "explicit"
    inference_level: str = "low"
    moral_clarity: str = "clear"
    flashbacks: bool = False


@dataclass
class StyleRules:
    """Prose style rules."""
    avg_sentence_length_min: int = 10
    avg_sentence_length_max: int = 13
    max_clauses: int = 1
    sentence_types: list[str] = field(default_factory=lambda: ["simple", "compound"])
    dialogue_ratio: str = "medium"
    dialogue_ratio_min: float = 0.20
    dialogue_ratio_max: float = 0.40
    paragraph_length: str = "short"
    sensory_detail: str = "moderate"
    figurative_language: str = "simple"
    pacing: str = "moderate"
    writing_voice: dict = field(default_factory=dict)
    style_avoid: list[str] = field(default_factory=list)


@dataclass
class VocabularyRules:
    """Vocabulary constraint rules."""
    level: str = "mostly_common"
    abstract_nouns: str = "occasional"
    academic_terms: str = "rare"
    frequency_tier: str = "top_3000"
    passive_voice: str = "avoid"


@dataclass
class VocabularyConstraints:
    """
    Vocabulary control settings for glossary-locked stories.

    Modes:
    - "none": No vocabulary restrictions
    - "prefer": Prefer allowed words but permit others within frequency tier
    - "strict": Only use allowed words (with stretch word allowance)
    """
    mode: str = "none"  # none, prefer, strict
    allowed_words: list[str] = field(default_factory=list)
    restricted_words: list[str] = field(default_factory=list)
    max_stretch_words: int = 5  # Words outside allowed list (strict mode)
    stretch_words_require_definition: bool = True
    frequency_threshold: str = "top_3000"  # For "prefer" mode fallback


@dataclass
class GenreRules:
    """Genre-specific rules."""
    genre: str = "realistic_fiction"
    setting: str = "grounded"
    requirements: dict = field(default_factory=dict)
    guidance: list[str] = field(default_factory=list)


@dataclass
class WritingProfile:
    """
    Complete writing profile assembled from rule files.

    This object is passed to the Prompt Composer to generate
    the final AI prompt.
    """
    # Input parameters (for logging)
    age_band: str
    genre: str
    lexile_band: str
    style_profile: str | None = None
    ell_mode: str | None = None
    study_mode: bool = False

    # Merged rules
    narrative: NarrativeRules = field(default_factory=NarrativeRules)
    style: StyleRules = field(default_factory=StyleRules)
    vocabulary: VocabularyRules = field(default_factory=VocabularyRules)
    genre_rules: GenreRules = field(default_factory=GenreRules)

    # Vocabulary constraints (glossary-locked mode)
    vocab_constraints: VocabularyConstraints = field(default_factory=VocabularyConstraints)

    # Legacy fields (for backwards compatibility)
    allowed_vocabulary: list[str] = field(default_factory=list)
    restricted_vocabulary: list[str] = field(default_factory=list)

    # Assembled guidance (human-readable rules)
    guidance: list[str] = field(default_factory=list)

    # Audit fields
    profile_hash: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """Convert profile to dictionary for logging/serialization."""
        return asdict(self)

    def compute_hash(self) -> str:
        """Compute a deterministic hash of the profile for auditability."""
        # Exclude the hash itself from computation
        data = self.to_dict()
        data.pop("profile_hash", None)
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class WritingProfileBuilder:
    """
    Builds a WritingProfile by merging rules from multiple sources.

    Merge order:
    1. Age rules (base developmental constraints)
    2. Genre rules (narrative/structural requirements)
    3. Lexile rules (linguistic constraints)
    4. Style profile (optional overlay)
    5. ELL rules (optional overlay)
    6. Vocabulary constraints (allowed/restricted lists)
    """

    def __init__(
        self,
        rules_loader: RulesLoader | None = None,
        guardrails: ContentGuardrails | None = None
    ):
        self.rules = rules_loader or get_rules_loader()
        self.guardrails = guardrails or get_guardrails()

    def build(
        self,
        age_band: str,
        genre: str,
        lexile_band: str,
        style_profile: str | None = None,
        ell_mode: str | None = None,
        study_mode: bool = False,
        allowed_vocabulary: list[str] | None = None,
        restricted_vocabulary: list[str] | None = None,
        vocabulary_mode: str = "none",
        max_stretch_words: int = 5,
        theme: str | None = None,
    ) -> WritingProfile:
        """
        Build a complete writing profile.

        Args:
            age_band: Target age band (e.g., "8-10")
            genre: Story genre (e.g., "fantasy")
            lexile_band: Target Lexile band (e.g., "500-600L")
            style_profile: Optional style overlay (e.g., "cinematic")
            ell_mode: Optional ELL level (e.g., "intermediate")
            study_mode: If True, include inline definitions
            allowed_vocabulary: Glossary-locked vocabulary list
            restricted_vocabulary: Words to avoid
            vocabulary_mode: "none", "prefer", or "strict"
            max_stretch_words: Max words outside allowed list (strict mode)
            theme: Story theme (for guardrail checking)

        Returns:
            Complete WritingProfile ready for prompt composition
        """
        # Check guardrails first
        check = self.guardrails.check_request(
            theme=theme,
            age_band=age_band,
        )
        if not check.allowed:
            raise ValueError(f"Request blocked by guardrails: {check.violations}")

        # Determine vocabulary mode automatically if vocabulary is provided
        effective_vocab_mode = vocabulary_mode
        if effective_vocab_mode == "none" and allowed_vocabulary:
            effective_vocab_mode = "prefer"  # Auto-enable prefer mode

        # Build vocabulary constraints
        vocab_constraints = VocabularyConstraints(
            mode=effective_vocab_mode,
            allowed_words=allowed_vocabulary or [],
            restricted_words=restricted_vocabulary or [],
            max_stretch_words=max_stretch_words,
            stretch_words_require_definition=study_mode,
            frequency_threshold=self._get_frequency_threshold(lexile_band),
        )

        # Start with base profile
        profile = WritingProfile(
            age_band=age_band,
            genre=genre,
            lexile_band=lexile_band,
            style_profile=style_profile,
            ell_mode=ell_mode,
            study_mode=study_mode,
            vocab_constraints=vocab_constraints,
            # Legacy fields for backwards compatibility
            allowed_vocabulary=allowed_vocabulary or [],
            restricted_vocabulary=restricted_vocabulary or [],
        )

        # Layer 1: Age rules
        self._apply_age_rules(profile)

        # Layer 2: Genre rules
        self._apply_genre_rules(profile)

        # Layer 3: Lexile rules
        self._apply_lexile_rules(profile)

        # Layer 4: Style profile (optional)
        if style_profile:
            self._apply_style_profile(profile)

        # Layer 5: ELL rules (optional)
        if ell_mode:
            self._apply_ell_rules(profile)

        # Compute audit hash
        profile.profile_hash = profile.compute_hash()

        return profile

    def _apply_age_rules(self, profile: WritingProfile) -> None:
        """Apply age-based developmental rules."""
        age_rules = self.rules.get_age_rules(profile.age_band)

        # Apply narrative rules
        narrative = age_rules.get("narrative", {})
        profile.narrative.max_characters = narrative.get("max_characters", 2)
        profile.narrative.conflict_count = narrative.get("conflict_count", 1)
        profile.narrative.timeline = narrative.get("timeline", "linear")
        profile.narrative.emotion_expression = narrative.get("emotion_expression", "explicit")
        profile.narrative.inference_level = narrative.get("inference_level", "low")
        profile.narrative.moral_clarity = narrative.get("moral_clarity", "clear")
        profile.narrative.flashbacks = narrative.get("flashbacks", False)

        # Add guidance
        guidance = age_rules.get("guidance", [])
        profile.guidance.extend(guidance)

    def _apply_genre_rules(self, profile: WritingProfile) -> None:
        """Apply genre-specific rules."""
        genre_rules = self.rules.get_genre_rules(profile.genre)

        profile.genre_rules.genre = profile.genre
        profile.genre_rules.requirements = genre_rules.get("requirements", {})
        profile.genre_rules.guidance = genre_rules.get("guidance", [])

        # Check for age-specific adjustments
        age_adjustments = genre_rules.get("age_adjustments", {}).get(profile.age_band, {})
        if age_adjustments:
            # Apply any age-specific genre adjustments
            profile.genre_rules.requirements.update(age_adjustments)

        # Add genre guidance
        profile.guidance.extend(genre_rules.get("guidance", []))

    def _apply_lexile_rules(self, profile: WritingProfile) -> None:
        """Apply Lexile linguistic constraints."""
        lexile_rules = self.rules.get_lexile_rules(profile.lexile_band)

        # Apply sentence rules
        sentence = lexile_rules.get("sentence", {})
        avg_length = sentence.get("avg_length", {"min": 10, "max": 13})
        profile.style.avg_sentence_length_min = avg_length["min"]
        profile.style.avg_sentence_length_max = avg_length["max"]
        profile.style.max_clauses = sentence.get("max_clauses", 1)
        profile.style.sentence_types = sentence.get("types", ["simple", "compound"])

        # Apply vocabulary rules
        vocab = lexile_rules.get("vocabulary", {})
        profile.vocabulary.level = vocab.get("level", "mostly_common")
        profile.vocabulary.abstract_nouns = vocab.get("abstract_nouns", "occasional")
        profile.vocabulary.academic_terms = vocab.get("academic_terms", "rare")
        profile.vocabulary.frequency_tier = vocab.get("frequency_tier", "top_3000")

        # Apply grammar rules
        grammar = lexile_rules.get("grammar", {})
        profile.vocabulary.passive_voice = grammar.get("passive_voice", "avoid")

        # Add guidance
        profile.guidance.extend(lexile_rules.get("guidance", []))

    def _apply_style_profile(self, profile: WritingProfile) -> None:
        """Apply optional style profile overlay."""
        style = self.rules.get_style_profile(profile.style_profile)

        adjustments = style.get("adjustments", {})

        # Apply sentence length modifier
        modifier = adjustments.get("sentence_length_modifier", 0)
        profile.style.avg_sentence_length_min += modifier
        profile.style.avg_sentence_length_max += modifier

        # Apply dialogue ratio adjustments
        if "dialogue_ratio_target" in adjustments:
            target = adjustments["dialogue_ratio_target"]
            profile.style.dialogue_ratio_min = target.get("min", profile.style.dialogue_ratio_min)
            profile.style.dialogue_ratio_max = target.get("max", profile.style.dialogue_ratio_max)
        elif "dialogue_ratio_modifier" in adjustments:
            # Apply modifier to existing range
            modifier = adjustments["dialogue_ratio_modifier"]
            profile.style.dialogue_ratio_min += modifier
            profile.style.dialogue_ratio_max += modifier
            # Clamp to valid range
            profile.style.dialogue_ratio_min = max(0.05, profile.style.dialogue_ratio_min)
            profile.style.dialogue_ratio_max = min(0.70, profile.style.dialogue_ratio_max)

        # Apply other style adjustments
        if "sensory_detail" in adjustments:
            profile.style.sensory_detail = adjustments["sensory_detail"]
        if "figurative_language" in adjustments:
            profile.style.figurative_language = adjustments["figurative_language"]

        # Apply writing voice settings
        writing_voice = style.get("writing_voice", {})
        if writing_voice:
            profile.style.writing_voice = writing_voice
            if "pacing" in writing_voice:
                profile.style.pacing = writing_voice["pacing"]

        # Apply style-specific avoid list
        avoid_list = style.get("avoid", [])
        if avoid_list:
            profile.style.style_avoid = avoid_list

        # Check for age-specific restrictions
        age_restrictions = style.get("age_restrictions", {}).get(profile.age_band, {})
        if age_restrictions:
            # Add any age-specific guidance
            if "avoid" in age_restrictions:
                for item in age_restrictions["avoid"]:
                    profile.guidance.append(f"Avoid {item}")
            # Add age-appropriate techniques
            if "techniques" in age_restrictions:
                for technique in age_restrictions["techniques"]:
                    profile.guidance.append(f"Use {technique.replace('_', ' ')}")
            if "humor_types" in age_restrictions:
                humor_types = ", ".join(h.replace("_", " ") for h in age_restrictions["humor_types"])
                profile.guidance.append(f"Humor types appropriate for this age: {humor_types}")

        # Add style guidance
        profile.guidance.extend(style.get("guidance", []))

    def _apply_ell_rules(self, profile: WritingProfile) -> None:
        """Apply ELL overlay rules."""
        ell = self.rules.get_ell_rules(profile.ell_mode)

        # Apply vocabulary constraints (more restrictive)
        vocab = ell.get("vocabulary", {})
        if vocab.get("frequency_tier"):
            # Use more restrictive tier
            current_tier = int(profile.vocabulary.frequency_tier.replace("top_", ""))
            ell_tier = int(vocab["frequency_tier"].replace("top_", ""))
            if ell_tier < current_tier:
                profile.vocabulary.frequency_tier = vocab["frequency_tier"]

        # Apply grammar constraints
        grammar = ell.get("grammar", {})
        if grammar.get("avoid_passive"):
            profile.vocabulary.passive_voice = "never"

        # Add ELL-specific guidance
        profile.guidance.extend(ell.get("guidance", []))

        # Add general ELL guidance
        general_guidance = self.rules._cache.get("ell_rules", {}).get("general_ell_guidance", [])
        profile.guidance.extend(general_guidance)

    def _get_frequency_threshold(self, lexile_band: str) -> str:
        """Get vocabulary frequency threshold for a Lexile band."""
        try:
            lexile_rules = self.rules.get_lexile_rules(lexile_band)
            vocab = lexile_rules.get("vocabulary", {})
            return vocab.get("frequency_tier", "top_3000")
        except ValueError:
            return "top_3000"
