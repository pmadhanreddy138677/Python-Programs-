from django.core.validators import URLValidator

http_only = URLValidator(schemes=["http", "https"])


from django.forms import BoundField, CheckboxInput, CheckboxSelectMultiple, HiddenInput, MultiWidget, RadioSelect  # noqa: E402


class LabelledBoundField(BoundField):
    """Adds aria-label=<field label> to single-control widgets so raw `{{ form.field }}` output is never unlabelled.
    Skipped for checkbox/radio groups (each option has its own label) and single checkboxes (always wrapped in a <label>)."""

    def build_widget_attrs(self, attrs, widget=None):
        attrs = super().build_widget_attrs(attrs, widget)
        w = widget or self.field.widget
        if not isinstance(w, (CheckboxInput, CheckboxSelectMultiple, RadioSelect, MultiWidget, HiddenInput)) and "aria-label" not in attrs and "aria-label" not in w.attrs:
            attrs["aria-label"] = str(self.label)
        return attrs
