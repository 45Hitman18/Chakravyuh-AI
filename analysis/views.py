from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import AIAnalysisResult, ScamProbabilityScore
from calls.models import CallRecord
from accounts.utils import admin_required, law_enforcement_required, role_required
import logging

logger = logging.getLogger(__name__)

@login_required
def analysis_list_view(request):
    """List all AI analysis results with filtering and pagination"""
    analyses = AIAnalysisResult.objects.select_related(
        'call_record', 'requested_by', 'scam_probability'
    ).order_by('-created_at')

    # Apply filters
    analysis_type = request.GET.get('analysis_type')
    status = request.GET.get('status')
    confidence_min = request.GET.get('confidence_min')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if analysis_type:
        analyses = analyses.filter(analysis_type=analysis_type)
    if status:
        analyses = analyses.filter(status=status)
    if confidence_min:
        analyses = analyses.filter(confidence_score__gte=float(confidence_min))
    if date_from:
        analyses = analyses.filter(created_at__date__gte=date_from)
    if date_to:
        analyses = analyses.filter(created_at__date__lte=date_to)

    # Role-based filtering
    if request.user.role == 'user':
        analyses = analyses.filter(requested_by=request.user)

    # Summary metrics
    total_analyses = AIAnalysisResult.objects.filter(status='completed').count()
    safe_results = ScamProbabilityScore.objects.filter(scam_level='low').count()
    suspicious_results = ScamProbabilityScore.objects.filter(scam_level='medium').count()
    fraud_confirmed = ScamProbabilityScore.objects.filter(scam_level__in=['high', 'critical']).count()

    # Pagination
    paginator = Paginator(analyses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Prepare analysis data for the list
    analysis_list = []
    for analysis in page_obj:
        scam_score = getattr(analysis, 'scam_probability', None)
        analysis_list.append({
            'id': analysis.id,
            'analysis_id': str(analysis.id)[:8],
            'source': 'Call Recording' if analysis.audio_upload else 'Unknown',
            'timestamp': analysis.created_at,
            'risk_level': scam_score.get_scam_level_display() if scam_score else 'Unknown',
            'confidence': analysis.confidence_score or 0,
            'status': scam_score.scam_level if scam_score else 'unknown',
            'call_record': analysis.call_record,
            'scam_score': scam_score,
        })

    context = {
        'page_obj': page_obj,
        'analysis_list': analysis_list,
        'analysis_types': AIAnalysisResult.ANALYSIS_TYPE_CHOICES,
        'status_choices': AIAnalysisResult.ANALYSIS_STATUS_CHOICES,
        'total_analyses': total_analyses,
        'safe_results': safe_results,
        'suspicious_results': suspicious_results,
        'fraud_confirmed': fraud_confirmed,
        'filters': {
            'analysis_type': analysis_type,
            'status': status,
            'confidence_min': confidence_min,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    return render(request, 'analysis/analysis_list.html', context)

@login_required
def analysis_detail_view(request, analysis_id):
    """View detailed information about a specific AI analysis"""
    analysis = get_object_or_404(AIAnalysisResult, id=analysis_id)

    # Check permissions
    if request.user.role == 'user' and analysis.requested_by != request.user:
        messages.error(request, 'You do not have permission to view this analysis.')
        return redirect('analysis_list')

    # Get related data
    scam_score = getattr(analysis, 'scam_probability', None)
    call_record = analysis.call_record

    context = {
        'analysis': analysis,
        'scam_score': scam_score,
        'call_record': call_record,
    }
    return render(request, 'analysis/analysis_detail.html', context)

@login_required
@require_POST
def request_analysis_view(request, call_id):
    """Request AI analysis for a specific call"""
    call = get_object_or_404(CallRecord, id=call_id)

    # Check permissions
    if request.user.role == 'user':
        messages.error(request, 'You do not have permission to request AI analysis.')
        return redirect('call_detail', call_id=call.id)

    analysis_type = request.POST.get('analysis_type', 'comprehensive')

    # Check if analysis already exists
    existing_analysis = AIAnalysisResult.objects.filter(
        call_record=call,
        analysis_type=analysis_type,
        status__in=['completed', 'processing']
    ).first()

    if existing_analysis:
        messages.warning(request, f'Analysis of type "{analysis_type}" is already {existing_analysis.get_status_display().lower()}.')
        return redirect('call_detail', call_id=call.id)

    # Create new analysis request
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=getattr(call, 'audio', None),
        analysis_type=analysis_type,
        status='pending',
        requested_by=request.user
    )

    # TODO: Trigger actual AI analysis (would integrate with AI service here)
    # For now, we'll simulate analysis completion
    analysis.status = 'processing'
    analysis.save()

    logger.info(f"AI analysis requested for call {call.id} by user {request.user.username}")

    messages.success(request, f'AI analysis ({analysis.get_analysis_type_display()}) has been queued for processing.')
    return redirect('call_detail', call_id=call.id)

@login_required
def scam_scores_view(request):
    """View scam probability scores with filtering"""
    scores = ScamProbabilityScore.objects.select_related(
        'call_record', 'ai_analysis', 'reviewed_by'
    ).order_by('-overall_score')

    # Apply filters
    min_score = request.GET.get('min_score')
    max_score = request.GET.get('max_score')
    scam_level = request.GET.get('scam_level')
    reviewed = request.GET.get('reviewed')

    if min_score:
        scores = scores.filter(overall_score__gte=float(min_score))
    if max_score:
        scores = scores.filter(overall_score__lte=float(max_score))
    if scam_level:
        scores = scores.filter(scam_level=scam_level)
    if reviewed == 'yes':
        scores = scores.filter(reviewed_by__isnull=False)
    elif reviewed == 'no':
        scores = scores.filter(reviewed_by__isnull=True)

    # Role-based filtering
    if request.user.role == 'user':
        # Users can only see scores for calls they're involved in
        scores = scores.filter(
            Q(call_record__caller_number__in=getattr(request.user, 'phone_numbers', [])) |
            Q(call_record__recipient_number__in=getattr(request.user, 'phone_numbers', []))
        )

    # Pagination
    paginator = Paginator(scores, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'scam_levels': ScamProbabilityScore.SCAM_LEVEL_CHOICES,
        'filters': {
            'min_score': min_score,
            'max_score': max_score,
            'scam_level': scam_level,
            'reviewed': reviewed,
        }
    }
    return render(request, 'analysis/scam_scores.html', context)

@role_required('law_enforcement', 'admin')
@require_POST
def review_scam_score_view(request, score_id):
    """Review and potentially override a scam score"""
    score = get_object_or_404(ScamProbabilityScore, id=score_id)

    action = request.POST.get('action')
    review_notes = request.POST.get('review_notes', '')

    if action == 'override':
        new_score = float(request.POST.get('new_score', score.overall_score))
        score.is_manually_overridden = True
        score.original_score = score.overall_score
        score.overall_score = min(max(new_score, 0.0), 1.0)  # Clamp to 0-1
        score.review_notes = review_notes
        score.reviewed_by = request.user
        score.save()

        # Recalculate scam level
        score.scam_level = score.calculate_scam_level()
        score.save()

        messages.success(request, f'Scam score updated to {score.overall_score:.3f}')
    elif action == 'approve':
        score.reviewed_by = request.user
        score.review_notes = review_notes
        score.save()
        messages.success(request, 'Scam score approved')

    logger.info(f"Scam score {score.id} reviewed by user {request.user.username}")

    return redirect('scam_scores')

@admin_required
def analysis_statistics_view(request):
    """View AI analysis statistics and performance metrics"""
    # Basic statistics
    total_analyses = AIAnalysisResult.objects.count()
    completed_analyses = AIAnalysisResult.objects.filter(status='completed').count()
    avg_confidence = AIAnalysisResult.objects.filter(status='completed').aggregate(
        avg_confidence=models.Avg('confidence_score')
    )['avg_confidence'] or 0

    # Analysis type breakdown
    type_stats = {}
    for analysis_type, _ in AIAnalysisResult.ANALYSIS_TYPE_CHOICES:
        count = AIAnalysisResult.objects.filter(analysis_type=analysis_type, status='completed').count()
        type_stats[analysis_type] = count

    # Scam score statistics
    total_scores = ScamProbabilityScore.objects.count()
    high_risk_scores = ScamProbabilityScore.objects.filter(scam_level='high').count()
    critical_scores = ScamProbabilityScore.objects.filter(scam_level='critical').count()

    # Recent activity
    recent_analyses = AIAnalysisResult.objects.select_related('requested_by', 'call_record')[:10]

    context = {
        'total_analyses': total_analyses,
        'completed_analyses': completed_analyses,
        'avg_confidence': avg_confidence,
        'type_stats': type_stats,
        'total_scores': total_scores,
        'high_risk_scores': high_risk_scores,
        'critical_scores': critical_scores,
        'recent_analyses': recent_analyses,
    }
    return render(request, 'analysis/statistics.html', context)

@login_required
def api_analysis_status(request, analysis_id):
    """API endpoint to check analysis status"""
    analysis = get_object_or_404(AIAnalysisResult, id=analysis_id)

    # Check permissions
    if request.user.role == 'user' and analysis.requested_by != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    data = {
        'id': str(analysis.id),
        'status': analysis.status,
        'status_display': analysis.get_status_display(),
        'confidence_score': analysis.confidence_score,
        'processing_time': str(analysis.processing_time) if analysis.processing_time else None,
        'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
    }

    return JsonResponse(data)
