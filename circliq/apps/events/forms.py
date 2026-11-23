from django import forms
from django.utils import timezone

from apps.profiles.forms import check_image
from .models import Event

DT = "%Y-%m-%dT%H:%M"


class EventForm(forms.ModelForm):
    start_at = forms.DateTimeField(input_formats=[DT], widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT))
    end_at = forms.DateTimeField(required=False, input_formats=[DT], widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT))

    class Meta:
        model = Event
        fields = ["title", "description", "category", "start_at", "end_at", "venue", "capacity", "banner"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5, "maxlength": 3000})}

    def clean_banner(self):
        return check_image(self.cleaned_data.get("banner"), 3 * 1024 * 1024)

    def clean_capacity(self):
        c = self.cleaned_data.get("capacity")
        if c is not None and c < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return c

    def clean(self):
        d = super().clean()
        s, e = d.get("start_at"), d.get("end_at")
        if s and not self.instance.pk and s < timezone.now():
            self.add_error("start_at", "Pick a time in the future.")
        if s and e and e <= s:
            self.add_error("end_at", "The event must end after it starts.")
        return d
