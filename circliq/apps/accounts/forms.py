from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.institutions.models import Department, Program
from .models import User

ACCOUNT_TYPES = [(User.Role.STUDENT, "Student"), (User.Role.FACULTY, "Faculty (needs approval)")]
YEARS = [("", "Select year")] + [(i, f"Year {i}") for i in range(1, 6)]


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    remember_me = forms.BooleanField(required=False, label="Remember me")

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Incorrect email or password.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_email_verified:
            raise ValidationError("Please verify your email first. Check your inbox, or request a new link below.",
                                  code="unverified")


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField(label="University email")
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPES, initial=User.Role.STUDENT)
    department = forms.ModelChoiceField(queryset=Department.objects.none())
    program = forms.ModelChoiceField(queryset=Program.objects.none(), required=False)
    academic_year = forms.TypedChoiceField(choices=YEARS, coerce=int, empty_value=None, required=False)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, institution, **kwargs):
        super().__init__(*args, **kwargs)
        self.institution = institution
        # Scoping choices to the institution prevents cross-institution selection.
        self.fields["department"].queryset = Department.objects.filter(institution=institution)
        self.fields["program"].queryset = Program.objects.filter(institution=institution)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not self.institution.email_allowed(email):
            raise ValidationError(f"Please use your {self.institution.name} email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        elif p1:
            try:
                password_validation.validate_password(p1)
            except ValidationError as exc:
                self.add_error("password1", exc)
        if data.get("account_type") == User.Role.STUDENT:
            if not data.get("program"):
                self.add_error("program", "Please select your program.")
            if not data.get("academic_year"):
                self.add_error("academic_year", "Please select your academic year.")
        return data

    def save(self):
        d = self.cleaned_data
        is_faculty = d["account_type"] == User.Role.FACULTY
        return User.objects.create_user(
            email=d["email"], password=d["password1"], full_name=d["full_name"].strip(),
            role=User.Role.FACULTY if is_faculty else User.Role.STUDENT,  # never admin from public form
            institution=self.institution, department=d["department"],
            program=d.get("program"), academic_year=None if is_faculty else d.get("academic_year"),
            is_approved=not is_faculty,
        )


class ResendVerificationForm(forms.Form):
    email = forms.EmailField()
