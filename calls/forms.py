from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import CallRecord, AudioUpload
import os

class CallRecordForm(forms.ModelForm):
    """Form for creating and editing call records"""

    class Meta:
        model = CallRecord
        fields = [
            'caller_number', 'recipient_number', 'call_start_time',
            'call_end_time', 'duration', 'status'
        ]
        widgets = {
            'call_start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'call_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'duration': forms.TextInput(attrs={'placeholder': 'HH:MM:SS'}),
        }

    def clean_caller_number(self):
        """Validate phone number format"""
        caller_number = self.cleaned_data.get('caller_number')
        if caller_number:
            # Basic phone number validation (allow international format)
            cleaned = ''.join(filter(str.isdigit, caller_number))
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValidationError('Phone number must be between 7 and 15 digits.')
        return caller_number

    def clean_recipient_number(self):
        """Validate phone number format"""
        recipient_number = self.cleaned_data.get('recipient_number')
        if recipient_number:
            cleaned = ''.join(filter(str.isdigit, recipient_number))
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise ValidationError('Phone number must be between 7 and 15 digits.')
        return recipient_number

    def clean(self):
        """Validate that end time is after start time"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('call_start_time')
        end_time = cleaned_data.get('call_end_time')

        if start_time and end_time and end_time <= start_time:
            raise ValidationError('Call end time must be after start time.')

        return cleaned_data

class AudioUploadForm(forms.ModelForm):
    """Form for uploading audio files with security validation"""

    class Meta:
        model = AudioUpload
        fields = ['audio_file', 'format']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make format field optional, we'll try to detect it
        self.fields['format'].required = False
        # Audio file is required
        self.fields['audio_file'].required = True

    def clean_audio_file(self):
        """Validate audio file with size, format, and security checks"""
        audio_file = self.cleaned_data.get('audio_file')

        if audio_file:
            # Check file size
            max_size = getattr(settings, 'UPLOAD_MAX_FILE_SIZE', 100 * 1024 * 1024)
            if audio_file.size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                raise ValidationError(f'Audio file size must be less than {max_size_mb:.0f}MB.')

            # Check file extension
            allowed_formats = getattr(settings, 'UPLOAD_ALLOWED_AUDIO_FORMATS', 
                                    ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'mpeg'])
            file_extension = os.path.splitext(audio_file.name)[1].lower()

            if file_extension not in [f'.{fmt}' for fmt in allowed_formats]:
                raise ValidationError(
                    f'Unsupported file format. Allowed formats: {", ".join(allowed_formats)}'
                )

            # Security check: Verify file doesn't have suspicious content in filename
            if any(char in audio_file.name for char in ['..', '/', '\\', '%']):
                raise ValidationError('Filename contains invalid characters.')

        return audio_file

    def clean_format(self):
        """Auto-detect format if not provided"""
        audio_file = self.cleaned_data.get('audio_file')
        file_format = self.cleaned_data.get('format')
        
        if audio_file and not file_format:
            # Auto-detect format from file extension
            file_extension = os.path.splitext(audio_file.name)[1].lower()
            format_map = {
                '.mp3': 'mp3',
                '.wav': 'wav',
                '.flac': 'flac',
                '.aac': 'aac',
                '.ogg': 'ogg',
                '.m4a': 'm4a',
                '.mpeg': 'mpeg',
            }
            file_format = format_map.get(file_extension, 'mp3')  # Default to mp3 if unknown
            
        return file_format


class CallFilterForm(forms.Form):
    """Form for filtering call records"""

    status = forms.ChoiceField(
        choices=[('', 'All')] + list(CallRecord.CALL_STATUS_CHOICES),
        required=False
    )
    caller_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Caller number'})
    )
    recipient_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Recipient number'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    has_audio = forms.BooleanField(
        required=False,
        label="Has audio recording"
    )
    min_scam_score = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.1', 'placeholder': '0.0 - 1.0'})
    )

class BulkActionForm(forms.Form):
    """Form for bulk actions on call records"""

    ACTION_CHOICES = [
        ('delete', 'Delete selected calls'),
        ('export', 'Export selected calls'),
        ('analyze', 'Send for AI analysis'),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    call_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated list of call IDs"
    )

    def clean_call_ids(self):
        """Validate and parse call IDs"""
        call_ids_str = self.cleaned_data.get('call_ids')
        if not call_ids_str:
            raise ValidationError('No call IDs provided.')

        try:
            call_ids = [id.strip() for id in call_ids_str.split(',') if id.strip()]
            # Validate UUID format
            import uuid
            for call_id in call_ids:
                uuid.UUID(call_id)
            return call_ids
        except ValueError:
            raise ValidationError('Invalid call ID format.')
