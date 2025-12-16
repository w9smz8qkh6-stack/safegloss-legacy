from django import forms
from django.forms import inlineformset_factory
from .models import (
    Lesson, Story, StorySegment, Quiz, ItemBankQuestion, ItemBankChoice,
    Roster, RosterMembership, Glossary, Term, Site, Unit, UnitLesson,
    Course, CourseUnit
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
    MODE_CHOICES = [
        ("continuous", "Continuous"),
        ("cards", "Cards"),
        ("movie", "Movie"),
    ]

    allowed_modes = forms.MultipleChoiceField(
        choices=MODE_CHOICES,
        initial=["continuous"],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=False,
        help_text="Select which reading modes students can use"
    )

    class Meta:
        model = Lesson
        fields = [
            "title", "introduction_html", "story", "quiz",
            "rosters", "allowed_modes", "default_mode", "is_active"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter lesson title"}),
            "introduction_html": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Introduction text for students"}),
            "story": forms.Select(attrs={"class": "form-select"}),
            "quiz": forms.Select(attrs={"class": "form-select"}),
            "rosters": forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
            "default_mode": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Make introduction optional
        self.fields["introduction_html"].required = False
        # Set default allowed_modes if not editing
        if not kwargs.get("instance"):
            self.initial["allowed_modes"] = ["continuous"]
        if user:
            self.fields["story"].queryset = Story.objects.filter(instructor=user)
            self.fields["quiz"].queryset = Quiz.objects.filter(owner=user)
            if user.site:
                self.fields["rosters"].queryset = Roster.objects.filter(site=user.site)


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter unit title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description of this unit"}),
        }


class UnitLessonForm(forms.ModelForm):
    class Meta:
        model = UnitLesson
        fields = ["lesson", "order"]
        widgets = {
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0, "style": "width: 80px;"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["lesson"].queryset = Lesson.objects.filter(instructor=user).order_by("title")


UnitLessonFormSet = inlineformset_factory(
    Unit,
    UnitLesson,
    form=UnitLessonForm,
    extra=5,
    can_delete=True,
    min_num=0,
)


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "rosters"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter course title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description of this course"}),
            "rosters": forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.site:
            self.fields["rosters"].queryset = Roster.objects.filter(site=user.site)


class CourseUnitForm(forms.ModelForm):
    class Meta:
        model = CourseUnit
        fields = ["unit", "order"]
        widgets = {
            "unit": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0, "style": "width: 80px;"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["unit"].queryset = Unit.objects.filter(instructor=user).order_by("title")


CourseUnitFormSet = inlineformset_factory(
    Course,
    CourseUnit,
    form=CourseUnitForm,
    extra=5,
    can_delete=True,
    min_num=0,
)


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["story", "title", "instructions_html", "total_points", "time_limit_minutes"]
        widgets = {
            "story": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter quiz title"}),
            "instructions_html": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Instructions for students"}),
            "total_points": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "time_limit_minutes": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 180,
                "placeholder": "e.g., 30"
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["story"].queryset = Story.objects.filter(instructor=user).order_by("-created_at")
        self.fields["time_limit_minutes"].required = False


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
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 5}),
        help_text="Select courses this roster is enrolled in."
    )

    class Meta:
        model = Roster
        fields = ["name", "site", "grade_band"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter roster name"}),
            "site": forms.Select(attrs={"class": "form-select"}),
            "grade_band": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Grade 6-7"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            self.fields["courses"].queryset = Course.objects.filter(instructor=user).order_by("title")
        # If editing, set initial courses from the reverse relationship
        if self.instance and self.instance.pk:
            self.fields["courses"].initial = self.instance.courses.all()

    def save(self, commit=True):
        roster = super().save(commit=False)
        # Set instructor for new rosters
        if not roster.pk and self.user:
            roster.instructor = self.user
        if commit:
            roster.save()
        if commit and self.cleaned_data.get("courses") is not None:
            # Update the reverse ManyToMany relationship
            current_courses = set(roster.courses.all())
            selected_courses = set(self.cleaned_data["courses"])

            # Remove roster from courses no longer selected
            for course in current_courses - selected_courses:
                course.rosters.remove(roster)

            # Add roster to newly selected courses
            for course in selected_courses - current_courses:
                course.rosters.add(roster)

        return roster


class RosterAddStudentForm(forms.Form):
    """Form for bulk adding students to a roster by email or username."""
    identifiers = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Enter student emails or usernames, one per line"
        }),
        help_text="Enter emails or usernames, one per line. New accounts will be created for unknown emails."
    )

    def __init__(self, *args, roster=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.roster = roster
        self.results = {
            "added": [],        # Successfully added existing users
            "created": [],      # New accounts created and added
            "skipped": [],      # Already in roster
            "errors": [],       # Invalid entries
        }

    def _generate_username(self, email):
        """Generate a unique username from email."""
        from .models import User
        import re
        base = email.split("@")[0]
        base = re.sub(r"[^a-zA-Z0-9]", "", base)[:20]
        if not base:
            base = "student"

        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        return username

    def clean_identifiers(self):
        from .models import User, RosterMembership
        import re

        raw_input = self.cleaned_data["identifiers"]
        lines = [line.strip() for line in raw_input.strip().split("\n") if line.strip()]

        if not lines:
            raise forms.ValidationError("Please enter at least one email or username.")

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        students_to_add = []

        for identifier in lines:
            # Try to find user by email or username
            user = User.objects.filter(email__iexact=identifier).first()
            if not user:
                user = User.objects.filter(username__iexact=identifier).first()

            if not user:
                # Check if it looks like an email
                if re.match(email_pattern, identifier):
                    # Create new student account
                    username = self._generate_username(identifier)
                    user = User.objects.create_user(
                        username=username,
                        email=identifier,
                        role=User.ROLE_STUDENT,
                    )
                    user.set_unusable_password()
                    user.save()
                    self.results["created"].append(identifier)
                else:
                    self.results["errors"].append(f"'{identifier}' - not found and not a valid email")
                    continue

            # Check if user is a student
            if not user.is_student():
                self.results["errors"].append(f"'{identifier}' - not a student account")
                continue

            # Check if already in roster
            if self.roster and RosterMembership.objects.filter(roster=self.roster, student=user).exists():
                self.results["skipped"].append(identifier)
                continue

            # Track as added (unless just created)
            if identifier not in self.results["created"]:
                self.results["added"].append(identifier)

            students_to_add.append(user)

        self.cleaned_data["students"] = students_to_add
        return raw_input


class StoryGeneratorForm(forms.Form):
    """Form for AI-powered story generation with Lexile-aligned constraints."""

    # Age and reading level
    AGE_BAND_CHOICES = [
        ("6-8", "Ages 6-8 (Early Readers)"),
        ("8-10", "Ages 8-10 (Developing Readers)"),
        ("10-12", "Ages 10-12 (Transitional Readers)"),
        ("12-14", "Ages 12-14 (Advanced Young Readers)"),
        ("14-16", "Ages 14-16 (High School)"),
        ("16-18", "Ages 16-18 (Advanced High School)"),
    ]

    LEXILE_BAND_CHOICES = [
        ("300-400L", "300-400L (Beginning Reader)"),
        ("400-500L", "400-500L (Early Elementary)"),
        ("500-600L", "500-600L (Elementary)"),
        ("600-700L", "600-700L (Upper Elementary)"),
        ("700-900L", "700-900L (Middle School)"),
        ("900-1100L", "900-1100L (Advanced Middle School)"),
        ("1100-1200L", "1100-1200L (High School)"),
        ("1200-1400L", "1200-1400L (Advanced High School)"),
    ]

    GENRE_CHOICES = [
        ("realistic_fiction", "Realistic Fiction"),
        ("fantasy", "Fantasy"),
        ("mystery", "Mystery"),
        ("informational_fiction", "Informational Fiction"),
        ("nonfiction_expository", "Nonfiction - Expository"),
        ("nonfiction_narrative", "Nonfiction - Narrative"),
        ("nonfiction_persuasive", "Nonfiction - Persuasive/Argumentative"),
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


class QuizGeneratorForm(forms.Form):
    """Form for AI-powered quiz generation based on story content."""

    QUESTION_TYPE_CHOICES = [
        ("mcq_single", "Multiple Choice (Single Answer)"),
        ("true_false", "True / False"),
        ("short_answer", "Short Answer"),
    ]

    DIFFICULTY_CHOICES = [
        ("easy", "Easy - Basic recall and comprehension"),
        ("medium", "Medium - Understanding and application"),
        ("hard", "Hard - Analysis and inference"),
    ]

    FOCUS_CHOICES = [
        ("comprehension", "Reading Comprehension"),
        ("vocabulary", "Vocabulary"),
        ("inference", "Inference & Critical Thinking"),
        ("mixed", "Mixed (All Types)"),
    ]

    # Story selection
    story = forms.ModelChoiceField(
        queryset=Story.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Select a story to generate quiz questions from"
    )

    # Quiz parameters
    num_questions = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=5,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Number of questions to generate (1-20)"
    )

    question_types = forms.MultipleChoiceField(
        choices=QUESTION_TYPE_CHOICES,
        initial=["mcq_single"],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        help_text="Types of questions to generate"
    )

    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        initial="medium",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Overall difficulty level"
    )

    focus = forms.ChoiceField(
        choices=FOCUS_CHOICES,
        initial="mixed",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Question focus area"
    )

    # Optional: Quiz metadata
    quiz_title = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Auto-generated from story title if blank"
        }),
        help_text="Title for the new quiz"
    )

    include_instructions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Generate quiz instructions automatically"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["story"].queryset = Story.objects.filter(instructor=user).order_by("-created_at")


