from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from course.models import Course
from lesson.models import Lesson, CourseTheory

User = get_user_model()

class Command(BaseCommand):
    help = 'Заповнення бази україномовними курсами, уроками та теоріями'

    def handle(self, *args, **kwargs):
        # Очистка
        Course.objects.all().delete()
        Lesson.objects.all().delete()
        CourseTheory.objects.all().delete()

        # Создание учителя
        teacher, _ = User.objects.get_or_create(
            username='teacher',
            defaults={
                'email': 'teacher@example.com',
                'is_teacher': True,
                'password': 'pbkdf2_sha256$260000$example$examplehashedpassword'
            }
        )

        # Создание студента
        student, _ = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@example.com',
                'is_teacher': False,
                'password': 'pbkdf2_sha256$260000$example$examplehashedpassword'
            }
        )

        # Список курсов
        courses_data = [
            {
                'title': 'Базовий курс з фізики',
                'description': 'Основи фізики для початківців.',
                'topic': 'Фізика'
            },
            {
                'title': 'Курс з хімії: Вступ',
                'description': 'Ознайомлення з базовими поняттями хімії.',
                'topic': 'Хімія'
            },
            {
                'title': 'Біологія людини',
                'description': 'Курс про будову та функції людського організму.',
                'topic': 'Біологія'
            }
        ]

        for course_data in courses_data:
            course = Course.objects.create(
                title=course_data['title'],
                description=course_data['description'],
                price=0.00,
                author='Іван Петренко',
                language='Українська',
                topic=course_data['topic'],
                rating=4.7
            )

            # Создание урока для каждого курса
            lesson = Lesson.objects.create(
                course=course,
                title=f'Вступ до курсу "{course.title}"',
                description=f'Це перший урок курсу "{course.title}".'
            )

            # Добавление теории
            CourseTheory.objects.create(
                lesson=lesson,
                theory_text=f'Теоретичний матеріал для курсу "{course.title}". Тут описуються базові поняття теми "{course.topic}".'
            )

        self.stdout.write(self.style.SUCCESS('База даних успішно заповнена: курси, уроки, теорії, учитель, студент.'))
