from django.contrib import admin
from .models import Test, Question, Choice, Answer

# Register your models here.
admin.site.register(Test)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(Answer)
