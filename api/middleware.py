from django.utils import timezone
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status

class APIRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path.startswith('/api/matches/'):
            user = request.user
            cache_key = f"api_rate_limit_{user.id}"
            
            # Check if user has exceeded rate limit
            request_count = cache.get(cache_key, 0)
            if request_count >= 100:  # 100 requests per minute limit
                return Response({
                    'error': 'Rate limit exceeded',
                    'message': 'Maximum 100 requests per minute allowed'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, timeout=60)
        
        return self.get_response(request)