from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .models import AuditLog, SystemLog


@login_required
def audit_log_list(request):
	logs = AuditLog.objects.select_related("user").order_by("-timestamp")

	severity = request.GET.get("severity")
	action = request.GET.get("action")

	if severity:
		logs = logs.filter(severity=severity)
	if action:
		logs = logs.filter(action=action)

	paginator = Paginator(logs, 25)
	page_number = request.GET.get("page")
	page_obj = paginator.get_page(page_number)

	context = {
		"page_obj": page_obj,
		"severity_choices": AuditLog.SEVERITY_CHOICES,
		"action_choices": AuditLog.ACTION_CHOICES,
		"filters": {
			"severity": severity,
			"action": action,
		},
	}
	return render(request, "logs/audit_log_list.html", context)


@login_required
def system_log_list(request):
	logs = SystemLog.objects.order_by("-timestamp")

	level = request.GET.get("level")
	component = request.GET.get("component")

	if level:
		logs = logs.filter(level=level)
	if component:
		logs = logs.filter(component=component)

	paginator = Paginator(logs, 25)
	page_number = request.GET.get("page")
	page_obj = paginator.get_page(page_number)

	context = {
		"page_obj": page_obj,
		"level_choices": SystemLog.LOG_LEVEL_CHOICES,
		"component_choices": SystemLog.COMPONENT_CHOICES,
		"filters": {
			"level": level,
			"component": component,
		},
	}
	return render(request, "logs/system_log_list.html", context)
