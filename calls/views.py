from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult
from .forms import CallRecordForm, AudioUploadForm
from accounts.utils import admin_required, law_enforcement_required
from accounts.rate_limiting import rate_limit_uploads
import logging

logger = logging.getLogger(__name__)

@login_required
def call_list_view(request):
    """List all call records with filtering and pagination"""
    calls = CallRecord.objects.select_related('recorded_by').order_by('-call_start_time')

    # Apply filters
    status = request.GET.get('status')
    caller = request.GET.get('caller')
    recipient = request.GET.get('recipient')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status:
        calls = calls.filter(status=status)
    if caller:
        calls = calls.filter(caller_number__icontains=caller)
    if recipient:
        calls = calls.filter(recipient_number__icontains=recipient)
    if date_from:
        calls = calls.filter(call_start_time__date__gte=date_from)
    if date_to:
        calls = calls.filter(call_start_time__date__lte=date_to)

    # Role-based filtering
    if request.user.role == 'user':
        calls = calls.filter(Q(caller_number__in=request.user.phone_numbers) |
                           Q(recipient_number__in=request.user.phone_numbers))

    # Pagination
    paginator = Paginator(calls, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Summary statistics
    total_calls = CallRecord.objects.count()
    analyzed_calls = CallRecord.objects.filter(ai_analysis__isnull=False).count()
    suspicious_calls = CallRecord.objects.filter(
        scam_probability__overall_score__gte=0.6
    ).count()
    confirmed_scams = CallRecord.objects.filter(
        scam_probability__scam_level__in=['high', 'critical']
    ).count()

    context = {
        'page_obj': page_obj,
        'status_choices': CallRecord.CALL_STATUS_CHOICES,
        'filters': {
            'status': status,
            'caller': caller,
            'recipient': recipient,
            'date_from': date_from,
            'date_to': date_to,
        },
        'total_calls': total_calls,
        'analyzed_calls': analyzed_calls,
        'suspicious_calls': suspicious_calls,
        'confirmed_scams': confirmed_scams,
    }
    return render(request, 'calls/call_list.html', context)

@login_required
def call_detail_view(request, call_id):
    """View detailed information about a specific call"""
    call = get_object_or_404(CallRecord, id=call_id)

    # Check permissions
    if request.user.role == 'user':
        if not (call.caller_number in getattr(request.user, 'phone_numbers', []) or
                call.recipient_number in getattr(request.user, 'phone_numbers', [])):
            messages.error(request, 'You do not have permission to view this call.')
            return redirect('call_list')

    # Get related data
    audio_upload = getattr(call, 'audio', None)
    ai_analysis = getattr(call, 'ai_analysis', None)
    scam_score = getattr(call, 'scam_probability', None)
    reports = call.reports.all()

    context = {
        'call': call,
        'audio_upload': audio_upload,
        'ai_analysis': ai_analysis,
        'scam_score': scam_score,
        'reports': reports,
    }
    return render(request, 'calls/call_detail.html', context)

@login_required
@require_POST
@login_required
@rate_limit_uploads(max_uploads=10, period=3600)
def upload_audio_view(request, call_id):
    """Upload audio file for a call record"""
    call = get_object_or_404(CallRecord, id=call_id)

    # Check permissions
    if request.user.role == 'user' and call.recorded_by != request.user:
        messages.error(request, 'You do not have permission to upload audio for this call.')
        return redirect('call_detail', call_id=call.id)

    if request.method == 'POST':
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Replace existing audio upload if present
            existing_audio = getattr(call, 'audio', None)
            if existing_audio:
                existing_audio.delete()

            audio_upload = form.save(commit=False)
            audio_upload.call_record = call
            audio_upload.uploaded_by = request.user
            audio_upload.save()

            # Log the action
            logger.info(f"Audio uploaded for call {call.id} by user {request.user.username}")

            # Create or refresh analysis
            analysis = getattr(call, 'ai_analysis', None)
            if analysis:
                analysis.audio_upload = audio_upload
                analysis.status = 'pending'
                analysis.error_message = ''
                analysis.save()
            else:
                analysis = AIAnalysisResult.objects.create(
                    call_record=call,
                    audio_upload=audio_upload,
                    analysis_type='comprehensive',
                    status='pending',
                    requested_by=request.user,
                )

            try:
                from analysis.pipeline import process_analysis
                logger.info(f"Starting analysis for {analysis.id}")
                process_analysis(str(analysis.id))
                logger.info(f"Analysis {analysis.id} completed successfully")
            except Exception as e:
                logger.error(f"Analysis pipeline error for {analysis.id}: {str(e)}", exc_info=True)
                analysis.status = 'failed'
                analysis.error_message = f"Analysis failed: {str(e)}"
                analysis.save()

            messages.success(request, 'Audio file uploaded successfully.')
            return redirect('call_detail', call_id=call.id)
        else:
            messages.error(request, 'Error uploading audio file.')
    else:
        form = AudioUploadForm()

    return redirect('call_detail', call_id=call.id)

@login_required
def create_call_view(request):
    """Create a new call record manually"""
    if request.user.role == 'user':
        messages.error(request, 'You do not have permission to create call records.')
        return redirect('call_list')

    if request.method == 'POST':
        form = CallRecordForm(request.POST)
        if form.is_valid():
            call = form.save(commit=False)
            call.recorded_by = request.user
            call.save()

            logger.info(f"Call record created: {call.id} by user {request.user.username}")

            messages.success(request, 'Call record created successfully.')
            return redirect('call_detail', call_id=call.id)
    else:
        form = CallRecordForm()

    return render(request, 'calls/create_call.html', {'form': form})

@admin_required
def call_statistics_view(request):
    """View call statistics and analytics"""
    # Basic statistics
    total_calls = CallRecord.objects.count()
    calls_today = CallRecord.objects.filter(call_start_time__date=timezone.now().date()).count()
    suspicious_calls = CallRecord.objects.filter(
        scam_probability__overall_score__gte=0.6
    ).count()

    # Status breakdown
    status_stats = {}
    for status, _ in CallRecord.CALL_STATUS_CHOICES:
        status_stats[status] = CallRecord.objects.filter(status=status).count()

    # Recent activity
    recent_calls = CallRecord.objects.select_related('recorded_by')[:10]

    context = {
        'total_calls': total_calls,
        'calls_today': calls_today,
        'suspicious_calls': suspicious_calls,
        'status_stats': status_stats,
        'recent_calls': recent_calls,
    }
    return render(request, 'calls/statistics.html', context)

@login_required
def api_call_list(request):
    """API endpoint for call list (for AJAX requests)"""
    calls = CallRecord.objects.order_by('-call_start_time')[:50]  # Limit for performance

    if request.user.role == 'user':
        calls = calls.filter(Q(caller_number__in=getattr(request.user, 'phone_numbers', [])) |
                           Q(recipient_number__in=getattr(request.user, 'phone_numbers', [])))

    data = []
    for call in calls:
        data.append({
            'id': str(call.id),
            'caller_number': call.caller_number,
            'recipient_number': call.recipient_number,
            'start_time': call.call_start_time.isoformat(),
            'status': call.status,
            'duration': str(call.duration) if call.duration else None,
            'has_audio': hasattr(call, 'audio'),
            'scam_score': call.scam_probability.overall_score if hasattr(call, 'scam_probability') else None,
        })

    return JsonResponse({'calls': data})
