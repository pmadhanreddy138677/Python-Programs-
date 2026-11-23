from django.contrib import admin
from .models import Answer, AskReport, Question

admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(AskReport)