class GlossaryGeneratorForm(forms.Form):
    """Form for AI-powered glossary generation based on story content."""

    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner - Basic vocabulary only"),
        ("intermediate", "Intermediate - Include some advanced terms"),
        ("advanced", "Advanced - Include challenging vocabulary"),
        ("auto", "Auto-detect from reading level"),
    ]

    FOCUS_CHOICES = [
        ("general", "General Vocabulary"),
        ("academic", "Academic Words"),
        ("domain", "Domain-Specific Terms"),
        ("mixed", "Mixed (All Types)"),
    ]

    # Number of terms to generate
    num_terms = forms.IntegerField(
        min_value=5,
        max_value=50,
        initial=15,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Number of vocabulary terms to identify (5-50)"
    )

    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        initial="auto",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Vocabulary difficulty level"
    )

    focus = forms.ChoiceField(
        choices=FOCUS_CHOICES,
        initial="mixed",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Type of vocabulary to focus on"
    )

    # Translation language
    translation_language = forms.CharField(
        max_length=50,
        initial="Vietnamese",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Vietnamese, Spanish, Chinese"}),
        help_text="Target language for translations"
    )

    include_definitions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Generate definitions in English"
    )

    include_translations = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Generate translations"
    )

    include_part_of_speech = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Include part of speech"
    )

    clear_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Replace existing glossary terms"
    )


