from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"

    def ready(self):
        from django import forms
        from .forms import LabelledBoundField
        # Every rendered form control gets an accessible name (its label) unless it already has one.
        forms.forms.BaseForm.bound_field_class = LabelledBoundField
