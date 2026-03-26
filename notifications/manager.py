from .models import Notification, NotificationSettings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """Centralized notification management system"""

    @staticmethod
    def create_notification(user, notification_type, title, message, priority='medium',
                          delivery_methods=None, related_call=None, related_analysis=None,
                          related_report=None, data=None, expires_days=30):
        """
        Create and send notifications based on user preferences
        """
        if delivery_methods is None:
            delivery_methods = ['dashboard']

        if data is None:
            data = {}

        # Get user notification settings
        settings, created = NotificationSettings.objects.get_or_create(user=user)

        notifications_created = []

        for method in delivery_methods:
            # Check if user wants this type of notification via this method
            setting_attr = f"{method}_{notification_type}"
            if hasattr(settings, setting_attr) and getattr(settings, setting_attr):

                # Create notification
                notification = Notification.objects.create(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    priority=priority,
                    delivery_method=method,
                    related_call=related_call,
                    related_analysis=related_analysis,
                    related_report=related_report,
                    data=data,
                    expires_at=timezone.now() + timedelta(days=expires_days)
                )

                # Send immediately for email
                if method == 'email':
                    notification.send_email()

                notifications_created.append(notification)
                logger.info(f"Created {method} notification for {user.username}: {title}")

        return notifications_created

    @staticmethod
    def notify_analysis_complete(user, analysis):
        """Notify user when analysis is complete"""
        scam_score = getattr(analysis, 'scam_probability', None)

        if scam_score and scam_score.overall_score >= 0.8:
            priority = 'high'
            title = "High Risk Call Detected!"
        elif scam_score and scam_score.overall_score >= 0.6:
            priority = 'medium'
            title = "Potential Scam Call Detected"
        else:
            priority = 'low'
            title = "Call Analysis Complete"

        message = f"Analysis of call from {analysis.call_record.caller_number} is complete."

        data = {
            'scam_score': scam_score.overall_score if scam_score else None,
            'scam_level': scam_score.get_scam_level_display() if scam_score else None,
            'confidence': analysis.confidence_score,
        }

        return NotificationManager.create_notification(
            user=user,
            notification_type='analysis_complete',
            title=title,
            message=message,
            priority=priority,
            delivery_methods=['dashboard', 'email'],
            related_call=analysis.call_record,
            related_analysis=analysis,
            data=data
        )

    @staticmethod
    def notify_high_risk_alert(user, analysis, scam_score):
        """Notify user of high-risk calls"""
        title = "🚨 CRITICAL: High-Risk Scam Call Detected!"
        message = f"Call from {analysis.call_record.caller_number} shows high scam probability ({scam_score.overall_score:.1%})"

        data = {
            'scam_score': scam_score.overall_score,
            'scam_level': scam_score.scam_level,
            'recommendations': [
                "Do not share any personal information",
                "Hang up immediately",
                "Block the number",
                "Report to local authorities",
                "Consider filing a formal complaint"
            ]
        }

        return NotificationManager.create_notification(
            user=user,
            notification_type='high_risk_alert',
            title=title,
            message=message,
            priority='critical',
            delivery_methods=['dashboard', 'email'],
            related_call=analysis.call_record,
            related_analysis=analysis,
            data=data
        )

    @staticmethod
    def notify_honeypot_engaged(user, honeypot_session, scammer_profile):
        """Notify when honeypot is engaged"""
        title = "Honeypot Engaged"
        message = f"AI honeypot has been engaged for suspicious number {scammer_profile.phone_number}"

        data = {
            'session_name': honeypot_session.session_name,
            'scammer_phone': scammer_profile.phone_number,
            'risk_score': scammer_profile.risk_score,
        }

        return NotificationManager.create_notification(
            user=user,
            notification_type='honeypot_engaged',
            title=title,
            message=message,
            priority='medium',
            delivery_methods=['dashboard'],
            data=data
        )

    @staticmethod
    def notify_admin_review_required(analysis, scam_score):
        """Notify admins when high-risk analysis requires review"""
        from accounts.models import CustomUser

        title = "Admin Review Required: High-Risk Analysis"
        message = f"Call from {analysis.call_record.caller_number} requires admin review (Score: {scam_score.overall_score:.3f})"

        data = {
            'analysis_id': str(analysis.id),
            'call_id': str(analysis.call_record.id),
            'scam_score': scam_score.overall_score,
            'user': analysis.call_record.recorded_by.username,
        }

        # Notify all admin users
        admins = CustomUser.objects.filter(role='admin')
        notifications = []

        for admin in admins:
            notifications.extend(NotificationManager.create_notification(
                user=admin,
                notification_type='admin_review',
                title=title,
                message=message,
                priority='high',
                delivery_methods=['dashboard', 'email'],
                related_call=analysis.call_record,
                related_analysis=analysis,
                data=data
            ))

        return notifications

    @staticmethod
    def notify_law_enforcement(report):
        """Notify law enforcement of escalated cases"""
        from accounts.models import CustomUser

        title = "Law Enforcement Alert: Scam Case Escalated"
        message = f"Case #{report.id} has been escalated to law enforcement: {report.title}"

        data = {
            'report_id': str(report.id),
            'priority': report.priority,
            'description': report.description[:200],
            'submitted_by': report.submitted_by.username,
        }

        # Notify all law enforcement users
        le_users = CustomUser.objects.filter(role='law_enforcement')
        notifications = []

        for le_user in le_users:
            notifications.extend(NotificationManager.create_notification(
                user=le_user,
                notification_type='law_enforcement',
                title=title,
                message=message,
                priority='high',
                delivery_methods=['dashboard', 'email'],
                related_report=report,
                data=data
            ))

        return notifications

    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications for user"""
        return Notification.objects.filter(
            user=user,
            is_read=False,
            expires_at__gt=timezone.now()
        ).count()

    @staticmethod
    def get_recent_notifications(user, limit=10):
        """Get recent notifications for user"""
        return Notification.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')[:limit]

    @staticmethod
    def cleanup_expired_notifications():
        """Remove expired notifications"""
        expired_count = Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()

        logger.info(f"Cleaned up {expired_count[0]} expired notifications")
        return expired_count[0]
