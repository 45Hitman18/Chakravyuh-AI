from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from logs.models import AuditLog
from calls.models import AudioUpload
from analysis.models import AIAnalysisResult
from reports.models import Report
from notifications.manager import NotificationManager


def _create_audit_log(user=None, action="view", resource_type="system", resource_id=None,
                      resource_name=None, severity="info", details=None, request=None):
    details = details or {}
    details.setdefault("severity", severity)

    ip_address = None
    user_agent = None
    session_id = None
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")
        session_id = request.session.session_key

    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
        severity=severity,
        details=details,
    )


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    _create_audit_log(
        user=user,
        action="login",
        resource_type="user",
        resource_id=getattr(user, "id", None),
        resource_name=getattr(user, "username", None),
        severity="info",
        details={"event": "login"},
        request=request,
    )


@receiver(post_save, sender=AudioUpload)
def log_audio_upload(sender, instance, created, **kwargs):
    if not created:
        return

    _create_audit_log(
        user=instance.uploaded_by,
        action="upload",
        resource_type="audio_upload",
        resource_id=getattr(instance, "id", None),
        resource_name=getattr(instance, "audio_file", None),
        severity="info",
        details={
            "event": "upload",
            "call_id": str(instance.call_record_id) if instance.call_record_id else None,
        },
    )


@receiver(pre_save, sender=AIAnalysisResult)
def cache_previous_analysis_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        previous = AIAnalysisResult.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except AIAnalysisResult.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=AIAnalysisResult)
def log_analysis_completion(sender, instance, created, **kwargs):
    if instance.status != "completed":
        return

    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == "completed":
        return

    scam_score = getattr(instance, "scam_probability", None)
    overall_score = getattr(scam_score, "overall_score", None)

    severity = "info"
    if overall_score is not None:
        if overall_score >= 0.8:
            severity = "critical"
        elif overall_score >= 0.6:
            severity = "high"
        elif overall_score >= 0.4:
            severity = "medium"
        else:
            severity = "low"

    _create_audit_log(
        user=instance.requested_by,
        action="analyze",
        resource_type="ai_analysis",
        resource_id=getattr(instance, "id", None),
        resource_name=str(instance),
        severity=severity,
        details={
            "event": "analysis_completed",
            "call_id": str(instance.call_record_id) if instance.call_record_id else None,
            "scam_score": overall_score,
        },
    )

    if instance.requested_by:
        NotificationManager.notify_analysis_complete(instance.requested_by, instance)
        if overall_score is not None and overall_score >= 0.8:
            NotificationManager.notify_high_risk_alert(instance.requested_by, instance, scam_score)


@receiver(pre_save, sender=Report)
def cache_previous_report_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        previous = Report.objects.get(pk=instance.pk)
        instance._previous_status = previous.status
    except Report.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Report)
def log_report_filed(sender, instance, created, **kwargs):
    if created:
        event = "report_filed"
        should_log = True
    else:
        previous_status = getattr(instance, "_previous_status", None)
        should_log = previous_status != instance.status and instance.status in {"submitted", "escalated"}
        event = "report_status_changed"

    if not should_log:
        return

    severity = "medium"
    if instance.priority in {"high", "critical"}:
        severity = "high" if instance.priority == "high" else "critical"

    _create_audit_log(
        user=instance.created_by,
        action="report",
        resource_type="report",
        resource_id=getattr(instance, "id", None),
        resource_name=instance.title,
        severity=severity,
        details={
            "event": event,
            "status": instance.status,
            "priority": instance.priority,
        },
    )

    if instance.created_by and instance.status == "escalated":
        NotificationManager.create_notification(
            user=instance.created_by,
            notification_type="system_alert",
            title="Case escalated",
            message=f"Report '{instance.title}' has been escalated for review.",
            priority="high",
            delivery_methods=["dashboard"],
            related_report=instance,
        )
