"""
Views for Honeypot Management
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from accounts.utils import admin_required, law_enforcement_required

from .models import HoneypotSession, HoneypotInteraction, ScammerProfile
from .forms import HoneypotSessionForm, HoneypotInteractionForm, ScammerProfileForm, HoneypotConfigurationForm
from .ai_agent import HoneypotAIAgent, ScamType

logger = logging.getLogger(__name__)

@login_required
def honeypot_dashboard(request):
    """Main honeypot dashboard view"""
    if request.user.role == 'law_enforcement':
        # Law enforcement sees all data
        active_sessions = HoneypotSession.objects.filter(status='active').order_by('-start_time')
        recent_interactions = HoneypotInteraction.objects.select_related('honeypot_session', 'scammer_profile').order_by('-start_time')[:20]
        top_scammers = ScammerProfile.objects.order_by('-risk_score')[:10]
        total_sessions = HoneypotSession.objects.count()
        total_interactions = HoneypotInteraction.objects.count()
        total_scammers = ScammerProfile.objects.count()
        high_risk_sessions = HoneypotInteraction.objects.filter(scammer_profile__risk_score__gte=0.7).count()
        ai_learning_feeds = HoneypotInteraction.objects.filter(start_time__gte=timezone.now() - timezone.timedelta(days=7)).count()

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

        origin_aggregate = {}
        origin_interactions = HoneypotInteraction.objects.select_related('scammer_profile').exclude(scammer_profile__isnull=True)

        for interaction in origin_interactions:
            location_data = interaction.scammer_profile.location_data or {}
            state = location_data.get('state') or location_data.get('region') or location_data.get('province')
            lat = location_data.get('lat') or location_data.get('latitude')
            lng = location_data.get('lng') or location_data.get('longitude') or location_data.get('lon')

            if state:
                state_key = str(state).strip().lower()
                if state_key in state_coords:
                    coords = state_coords[state_key]
                    key = coords['name']
                    origin_aggregate.setdefault(key, {
                        'state': coords['name'],
                        'lat': coords['lat'],
                        'lng': coords['lng'],
                        'count': 0
                    })
                    origin_aggregate[key]['count'] += 1
                    continue

            if lat is not None and lng is not None:
                key = f"{lat},{lng}"
                origin_aggregate.setdefault(key, {
                    'state': state or 'Unknown',
                    'lat': float(lat),
                    'lng': float(lng),
                    'count': 0
                })
                origin_aggregate[key]['count'] += 1

        origin_points = list(origin_aggregate.values())

        context = {
            'active_sessions': active_sessions,
            'recent_interactions': recent_interactions,
            'top_scammers': top_scammers,
            'total_sessions': total_sessions,
            'total_interactions': total_interactions,
            'total_scammers': total_scammers,
            'high_risk_sessions': high_risk_sessions,
            'ai_learning_feeds': ai_learning_feeds,
            'origin_points': json.dumps(origin_points),
        }

        return render(request, 'honeypot/dashboard_law_enforcement.html', context)
    else:
        # Regular users see their own data
        active_sessions = HoneypotSession.objects.filter(
            Q(created_by=request.user) | Q(assigned_to=request.user),
            status='active'
        ).order_by('-start_time')

        # Get recent interactions
        recent_interactions = HoneypotInteraction.objects.filter(
            honeypot_session__created_by=request.user
        ).select_related('honeypot_session', 'scammer_profile').order_by('-start_time')[:10]

        # Get top scammer profiles
        top_scammers = ScammerProfile.objects.filter(
            created_by=request.user
        ).order_by('-risk_score')[:5]

        context = {
            'active_sessions': active_sessions,
            'recent_interactions': recent_interactions,
            'top_scammers': top_scammers,
            'total_sessions': HoneypotSession.objects.filter(created_by=request.user).count(),
            'total_interactions': HoneypotInteraction.objects.filter(honeypot_session__created_by=request.user).count(),
            'total_scammers': ScammerProfile.objects.filter(created_by=request.user).count(),
        }

        return render(request, 'honeypot/dashboard.html', context)

@login_required
def honeypot_session_list(request):
    """List all honeypot sessions"""
    sessions = HoneypotSession.objects.filter(
        Q(created_by=request.user) | Q(assigned_to=request.user)
    ).order_by('-start_time')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        sessions = sessions.filter(
            Q(session_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': HoneypotSession.SESSION_STATUS_CHOICES,
    }

    return render(request, 'honeypot/session_list.html', context)

@login_required
def honeypot_session_create(request):
    """Create a new honeypot session"""
    if request.method == 'POST':
        form = HoneypotSessionForm(request.POST)
        config_form = HoneypotConfigurationForm(request.POST)

        if form.is_valid() and config_form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user

            # Save configuration
            config_data = config_form.cleaned_data
            session.configuration = {
                'personality': {
                    'name': config_data['personality_name'],
                    'age': config_data['personality_age'],
                    'occupation': config_data['personality_occupation'],
                    'location': config_data['personality_location'],
                },
                'behavior': {
                    'max_conversation_length': config_data['max_conversation_length'],
                    'resistance_threshold': config_data['resistance_threshold'],
                    'enable_auto_termination': config_data['enable_auto_termination'],
                    'scam_type_focus': config_data['scam_type_focus'] or None,
                }
            }

            session.save()

            messages.success(request, f'Honeypot session "{session.session_name}" created successfully.')
            return redirect('honeypot_session_detail', session_id=session.id)
    else:
        form = HoneypotSessionForm()
        config_form = HoneypotConfigurationForm()

    context = {
        'form': form,
        'config_form': config_form,
        'title': 'Create Honeypot Session',
    }

    return render(request, 'honeypot/session_form.html', context)

@login_required
def honeypot_session_detail(request, session_id):
    """View honeypot session details"""
    session = get_object_or_404(
        HoneypotSession,
        id=session_id,
        created_by=request.user
    )

    # Get interactions for this session
    interactions = session.interactions.select_related('scammer_profile').order_by('-start_time')

    # Pagination for interactions
    paginator = Paginator(interactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'session': session,
        'page_obj': page_obj,
        'total_interactions': interactions.count(),
        'active_interactions': interactions.filter(status='active').count(),
        'completed_interactions': interactions.filter(status='completed').count(),
    }

    return render(request, 'honeypot/session_detail.html', context)

@login_required
def honeypot_session_edit(request, session_id):
    """Edit honeypot session"""
    session = get_object_or_404(
        HoneypotSession,
        id=session_id,
        created_by=request.user
    )

    if request.method == 'POST':
        form = HoneypotSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f'Session "{session.session_name}" updated successfully.')
            return redirect('honeypot_session_detail', session_id=session.id)
    else:
        form = HoneypotSessionForm(instance=session)

    context = {
        'form': form,
        'session': session,
        'title': 'Edit Honeypot Session',
    }

    return render(request, 'honeypot/session_edit.html', context)

@login_required
@require_POST
def honeypot_session_toggle_status(request, session_id):
    """Toggle honeypot session status (activate/deactivate)"""
    session = get_object_or_404(
        HoneypotSession,
        id=session_id,
        created_by=request.user
    )

    if session.status == 'active':
        session.status = 'completed'
        session.end_time = timezone.now()
        messages.success(request, f'Session "{session.session_name}" deactivated.')
    elif session.status in ['completed', 'terminated']:
        session.status = 'active'
        session.end_time = None
        messages.success(request, f'Session "{session.session_name}" reactivated.')

    session.save()

    return redirect('honeypot_session_detail', session_id=session.id)

@login_required
def honeypot_interaction_detail(request, interaction_id):
    """View honeypot interaction details"""
    interaction = get_object_or_404(
        HoneypotInteraction,
        id=interaction_id,
        honeypot_session__created_by=request.user
    )

    # Get conversation transcript
    transcript = interaction.get_conversation_transcript()

    # Get extracted information
    extracted_info = interaction.extracted_information

    context = {
        'interaction': interaction,
        'transcript': transcript,
        'extracted_info': extracted_info,
        'phone_numbers': extracted_info.get('phone_numbers', []),
        'payment_details': extracted_info.get('payment_details', []),
        'scam_scripts': extracted_info.get('scam_scripts', []),
        'threats': extracted_info.get('threats', []),
    }

    return render(request, 'honeypot/interaction_detail.html', context)

@login_required
def honeypot_interaction_manual(request, session_id):
    """Manual interaction input for honeypot session"""
    session = get_object_or_404(
        HoneypotSession,
        id=session_id,
        created_by=request.user,
        status='active'
    )

    if request.method == 'POST':
        form = HoneypotInteractionForm(request.POST)
        if form.is_valid():
            # Create AI agent for this session
            agent = HoneypotAIAgent(session)

            # Process the scammer's message
            scammer_message = form.cleaned_data['scammer_message']
            call_context = form.cleaned_data.get('call_context', '{}')

            if call_context:
                call_context = json.loads(call_context)
            else:
                call_context = {}

            # Generate response
            response, should_terminate = agent.process_incoming_message(scammer_message, call_context)

            # For manual interaction, we'll assume a dummy scammer number
            # In real implementation, this would come from the actual call
            dummy_scammer_number = call_context.get('caller_number', 'unknown')

            # Save interaction if this is the start of a conversation
            if agent.turn_count == 1:
                interaction = agent.save_interaction(dummy_scammer_number)
                if interaction:
                    messages.success(request, 'Interaction started and response generated.')
                    return redirect('honeypot_interaction_detail', interaction_id=interaction.id)
                else:
                    messages.error(request, 'Failed to save interaction.')
            else:
                messages.info(request, f'Generated response: {response}')

    else:
        form = HoneypotInteractionForm()

    context = {
        'session': session,
        'form': form,
        'title': 'Manual Interaction',
    }

    return render(request, 'honeypot/interaction_manual.html', context)

@login_required
def scammer_profile_list(request):
    """List all scammer profiles"""
    profiles = ScammerProfile.objects.filter(
        created_by=request.user
    ).order_by('-risk_score')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        profiles = profiles.filter(
            Q(phone_number__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        profiles = profiles.filter(status=status_filter)

    # Risk score filter
    risk_filter = request.GET.get('risk_level', '')
    if risk_filter:
        if risk_filter == 'high':
            profiles = profiles.filter(risk_score__gte=0.7)
        elif risk_filter == 'medium':
            profiles = profiles.filter(risk_score__gte=0.4, risk_score__lt=0.7)
        elif risk_filter == 'low':
            profiles = profiles.filter(risk_score__lt=0.4)

    # Pagination
    paginator = Paginator(profiles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'risk_filter': risk_filter,
        'status_choices': ScammerProfile.PROFILE_STATUS_CHOICES,
        'risk_levels': [('high', 'High Risk'), ('medium', 'Medium Risk'), ('low', 'Low Risk')],
    }

    return render(request, 'honeypot/scammer_list.html', context)

@login_required
def scammer_profile_detail(request, profile_id):
    """View scammer profile details"""
    profile = get_object_or_404(
        ScammerProfile,
        id=profile_id,
        created_by=request.user
    )

    # Get interactions for this scammer
    interactions = profile.interactions.select_related('honeypot_session').order_by('-start_time')

    # Pagination
    paginator = Paginator(interactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': profile,
        'page_obj': page_obj,
        'total_interactions': interactions.count(),
        'scam_types': profile.scam_types,
        'associated_numbers': profile.associated_numbers,
    }

    return render(request, 'honeypot/scammer_detail.html', context)

@login_required
def scammer_profile_create(request):
    """Create a new scammer profile"""
    if request.method == 'POST':
        form = ScammerProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.created_by = request.user
            profile.save()

            messages.success(request, f'Scammer profile for {profile.phone_number} created successfully.')
            return redirect('scammer_profile_detail', profile_id=profile.id)
    else:
        form = ScammerProfileForm()

    context = {
        'form': form,
        'title': 'Create Scammer Profile',
    }

    return render(request, 'honeypot/scammer_form.html', context)

@login_required
def scammer_profile_edit(request, profile_id):
    """Edit scammer profile"""
    profile = get_object_or_404(
        ScammerProfile,
        id=profile_id,
        created_by=request.user
    )

    if request.method == 'POST':
        form = ScammerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Profile for {profile.phone_number} updated successfully.')
            return redirect('scammer_profile_detail', profile_id=profile.id)
    else:
        form = ScammerProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
        'title': 'Edit Scammer Profile',
    }

    return render(request, 'honeypot/scammer_edit.html', context)

@law_enforcement_required
def honeypot_reports(request):
    """Generate reports for honeypot activities"""
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base querysets
    sessions = HoneypotSession.objects.filter(created_by=request.user)
    interactions = HoneypotInteraction.objects.filter(honeypot_session__created_by=request.user)
    profiles = ScammerProfile.objects.filter(created_by=request.user)

    if start_date:
        sessions = sessions.filter(start_time__gte=start_date)
        interactions = interactions.filter(start_time__gte=start_date)
        profiles = profiles.filter(first_seen__gte=start_date)

    if end_date:
        sessions = sessions.filter(start_time__lte=end_date)
        interactions = interactions.filter(start_time__lte=end_date)
        profiles = profiles.filter(first_seen__lte=end_date)

    # Aggregate statistics
    stats = {
        'total_sessions': sessions.count(),
        'active_sessions': sessions.filter(status='active').count(),
        'total_interactions': interactions.count(),
        'successful_interactions': interactions.filter(success_rating__gte=0.7).count(),
        'total_scammers': profiles.count(),
        'high_risk_scammers': profiles.filter(risk_score__gte=0.7).count(),
        'extracted_phone_numbers': sum(len(interaction.get_extracted_phone_numbers()) for interaction in interactions),
        'extracted_payment_details': sum(len(interaction.get_extracted_payment_details()) for interaction in interactions),
    }

    # Scam type distribution
    scam_types = {}
    for interaction in interactions:
        scam_type = interaction.scam_type_identified or 'unknown'
        scam_types[scam_type] = scam_types.get(scam_type, 0) + 1

    context = {
        'stats': stats,
        'scam_types': scam_types,
        'start_date': start_date,
        'end_date': end_date,
        'sessions': sessions.order_by('-start_time')[:10],  # Recent sessions
        'top_scammers': profiles.order_by('-risk_score')[:10],  # Top risk scammers
    }

    return render(request, 'honeypot/reports.html', context)

# API endpoints for real-time honeypot operations

@login_required
@require_POST
def api_process_call(request, session_id):
    """API endpoint to process incoming calls for honeypot sessions"""
    try:
        session = get_object_or_404(
            HoneypotSession,
            id=session_id,
            created_by=request.user,
            status='active'
        )

        # Parse request data
        data = json.loads(request.body)
        scammer_message = data.get('message', '')
        caller_number = data.get('caller_number', 'unknown')
        call_context = data.get('context', {})

        # Create AI agent and process message
        agent = HoneypotAIAgent(session)
        response, should_terminate = agent.process_incoming_message(scammer_message, call_context)

        # Save interaction
        interaction = agent.save_interaction(caller_number)

        return JsonResponse({
            'success': True,
            'response': response,
            'terminate': should_terminate,
            'interaction_id': str(interaction.id) if interaction else None,
            'state': agent.state.value,
            'turn_count': agent.turn_count
        })

    except Exception as e:
        logger.error(f"API call processing error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def api_session_status(request, session_id):
    """API endpoint to get honeypot session status"""
    session = get_object_or_404(
        HoneypotSession,
        id=session_id,
        created_by=request.user
    )

    # Get recent interactions
    recent_interactions = session.interactions.order_by('-start_time')[:5]

    data = {
        'id': str(session.id),
        'status': session.status,
        'total_calls': session.total_calls_received,
        'suspicious_calls': session.suspicious_calls_count,
        'recent_interactions': [
            {
                'id': str(interaction.id),
                'scammer': interaction.scammer_profile.phone_number,
                'status': interaction.status,
                'start_time': interaction.start_time.isoformat(),
                'success_rating': interaction.success_rating
            }
            for interaction in recent_interactions
        ]
    }

    return JsonResponse(data)
