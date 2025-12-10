from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import (
    User, Site, Roster, RosterMembership, Story, StorySegment, Glossary, Term,
    Lesson, LessonProgress, Quiz, QuizQuestion, QuizSubmission, QuizSubmissionAnswer,
    ItemBankQuestion, ItemBankChoice
)


class UserModelTests(TestCase):
    """Tests for the User model."""

    def setUp(self):
        self.site = Site.objects.create(name="Test School", code="TEST")

    def test_user_default_role_is_student(self):
        """New users should default to student role."""
        user = User.objects.create_user(username="testuser", password="pass123")
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertTrue(user.is_student())
        self.assertFalse(user.is_instructor())
        self.assertFalse(user.is_researcher())

    def test_instructor_role(self):
        """Instructor role should be correctly identified."""
        user = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )
        self.assertTrue(user.is_instructor())
        self.assertFalse(user.is_student())

    def test_researcher_role(self):
        """Researcher role should be correctly identified."""
        user = User.objects.create_user(
            username="researcher",
            password="pass123",
            role=User.ROLE_RESEARCHER
        )
        self.assertTrue(user.is_researcher())
        self.assertFalse(user.is_student())

    def test_user_site_association(self):
        """Users can be associated with a site."""
        user = User.objects.create_user(
            username="student",
            password="pass123",
            site=self.site
        )
        self.assertEqual(user.site, self.site)


class RosterModelTests(TestCase):
    """Tests for roster and membership models."""

    def setUp(self):
        self.site = Site.objects.create(name="Test School", code="TEST")
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )
        self.student1 = User.objects.create_user(username="student1", password="pass123")
        self.student2 = User.objects.create_user(username="student2", password="pass123")

    def test_roster_creation(self):
        """Rosters can be created with a site."""
        roster = Roster.objects.create(
            site=self.site,
            name="Class A",
            grade_band="9-12"
        )
        self.assertEqual(str(roster), "Class A (TEST)")

    def test_roster_membership(self):
        """Students can be added to rosters."""
        roster = Roster.objects.create(site=self.site, name="Class A")
        RosterMembership.objects.create(roster=roster, student=self.student1)
        RosterMembership.objects.create(roster=roster, student=self.student2)

        self.assertEqual(roster.memberships.count(), 2)

    def test_unique_membership(self):
        """Students cannot be added to the same roster twice."""
        roster = Roster.objects.create(site=self.site, name="Class A")
        RosterMembership.objects.create(roster=roster, student=self.student1)

        with self.assertRaises(Exception):
            RosterMembership.objects.create(roster=roster, student=self.student1)


class QuizScoringTests(TestCase):
    """Tests for quiz submission and scoring logic."""

    def setUp(self):
        self.site = Site.objects.create(name="Test School", code="TEST")
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="student",
            password="pass123",
            site=self.site
        )

        # Create a quiz with questions
        self.quiz = Quiz.objects.create(
            owner=self.instructor,
            title="Test Quiz",
            total_points=3.0
        )

        # Create MCQ question with choices
        self.q1 = ItemBankQuestion.objects.create(
            owner=self.instructor,
            prompt_html="What is 2+2?",
            question_type="mcq_single",
            default_points=1.0
        )
        self.q1_correct = ItemBankChoice.objects.create(
            question=self.q1, label="A", text_html="4", is_correct=True, order=0
        )
        self.q1_wrong1 = ItemBankChoice.objects.create(
            question=self.q1, label="B", text_html="3", is_correct=False, order=1
        )
        self.q1_wrong2 = ItemBankChoice.objects.create(
            question=self.q1, label="C", text_html="5", is_correct=False, order=2
        )

        # Create true/false question
        self.q2 = ItemBankQuestion.objects.create(
            owner=self.instructor,
            prompt_html="The sky is blue.",
            question_type="true_false",
            default_points=1.0
        )
        self.q2_true = ItemBankChoice.objects.create(
            question=self.q2, label="T", text_html="True", is_correct=True, order=0
        )
        self.q2_false = ItemBankChoice.objects.create(
            question=self.q2, label="F", text_html="False", is_correct=False, order=1
        )

        # Create another MCQ
        self.q3 = ItemBankQuestion.objects.create(
            owner=self.instructor,
            prompt_html="Capital of France?",
            question_type="mcq_single",
            default_points=1.0
        )
        self.q3_correct = ItemBankChoice.objects.create(
            question=self.q3, label="A", text_html="Paris", is_correct=True, order=0
        )
        self.q3_wrong = ItemBankChoice.objects.create(
            question=self.q3, label="B", text_html="London", is_correct=False, order=1
        )

        # Add questions to quiz
        QuizQuestion.objects.create(quiz=self.quiz, question=self.q1, order=0, points=1.0)
        QuizQuestion.objects.create(quiz=self.quiz, question=self.q2, order=1, points=1.0)
        QuizQuestion.objects.create(quiz=self.quiz, question=self.q3, order=2, points=1.0)

    def test_quiz_submission_creation(self):
        """Quiz submissions can be created."""
        submission = QuizSubmission.objects.create(
            student=self.student,
            quiz=self.quiz
        )
        self.assertFalse(submission.is_submitted)
        self.assertIsNone(submission.submitted_at)

    def test_quiz_submission_complete(self):
        """Quiz submissions can be marked as complete."""
        submission = QuizSubmission.objects.create(
            student=self.student,
            quiz=self.quiz,
            submitted_at=timezone.now(),
            raw_score=2.0,
            max_score=3.0
        )
        self.assertTrue(submission.is_submitted)

    def test_answer_correct_tracking(self):
        """Answers track correctness."""
        submission = QuizSubmission.objects.create(
            student=self.student,
            quiz=self.quiz
        )

        # Correct answer
        answer1 = QuizSubmissionAnswer.objects.create(
            submission=submission,
            question=self.q1,
            question_type="mcq_single",
            selected_choice_ids=[self.q1_correct.id],
            is_correct=True
        )
        self.assertTrue(answer1.is_correct)

        # Wrong answer
        answer2 = QuizSubmissionAnswer.objects.create(
            submission=submission,
            question=self.q2,
            question_type="true_false",
            selected_choice_ids=[self.q2_false.id],
            is_correct=False
        )
        self.assertFalse(answer2.is_correct)

    def test_perfect_score(self):
        """All correct answers should result in full score."""
        submission = QuizSubmission.objects.create(
            student=self.student,
            quiz=self.quiz,
            submitted_at=timezone.now(),
            raw_score=3.0,
            max_score=3.0
        )

        QuizSubmissionAnswer.objects.create(
            submission=submission,
            question=self.q1,
            question_type="mcq_single",
            selected_choice_ids=[self.q1_correct.id],
            is_correct=True
        )
        QuizSubmissionAnswer.objects.create(
            submission=submission,
            question=self.q2,
            question_type="true_false",
            selected_choice_ids=[self.q2_true.id],
            is_correct=True
        )
        QuizSubmissionAnswer.objects.create(
            submission=submission,
            question=self.q3,
            question_type="mcq_single",
            selected_choice_ids=[self.q3_correct.id],
            is_correct=True
        )

        self.assertEqual(submission.raw_score, 3.0)
        self.assertEqual(submission.answers.filter(is_correct=True).count(), 3)


