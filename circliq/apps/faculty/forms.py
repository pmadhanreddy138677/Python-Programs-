from django import forms

from .models import Announcement, FacultyProfile, MentorshipRequest


class FacultyProfileForm(forms.ModelForm):
    class Meta:
        model = FacultyProfile
        fields = ["designation", "expertise", "research_interests", "office_hours", "allow_direct_messages", "accepts_mentorship"]
        widgets = {"research_interests": forms.Textarea(attrs={"rows": 4, "maxlength": 800}),
                   "designation": forms.TextInput(attrs={"placeholder": "e.g. Assistant Professor"})}


class MentorshipForm(forms.ModelForm):
    class Meta:
        model = MentorshipRequest
        fields = ["message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "What would you like guidance on?"})}

    def clean_message(self):
        m = self.cleaned_data["message"].strip()
        if not m:
            raise forms.ValidationError("Tell the faculty member what you're looking for.")
        return m


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "link"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5, "maxlength": 3000}), "link": forms.URLInput(attrs={"placeholder": "https:// (optional)"})}
