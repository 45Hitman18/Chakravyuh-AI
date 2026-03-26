from django import forms
from .models import Report


class ReportForm(forms.ModelForm):
    incident_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        required=True,
    )

    class Meta:
        model = Report
        fields = [
            "title",
            "report_type",
            "description",
            "incident_date",
            "location",
            "call_record",
            "ai_analysis",
            "priority",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
