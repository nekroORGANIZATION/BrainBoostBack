from django.db import models
from course.models import Course  # ссылка на модель курса
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
        return f'Theory for {self.lesson.course.title}'


class Test(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='test')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    max_score = models.IntegerField(default=0)

    def __str__(self):
        return f"Test for {self.lesson.title}"


class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='test_questions')
    question_text = models.TextField()

    def __str__(self):
        return f'Question: {self.question_text} for {self.lesson.title}'


class TestAnswer(models.Model):
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f'Answer: {self.answer_text} for {self.question.question_text}'


class TrueFalseQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='true_false_questions')
    question_text = models.TextField()
    is_true = models.BooleanField()

    def __str__(self):
        return f'True/False Question: {self.question_text} for {self.lesson.title}'


class OpenQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='open_questions')
    question_text = models.TextField()
    correct_answer = models.TextField()

    def __str__(self):
        return f'Open Question: {self.question_text} for {self.lesson.title}'
