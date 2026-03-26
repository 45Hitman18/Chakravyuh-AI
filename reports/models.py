from django.db import models
from django.conf import settings
from django.core.files.storage import default_storage
import uuid

class Report(models.Model):
    REPORT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
    ]

    REPORT_TYPE_CHOICES = [
        ('scam_call', 'Scam Call Report'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('honeypot_interaction', 'Honeypot Interaction'),
        ('investigation', 'Investigation Report'),
        ('follow_up', 'Follow-up Report'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='draft')
    description = models.TextField()
    incident_date = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    involved_parties = models.JSONField(default=dict)  # Names, numbers, etc.
    call_record = models.ForeignKey('calls.CallRecord', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    scammer_profile = models.ForeignKey('honeypot.ScammerProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    honeypot_session = models.ForeignKey('honeypot.HoneypotSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    ai_analysis = models.ForeignKey('analysis.AIAnalysisResult', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    scam_probability = models.ForeignKey('analysis.ScamProbabilityScore', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_reports')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reports')
    priority = models.CharField(max_length=20, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium')
    tags = models.JSONField(default=list)  # For categorization
    internal_notes = models.TextField(blank=True, null=True)
    public_summary = models.TextField(blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"{self.report_type}: {self.title} - {self.status}"

class EvidenceFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('audio', 'Audio Recording'),
        ('transcript', 'Transcript'),
        ('screenshot', 'Screenshot'),
        ('document', 'Document'),
        ('log', 'Log File'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='evidence_files')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='evidence/', storage=default_storage)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=128)  # For integrity verification
    description = models.TextField(blank=True, null=True)
    is_encrypted = models.BooleanField(default=False)
    encryption_key = models.CharField(max_length=256, blank=True, null=True)  # Store securely in production
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        unique_together = ['report', 'checksum']  # Prevent duplicate files

    def __str__(self):
        return f"Evidence: {self.file_name} for report {self.report.id}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete the file from storage when the model is deleted
        if self.file:
            if default_storage.exists(self.file.name):
                default_storage.delete(self.file.name)
        super().delete(*args, **kwargs)
