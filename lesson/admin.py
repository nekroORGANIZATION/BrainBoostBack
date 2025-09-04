from django.contrib import admin

from .models import Lesson
from .models import Module
from .models import LessonContent, LessonProgress

admin.site.register(Lesson)
admin.site.register(Module)
admin.site.register(LessonContent)
admin.site.register(LessonProgress)
