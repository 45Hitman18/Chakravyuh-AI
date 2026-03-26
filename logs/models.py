from django.db import models
from django.conf import settings
import uuid

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload', 'Upload'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('analyze', 'Analyze'),
        ('report', 'Report'),
    ]

    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    RESOURCE_CHOICES = [
        ('user', 'User'),
        ('call_record', 'Call Record'),
        ('audio_upload', 'Audio Upload'),
        ('ai_analysis', 'AI Analysis'),
        ('scam_score', 'Scam Score'),
        ('honeypot_session', 'Honeypot Session'),
        ('scammer_profile', 'Scammer Profile'),
        ('report', 'Report'),
        ('evidence_file', 'Evidence File'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_CHOICES)
    resource_id = models.UUIDField(null=True, blank=True)  # ID of the affected resource
    resource_name = models.CharField(max_length=255, blank=True, null=True)  # Human-readable name
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)  # Additional context about the action
    old_values = models.JSONField(default=dict)  # For update actions
    new_values = models.JSONField(default=dict)  # For create/update actions
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    duration = models.DurationField(null=True, blank=True)  # For operations that take time

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'resource_type', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} {self.action} {self.resource_type} at {self.timestamp}"

class SystemLog(models.Model):
    LOG_LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    COMPONENT_CHOICES = [
        ('auth', 'Authentication'),
        ('calls', 'Call Processing'),
        ('analysis', 'AI Analysis'),
        ('storage', 'File Storage'),
        ('api', 'API'),
        ('database', 'Database'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default='info')
    component = models.CharField(max_length=20, choices=COMPONENT_CHOICES)
    message = models.TextField()
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    hostname = models.CharField(max_length=100, blank=True, null=True)
    process_id = models.PositiveIntegerField(null=True, blank=True)
    thread_id = models.CharField(max_length=50, blank=True, null=True)
    request_id = models.UUIDField(null=True, blank=True)  # For tracking related logs

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level', 'component', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['request_id']),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.component}: {self.message[:50]}..."