class ExternalBookSearchForm(forms.Form):
    """Form for searching external book sources (Open Library, Gutenberg, Open Textbook Library)."""
    SOURCE_CHOICES = [
        ("all", "All Sources"),
        ("gutenberg", "Project Gutenberg"),
        ("openlibrary", "Open Library"),
        ("opentextbook", "Open Textbook Library"),
    ]

    LANGUAGE_CHOICES = [
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
    ]

    query = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search by title, author, or keyword..."
        })
    )
    source = forms.ChoiceField(
        choices=SOURCE_CHOICES,
        initial="all",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        initial="en",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )


class ExternalBookImportForm(forms.Form):
    """Form for configuring how to import a book from external sources."""
    IMPORT_MODE_CHOICES = [
        ("excerpt", "Excerpt (First N words)"),
        ("chapter", "Single Chapter"),
        ("full", "Full Text (may be very long)"),
    ]

    import_mode = forms.ChoiceField(
        choices=IMPORT_MODE_CHOICES,
        initial="excerpt",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    chapter_number = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "Chapter number"
        })
    )
    excerpt_words = forms.IntegerField(
        min_value=100,
        max_value=10000,
        initial=2000,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Number of words to import (100-10,000)"
    )
    custom_title = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Leave blank to use original title"
        })
    )
