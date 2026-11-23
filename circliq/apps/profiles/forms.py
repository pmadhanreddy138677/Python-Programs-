from django import forms

from apps.institutions.models import Department, Program
from .models import AVAILABILITY, COLLAB_PREFS, GOAL_CHOICES, Interest, Profile, Skill

MAX_AVATAR = 2 * 1024 * 1024


def check_image(f, max_bytes=MAX_AVATAR):
    """Shared upload guard: size/type limits, then re-encode (strips EXIF/GPS, bounds dimensions, random file name)."""
    if f and hasattr(f, "size"):
        if f.size > max_bytes:
            raise forms.ValidationError(f"Image must be {max_bytes // (1024 * 1024)} MB or smaller.")
        if getattr(f, "content_type", "") not in ("image/jpeg", "image/png", "image/webp"):
            raise forms.ValidationError("Use a JPG, PNG or WebP image.")
        from django.core.exceptions import ValidationError
        from apps.core.images import sanitize_image
        try:
            return sanitize_image(f)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
    return f


def _clean_avatar(form):
    return check_image(form.cleaned_data.get("avatar"))


class StepProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar", "bio"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3, "placeholder": "A line or two about you…", "maxlength": 300})}

    clean_avatar = lambda self: _clean_avatar(self)  # noqa: E731


class StepInterestsForm(forms.ModelForm):
    interests = forms.ModelMultipleChoiceField(Interest.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    skills = forms.ModelMultipleChoiceField(Skill.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = Profile
        fields = ["interests", "skills"]


class StepGoalsForm(forms.ModelForm):
    goals = forms.MultipleChoiceField(choices=GOAL_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = Profile
        fields = ["goals"]


class ProfileEditForm(StepProfileForm):
    full_name = forms.CharField(max_length=150)
    department = forms.ModelChoiceField(Department.objects.none(), required=False)
    program = forms.ModelChoiceField(Program.objects.none(), required=False)
    academic_year = forms.TypedChoiceField(choices=[("", "—")] + [(i, f"Year {i}") for i in range(1, 6)],
                                           coerce=int, empty_value=None, required=False)
    interests = forms.ModelMultipleChoiceField(Interest.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    skills = forms.ModelMultipleChoiceField(Skill.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    goals = forms.MultipleChoiceField(choices=GOAL_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    availability = forms.MultipleChoiceField(choices=AVAILABILITY, widget=forms.CheckboxSelectMultiple, required=False)
    collab_preferences = forms.MultipleChoiceField(choices=COLLAB_PREFS, widget=forms.CheckboxSelectMultiple, required=False, label="How do you like to collaborate?")

    class Meta(StepProfileForm.Meta):
        fields = ["avatar", "bio", "interests", "skills", "goals", "study_subjects", "availability", "collab_preferences", "is_discoverable", "match_enabled"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3, "maxlength": 300}),
                   "study_subjects": forms.TextInput(attrs={"placeholder": "e.g. DBMS, Python, Statistics"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["department"].queryset = Department.objects.filter(institution_id=user.institution_id)
        self.fields["program"].queryset = Program.objects.filter(institution_id=user.institution_id)
        for f in ("full_name", "department", "program", "academic_year"):
            self.fields[f].initial = getattr(user, f)
        self.order_fields(["full_name", "avatar", "bio", "department", "program", "academic_year",
                           "interests", "skills", "goals", "study_subjects", "availability", "collab_preferences",
                           "is_discoverable", "match_enabled"])

    def save(self, commit=True):
        profile = super().save(commit)
        u, d = self.user, self.cleaned_data
        u.full_name, u.department, u.program = d["full_name"].strip(), d["department"], d["program"]
        u.academic_year = d["academic_year"] if u.is_student else None
        u.save(update_fields=["full_name", "department", "program", "academic_year"])
        return profile
