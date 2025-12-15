"""
Prompt Composer

Emits natural-language constraints in the mandatory layered order.
Converts WritingProfile rules into deterministic, auditable prompts.

Prompt ordering (mandatory):
1. Reader & Age Profile
2. Developmental Writing Rules
3. Genre-Specific Rules
4. Style Profile Rules (if style_profile selected)
5. Lexile & Language Constraints
6. Story-Specific Parameters
7. Output Constraints
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

        # Section 4: Style Profile Rules (if style_profile selected)
        if profile.style_profile:
            sections.append(self._compose_style_rules(profile))

        # Section 5: Lexile & Language Constraints
        sections.append(self._compose_language_constraints(profile))

        # Section 5b: Vocabulary Control (if glossary-locked)
        if profile.vocab_constraints.mode != "none":
            sections.append(self._compose_vocabulary_control(profile))

        # Section 6: Story-Specific Parameters
        sections.append(self._compose_story_parameters(
            profile, theme, setting, main_character, word_count, tone
        ))

        # Section 7: Output Constraints
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

    def _compose_style_rules(self, profile: WritingProfile) -> str:
        """Section 4: Style Profile Rules."""
        style = profile.style
        style_name = profile.style_profile

        lines = [
            "## WRITING STYLE",
            "",
            f"Style: {style_name.replace('_', ' ').title()}",
            "",
        ]

        # Writing voice characteristics
        if style.writing_voice:
            voice = style.writing_voice
            lines.append("### Voice & Pacing")

            if voice.get("pacing"):
                pacing_desc = {
                    "fast": "Keep the pace fast. Something should happen in every paragraph.",
                    "punchy": "Use punchy, energetic prose. Quick exchanges and snappy dialogue.",
                    "steady": "Maintain a steady, even pace throughout.",
                    "varied": "Vary the pace—slower for atmosphere, faster for action.",
                    "contemplative": "Allow for reflection and contemplation.",
                    "reflective": "Include moments of pause and emotional processing.",
                    "moderate": "Balance action with reflection.",
                }
                lines.append(f"- {pacing_desc.get(voice['pacing'], f'Pacing: {voice[\"pacing\"]}')}")

            if voice.get("description_style"):
                desc_style = {
                    "action-focused": "Descriptions should focus on what characters do, not how things look.",
                    "sensory-immersive": "Descriptions should immerse the reader through sensory details.",
                    "kinetic": "Descriptions should convey motion and energy.",
                    "internal-focused": "Focus on characters' inner experiences and thoughts.",
                    "metaphorical": "Use imagery and metaphor to create atmosphere.",
                    "comic-timing": "Pace descriptions for maximum comedic effect.",
                }
                lines.append(f"- {desc_style.get(voice['description_style'], '')}")

            if voice.get("emotional_showing"):
                emotion_style = {
                    "through_action": "Show emotions through what characters do, not what they feel.",
                    "through_environment": "Reflect emotions through environmental details.",
                    "through_stakes": "Build emotion through what characters might lose.",
                    "through_reaction": "Show emotions through character reactions.",
                    "through_imagery": "Use imagery to evoke emotional responses.",
                    "explicit_naming": "Name emotions explicitly when characters experience them.",
                }
                lines.append(f"- {emotion_style.get(voice['emotional_showing'], '')}")

            if voice.get("sentence_variation"):
                variation = {
                    "low": "Keep sentence length consistent.",
                    "high": "Vary sentence length significantly for rhythm and effect.",
                    "dynamic": "Use sentence length dynamically—short for tension, longer for reflection.",
                    "moderate": "Moderate variation in sentence length.",
                    "musical": "Choose sentence lengths for their rhythm and sound.",
                }
                lines.append(f"- {variation.get(voice['sentence_variation'], '')}")

        # Sensory detail level
        lines.append("")
        lines.append("### Sensory & Descriptive Detail")
        sensory_desc = {
            "sparse": "Keep sensory details minimal. Focus on action and dialogue.",
            "selective": "Choose sensory details selectively for emphasis.",
            "moderate": "Include moderate sensory detail to ground scenes.",
            "rich": "Use rich sensory details—sight, sound, texture, smell.",
            "action_focused": "Focus on physical sensations during action (impact, speed, breath).",
            "poetic": "Use sensory details poetically to evoke mood and atmosphere.",
        }
        lines.append(f"- {sensory_desc.get(style.sensory_detail, 'Include appropriate sensory detail.')}")

        # Figurative language
        fig_lang = {
            "none": "Do not use figurative language (similes, metaphors).",
            "minimal": "Use figurative language sparingly, if at all.",
            "simple": "Simple similes allowed (like, as). No complex metaphors.",
            "playful": "Use playful comparisons and humorous exaggerations.",
            "emotion_metaphors": "Use metaphors to describe emotional experiences.",
            "rich": "Use figurative language to create imagery and atmosphere.",
        }
        lines.append(f"- {fig_lang.get(style.figurative_language, '')}")

        # Dialogue guidance
        lines.append("")
        lines.append("### Dialogue")
        lines.append(f"- Target dialogue ratio: {int(style.dialogue_ratio_min * 100)}% to {int(style.dialogue_ratio_max * 100)}% of the story should be dialogue.")

        # Things to avoid
        if style.style_avoid:
            lines.append("")
            lines.append("### Avoid in This Style")
            for item in style.style_avoid:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _compose_language_constraints(self, profile: WritingProfile) -> str:
        """Section 5: Lexile & Language Constraints."""
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

        return "\n".join(lines)

    def _compose_vocabulary_control(self, profile: WritingProfile) -> str:
        """Section 5b: Vocabulary Control for glossary-locked stories."""
        vc = profile.vocab_constraints
        lines = ["## VOCABULARY CONTROL", ""]

        if vc.mode == "strict":
            lines.extend([
                "### Strict Glossary Mode",
                "",
                "You MUST primarily use words from the allowed vocabulary list below.",
                f"You may introduce up to {vc.max_stretch_words} 'stretch words' that are NOT on the list.",
                "",
            ])

            if vc.stretch_words_require_definition:
                lines.extend([
                    "**Stretch Word Requirements:**",
                    "- Each stretch word must be defined inline when first used.",
                    "- Use a simple, natural definition within the sentence.",
                    "- Example: 'The bird was resilient—it kept trying even when things were hard.'",
                    "",
                ])

            lines.append("### Allowed Words (Use These)")
            self._append_word_list(lines, vc.allowed_words, 30)

        elif vc.mode == "prefer":
            lines.extend([
                "### Preferred Vocabulary Mode",
                "",
                "Prioritize using words from the preferred vocabulary list below.",
                "Other common words are allowed, but prefer the listed terms when natural.",
                f"Stay within the {vc.frequency_threshold.replace('_', ' ')} most common words for unlisted vocabulary.",
                "",
            ])

            lines.append("### Preferred Words")
            self._append_word_list(lines, vc.allowed_words, 30)

        # Restricted words (both modes)
        if vc.restricted_words:
            lines.append("")
            lines.append("### Words to Avoid")
            lines.append("Do NOT use the following words in the story:")
            self._append_word_list(lines, vc.restricted_words, 20)

        return "\n".join(lines)

    def _append_word_list(self, lines: list[str], words: list[str], limit: int) -> None:
        """Append a word list to lines, grouping for readability."""
        if not words:
            lines.append("(No specific words provided)")
            return

        # Group words into rows of 5-6 for readability
        displayed = words[:limit]
        for i in range(0, len(displayed), 5):
            chunk = displayed[i:i+5]
            lines.append(f"  {', '.join(chunk)}")

        if len(words) > limit:
            lines.append(f"  ... and {len(words) - limit} more words")

    def _compose_story_parameters(
        self,
        profile: WritingProfile,
        theme: str,
        setting: str | None,
        main_character: str | None,
        word_count: int,
        tone: str | None,
    ) -> str:
        """Section 6: Story-Specific Parameters."""
        lines = ["## STORY PARAMETERS", ""]

        lines.append(f"Theme: {theme}")
        if setting:
            lines.append(f"Setting: {setting}")
        if main_character:
            lines.append(f"Main character: {main_character}")
        if tone:
            lines.append(f"Tone: {tone}")

        lines.append(f"Target length: {word_count} words (±5%)")

        # Dialogue level - use numeric if no style profile, otherwise style handles it
        if not profile.style_profile:
            dialogue_pct = int((profile.style.dialogue_ratio_min + profile.style.dialogue_ratio_max) / 2 * 100)
            lines.append(f"Dialogue level: approximately {dialogue_pct}% of the story should be dialogue")

        # Study mode
        if profile.study_mode:
            lines.append("")
            lines.append("### Study Mode")
            lines.append("When a potentially difficult word appears,")
            lines.append("define it immediately using simple language within the sentence.")

        return "\n".join(lines)

    def _compose_output_constraints(self, profile: WritingProfile) -> str:
        """Section 7: Output Constraints."""
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
    vocabulary_mode: str = "none",
    max_stretch_words: int = 5,
) -> ComposedPrompt:
    """
    Convenience function to build profile and compose prompt in one step.

    Args:
        vocabulary_mode: "none", "prefer", or "strict"
        max_stretch_words: Max words outside allowed list (strict mode)

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
        vocabulary_mode=vocabulary_mode,
        max_stretch_words=max_stretch_words,
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
