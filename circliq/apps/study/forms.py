from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import StudyRequest


class StudyRequestForm(forms.ModelForm):
    group_size = forms.IntegerField(label="Preferred group size", min_value=2, max_value=12, initial=4)

    class Meta:
        model = StudyRequest
        fields = ["subject", "topic", "description", "goal", "group_size", "schedule", "mode"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3, "maxlength": 600}),
                   "subject": forms.TextInput(attrs={"placeholder": "e.g. DBMS"}),
                   "topic": forms.TextInput(attrs={"placeholder": "e.g. Normalization and SQL joins"}),
                   "goal": forms.TextInput(attrs={"placeholder": "e.g. Prepare for the mid-sem exam"})}
