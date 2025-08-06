from django.db import models

class Test(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

class Question(models.Model):
    QUESTION_TYPES = [
        ('TF', 'True/False'),
        ('MC', 'Multiple Choice'),
        ('TXT', 'Text Answer'),
    ]

    test = models.ForeignKey(Test, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    question_type = models.CharField(max_length=3, choices=QUESTION_TYPES)

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_identifier = models.CharField(max_length=255)
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    text_answer = models.TextField(blank=True)
    is_true_false = models.BooleanField(null=True, blank=True)
