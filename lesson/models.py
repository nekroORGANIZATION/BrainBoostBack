from django.db import models
from course.models import Course
from django.conf import settings

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return f'Lesson: {self.title} in {self.course.title}'


class CourseTheory(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='theories')
    theory_text = models.TextField()
    image = models.ImageField(upload_to='theory_images/', blank=True, null=True)

    def __str__(self):
        return f'Theory for {self.lesson.title}'


# Тест, связанный с уроком
class Test(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=200)

    def __str__(self):
        return f'Test: {self.title} for lesson {self.lesson.title}'


# Вопрос с вариантами ответов (множественный выбор)
class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='test_questions')
    question_text = models.TextField()

    def __str__(self):
        return f'MC Question: {self.question_text[:50]}'


class TestAnswer(models.Model):
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f'Answer: {self.answer_text[:50]} (Correct: {self.is_correct})'


# Вопрос True/False
class TrueFalseQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='true_false_questions')
    question_text = models.TextField()
    correct_answer = models.BooleanField()

    def __str__(self):
        return f'TF Question: {self.question_text[:50]}'


# Открытый вопрос (текстовый ответ)
class OpenQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='open_questions')
    question_text = models.TextField()

    def __str__(self):
        return f'Open Question: {self.question_text[:50]}'


class TestAttempt(models.Model):
    test = models.ForeignKey('Test', on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)


class QuestionAttempt(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='question_attempts')
    question_text = models.TextField()
    user_answer = models.TextField()
    correct_answer = models.TextField()
    is_correct = models.BooleanField()

    class Meta:
        unique_together = ('attempt', 'question_text')

class TestAnswerAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey('TestQuestion', on_delete=models.CASCADE)
    selected_answer = models.ForeignKey('TestAnswer', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
