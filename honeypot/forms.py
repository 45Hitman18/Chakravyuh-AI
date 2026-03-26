from django import forms
from django.core.exceptions import ValidationError
from .models import HoneypotSession, HoneypotInteraction, ScammerProfile
from .ai_agent import ScamType
import json

class HoneypotSessionForm(forms.ModelForm):
    """Form for creating and editing honeypot sessions"""

    class Meta:
        model = HoneypotSession
        fields = [
            'session_name', 'phone_number', 'description',
            'status', 'assigned_to'
        ]
        widgets = {
            'session_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter session name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-800-XXXX-XXXX'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Describe the honeypot setup...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_phone_number(self):
        """Validate phone number format"""
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Basic phone number validation (allow international format)
            cleaned = ''.join(filter(str.isdigit, phone_number))
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValidationError('Phone number must be between 7 and 15 digits.')
        return phone_number

class HoneypotInteractionForm(forms.Form):
    """Form for manual honeypot interactions"""

    scammer_message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Enter the scammer\'s message...'}),
        label="Scammer's Message",
        required=True
    )

    call_context = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        initial='{}'
    )

class ScammerProfileForm(forms.ModelForm):
    """Form for creating and editing scammer profiles"""

    class Meta:
        model = ScammerProfile
        fields = [
            'phone_number', 'name',
            'scam_types', 'risk_score', 'notes', 'status'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1-800-XXXX-XXXX'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scammer name or alias'}),
            'scam_types': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Observations and notes...'}),
            'risk_score': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '1', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for scam_types
        self.fields['scam_types'].choices = [(scam.value, scam.value.title()) for scam in ScamType]

    def clean_phone_number(self):
        """Validate phone number format"""
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Basic phone number validation (allow international format)
            cleaned = ''.join(filter(str.isdigit, phone_number))
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValidationError('Phone number must be between 7 and 15 digits.')
        return phone_number

    def clean_risk_score(self):
        """Validate risk score range"""
        risk_score = self.cleaned_data.get('risk_score')
        if risk_score is not None and (risk_score < 0 or risk_score > 1):
            raise ValidationError('Risk score must be between 0 and 1.')
        return risk_score

class HoneypotConfigurationForm(forms.Form):
    """Form for honeypot session configuration"""

    # Personality settings
    personality_name = forms.CharField(
        max_length=100,
        initial='John Smith',
        help_text="The name the honeypot will use",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., John Smith'})
    )

    personality_age = forms.IntegerField(
        min_value=18,
        max_value=100,
        initial=35,
        help_text="Age of the honeypot persona",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '100'})
    )

    personality_occupation = forms.CharField(
        max_length=100,
        initial='Office Worker',
        help_text="Occupation of the honeypot persona",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Office Worker'})
    )

    personality_location = forms.CharField(
        max_length=100,
        initial='New York',
        help_text="Location of the honeypot persona",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., New York'})
    )

    # Behavior settings
    max_conversation_length = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        help_text="Maximum number of turns in a conversation",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '50'})
    )

    resistance_threshold = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.3,
        widget=forms.NumberInput(attrs={'step': '0.1', 'class': 'form-control', 'min': '0', 'max': '1'}),
        help_text="Threshold for showing resistance to scam attempts (0-1)"
    )

    enable_auto_termination = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Automatically terminate suspicious conversations",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    scam_type_focus = forms.ChoiceField(
        choices=[('', 'All Types')] + [(scam.value, scam.value.title()) for scam in ScamType],
        required=False,
        help_text="Focus on specific scam type (leave empty for all)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_resistance_threshold(self):
        """Validate resistance threshold range"""
        threshold = self.cleaned_data.get('resistance_threshold')
        if threshold is not None and (threshold < 0 or threshold > 1):
            raise ValidationError('Resistance threshold must be between 0 and 1.')
        return threshold