class LessonProgressTests(TestCase):
    """Tests for lesson progress tracking."""

    def setUp(self):
        self.site = Site.objects.create(name="Test School", code="TEST")
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="student",
            password="pass123",
            site=self.site
        )

        self.story = Story.objects.create(
            instructor=self.instructor,
            title="Test Story",
            text_html="<p>Once upon a time...</p>"
        )

        self.lesson = Lesson.objects.create(
            instructor=self.instructor,
            site=self.site,
            title="Test Lesson",
            introduction_html="<p>Welcome</p>",
            story=self.story
        )

    def test_reading_duration_calculation(self):
        """Reading duration should be calculated correctly."""
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=5, seconds=30)

        progress = LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson,
            reading_start=start_time,
            reading_end=end_time
        )

        # 5 minutes 30 seconds = 330 seconds
        self.assertEqual(progress.reading_duration_seconds, 330.0)

    def test_reading_duration_none_when_incomplete(self):
        """Reading duration should be None when reading is not complete."""
        progress = LessonProgress.objects.create(
            student=self.student,
            lesson=self.lesson,
            reading_start=timezone.now()
        )
        self.assertIsNone(progress.reading_duration_seconds)


class ViewAccessTests(TestCase):
    """Tests for view access control."""

    def setUp(self):
        self.client = Client()
        self.site = Site.objects.create(name="Test School", code="TEST")

        self.student = User.objects.create_user(
            username="student",
            password="pass123",
            site=self.site
        )
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )

        self.story = Story.objects.create(
            instructor=self.instructor,
            title="Test Story",
            text_html="<p>Content</p>"
        )

        self.roster = Roster.objects.create(site=self.site, name="Class A")
        RosterMembership.objects.create(roster=self.roster, student=self.student)

        self.lesson = Lesson.objects.create(
            instructor=self.instructor,
            site=self.site,
            title="Test Lesson",
            introduction_html="<p>Welcome</p>",
            story=self.story,
            is_active=True
        )
        self.lesson.rosters.add(self.roster)

    def test_unauthenticated_redirect(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.get(reverse("core:student_lessons"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_student_can_access_lessons(self):
        """Students can access their lessons list."""
        self.client.login(username="student", password="pass123")
        response = self.client.get(reverse("core:student_lessons"))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_instructor_dashboard(self):
        """Students should be redirected from instructor pages."""
        self.client.login(username="student", password="pass123")
        response = self.client.get(reverse("core:instructor_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_instructor_can_access_dashboard(self):
        """Instructors can access the dashboard."""
        self.client.login(username="instructor", password="pass123")
        response = self.client.get(reverse("core:instructor_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_access_story_list(self):
        """Instructors can access story management."""
        self.client.login(username="instructor", password="pass123")
        response = self.client.get(reverse("core:story_list"))
        self.assertEqual(response.status_code, 200)


class QuizSubmissionViewTests(TestCase):
    """Tests for quiz submission view logic."""

    def setUp(self):
        self.client = Client()
        self.site = Site.objects.create(name="Test School", code="TEST")

        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )
        self.student = User.objects.create_user(
            username="student",
            password="pass123",
            site=self.site
        )

        self.story = Story.objects.create(
            instructor=self.instructor,
            title="Test Story",
            text_html="<p>Content</p>"
        )

        # Create quiz with one question
        self.quiz = Quiz.objects.create(
            owner=self.instructor,
            title="Test Quiz",
            total_points=1.0
        )

        self.question = ItemBankQuestion.objects.create(
            owner=self.instructor,
            prompt_html="What is 1+1?",
            question_type="mcq_single",
            default_points=1.0
        )
        self.correct_choice = ItemBankChoice.objects.create(
            question=self.question,
            label="A",
            text_html="2",
            is_correct=True,
            order=0
        )
        self.wrong_choice = ItemBankChoice.objects.create(
            question=self.question,
            label="B",
            text_html="3",
            is_correct=False,
            order=1
        )

        QuizQuestion.objects.create(
            quiz=self.quiz,
            question=self.question,
            order=0,
            points=1.0
        )

        self.roster = Roster.objects.create(site=self.site, name="Class A")
        RosterMembership.objects.create(roster=self.roster, student=self.student)

        self.lesson = Lesson.objects.create(
            instructor=self.instructor,
            site=self.site,
            title="Test Lesson",
            introduction_html="<p>Welcome</p>",
            story=self.story,
            quiz=self.quiz,
            is_active=True
        )
        self.lesson.rosters.add(self.roster)

    def test_quiz_page_loads(self):
        """Quiz page should load for enrolled students."""
        self.client.login(username="student", password="pass123")
        response = self.client.get(
            reverse("core:lesson_quiz", kwargs={"pk": self.lesson.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is 1+1?")

    def test_quiz_submission_creates_record(self):
        """Submitting quiz should create submission record."""
        self.client.login(username="student", password="pass123")

        response = self.client.post(
            reverse("core:lesson_quiz", kwargs={"pk": self.lesson.pk}),
            {f"question_{self.question.pk}": str(self.correct_choice.pk)}
        )

        # Should redirect to results
        self.assertEqual(response.status_code, 302)

        # Submission should exist
        submission = QuizSubmission.objects.filter(
            student=self.student,
            quiz=self.quiz
        ).first()
        self.assertIsNotNone(submission)
        self.assertTrue(submission.is_submitted)


class StorySegmentTests(TestCase):
    """Tests for story segment functionality."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )

        self.story = Story.objects.create(
            instructor=self.instructor,
            title="Test Story",
            text_html="<p>Full story content here</p>"
        )

    def test_segment_ordering(self):
        """Segments should be ordered by index."""
        seg3 = StorySegment.objects.create(
            story=self.story, index=2, text_html="<p>Third</p>"
        )
        seg1 = StorySegment.objects.create(
            story=self.story, index=0, text_html="<p>First</p>"
        )
        seg2 = StorySegment.objects.create(
            story=self.story, index=1, text_html="<p>Second</p>"
        )

        segments = list(self.story.segments.all())
        self.assertEqual(segments[0], seg1)
        self.assertEqual(segments[1], seg2)
        self.assertEqual(segments[2], seg3)

    def test_segment_unique_index(self):
        """Segment index must be unique per story."""
        StorySegment.objects.create(story=self.story, index=0, text_html="<p>First</p>")

        with self.assertRaises(Exception):
            StorySegment.objects.create(
                story=self.story, index=0, text_html="<p>Duplicate</p>"
            )


class GlossaryTests(TestCase):
    """Tests for glossary and term functionality."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="pass123",
            role=User.ROLE_INSTRUCTOR
        )

        self.story = Story.objects.create(
            instructor=self.instructor,
            title="Test Story",
            text_html="<p>The cat sat on the mat.</p>"
        )

        self.glossary = Glossary.objects.create(
            story=self.story,
            name="Test Glossary",
            language_code="en",
            native_language_code="vi"
        )

    def test_glossary_term_creation(self):
        """Terms can be created in a glossary."""
        term = Term.objects.create(
            glossary=self.glossary,
            term_text="cat",
            definition_html="A small domesticated carnivorous mammal.",
            translation="con mèo",
            part_of_speech="noun"
        )

        self.assertEqual(term.glossary, self.glossary)
        self.assertEqual(str(term), "cat")

    def test_glossary_string_representation(self):
        """Glossary should have proper string representation."""
        self.assertEqual(str(self.glossary), "Test Glossary")

        # Without name
        glossary2 = Glossary.objects.create(
            story=Story.objects.create(
                instructor=self.instructor,
                title="Story 2",
                text_html="<p>Content</p>"
            ),
            language_code="en",
            native_language_code="vi"
        )
        self.assertIn("Story 2", str(glossary2))
