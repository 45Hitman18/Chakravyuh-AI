from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from accounts.utils import admin_required, law_enforcement_required
from accounts.rate_limiting import rate_limit_uploads
from calls.models import CallRecord, AudioUpload
from analysis.models import ScamProbabilityScore, AIAnalysisResult
from analysis.cache_utils import cache_dashboard_stats, invalidate_dashboard_cache
from calls.forms import AudioUploadForm
from reports.models import Report, EvidenceFile
from honeypot.models import HoneypotInteraction, ScammerProfile
from logs.models import SystemLog
from accounts.models import User
from django.db import models
from django.db.models import Count, Avg, Max
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
import json
import uuid
import logging

logger = logging.getLogger(__name__)

@login_required
def dashboard_view(request):
    from notifications.manager import NotificationManager

    # Redirect to appropriate dashboard based on user role
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    elif request.user.role == 'law_enforcement':
        return redirect('law_enforcement_dashboard')

    # Use cache for dashboard statistics
    stats = cache_dashboard_stats(request.user.id)
    total_calls = stats['total_calls']
    total_scams = stats['confirmed_scams']
    suspicious_alerts = stats['suspicious_calls'] - stats['confirmed_scams']

    # Scam trends: monthly counts for the last 12 months
    cache_key = f'scam_trends_{request.user.id}'
    scam_trends = cache.get(cache_key)
    
    if scam_trends is None:
        scam_trends = ScamProbabilityScore.objects.filter(
            call_record__recorded_by=request.user,
            scam_level__in=['high', 'critical']
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(count=Count('id')).order_by('month')
        cache.set(cache_key, list(scam_trends), 600)  # Cache for 10 minutes
    else:
        scam_trends = list(scam_trends)

    # Prepare data for Chart.js
    months = []
    counts = []
    for trend in scam_trends:
        months.append(trend['month'].strftime('%Y-%m'))
        counts.append(trend['count'])

    # Recent uploads and analyses (not cached, get fresh data)
    recent_uploads = AudioUpload.objects.filter(uploaded_by=request.user).select_related('call_record').order_by('-uploaded_at')[:5]
    recent_analyses = AIAnalysisResult.objects.filter(requested_by=request.user).select_related('call_record').order_by('-created_at')[:5]

    # Combine recent activities
    recent_activities = []
    for analysis in recent_analyses:
        recent_activities.append({
            'type': 'analysis',
            'date': analysis.created_at,
            'analysis': analysis,
        })
    for upload in recent_uploads:
        recent_activities.append({
            'type': 'upload',
            'date': upload.uploaded_at,
            'upload': upload,
        })
    # Sort by date descending
    recent_activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = recent_activities[:5]

    # Get notifications
    unread_notifications = NotificationManager.get_unread_count(request.user)
    recent_notifications = NotificationManager.get_recent_notifications(request.user, 5)

    # Get pending analyses
    pending_analyses = AIAnalysisResult.objects.filter(
        requested_by=request.user,
        status__in=['pending', 'processing']
    ).select_related('call_record').order_by('-created_at')[:3]

    context = {
        'total_calls': total_calls,
        'total_scams': total_scams,
        'suspicious_alerts': suspicious_alerts,
        'scam_trends_months': json.dumps(months),
        'scam_trends_counts': json.dumps(counts),
        'recent_uploads': recent_uploads,
        'recent_analyses': recent_analyses,
        'recent_activities': recent_activities,
        'upload_form': AudioUploadForm(),
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'pending_analyses': pending_analyses,
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@require_POST
@rate_limit_uploads(max_uploads=10, period=3600)
def dashboard_upload_audio(request):
    """Upload audio file directly from dashboard"""
    try:
        form = AudioUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            errors_dict = {}
            for field, errors in form.errors.items():
                errors_dict[field] = [str(e) for e in errors]
            return JsonResponse({
                'success': False,
                'errors': errors_dict
            }, status=400)
        
        # Get and validate phone numbers
        caller_number = request.POST.get('caller_number', '').strip()
        recipient_number = request.POST.get('recipient_number', '').strip()
        
        # Validate phone numbers
        if not caller_number:
            return JsonResponse({
                'success': False,
                'errors': {'caller_number': ['Caller number is required']}
            }, status=400)
        
        if not recipient_number:
            return JsonResponse({
                'success': False,
                'errors': {'recipient_number': ['Recipient number is required']}
            }, status=400)
        
        # Create a new call record first
        call = CallRecord.objects.create(
            caller_number=caller_number,
            recipient_number=recipient_number,
            call_start_time=timezone.now(),
            status='completed',
            recorded_by=request.user
        )

        # Save audio upload with checksum
        import hashlib
        audio_upload = form.save(commit=False)
        audio_upload.call_record = call
        audio_upload.uploaded_by = request.user
        
        # Generate checksum and set file size
        audio_file_content = audio_upload.audio_file.read()
        audio_upload.checksum = hashlib.sha256(audio_file_content).hexdigest()
        audio_upload.file_size = len(audio_file_content)
        audio_upload.audio_file.seek(0)  # Reset file pointer
        
        audio_upload.save()
        logger.info(f"Created new audio upload {audio_upload.id}")

        # Trigger AI analysis automatically
        analysis = AIAnalysisResult.objects.create(
            call_record=call,
            audio_upload=audio_upload,
            analysis_type='comprehensive',
            status='pending',
            requested_by=request.user
        )

        # Start AI analysis pipeline (if available)
        analysis_success = False
        try:
            from analysis.pipeline import process_analysis
            logger.info(f"Starting analysis for {analysis.id}")
            process_analysis(str(analysis.id))
            logger.info(f"Analysis {analysis.id} completed successfully")
            analysis_success = True
        except Exception as e:
            # Analysis pipeline failed with error
            logger.error(f'Analysis pipeline error for {analysis.id}: {str(e)}', exc_info=True)
            # Update analysis status to failed so we know it tried
            try:
                analysis.status = 'failed'
                analysis.error_message = f"Analysis failed: {str(e)}"
                analysis.save()
                logger.error(f"Analysis {analysis.id} marked as failed")
            except Exception as inner_e:
                logger.error(f"Failed to update analysis status: {str(inner_e)}")
        
        if analysis_success:
            logger.info(f"Analysis pipeline completed for {analysis.id}")
        else:
            logger.warning(f"Analysis pipeline did not complete for {analysis.id}")

        messages.success(request, 'Audio uploaded and analysis started successfully.')
        return JsonResponse({
            'success': True,
            'call_id': str(call.id),
            'analysis_id': str(analysis.id),
            'message': 'Upload and analysis initiated'
        }, status=200)
    
    except Exception as e:
        logger.error(f'Upload error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }, status=500)

@login_required
def dashboard_analysis_status(request, analysis_id):
    """API endpoint to check analysis status from dashboard"""
    try:
        analysis = get_object_or_404(AIAnalysisResult, id=analysis_id)

        # Check permissions
        if analysis.requested_by != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        # Get scam probability if it exists
        scam_score = None
        try:
            scam_score = analysis.scam_probability
        except:
            pass

        data = {
            'id': str(analysis.id),
            'status': analysis.status,
            'status_display': analysis.get_status_display(),
            'confidence_score': analysis.confidence_score,
            'scam_score': scam_score.overall_score if scam_score else None,
            'scam_level': scam_score.get_scam_level_display() if scam_score else None,
            'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
        }

        return JsonResponse(data)
    except Exception as e:
        logger.error(f'Status check error: {str(e)}')
        return JsonResponse({'error': f'Error fetching status: {str(e)}'}, status=500)

@admin_required
def admin_dashboard_view(request):

    # Summary cards
    total_reports = Report.objects.count()
    pending_reports = Report.objects.filter(status='pending').count()
    approved_reports = Report.objects.filter(status='approved').count()
    rejected_reports = Report.objects.filter(status='rejected').count()

    # Flagged numbers - with optimized queries
    flagged_numbers = ScamProbabilityScore.objects.filter(
        scam_level__in=['high', 'critical']
    ).select_related('call_record').values('call_record__caller_number').annotate(
        scam_count=Count('id'),
        avg_score=Avg('overall_score')
    ).order_by('-scam_count')[:10]

    # Honeypot conversations - optimized with select_related
    honeypot_logs = HoneypotInteraction.objects.select_related(
        'scammer_profile', 'honeypot_session'
    ).order_by('-created_at')[:5]

    # System logs - no user field in SystemLog model
    system_logs = SystemLog.objects.order_by('-timestamp')[:20]

    # Monthly stats for chart
    monthly_stats_qs = ScamProbabilityScore.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        reports=Count('id'),
        scams=Count('id', filter=models.Q(scam_level__in=['high', 'critical']))
    ).order_by('month')

    # Convert to list and format month as string
    monthly_stats_list = list(monthly_stats_qs)
    for item in monthly_stats_list:
        item['month'] = item['month'].strftime('%Y-%m') if item['month'] else None

    # Heatmap data (mock for now)
    heatmap_data = [
        {'state': 'Maharashtra', 'lat': 19.0760, 'lng': 72.8777, 'count': 25},
        {'state': 'Delhi', 'lat': 28.7041, 'lng': 77.1025, 'count': 18},
        {'state': 'Karnataka', 'lat': 12.9716, 'lng': 77.5946, 'count': 15},
        {'state': 'Tamil Nadu', 'lat': 13.0827, 'lng': 80.2707, 'count': 12},
        {'state': 'Gujarat', 'lat': 23.0225, 'lng': 72.5714, 'count': 10},
    ]

    # Other stats - optimized
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=timezone.now() - timezone.timedelta(days=30)).count()
    total_calls = CallRecord.objects.count()
    analyzed_calls = AIAnalysisResult.objects.filter(status='completed').count()

    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'approved_reports': approved_reports,
        'rejected_reports': rejected_reports,
        'flagged_numbers': flagged_numbers,
        'honeypot_logs': honeypot_logs,
        'system_logs': system_logs,
        'monthly_stats': json.dumps(monthly_stats_list),
        'heatmap_data': json.dumps(heatmap_data),
        'total_users': total_users,
        'active_users': active_users,
        'total_calls': total_calls,
        'analyzed_calls': analyzed_calls,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@law_enforcement_required
def law_enforcement_dashboard_view(request):
    from django.db.models import Count, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    import json

    # Command metrics
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    case_escalations = Report.objects.filter(status='escalated', created_at__gte=week_ago).count()
    inter_agency_flags = Report.objects.filter(priority__in=['high', 'critical']).count()  # Use priority as proxy for inter-agency flags
    evidence_count = EvidenceFile.objects.count()
    total_cases = Report.objects.count()

    # Case statistics
    active_cases = Report.objects.filter(status__in=['submitted', 'under_review', 'approved']).count()
    resolved_cases = Report.objects.filter(status__in=['approved', 'rejected']).count()
    high_priority_cases = Report.objects.filter(priority__in=['high', 'critical']).count()

    # Monthly stats for scam activity trends
    monthly_stats = Report.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        cases=Count('id'),
        scams=Count('id', filter=Q(scam_probability__scam_level__in=['high', 'critical']))
    ).order_by('month')
    
    # Convert monthly_stats to JSON-serializable format
    monthly_stats = [
        {
            'month': item['month'].strftime('%Y-%m') if item['month'] else '',
            'cases': item['cases'],
            'scams': item['scams']
        }
        for item in monthly_stats
    ]

    # Scam types distribution - using scam_level as proxy for types since scam_type field doesn't exist
    scam_types_stats = ScamProbabilityScore.objects.filter(
        scam_level__in=['high', 'critical']
    ).values('scam_level').annotate(
        count=Count('id')
    ).order_by('-count')

    # Map scam levels to types for display
    level_to_type = {
        'high': 'High Risk',
        'critical': 'Critical',
        'medium': 'Medium Risk',
        'low': 'Low Risk'
    }

    scam_types_stats = [
        {'type': level_to_type.get(item['scam_level'], item['scam_level']), 'count': item['count']}
        for item in scam_types_stats
    ]

    # Ensure we have at least some basic types if no data
    if not scam_types_stats:
        scam_types_stats = [
            {'type': 'High Risk', 'count': 0},
            {'type': 'Critical', 'count': 0},
            {'type': 'Medium Risk', 'count': 0},
            {'type': 'Low Risk', 'count': 0}
        ]

    # Recent cases
    recent_cases = Report.objects.select_related('created_by').order_by('-created_at')[:10]

    # Recent uploads (law e ent can see all uploads)
    recent_uploads = AudioUpload.objects.select_related('call_record', 'uploaded_by').order_by('-uploaded_at')[:10]

    # Flagged numbers
    flagged_numbers = ScamProbabilityScore.objects.filter(
        scam_level__in=['high', 'critical']
    ).values('call_record__caller_number').annotate(
        scam_count=Count('id'),
        avg_score=Avg('overall_score'),
        last_activity=Max('created_at')
    ).order_by('-scam_count')[:10]

    # Heatmap data - real data aggregated by location from reports
    # Define Indian states with coordinates
    state_coords = {
        'maharashtra': {'lat': 19.0760, 'lng': 72.8777, 'name': 'Maharashtra'},
        'delhi': {'lat': 28.7041, 'lng': 77.1025, 'name': 'Delhi'},
        'karnataka': {'lat': 12.9716, 'lng': 77.5946, 'name': 'Karnataka'},
        'tamil nadu': {'lat': 13.0827, 'lng': 80.2707, 'name': 'Tamil Nadu'},
        'gujarat': {'lat': 23.0225, 'lng': 72.5714, 'name': 'Gujarat'},
        'rajasthan': {'lat': 26.9124, 'lng': 75.7873, 'name': 'Rajasthan'},
        'uttar pradesh': {'lat': 26.8467, 'lng': 80.9462, 'name': 'Uttar Pradesh'},
        'west bengal': {'lat': 22.5726, 'lng': 88.3639, 'name': 'West Bengal'},
        'punjab': {'lat': 30.7333, 'lng': 76.7794, 'name': 'Punjab'},
        'haryana': {'lat': 29.0588, 'lng': 76.0856, 'name': 'Haryana'},
        'kerala': {'lat': 10.8505, 'lng': 76.2711, 'name': 'Kerala'},
        'madhya pradesh': {'lat': 22.9734, 'lng': 78.6569, 'name': 'Madhya Pradesh'},
        'andhra pradesh': {'lat': 15.9129, 'lng': 79.7400, 'name': 'Andhra Pradesh'},
        'telangana': {'lat': 17.3850, 'lng': 78.4867, 'name': 'Telangana'},
        'bihar': {'lat': 25.0961, 'lng': 85.3131, 'name': 'Bihar'},
        'jharkhand': {'lat': 23.6102, 'lng': 85.2799, 'name': 'Jharkhand'},
        'odisha': {'lat': 20.9517, 'lng': 85.0985, 'name': 'Odisha'},
        'chhattisgarh': {'lat': 21.2787, 'lng': 81.8661, 'name': 'Chhattisgarh'},
        'assam': {'lat': 26.2006, 'lng': 92.9376, 'name': 'Assam'},
        'meghalaya': {'lat': 25.4670, 'lng': 91.3662, 'name': 'Meghalaya'},
        'tripura': {'lat': 23.9408, 'lng': 91.9882, 'name': 'Tripura'},
        'manipur': {'lat': 24.6637, 'lng': 93.9063, 'name': 'Manipur'},
        'nagaland': {'lat': 25.6586, 'lng': 94.1053, 'name': 'Nagaland'},
        'mizoram': {'lat': 23.1645, 'lng': 92.9376, 'name': 'Mizoram'},
        'arunachal pradesh': {'lat': 28.2180, 'lng': 94.7278, 'name': 'Arunachal Pradesh'},
        'sikkim': {'lat': 27.5330, 'lng': 88.5122, 'name': 'Sikkim'},
        'goa': {'lat': 15.2993, 'lng': 74.1240, 'name': 'Goa'},
        'puducherry': {'lat': 11.9416, 'lng': 79.8083, 'name': 'Puducherry'},
        'chandigarh': {'lat': 30.7333, 'lng': 76.7794, 'name': 'Chandigarh'},
        'dadra and nagar haveli and daman and diu': {'lat': 20.4283, 'lng': 72.8397, 'name': 'Dadra and Nagar Haveli and Daman and Diu'},
        'lakshadweep': {'lat': 10.5667, 'lng': 72.6417, 'name': 'Lakshadweep'},
        'jammu and kashmir': {'lat': 33.7782, 'lng': 76.5762, 'name': 'Jammu and Kashmir'},
        'ladakh': {'lat': 34.2095, 'lng': 77.6151, 'name': 'Ladakh'},
    }

    city_to_state = {
        'vadodara': 'gujarat',
        'baroda': 'gujarat',
        'ahmedabad': 'gujarat',
        'surat': 'gujarat',
        'rajkot': 'gujarat',
        'mumbai': 'maharashtra',
        'pune': 'maharashtra',
        'nagpur': 'maharashtra',
        'delhi': 'delhi',
        'new delhi': 'delhi',
        'bengaluru': 'karnataka',
        'bangalore': 'karnataka',
        'mysuru': 'karnataka',
        'chennai': 'tamil nadu',
        'coimbatore': 'tamil nadu',
        'hyderabad': 'telangana',
        'kolkata': 'west bengal',
        'jaipur': 'rajasthan',
        'lucknow': 'uttar pradesh',
        'kanpur': 'uttar pradesh',
        'patna': 'bihar',
        'bhopal': 'madhya pradesh',
        'indore': 'madhya pradesh',
        'chandigarh': 'chandigarh',
        'kochi': 'kerala',
        'thiruvananthapuram': 'kerala',
        'bhubaneswar': 'odisha',
        'visakhapatnam': 'andhra pradesh',
    }

    def normalize_state_key(raw_location: str):
        if not raw_location:
            return None

        location = raw_location.strip().lower()

        if location in state_coords:
            return location

        if ',' in location:
            parts = [p.strip() for p in location.split(',') if p.strip()]
            if parts:
                last = parts[-1]
                if last in state_coords:
                    return last
                if last in city_to_state:
                    return city_to_state[last]

        if location in city_to_state:
            return city_to_state[location]

        for state_key in state_coords.keys():
            if state_key in location:
                return state_key

        return None

    # Aggregate real case data by state
    state_cases = Report.objects.values('location').annotate(
        active_cases=Count('id', filter=Q(status__in=['submitted', 'under_review', 'approved'])),
        high_priority=Count('id', filter=Q(priority__in=['high', 'critical'])),
        total_cases=Count('id')
    ).exclude(location__isnull=True).exclude(location='')

    heatmap_data = []
    for case_data in state_cases:
        raw_location = case_data['location']
        state_key = normalize_state_key(raw_location)
        if state_key and state_key in state_coords:
            coords = state_coords[state_key]
            heatmap_data.append({
                'state': coords['name'],
                'lat': coords['lat'],
                'lng': coords['lng'],
                'active_cases': case_data['active_cases'],
                'high_priority': case_data['high_priority']
            })

    # If no real data but scams exist, show a fallback marker at India center
    if not heatmap_data:
        fallback_scams = Report.objects.filter(
            scam_probability__scam_level__in=['high', 'critical']
        ).count()

        if fallback_scams > 0:
            heatmap_data = [
                {
                    'state': 'Unknown',
                    'lat': 20.5937,
                    'lng': 78.9629,
                    'active_cases': fallback_scams,
                    'high_priority': Report.objects.filter(priority__in=['high', 'critical']).count(),
                }
            ]
        else:
            heatmap_data = []

    # Additional data for new dashboard layout
    threat_level = 'elevated'  # Could be 'low', 'elevated', 'critical'
    active_investigations = active_cases
    escalations_pending = case_escalations
    inter_agency_coordination = inter_agency_flags
    evidence_integrity = '98%'  # Mock - could calculate from evidence status

    # Recent activities for live stream
    recent_activities = [
        {'type': 'Case Updated', 'location': 'Mumbai', 'severity': 'warning', 'time': '14:32'},
        {'type': 'New Report Filed', 'location': 'Delhi', 'severity': 'info', 'time': '14:28'},
        {'type': 'Escalation Triggered', 'location': 'Bangalore', 'severity': 'critical', 'time': '14:15'},
        {'type': 'Evidence Verified', 'location': 'Chennai', 'severity': 'info', 'time': '14:02'},
        {'type': 'Inter-Agency Alert', 'location': 'Pune', 'severity': 'warning', 'time': '13:58'},
    ]

    # Priority queue
    priority_queue = recent_cases[:5]  # Use recent cases as priority queue

    # Intelligence breakdown data
    scam_vectors = {
        'impersonation': 45,
        'financial': 32,
        'social': 28,
    }

    victim_profiles = {
        'elderly': 38,
        'businesses': 25,
        'general': 37,
    }

    infrastructure = {
        'repeat_numbers': 156,
        'call_bursts': 23,
        'cross_state': 12,
    }

    # Escalation alerts
    escalation_alerts = [
        {'title': 'Escalation Overdue', 'message': 'Case LE-045 requires immediate attention', 'type': 'escalation_overdue', 'created_at': (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')},
        {'title': 'Jurisdiction Conflict', 'message': 'Cross-state investigation needs coordination', 'type': 'jurisdiction_conflict', 'created_at': (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')},
        {'title': 'Evidence Degradation Risk', 'message': 'Audio files expiring in 24 hours', 'type': 'evidence_degradation', 'created_at': (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')},
    ]

    # Recent alerts for notifications section - real data from notifications system
    from notifications.manager import NotificationManager
    recent_alerts = NotificationManager.get_recent_notifications(request.user, 5)  # Get recent notifications for current LE user

    # Convert to list format expected by template
    recent_alerts = list(recent_alerts.values('title', 'message', 'priority', 'created_at'))
    
    # Convert datetime objects to strings for template rendering
    for alert in recent_alerts:
        if 'created_at' in alert and alert['created_at']:
            alert['created_at'] = alert['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    # If no real notifications, provide some default alerts based on actual data
    if not recent_alerts:
        recent_alerts = []
        if high_priority_cases > 0:
            recent_alerts.append({
                'title': f'{high_priority_cases} High Priority Cases Active',
                'message': 'Immediate attention required for critical investigations.',
                'priority': 'urgent',
                'created_at': now.strftime('%Y-%m-%d %H:%M:%S')
            })
        if case_escalations > 0:
            recent_alerts.append({
                'title': f'{case_escalations} Cases Escalated This Week',
                'message': 'Escalated cases require inter-agency coordination.',
                'priority': 'warning',
                'created_at': (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            })
        if active_cases > 10:
            recent_alerts.append({
                'title': 'High Case Volume Detected',
                'message': f'{active_cases} active investigations currently ongoing.',
                'priority': 'info',
                'created_at': (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
            })

    context = {
        'case_escalations': case_escalations,
        'inter_agency_flags': inter_agency_flags,
        'evidence_count': evidence_count,
        'total_cases': total_cases,
        'active_cases': active_cases,
        'resolved_cases': resolved_cases,
        'high_priority_cases': high_priority_cases,
        'monthly_stats': json.dumps(monthly_stats),
        'scam_types_stats': json.dumps(scam_types_stats),
        'recent_cases': recent_cases,
        'recent_uploads': recent_uploads,
        'flagged_numbers': flagged_numbers,
        'heatmap_data': json.dumps(heatmap_data),
        'recent_alerts': recent_alerts,
        'last_updated': now.strftime('%Y-%m-%d %H:%M UTC'),
        # New context variables
        'threat_level': threat_level,
        'active_investigations': active_investigations,
        'escalations_pending': escalations_pending,
        'inter_agency_coordination': inter_agency_coordination,
        'evidence_integrity': evidence_integrity,
        'recent_activities': recent_activities,
        'priority_queue': priority_queue,
        'scam_vectors': scam_vectors,
        'victim_profiles': victim_profiles,
        'infrastructure': infrastructure,
        'escalation_alerts': escalation_alerts,
    }
    return render(request, 'dashboard/law_enforcement_dashboard.html', context)

@law_enforcement_required
def law_enforcement_analysis_view(request):
    """Analysis results page for law enforcement"""
    from analysis.models import AIAnalysisResult, ScamProbabilityScore
    from django.db.models import Count, Avg
    from django.db.models.functions import TruncDate

    # Get all analyses (law enforcement can see all)
    analyses = AIAnalysisResult.objects.select_related('call_record', 'requested_by').filter(status='completed').order_by('-created_at')[:50]

    # Summary statistics
    total_analyses = AIAnalysisResult.objects.filter(status='completed').count()
    safe_results = ScamProbabilityScore.objects.filter(scam_level='low').count()
    suspicious_results = ScamProbabilityScore.objects.filter(scam_level='medium').count()
    fraud_detected = ScamProbabilityScore.objects.filter(scam_level__in=['high', 'critical']).count()

    # Recent analyses for the list
    recent_analyses = []
    for analysis in analyses:
        scam_score = getattr(analysis, 'scam_probability', None)
        recent_analyses.append({
            'id': analysis.id,
            'analysis_id': str(analysis.id)[:8],
            'source': 'Call Recording' if analysis.audio_upload else 'Unknown',
            'date': analysis.created_at.date(),
            'risk_level': scam_score.get_scam_level_display() if scam_score else 'Unknown',
            'confidence_score': analysis.confidence_score or 0,
            'status': scam_score.scam_level if scam_score else 'unknown',
            'call_record': analysis.call_record,
            'scam_score': scam_score,
        })

    # Patterns and timeline data (mock for now, would be from actual analysis)
    detected_patterns = [
        {'name': 'Impersonation', 'count': 15},
        {'name': 'Urgency Pressure', 'count': 12},
        {'name': 'Repeated Attempts', 'count': 8},
        {'name': 'Known Scam Signature', 'count': 6},
    ]

    analysis_timeline = [
        {'step': 'Call Received', 'time': '0:00'},
        {'step': 'Audio Processed', 'time': '0:15'},
        {'step': 'Pattern Matched', 'time': '0:30'},
        {'step': 'Risk Scored', 'time': '0:45'},
    ]

    context = {
        'total_analyses': total_analyses,
        'safe_results': safe_results,
        'suspicious_results': suspicious_results,
        'fraud_detected': fraud_detected,
        'recent_analyses': recent_analyses,
        'detected_patterns': detected_patterns,
        'analysis_timeline': analysis_timeline,
    }
    return render(request, 'dashboard/law_enforcement_analysis.html', context)




