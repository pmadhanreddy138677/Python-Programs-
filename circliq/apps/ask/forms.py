from django import forms

from .models import Answer, AnswerComment, AskReport, Question


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["category", "title", "body"]
        widgets = {"title": forms.TextInput(attrs={"placeholder": "Ask clearly, e.g. How do I normalise this table to 3NF?"}),
                   "body": forms.Textarea(attrs={"rows": 6, "maxlength": 3000, "placeholder": "Add the details, what you tried, and what you expected."})}

    def clean_title(self):
        t = self.cleaned_data["title"].strip()
        if len(t) < 8:
            raise forms.ValidationError("Make the title a little more descriptive.")
        return t


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5, "maxlength": 3000, "placeholder": "Write a helpful answer…"})}

    def clean_body(self):
        b = self.cleaned_data["body"].strip()
        if len(b) < 5:
            raise forms.ValidationError("Write a bit more.")
        return b


class CommentForm(forms.ModelForm):
    class Meta:
        model = AnswerComment
        fields = ["body"]
        widgets = {"body": forms.TextInput(attrs={"placeholder": "Add a comment…", "maxlength": 500})}


class ReportForm(forms.ModelForm):
    class Meta:
        model = AskReport
        fields = ["reason"]
