"""
Prompt Composer

Emits natural-language constraints in the mandatory layered order.
Converts WritingProfile rules into deterministic, auditable prompts.

Prompt ordering (mandatory):
1. Reader & Age Profile
2. Developmental Writing Rules
3. Genre-Specific Rules
4. Lexile & Language Constraints
5. Story-Specific Parameters
6. Output Constraints
"""

from dataclasses import dataclass
from .profile_builder import WritingProfile


@dataclass
class ComposedPrompt:
    """The final composed prompt ready for LLM submission."""
    system_message: str
    user_prompt: str
    profile_hash: str

    def full_prompt(self) -> str:
        """Combine system and user prompts."""
        return f"{self.system_message}\n\n---\n\n{self.user_prompt}"


class PromptComposer:
    """
    Composes deterministic prompts from WritingProfile objects.

    Each rule maps to specific natural-language phrasing.
    Given identical input, prompt text is identical (stable).
    """

    SYSTEM_MESSAGE = """You are an educational content generator specializing in leveled reading texts.
You strictly follow linguistic constraints related to sentence length, syntax complexity, and vocabulary usage.
You create age-appropriate stories that support young readers' development.
Never mention the rules or constraints in your output."""

    def compose(
        self,
        profile: WritingProfile,
        theme: str,
        setting: str | None = None,
        main_character: str | None = None,
        word_count: int = 400,
        tone: str | None = None,
    ) -> ComposedPrompt:
        """
        Compose a complete prompt from a writing profile.

        Args:
            profile: The assembled WritingProfile
            theme: Story theme/topic
            setting: Optional story setting
            main_character: Optional character description
            word_count: Target word count
            tone: Optional tone (adventure, calm, humorous, etc.)

        Returns:
            ComposedPrompt with system message and user prompt
        """
        sections = []

        # Section 1: Reader & Age Profile
        sections.append(self._compose_reader_profile(profile))

        # Section 2: Developmental Writing Rules
        sections.append(self._compose_developmental_rules(profile))

        # Section 3: Genre-Specific Rules
        sections.append(self._compose_genre_rules(profile))

        # Section 4: Lexile & Language Constraints
        sections.append(self._compose_language_constraints(profile))

        # Section 5: Story-Specific Parameters
        sections.append(self._compose_story_parameters(
            profile, theme, setting, main_character, word_count, tone
        ))

        # Section 6: Output Constraints
        sections.append(self._compose_output_constraints(profile))

        user_prompt = "\n\n".join(filter(None, sections))

        return ComposedPrompt(
            system_message=self.SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            profile_hash=profile.profile_hash
        )

    def _compose_reader_profile(self, profile: WritingProfile) -> str:
        """Section 1: Reader & Age Profile."""
        lines = [
            "## READER PROFILE",
            "",
            f"You are writing for readers aged {profile.age_band}.",
            "",
            "These readers are still developing reading comprehension and require writing",
            "that matches their cognitive and emotional stage.",
        ]
        return "\n".join(lines)

    def _compose_developmental_rules(self, profile: WritingProfile) -> str:
        """Section 2: Developmental Writing Rules."""
        lines = ["## DEVELOPMENTAL WRITING RULES", ""]

        narrative = profile.narrative

        # Character rules
        if narrative.max_characters == 1:
            lines.append("- Use only one main character.")
            lines.append("- Do not introduce additional named characters.")
        elif narrative.max_characters == 2:
            lines.append("- Use no more than two main characters.")
            lines.append("- Keep their roles clearly distinct.")
        else:
            lines.append(f"- Limit the story to {narrative.max_characters} main characters.")
            lines.append("- Avoid unnecessary minor characters.")

        # Conflict rules
        if narrative.conflict_count == 1:
            lines.append("- Focus on a single, clear problem or challenge.")
            lines.append("- Do not introduce multiple conflicts.")
        else:
            lines.append(f"- The story may include up to {narrative.conflict_count} related challenges.")
            lines.append("- Ensure all conflicts are resolved clearly.")

        # Timeline rules
        if narrative.timeline == "linear":
            lines.append("- The story must move forward in time without flashbacks.")
            lines.append("- Events should occur in the order they happen.")
        elif narrative.timeline == "mostly_linear":
            lines.append("- The story should be mostly linear in time.")
            lines.append("- Avoid complex time shifts.")
        else:
            lines.append("- Nonlinear storytelling is allowed if it remains clear.")

        # Emotion expression rules
        if narrative.emotion_expression == "explicit":
            lines.append("- Characters' emotions must be named directly.")
            lines.append("- Do not rely on the reader to infer feelings.")
        elif narrative.emotion_expression == "mixed":
            lines.append("- Some emotions may be shown through actions, but key feelings should still be stated.")
        else:
            lines.append("- Emotions may be implied through actions and dialogue.")

        # Inference level rules
        if narrative.inference_level == "none":
            lines.append("- Do not require the reader to infer meaning.")
            lines.append("- Explain all important ideas directly.")
        elif narrative.inference_level == "low":
            lines.append("- Keep inference minimal.")
            lines.append("- Important meanings should be explained.")
        elif narrative.inference_level == "moderate":
            lines.append("- Allow some inference, but ensure understanding by the end.")
        else:
            lines.append("- Readers may infer meaning without explicit explanation.")

        # Moral clarity rules
        if narrative.moral_clarity == "stated":
            lines.append("- State the lesson or moral of the story clearly.")
        elif narrative.moral_clarity == "clear":
            lines.append("- Make the lesson clear through the outcome of the story.")
        elif narrative.moral_clarity == "implied":
            lines.append("- The lesson may be implied but should be understandable.")
        else:
            lines.append("- Do not state the lesson explicitly.")

        # Flashback rules
        if not narrative.flashbacks:
            lines.append("- Do not use flashbacks or references to past events outside the main timeline.")
        elif narrative.flashbacks == "rare":
            lines.append("- Flashbacks should be avoided unless absolutely necessary.")
        else:
            lines.append("- Flashbacks are allowed if clearly signposted.")

        return "\n".join(lines)

    def _compose_genre_rules(self, profile: WritingProfile) -> str:
        """Section 3: Genre-Specific Rules."""
        lines = ["## GENRE RULES", ""]

        genre = profile.genre
        genre_rules = profile.genre_rules

        if genre == "realistic_fiction":
            lines.extend([
                "The story should be set in a realistic, everyday environment.",
                "All events must be believable.",
                "Clear cause-and-effect relationships are required.",
            ])
        elif genre == "fantasy":
            lines.extend([
                "The story may include magical or imaginary elements.",
                "The rules of the world must be explained clearly.",
                "Limit the number of invented terms.",
                "Do not assume prior knowledge of the fantasy setting.",
            ])
        elif genre == "mystery":
            lines.extend([
                "The story must include clear clues.",
                "The solution must be explained step-by-step.",
                "Do not hide essential information from the reader.",
            ])
        elif genre == "informational_fiction":
            lines.extend([
                "All factual information must be accurate.",
                "Each section should focus on one main idea.",
                "Key information should be reinforced through repetition.",
            ])

        # Add any additional genre guidance
        for guidance in genre_rules.guidance:
            if guidance not in lines:
                lines.append(f"- {guidance}")

        return "\n".join(lines)

    def _compose_language_constraints(self, profile: WritingProfile) -> str:
        """Section 4: Lexile & Language Constraints."""
        lines = [
            "## LANGUAGE CONSTRAINTS",
            "",
            f"Target reading band: {profile.lexile_band}",
            "(Achieve this using the linguistic constraints below.)",
            "",
        ]

        style = profile.style
        vocab = profile.vocabulary

        # Sentence length
        lines.append("### Sentence Rules")
        lines.append(f"- Aim for an average sentence length of {style.avg_sentence_length_min} to {style.avg_sentence_length_max} words.")
        lines.append("- Avoid long or complex sentences.")

        # Clause limits
        if style.max_clauses == 0:
            lines.append("- Use only simple sentences.")
            lines.append("- Do not use dependent clauses.")
        elif style.max_clauses == 1:
            lines.append("- Limit sentences to one clause.")
            lines.append("- Avoid nested or layered clauses.")
        else:
            lines.append(f"- Limit sentences to no more than {style.max_clauses} clauses.")

        # Sentence types
        types_str = ", ".join(style.sentence_types)
        lines.append(f"- Prefer {types_str} sentences.")

        lines.append("")
        lines.append("### Vocabulary Rules")

        # Vocabulary level
        if vocab.level == "very_common":
            lines.append("- Use only very common, everyday words.")
            lines.append("- Avoid academic or abstract vocabulary.")
        elif vocab.level == "common":
            lines.append("- Use common spoken English words.")
            lines.append("- Avoid rare or specialized vocabulary.")
        elif vocab.level == "mostly_common":
            lines.append("- Use mostly common words.")
            lines.append("- Introduce new words sparingly and clearly.")
        elif vocab.level == "mixed":
            lines.append("- Some academic words are allowed if clearly supported by context.")
        else:
            lines.append("- Academic vocabulary is allowed.")
            lines.append("- Ensure meaning is clear from context.")

        lines.append("")
        lines.append("### Grammar Rules")
        lines.append("- Use active voice.")

        if vocab.passive_voice in ["avoid", "never"]:
            lines.append("- Avoid passive constructions.")
        elif vocab.passive_voice == "rare":
            lines.append("- Minimize passive voice.")
        else:
            lines.append("- Passive voice acceptable when appropriate.")

        lines.append("- Use clear subject-verb-object sentence order.")

        # Allowed/restricted vocabulary
        if profile.allowed_vocabulary:
            lines.append("")
            lines.append("### Allowed Vocabulary (Prefer These Words)")
            for word in profile.allowed_vocabulary[:20]:  # Limit to prevent prompt bloat
                lines.append(f"- {word}")
            if len(profile.allowed_vocabulary) > 20:
                lines.append(f"- (and {len(profile.allowed_vocabulary) - 20} more)")

        if profile.restricted_vocabulary:
            lines.append("")
            lines.append("### Restricted Vocabulary (Avoid These Words)")
            for word in profile.restricted_vocabulary[:20]:
                lines.append(f"- {word}")

        return "\n".join(lines)

    def _compose_story_parameters(
        self,
        profile: WritingProfile,
        theme: str,
        setting: str | None,
        main_character: str | None,
        word_count: int,
        tone: str | None,
    ) -> str:
        """Section 5: Story-Specific Parameters."""
        lines = ["## STORY PARAMETERS", ""]

        lines.append(f"Theme: {theme}")
        if setting:
            lines.append(f"Setting: {setting}")
        if main_character:
            lines.append(f"Main character: {main_character}")
        if tone:
            lines.append(f"Tone: {tone}")

        lines.append(f"Target length: {word_count} words (±5%)")
        lines.append(f"Dialogue level: {profile.style.dialogue_ratio}")

        # Study mode
        if profile.study_mode:
            lines.append("")
            lines.append("### Study Mode")
            lines.append("When a potentially difficult word appears,")
            lines.append("define it immediately using simple language within the sentence.")

        return "\n".join(lines)

    def _compose_output_constraints(self, profile: WritingProfile) -> str:
        """Section 6: Output Constraints."""
        lines = [
            "## OUTPUT REQUIREMENTS",
            "",
            "- Output plain text only.",
            "- Do not include headings, bullet points, or explanations.",
            "- Do not mention rules or constraints in the output.",
            "- Begin the story immediately.",
        ]
        return "\n".join(lines)


def compose_story_prompt(
    age_band: str,
    genre: str,
    lexile_band: str,
    theme: str,
    word_count: int = 400,
    setting: str | None = None,
    main_character: str | None = None,
    tone: str | None = None,
    style_profile: str | None = None,
    ell_mode: str | None = None,
    study_mode: bool = False,
    allowed_vocabulary: list[str] | None = None,
    restricted_vocabulary: list[str] | None = None,
) -> ComposedPrompt:
    """
    Convenience function to build profile and compose prompt in one step.

    Returns a ComposedPrompt ready for LLM submission.
    """
    from .profile_builder import WritingProfileBuilder

    builder = WritingProfileBuilder()
    profile = builder.build(
        age_band=age_band,
        genre=genre,
        lexile_band=lexile_band,
        style_profile=style_profile,
        ell_mode=ell_mode,
        study_mode=study_mode,
        allowed_vocabulary=allowed_vocabulary,
        restricted_vocabulary=restricted_vocabulary,
        theme=theme,
    )

    composer = PromptComposer()
    return composer.compose(
        profile=profile,
        theme=theme,
        setting=setting,
        main_character=main_character,
        word_count=word_count,
        tone=tone,
    )
