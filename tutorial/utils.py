from .models import ViewerHistory, SearchHistory

def track_video_view(request, video):
    if request.user.is_authenticated:
        user = request.user
    else:
        user = None
    
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Create view history
    ViewerHistory.objects.create(
        user=user,
        video=video,
        ip_address=ip,
        user_agent=user_agent
    )

def track_search_query(request, query, results_count):
    if request.user.is_authenticated:
        user = request.user
    else:
        user = None
    
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Create search history
    SearchHistory.objects.create(
        user=user,
        query=query,
        ip_address=ip,
        user_agent=user_agent,
        results_count=results_count
    )