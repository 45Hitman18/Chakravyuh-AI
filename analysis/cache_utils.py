"""
Caching utilities for analysis and dashboard data.
Provides cache decorators and helper functions for frequently accessed queries.
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps
from .models import AIAnalysisResult, ScamProbabilityScore
from calls.models import CallRecord

# Cache key prefixes
CACHE_KEY_ANALYSIS_STATS = 'analysis_stats_{}'
CACHE_KEY_DASHBOARD_STATS = 'dashboard_stats_{}'
CACHE_KEY_SCAM_SCORES = 'scam_scores_{}'
CACHE_KEY_TOP_SCAMMERS = 'top_scammers_{}'
CACHE_KEY_CALL_STATS = 'call_stats_{}'


def cache_analysis_stats(user_id=None, timeout=None):
    """
    Cache analysis statistics for a user or globally.
    
    Args:
        user_id: Optional user ID for user-specific stats
        timeout: Cache timeout in seconds
    
    Returns:
        dict with analysis statistics
    """
    if timeout is None:
        timeout = settings.CACHE_TIMEOUT_ANALYSIS_STATS
    
    cache_key = CACHE_KEY_ANALYSIS_STATS.format(user_id or 'all')
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    # Query the data
    queryset = AIAnalysisResult.objects.filter(status='completed')
    if user_id:
        queryset = queryset.filter(requested_by_id=user_id)
    
    stats = {
        'total': queryset.count(),
        'safe': ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            scam_level='low'
        ).count() if not user_id else ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            analysis__requested_by_id=user_id,
            scam_level='low'
        ).count(),
        'suspicious': ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            scam_level='medium'
        ).count() if not user_id else ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            analysis__requested_by_id=user_id,
            scam_level='medium'
        ).count(),
        'fraud_confirmed': ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            scam_level__in=['high', 'critical']
        ).count() if not user_id else ScamProbabilityScore.objects.filter(
            analysis__status='completed',
            analysis__requested_by_id=user_id,
            scam_level__in=['high', 'critical']
        ).count(),
    }
    
    # Cache the result
    cache.set(cache_key, stats, timeout)
    return stats


def cache_dashboard_stats(user_id=None, timeout=None):
    """
    Cache comprehensive dashboard statistics.
    
    Args:
        user_id: Optional user ID for user-specific stats
        timeout: Cache timeout in seconds
    
    Returns:
        dict with dashboard statistics
    """
    if timeout is None:
        timeout = settings.CACHE_TIMEOUT_DASHBOARD_STATS
    
    cache_key = CACHE_KEY_DASHBOARD_STATS.format(user_id or 'all')
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    # Query the data
    call_queryset = CallRecord.objects.all()
    analysis_queryset = AIAnalysisResult.objects.all()
    
    if user_id:
        call_queryset = call_queryset.filter(recorded_by_id=user_id)
        analysis_queryset = analysis_queryset.filter(requested_by_id=user_id)
    
    stats = {
        'total_calls': call_queryset.count(),
        'analyzed_calls': analysis_queryset.filter(status='completed').count(),
        'suspicious_calls': call_queryset.filter(scam_probability__overall_score__gte=0.6).count(),
        'confirmed_scams': call_queryset.filter(
            scam_probability__scam_level__in=['high', 'critical']
        ).count(),
    }
    
    # Cache the result
    cache.set(cache_key, stats, timeout)
    return stats


def cache_scam_scores(score_id, timeout=None):
    """
    Cache individual scam probability scores.
    
    Args:
        score_id: ScamProbabilityScore ID
        timeout: Cache timeout in seconds
    
    Returns:
        ScamProbabilityScore data as dict
    """
    if timeout is None:
        timeout = settings.CACHE_TIMEOUT_SCAM_SCORES
    
    cache_key = CACHE_KEY_SCAM_SCORES.format(score_id)
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
    
    try:
        score = ScamProbabilityScore.objects.get(id=score_id)
        data = {
            'id': str(score.id),
            'overall_score': score.overall_score,
            'scam_level': score.scam_level,
            'voice_pattern_score': score.voice_pattern_score,
            'speech_content_score': score.speech_content_score,
            'urgency_indicators': score.urgency_indicators,
        }
        cache.set(cache_key, data, timeout)
        return data
    except ScamProbabilityScore.DoesNotExist:
        return None


def invalidate_analysis_cache(user_id=None):
    """Invalidate analysis cache when new data is added."""
    cache_key = CACHE_KEY_ANALYSIS_STATS.format(user_id or 'all')
    cache.delete(cache_key)


def invalidate_dashboard_cache(user_id=None):
    """Invalidate dashboard cache when data changes."""
    cache_key = CACHE_KEY_DASHBOARD_STATS.format(user_id or 'all')
    cache.delete(cache_key)


def invalidate_scam_score_cache(score_id):
    """Invalidate specific scam score cache."""
    cache_key = CACHE_KEY_SCAM_SCORES.format(score_id)
    cache.delete(cache_key)


def clear_all_cache():
    """Clear all analysis-related caches."""
    cache.delete_pattern(CACHE_KEY_ANALYSIS_STATS.format('*'))
    cache.delete_pattern(CACHE_KEY_DASHBOARD_STATS.format('*'))
    cache.delete_pattern(CACHE_KEY_SCAM_SCORES.format('*'))


# Decorator to cache view results
def cache_page_timeout(timeout):
    """
    Decorator to cache page results for a specified timeout.
    
    Usage:
        @cache_page_timeout(300)
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Create cache key based on user and URL
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            cache_key = f"page_{func.__name__}_{user_id}_{request.path_info}"
            
            # Check cache
            response = cache.get(cache_key)
            if response is not None:
                return response
            
            # Call the view
            response = func(request, *args, **kwargs)
            
            # Cache the response (only for GET requests)
            if request.method == 'GET':
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator
