from django import forms

from apps.communities.models import Community
from apps.profiles.forms import check_image
from .models import Comment, Post


class PostForm(forms.ModelForm):
    community = forms.ModelChoiceField(Community.objects.none(), empty_label=None)

    class Meta:
        model = Post
        fields = ["community", "kind", "title", "body", "image"]
        widgets = {"body": forms.Textarea(attrs={"class": "input", "rows": 3, "maxlength": 5000, "placeholder": "Start a discussion, ask a question or share an idea…"}),
                   "title": forms.TextInput(attrs={"placeholder": "Title (required for questions and projects)"})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.communities.models import CommunityMembership as M
        ids = M.objects.filter(user=user, status="active").values_list("community_id", flat=True)
        self.fields["community"].queryset = Community.objects.filter(pk__in=ids, institution_id=user.institution_id)

    def clean_image(self):
        return check_image(self.cleaned_data.get("image"), 3 * 1024 * 1024)

    def clean(self):
        d = super().clean()
        if d.get("kind") in ("question", "project") and not (d.get("title") or "").strip():
            self.add_error("title", "Please add a title.")
        if d.get("body") is not None and not d["body"].strip():
            self.add_error("body", "Write something first.")
        return d


class PostEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 6, "maxlength": 5000})}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "maxlength": 2000, "placeholder": "Write a comment…"})}
