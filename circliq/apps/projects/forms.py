from django import forms
from django.utils import timezone

from apps.profiles.models import Skill
from .models import Project, ProjectApplication, ProjectComment, ProjectTask


class ProjectForm(forms.ModelForm):
    required_skills = forms.ModelMultipleChoiceField(Skill.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    deadline = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Project
        fields = ["title", "description", "category", "kind", "required_skills", "technologies", "team_size", "deadline", "goals"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4, "maxlength": 2000}), "goals": forms.Textarea(attrs={"rows": 3, "maxlength": 1000}),
                   "technologies": forms.TextInput(attrs={"placeholder": "Django, React, PostgreSQL"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Only approved faculty can post mentorship / research opportunities.
        if not (user.role == "faculty" and user.is_approved):
            self.fields["kind"].choices = [(Project.Kind.PROJECT, "Student project")]
            self.fields["kind"].initial = Project.Kind.PROJECT

    def clean_kind(self):
        k = self.cleaned_data.get("kind") or Project.Kind.PROJECT
        if k != Project.Kind.PROJECT and not (self.user.role == "faculty" and self.user.is_approved):
            raise forms.ValidationError("Only approved faculty can post this type.")
        return k

    def clean_deadline(self):
        d = self.cleaned_data.get("deadline")
        if d and d < timezone.localdate() and not self.instance.pk:
            raise forms.ValidationError("Deadline must be in the future.")
        return d


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = ProjectApplication
        fields = ["message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "Why do you want to join? What can you contribute?"})}


class ProjectTaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ["title", "assignee"]

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        ids = project.memberships.values_list("user_id", flat=True)
        self.fields["assignee"].queryset = get_user_model().objects.filter(pk__in=ids)
        self.fields["assignee"].required = False
        self.fields["assignee"].empty_label = "Unassigned"


class ProjectCommentForm(forms.ModelForm):
    class Meta:
        model = ProjectComment
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "maxlength": 1000, "placeholder": "Message your team…"})}
