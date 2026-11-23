from django import forms
from django.utils import timezone

from .models import Circle, CircleMembership, CirclePost, CircleResource, CircleTask, StudySession

DT = "%Y-%m-%dT%H:%M"


class CircleForm(forms.ModelForm):
    class Meta:
        model = Circle
        fields = ["name", "purpose", "category", "max_members", "join_policy"]
        widgets = {"purpose": forms.Textarea(attrs={"rows": 3, "maxlength": 400})}


class CirclePostForm(forms.ModelForm):
    class Meta:
        model = CirclePost
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "maxlength": 1000, "placeholder": "Share an update or ask the group…"})}

    def clean_body(self):
        b = self.cleaned_data["body"].strip()
        if not b:
            raise forms.ValidationError("Write something first.")
        return b


class ResourceForm(forms.ModelForm):
    class Meta:
        model = CircleResource
        fields = ["title", "url", "note"]
        widgets = {"url": forms.URLInput(attrs={"placeholder": "https://…"})}


class SessionForm(forms.ModelForm):
    starts_at = forms.DateTimeField(input_formats=[DT], widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT))

    class Meta:
        model = StudySession
        fields = ["title", "starts_at", "duration_minutes", "mode", "location", "notes"]

    def clean_starts_at(self):
        v = self.cleaned_data["starts_at"]
        if v < timezone.now():
            raise forms.ValidationError("Pick a time in the future.")
        return v


class TaskForm(forms.ModelForm):
    class Meta:
        model = CircleTask
        fields = ["title", "assignee"]

    def __init__(self, *args, circle, **kwargs):
        super().__init__(*args, **kwargs)
        ids = CircleMembership.objects.filter(circle=circle, status="active").values_list("user_id", flat=True)
        from django.contrib.auth import get_user_model
        self.fields["assignee"].queryset = get_user_model().objects.filter(pk__in=ids)
        self.fields["assignee"].required = False
        self.fields["assignee"].empty_label = "Unassigned"
