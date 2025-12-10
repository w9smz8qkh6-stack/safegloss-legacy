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
        fields = ["name", "site", "grade_band", "invite_enabled"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter roster name"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "grade_band": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Grade 6-7"}),
            "invite_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class JoinRosterForm(forms.Form):
    """Form for students to join a roster via invite code."""
    invite_code = forms.CharField(
        max_length=8,
        min_length=6,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg text-center text-uppercase",
            "placeholder": "XXXXXX",
            "autocomplete": "off",
            "style": "letter-spacing: 0.3em; font-family: monospace;",
        }),
        help_text="Enter the 6-character code provided by your instructor."
    )

    def clean_invite_code(self):
        code = self.cleaned_data['invite_code'].upper().strip()
        try:
            roster = Roster.objects.get(invite_code=code, invite_enabled=True)
            self.roster = roster
        except Roster.DoesNotExist:
            raise forms.ValidationError("Invalid or expired invite code.")
        return code
