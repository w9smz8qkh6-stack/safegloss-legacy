from django.core.management.base import BaseCommand
from core.models import (
    User, Site, Roster, RosterMembership, Story, StorySegment,
    Glossary, Term, Quiz, QuizQuestion, ItemBankQuestion, ItemBankChoice, Lesson
)


class Command(BaseCommand):
    help = 'Set up demo data for testing the student experience'

    def handle(self, *args, **options):
        self.stdout.write('Setting up demo data...\n')

        # Create or get site
        site, _ = Site.objects.get_or_create(
            code='demo',
            defaults={'name': 'Demo School'}
        )
        self.stdout.write(f'  Site: {site.name}')

        # Create or get instructor
        instructor, created = User.objects.get_or_create(
            username='instructor',
            defaults={
                'email': 'instructor@demo.com',
                'role': 'instructor',
                'site': site,
            }
        )
        if created:
            instructor.set_password('demo1234')
            instructor.save()
            self.stdout.write(f'  Created instructor: instructor / demo1234')
        else:
            self.stdout.write(f'  Instructor already exists')

        # Create or get student
        student, created = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@demo.com',
                'role': 'student',
                'site': site,
            }
        )
        if created:
            student.set_password('demo1234')
            student.save()
            self.stdout.write(f'  Created student: student / demo1234')
        else:
            self.stdout.write(f'  Student already exists')

        # Create roster
        roster, _ = Roster.objects.get_or_create(
            name='Demo Class',
            site=site,
        )
        self.stdout.write(f'  Roster: {roster.name}')

        # Add student to roster
        RosterMembership.objects.get_or_create(
            roster=roster,
            student=student
        )
        self.stdout.write(f'  Added student to roster')

        # Create a demo story
        story, _ = Story.objects.get_or_create(
            title='The Fox and the Grapes',
            instructor=instructor,
            defaults={
                'text_html': '''<p>One hot summer day, a Fox was walking through an orchard when he came upon a bunch of grapes ripening on a vine that had been trained over a lofty branch.</p>
<p>"Just the thing to quench my thirst," said the Fox. Drawing back a few paces, he took a run and jumped, but just missed the grapes.</p>
<p>Turning round again with a one, two, three, he jumped up, but with no greater success. Again and again he tried after the tempting morsel, but at last had to give it up.</p>
<p>Walking away with his nose in the air, he said: "I am sure they are sour anyway."</p>
<p><strong>Moral:</strong> It is easy to despise what you cannot get.</p>''',
                'source_type': 'manual',
                'reading_level_label': 'Grade 4-5',
                'reading_level_metrics': {'word_count': 150, 'flesch_kincaid': 5.2},
            }
        )
        self.stdout.write(f'  Story: {story.title}')

        # Create story segments for card mode
        segments_data = [
            {'index': 0, 'title': 'The Discovery', 'text_html': '<p>One hot summer day, a Fox was walking through an orchard when he came upon a bunch of grapes ripening on a vine that had been trained over a lofty branch.</p>'},
            {'index': 1, 'title': 'First Attempt', 'text_html': '<p>"Just the thing to quench my thirst," said the Fox. Drawing back a few paces, he took a run and jumped, but just missed the grapes.</p>'},
            {'index': 2, 'title': 'Trying Again', 'text_html': '<p>Turning round again with a one, two, three, he jumped up, but with no greater success. Again and again he tried after the tempting morsel, but at last had to give it up.</p>'},
            {'index': 3, 'title': 'The Conclusion', 'text_html': '<p>Walking away with his nose in the air, he said: "I am sure they are sour anyway."</p><p><strong>Moral:</strong> It is easy to despise what you cannot get.</p>'},
        ]
        for seg_data in segments_data:
            StorySegment.objects.get_or_create(
                story=story,
                index=seg_data['index'],
                defaults={'title': seg_data['title'], 'text_html': seg_data['text_html']}
            )
        self.stdout.write(f'  Created {len(segments_data)} story segments')

        # Create glossary and terms
        glossary, _ = Glossary.objects.get_or_create(
            story=story,
            defaults={'language_code': 'en', 'native_language_code': 'vi'}
        )

        terms_data = [
            {'term_text': 'orchard', 'definition_html': 'A piece of land planted with fruit trees', 'translation': 'vườn cây ăn quả', 'part_of_speech': 'noun'},
            {'term_text': 'ripening', 'definition_html': 'Becoming ripe or mature', 'translation': 'chín', 'part_of_speech': 'verb'},
            {'term_text': 'quench', 'definition_html': 'To satisfy (thirst)', 'translation': 'làm dịu cơn khát', 'part_of_speech': 'verb'},
            {'term_text': 'tempting', 'definition_html': 'Attractive or appealing', 'translation': 'hấp dẫn', 'part_of_speech': 'adjective'},
            {'term_text': 'despise', 'definition_html': 'To feel contempt or dislike for', 'translation': 'khinh thường', 'part_of_speech': 'verb'},
        ]
        for term_data in terms_data:
            Term.objects.get_or_create(
                glossary=glossary,
                term_text=term_data['term_text'],
                defaults={
                    'definition_html': term_data['definition_html'],
                    'translation': term_data['translation'],
                    'part_of_speech': term_data['part_of_speech'],
                    'translation_lang_code': 'vi',
                    'is_selected_for_glossary': True,
                }
            )
        self.stdout.write(f'  Created {len(terms_data)} glossary terms')

        # Create a quiz
        quiz, _ = Quiz.objects.get_or_create(
            title='Fox and Grapes Quiz',
            owner=instructor,
            defaults={
                'instructions_html': '<p>Test your comprehension of the story.</p>',
            }
        )

        # Create quiz questions
        questions_data = [
            {
                'prompt_html': 'What did the Fox find in the orchard?',
                'question_type': 'mcq_single',
                'choices': [
                    ('A bunch of grapes', True),
                    ('An apple tree', False),
                    ('A water fountain', False),
                    ('Another fox', False),
                ]
            },
            {
                'prompt_html': 'Why did the Fox want the grapes?',
                'question_type': 'mcq_single',
                'choices': [
                    ('He was hungry', False),
                    ('He was thirsty', True),
                    ('He wanted to sell them', False),
                    ('He wanted to give them away', False),
                ]
            },
            {
                'prompt_html': 'What did the Fox say after giving up?',
                'question_type': 'mcq_single',
                'choices': [
                    ('"I will try again tomorrow"', False),
                    ('"The grapes are too high"', False),
                    ('"I am sure they are sour anyway"', True),
                    ('"I do not like grapes"', False),
                ]
            },
        ]

        for i, q_data in enumerate(questions_data):
            question, _ = ItemBankQuestion.objects.get_or_create(
                prompt_html=q_data['prompt_html'],
                owner=instructor,
                defaults={
                    'question_type': q_data['question_type'],
                    'default_points': 1.0,
                    'status': 'active',
                }
            )

            for j, (text, is_correct) in enumerate(q_data['choices']):
                ItemBankChoice.objects.get_or_create(
                    question=question,
                    text_html=text,
                    defaults={'is_correct': is_correct, 'order': j}
                )

            QuizQuestion.objects.get_or_create(
                quiz=quiz,
                question=question,
                defaults={'order': i}
            )

        self.stdout.write(f'  Created quiz with {len(questions_data)} questions')

        # Create a lesson
        lesson, _ = Lesson.objects.get_or_create(
            title='Reading: The Fox and the Grapes',
            instructor=instructor,
            site=site,
            defaults={
                'story': story,
                'quiz': quiz,
                'introduction_html': '<p>Welcome to this reading lesson! You will read a classic Aesop\'s fable and then take a short quiz to test your understanding.</p>',
                'allowed_modes': ['continuous', 'cards'],
                'default_mode': 'cards',
                'is_active': True,
            }
        )
        lesson.rosters.add(roster)
        self.stdout.write(f'  Lesson: {lesson.title}')

        self.stdout.write(self.style.SUCCESS('\nDemo setup complete!'))
        self.stdout.write('\nYou can now log in as:')
        self.stdout.write('  Student:    student / demo1234')
        self.stdout.write('  Instructor: instructor / demo1234')
