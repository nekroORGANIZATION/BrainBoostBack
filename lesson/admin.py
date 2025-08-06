from django.contrib import admin

from .models import Lesson, CourseTheory, TestQuestion, TestAnswer, TrueFalseQuestion, OpenQuestion, Test, TestAttempt, QuestionAttempt

admin.site.register(Lesson)
admin.site.register(CourseTheory)
admin.site.register(TestQuestion)
admin.site.register(TestAnswer)
admin.site.register(TrueFalseQuestion)
admin.site.register(OpenQuestion)
admin.site.register(Test)
admin.site.register(TestAttempt)
admin.site.register(QuestionAttempt)

# Register your models here.
