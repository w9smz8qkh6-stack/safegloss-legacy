from django import forms
from django.forms import inlineformset_factory
from .models import (
    Lesson, Story, StorySegment, Quiz, ItemBankQuestion, ItemBankChoice,
    Roster, RosterMembership, Glossary, Term, Site
)


class LessonFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ("all", "All"),
            ("in_progress", "In progress"),
            ("not_started", "Not started"),
            ("completed", "Completed"),
        ],
        required=False,
    )
    search = forms.CharField(required=False, max_length=100)


class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ["title", "text_html", "source_type", "reading_level_label"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter story title"}),
            "text_html": forms.Textarea(attrs={"class": "form-control", "rows": 15, "placeholder": "Enter story content (HTML supported)"}),
            "source_type": forms.Select(attrs={"class": "form-select"}),
            "reading_level_label": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Grade 6-7, B1, Lexile 780L"}),
        }


class StorySegmentForm(forms.ModelForm):
    class Meta:
        model = StorySegment
        fields = ["index", "title", "text_html"]
        widgets = {
            "index": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Segment title (optional)"}),
            "text_html": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }


StorySegmentFormSet = inlineformset_factory(
    Story, StorySegment,
    form=StorySegmentForm,
    extra=1,
    can_delete=True,
)


class GlossaryForm(forms.ModelForm):
    class Meta:
        model = Glossary
        fields = ["name", "language_code", "native_language_code"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Glossary name (optional)"}),
            "language_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., en"}),
            "native_language_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., vi"}),
        }


class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = [
            "term_text", "lemma", "part_of_speech", "definition_html",
            "translation", "translation_lang_code", "ipa",
            "difficulty_rating", "is_selected_for_glossary"
        ]
        widgets = {
            "term_text": forms.TextInput(attrs={"class": "form-control"}),
            "lemma": forms.TextInput(attrs={"class": "form-control"}),
            "part_of_speech": forms.TextInput(attrs={"class": "form-control"}),
            "definition_html": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "translation": forms.TextInput(attrs={"class": "form-control"}),
            "translation_lang_code": forms.TextInput(attrs={"class": "form-control"}),
            "ipa": forms.TextInput(attrs={"class": "form-control"}),
            "difficulty_rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5, "step": 0.5}),
            "is_selected_for_glossary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title", "site", "introduction_html", "story", "quiz",
            "rosters", "allowed_modes", "default_mode", "is_active"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter lesson title"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "introduction_html": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Introduction text for students"}),
            "story": forms.Select(attrs={"class": "form-select"}),
            "quiz": forms.Select(attrs={"class": "form-select"}),
            "rosters": forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
            "default_mode": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["story"].queryset = Story.objects.filter(instructor=user)
            self.fields["quiz"].queryset = Quiz.objects.filter(owner=user)
            if user.site:
                self.fields["rosters"].queryset = Roster.objects.filter(site=user.site)
            self.fields["site"].queryset = Site.objects.all()


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["title", "instructions_html", "total_points"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter quiz title"}),
            "instructions_html": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Instructions for students"}),
            "total_points": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class ItemBankQuestionForm(forms.ModelForm):
    class Meta:
        model = ItemBankQuestion
        fields = ["prompt_html", "question_type", "default_points", "subject", "grade_band", "status"]
        widgets = {
            "prompt_html": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter question text"}),
            "question_type": forms.Select(attrs={"class": "form-select"}),
            "default_points": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 0.5}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "grade_band": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class ItemBankChoiceForm(forms.ModelForm):
    class Meta:
        model = ItemBankChoice
        fields = ["label", "text_html", "is_correct", "order"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control", "placeholder": "A, B, C..."}),
            "text_html": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_correct": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


ItemBankChoiceFormSet = inlineformset_factory(
    ItemBankQuestion, ItemBankChoice,
    form=ItemBankChoiceForm,
    extra=4,
    can_delete=True,
)


class RosterForm(forms.ModelForm):
    class Meta:
        model = Roster
        fields = ["name", "site", "grade_band"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter roster name"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "grade_band": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Grade 6-7"}),
        }


