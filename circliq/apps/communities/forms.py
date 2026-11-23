from django import forms

from apps.profiles.forms import check_image
from .models import Community


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ["name", "description", "category", "visibility", "rules", "icon", "banner"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
            "rules": forms.Textarea(attrs={"rows": 4, "maxlength": 1500, "placeholder": "e.g. Be kind. No spam. Stay on topic."}),
        }

    def __init__(self, *args, institution, **kwargs):
        super().__init__(*args, **kwargs)
        self.institution = institution

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Community.objects.filter(institution=self.institution, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A community with this name already exists.")
        return name

    def clean_icon(self):
        return check_image(self.cleaned_data.get("icon"))

    def clean_banner(self):
        return check_image(self.cleaned_data.get("banner"), 3 * 1024 * 1024)
