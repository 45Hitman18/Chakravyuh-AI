from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import uuid

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('analysis_complete', 'Analysis Complete'),
        ('high_risk_alert', 'High Risk Alert'),
        ('honeypot_engaged', 'Honeypot Engaged'),
        ('admin_review', 'Admin Review Required'),
        ('law_enforcement', 'Law Enforcement Notification'),
        ('system_alert', 'System Alert'),
    ]

    DELIVERY_METHODS = [
        ('email', 'Email'),
        ('dashboard', 'Dashboard'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHODS, default='dashboard')
    related_call = models.ForeignKey('calls.CallRecord', on_delete=models.SET_NULL, null=True, blank=True)
    related_analysis = models.ForeignKey('analysis.AIAnalysisResult', on_delete=models.SET_NULL, null=True, blank=True)
    related_report = models.ForeignKey('reports.Report', on_delete=models.SET_NULL, null=True, blank=True)
    data = models.JSONField(default=dict)  # Additional context data
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority', 'created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}: {self.title}"

    def send_email(self):
        """Send notification via email"""
        try:
            subject = f"[{self.get_priority_display()}] {self.title}"

            # Choose template based on notification type
            template_map = {
                'analysis_complete': 'emails/analysis_complete.html',
                'high_risk_alert': 'emails/high_risk_alert.html',
                'honeypot_engaged': 'emails/honeypot_engaged.html',
                'admin_review': 'emails/admin_review.html',
                'law_enforcement': 'emails/law_enforcement_alert.html',
            }

            template = template_map.get(self.notification_type, 'emails/default.html')

            # Prepare context
            context = {
                'notification': self,
                'user': self.user,
                'site': {
                    'name': 'Chakravyuh Cybersecurity Platform',
                    'domain': 'https://chakravyuh.example.com'  # Replace with actual domain
                }
            }

            # Add related objects to context
            if self.related_call:
                context['call'] = self.related_call
            if self.related_analysis:
                context['analysis'] = self.related_analysis
                if hasattr(self.related_analysis, 'scam_probability'):
                    context['scam_score'] = self.related_analysis.scam_probability
            if self.related_report:
                context['report'] = self.related_report

            # Add custom data
            context.update(self.data)

            # Render email
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email='noreply@chakravyuh.com',
                recipient_list=[self.user.email],
                html_message=html_message,
                fail_silently=False
            )

            self.is_sent = True
            self.sent_at = timezone.now()
            self.save()

            return True
        except Exception as e:
            # Log error but don't fail
            print(f"Failed to send email notification: {e}")
            return False

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save()

class NotificationSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_settings')
    email_analysis_complete = models.BooleanField(default=True)
    email_high_risk_alert = models.BooleanField(default=True)
    email_honeypot_engaged = models.BooleanField(default=False)
    email_admin_review = models.BooleanField(default=False)
    email_law_enforcement = models.BooleanField(default=False)
    email_system_alert = models.BooleanField(default=True)

    dashboard_analysis_complete = models.BooleanField(default=True)
    dashboard_high_risk_alert = models.BooleanField(default=True)
    dashboard_honeypot_engaged = models.BooleanField(default=True)
    dashboard_admin_review = models.BooleanField(default=True)
    dashboard_law_enforcement = models.BooleanField(default=False)
    dashboard_system_alert = models.BooleanField(default=True)

    sms_high_risk_alert = models.BooleanField(default=False)
    sms_law_enforcement = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification settings for {self.user.username}"
