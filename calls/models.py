from django.db import models
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid

class CallRecord(models.Model):
    CALL_STATUS_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('missed', 'Missed'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caller_number = models.CharField(max_length=20, db_index=True)
    recipient_number = models.CharField(max_length=20, db_index=True)
    call_start_time = models.DateTimeField(db_index=True)
    call_end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='incoming')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-call_start_time']
        indexes = [
            models.Index(fields=['caller_number', 'call_start_time']),
            models.Index(fields=['recipient_number', 'call_start_time']),
        ]

    def __str__(self):
        return f"Call from {self.caller_number} to {self.recipient_number} at {self.call_start_time}"

class AudioUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_record = models.OneToOneField(CallRecord, on_delete=models.CASCADE, related_name='audio')
    audio_file = models.FileField(upload_to='call_recordings/', storage=default_storage)
    file_size = models.PositiveIntegerField()
    duration = models.DurationField(null=True, blank=True)
    format = models.CharField(max_length=10)  # mp3, wav, etc.
    checksum = models.CharField(max_length=128)  # For integrity verification
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Audio for call {self.call_record.id}"

    def save(self, *args, **kwargs):
        if self.audio_file:
            self.file_size = self.audio_file.size
            if not self.checksum:
                import hashlib
                self.audio_file.seek(0)
                self.checksum = hashlib.sha256(self.audio_file.read()).hexdigest()
                self.audio_file.seek(0)  # Reset file pointer
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the file from storage when the model is deleted
        if self.audio_file:
            if default_storage.exists(self.audio_file.name):
                default_storage.delete(self.audio_file.name)
        super().delete(*args, **kwargs)
