"""
Rate limiting utilities for API and upload endpoints.
Provides rate limiting decorators and middleware for security.
"""

from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.utils.decorators import wraps
from functools import update_wrapper
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Rate limit key prefixes
RATE_LIMIT_UPLOAD_KEY = 'ratelimit_upload_{}'
RATE_LIMIT_API_KEY = 'ratelimit_api_{}_{}'
RATE_LIMIT_LOGIN_KEY = 'ratelimit_login_{}'


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit_uploads(max_uploads=10, period=3600):
    """
    Decorator to rate limit file uploads per user.
    
    Args:
        max_uploads: Maximum number of uploads allowed
        period: Time period in seconds (default: 1 hour)
    
    Usage:
        @rate_limit_uploads(max_uploads=10, period=3600)
        def upload_audio(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_authenticated:
                return HttpResponse('Authentication required', status=401)
            
            # Create cache key
            user_id = request.user.id
            cache_key = RATE_LIMIT_UPLOAD_KEY.format(user_id)
            
            # Get current upload count
            upload_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time()})
            current_time = time.time()
            
            # Check if period has expired
            if current_time - upload_data['reset_time'] > period:
                upload_data = {'count': 0, 'reset_time': current_time}
            
            # Check if limit exceeded
            if upload_data['count'] >= max_uploads:
                remaining_time = int(period - (current_time - upload_data['reset_time']))
                error_msg = f'Upload limit exceeded. Please try again in {remaining_time} seconds.'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_msg}, status=429)
                else:
                    messages.error(request, error_msg)
                    return JsonResponse({'error': error_msg}, status=429)
            
            # Increment upload count
            upload_data['count'] += 1
            cache.set(cache_key, upload_data, period)
            
            # Add rate limit info to request for logging
            request.rate_limit_remaining = max_uploads - upload_data['count']
            request.rate_limit_reset = int(upload_data['reset_time'] + period)
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def rate_limit_api(endpoint_name, max_requests=100, period=3600):
    """
    Decorator to rate limit API endpoints.
    
    Args:
        endpoint_name: Name of the endpoint for logging
        max_requests: Maximum number of requests allowed
        period: Time period in seconds (default: 1 hour)
    
    Usage:
        @rate_limit_api('analysis_api', max_requests=100, period=3600)
        def api_analysis_status(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get identifier (user ID or IP)
            if request.user.is_authenticated:
                identifier = f'user_{request.user.id}'
            else:
                identifier = f'ip_{get_client_ip(request)}'
            
            cache_key = RATE_LIMIT_API_KEY.format(endpoint_name, identifier)
            
            # Get current request count
            request_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time()})
            current_time = time.time()
            
            # Check if period has expired
            if current_time - request_data['reset_time'] > period:
                request_data = {'count': 0, 'reset_time': current_time}
            
            # Check if limit exceeded
            if request_data['count'] >= max_requests:
                logger.warning(f'Rate limit exceeded for {endpoint_name}: {identifier}')
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': int(period - (current_time - request_data['reset_time']))
                }, status=429)
            
            # Increment request count
            request_data['count'] += 1
            cache.set(cache_key, request_data, period)
            
            # Add headers to response
            response = view_func(request, *args, **kwargs)
            response['X-RateLimit-Limit'] = str(max_requests)
            response['X-RateLimit-Remaining'] = str(max_requests - request_data['count'])
            response['X-RateLimit-Reset'] = str(int(request_data['reset_time'] + period))
            
            return response
        
        return wrapped_view
    return decorator


def rate_limit_login(max_attempts=5, period=900):
    """
    Decorator to rate limit login attempts.
    
    Args:
        max_attempts: Maximum failed attempts allowed
        period: Time period in seconds (default: 15 minutes)
    
    Usage:
        @rate_limit_login(max_attempts=5, period=900)
        def login_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get identifier (email or IP)
            identifier = request.POST.get('email', get_client_ip(request))
            cache_key = RATE_LIMIT_LOGIN_KEY.format(identifier)
            
            # Get current attempt count
            attempt_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time()})
            current_time = time.time()
            
            # Check if period has expired
            if current_time - attempt_data['reset_time'] > period:
                attempt_data = {'count': 0, 'reset_time': current_time}
            
            # Check if limit exceeded
            if attempt_data['count'] >= max_attempts:
                remaining_time = int(period - (current_time - attempt_data['reset_time']))
                error_msg = f'Too many login attempts. Please try again in {remaining_time} seconds.'
                messages.error(request, error_msg)
                return JsonResponse({'error': error_msg}, status=429)
            
            # Call the view
            response = view_func(request, *args, **kwargs)
            
            # If login failed (response has error), increment counter
            if hasattr(response, 'context_data') and response.context_data.get('error'):
                attempt_data['count'] += 1
                cache.set(cache_key, attempt_data, period)
            
            return response
        
        return wrapped_view
    return decorator


class RateLimitMiddleware:
    """
    Middleware to track and enforce rate limits across all requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get or create rate limit data
        if request.user.is_authenticated:
            identifier = f'user_{request.user.id}'
        else:
            identifier = f'ip_{get_client_ip(request)}'
        
        cache_key = f'ratelimit_global_{identifier}'
        request_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time()})
        current_time = time.time()
        
        # Check if global rate limit period has expired (1 hour)
        if current_time - request_data['reset_time'] > 3600:
            request_data = {'count': 0, 'reset_time': current_time}
        
        # Set global request limit to 1000 requests per hour
        if request_data['count'] >= 1000:
            return JsonResponse({
                'error': 'Global rate limit exceeded'
            }, status=429)
        
        # Increment global request count
        request_data['count'] += 1
        cache.set(cache_key, request_data, 3600)
        
        # Add rate limit info to request
        request.rate_limit_count = request_data['count']
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers to response
        response['X-RateLimit-Limit'] = '1000'
        response['X-RateLimit-Remaining'] = str(1000 - request_data['count'])
        response['X-RateLimit-Reset'] = str(int(request_data['reset_time'] + 3600))
        
        return response


def get_rate_limit_status(request):
    """
    Get rate limit status for a user or IP.
    
    Returns:
        dict with rate limit information
    """
    if request.user.is_authenticated:
        identifier = f'user_{request.user.id}'
    else:
        identifier = f'ip_{get_client_ip(request)}'
    
    cache_key = f'ratelimit_global_{identifier}'
    request_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time()})
    
    return {
        'requests': request_data['count'],
        'limit': 1000,
        'remaining': 1000 - request_data['count'],
        'reset_time': int(request_data['reset_time'] + 3600)
    }
