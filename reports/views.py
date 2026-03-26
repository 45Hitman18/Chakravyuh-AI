from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from accounts.utils import admin_required, law_enforcement_required
from .models import Report
from .forms import ReportForm

@login_required
def report_list_view(request):
    """List all reports with filtering and pagination"""
    reports = Report.objects.select_related(
        'created_by', 'assigned_to', 'call_record', 'scam_probability'
    ).order_by('-created_at')

    # Apply filters
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    report_type = request.GET.get('type')

    if status:
        reports = reports.filter(status=status)
    if priority:
        reports = reports.filter(priority=priority)
    if report_type:
        reports = reports.filter(report_type=report_type)

    # Role-based filtering
    if request.user.role == 'user':
        reports = reports.filter(created_by=request.user)

    # Pagination
    paginator = Paginator(reports, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Summary statistics
    total_reports = Report.objects.count()
    pending_review = Report.objects.filter(status='under_review').count()
    approved_reports = Report.objects.filter(status='approved').count()
    rejected_reports = Report.objects.filter(status='rejected').count()

    context = {
        'page_obj': page_obj,
        'status_choices': Report.REPORT_STATUS_CHOICES,
        'priority_choices': Report._meta.get_field('priority').choices,
        'type_choices': Report.REPORT_TYPE_CHOICES,
        'filters': {
            'status': status,
            'priority': priority,
            'type': report_type,
        },
        'total_reports': total_reports,
        'pending_review': pending_review,
        'approved_reports': approved_reports,
        'rejected_reports': rejected_reports,
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def report_create_view(request):
    """Create a new report"""
    initial = {}

    call_id = request.GET.get('call_id')
    analysis_id = request.GET.get('analysis_id')

    if call_id:
        initial['call_record'] = call_id
    if analysis_id:
        initial['ai_analysis'] = analysis_id

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user
            report.status = 'submitted'
            report.submitted_at = timezone.now()

            # Link AI analysis/scam score automatically
            if report.call_record and hasattr(report.call_record, 'ai_analysis'):
                report.ai_analysis = report.call_record.ai_analysis
            if report.ai_analysis and hasattr(report.ai_analysis, 'scam_probability'):
                report.scam_probability = report.ai_analysis.scam_probability

            report.save()
            messages.success(request, 'Report submitted successfully.')
            return redirect('reports:report_detail', report_id=report.id)
    else:
        form = ReportForm(initial=initial)

    return render(request, 'reports/report_form.html', {'form': form})


@admin_required
def report_review_view(request, report_id):
    """Admin review for reports"""
    report = get_object_or_404(Report, id=report_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('internal_notes', '').strip()

        if action == 'under_review':
            report.status = 'under_review'
        elif action == 'approve':
            report.status = 'approved'
        elif action == 'reject':
            report.status = 'rejected'

        if notes:
            report.internal_notes = notes

        report.save()
        messages.success(request, 'Report status updated.')
        return redirect('reports:report_detail', report_id=report.id)

    return render(request, 'reports/report_review.html', {'report': report})


@law_enforcement_required
def report_escalate_view(request, report_id):
    """Escalate report to law enforcement"""
    report = get_object_or_404(Report, id=report_id)

    report.status = 'escalated'
    report.assigned_to = request.user
    report.save(update_fields=['status', 'assigned_to', 'updated_at'])

    messages.success(request, 'Report escalated to law enforcement.')
    return redirect('reports:report_detail', report_id=report.id)

@login_required
def report_detail_view(request, report_id):
    """View detailed information about a specific report"""
    report = get_object_or_404(Report, id=report_id)

    # Check permissions
    if request.user.role == 'user' and report.created_by != request.user:
        # Users can only see their own reports
        from django.http import Http404
        raise Http404("Report not found")

    # Get related data
    evidence_files = report.evidence_files.all()

    context = {
        'report': report,
        'evidence_files': evidence_files,
    }
    return render(request, 'reports/report_detail.html', context)