class StoryGeneratorForm(forms.Form):
    """Form for AI-powered story generation with Lexile-aligned constraints."""

    # Age and reading level
    AGE_BAND_CHOICES = [
        ("6-8", "Ages 6-8 (Early Readers)"),
        ("8-10", "Ages 8-10 (Developing Readers)"),
        ("10-12", "Ages 10-12 (Transitional Readers)"),
        ("12-14", "Ages 12-14 (Advanced Young Readers)"),
    ]

    LEXILE_BAND_CHOICES = [
        ("300-400L", "300-400L (Beginning Reader)"),
        ("400-500L", "400-500L (Early Elementary)"),
        ("500-600L", "500-600L (Elementary)"),
        ("600-700L", "600-700L (Upper Elementary)"),
        ("700-900L", "700-900L (Middle School)"),
        ("900-1100L", "900-1100L (Advanced Middle School)"),
    ]

    GENRE_CHOICES = [
        ("realistic_fiction", "Realistic Fiction"),
        ("fantasy", "Fantasy"),
        ("mystery", "Mystery"),
        ("informational_fiction", "Informational Fiction"),
    ]

    STYLE_PROFILE_CHOICES = [
        ("", "None (Default)"),
        ("minimalist", "Minimalist"),
        ("cinematic", "Cinematic"),
        ("humorous", "Humorous"),
        ("sel_focused", "SEL-Focused"),
        ("adventure", "Adventure"),
        ("lyrical", "Lyrical"),
    ]

    TONE_CHOICES = [
        ("", "Default"),
        ("warm", "Warm and Uplifting"),
        ("adventurous", "Adventurous"),
        ("calm", "Calm and Gentle"),
        ("suspenseful", "Suspenseful"),
        ("humorous", "Humorous"),
    ]

    DIALOGUE_LEVEL_CHOICES = [
        ("low", "Low (mostly narrative)"),
        ("medium", "Medium (balanced)"),
        ("high", "High (dialogue-heavy)"),
    ]

    ELL_MODE_CHOICES = [
        ("", "None"),
        ("beginner", "Beginner ELL"),
        ("intermediate", "Intermediate ELL"),
        ("advanced", "Advanced ELL"),
    ]

    # Required fields
    age_band = forms.ChoiceField(
        choices=AGE_BAND_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Target age group for developmental appropriateness"
    )

    lexile_band = forms.ChoiceField(
        choices=LEXILE_BAND_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Target reading level (Lexile-aligned)"
    )

    genre = forms.ChoiceField(
        choices=GENRE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Story genre"
    )

    theme = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., friendship, courage, helping others"
        }),
        help_text="Main theme or topic of the story"
    )

    # Optional fields
    word_count = forms.IntegerField(
        min_value=100,
        max_value=2000,
        initial=400,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Target word count (100-2000)"
    )

    setting = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., a small town, a magical forest"
        }),
        help_text="Story setting (optional)"
    )

    main_character = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., a curious 10-year-old named Sam"
        }),
        help_text="Main character description (optional)"
    )

    tone = forms.ChoiceField(
        choices=TONE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Overall tone of the story"
    )

    dialogue_level = forms.ChoiceField(
        choices=DIALOGUE_LEVEL_CHOICES,
        initial="medium",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Amount of dialogue in the story"
    )

    style_profile = forms.ChoiceField(
        choices=STYLE_PROFILE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Writing style overlay"
    )

    ell_mode = forms.ChoiceField(
        choices=ELL_MODE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="English Language Learner support level"
    )

    study_mode = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Include inline definitions for difficult words"
    )

    # Advanced options (collapsed by default in UI)
    VOCABULARY_MODE_CHOICES = [
        ("none", "No Restrictions"),
        ("prefer", "Prefer Listed Words"),
        ("strict", "Strict Glossary Mode"),
    ]

    vocabulary_mode = forms.ChoiceField(
        choices=VOCABULARY_MODE_CHOICES,
        initial="none",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="How strictly to enforce vocabulary list"
    )

    allowed_vocabulary = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Enter words separated by commas (optional)"
        }),
        help_text="Glossary-locked vocabulary list"
    )

    restricted_vocabulary = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Enter words to avoid, separated by commas (optional)"
        }),
        help_text="Words to avoid in the story"
    )

    max_stretch_words = forms.IntegerField(
        min_value=0,
        max_value=20,
        initial=5,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Max new words beyond vocabulary list (strict mode)"
    )

    def clean_allowed_vocabulary(self):
        """Convert comma-separated string to list."""
        value = self.cleaned_data.get("allowed_vocabulary", "")
        if value:
            return [w.strip() for w in value.split(",") if w.strip()]
        return []

    def clean_restricted_vocabulary(self):
        """Convert comma-separated string to list."""
        value = self.cleaned_data.get("restricted_vocabulary", "")
        if value:
            return [w.strip() for w in value.split(",") if w.strip()]
        return []

    def get_generation_params(self):
        """
        Return cleaned data formatted for the story engine.

        Returns a dict ready to pass to compose_story_prompt().
        """
        data = self.cleaned_data
        params = {
            "age_band": data["age_band"],
            "genre": data["genre"],
            "lexile_band": data["lexile_band"],
            "theme": data["theme"],
            "word_count": data["word_count"],
        }

        # Add optional fields if provided
        if data.get("setting"):
            params["setting"] = data["setting"]
        if data.get("main_character"):
            params["main_character"] = data["main_character"]
        if data.get("tone"):
            params["tone"] = data["tone"]
        if data.get("style_profile"):
            params["style_profile"] = data["style_profile"]
        if data.get("ell_mode"):
            params["ell_mode"] = data["ell_mode"]
        if data.get("study_mode"):
            params["study_mode"] = True
        if data.get("allowed_vocabulary"):
            params["allowed_vocabulary"] = data["allowed_vocabulary"]
        if data.get("restricted_vocabulary"):
            params["restricted_vocabulary"] = data["restricted_vocabulary"]

        # Vocabulary control
        params["vocabulary_mode"] = data.get("vocabulary_mode", "none")
        params["max_stretch_words"] = data.get("max_stretch_words", 5)

        return params
