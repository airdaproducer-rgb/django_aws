from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.template.loader import render_to_string
from tutorial.models import YoutubeVideo, ViewerHistory, SearchHistory, SearchResult
from tutorial.forms import SearchForm

from django.http import HttpResponseRedirect
from django.urls import reverse

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def record_view(request, video, page_type):
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    user = request.user if request.user.is_authenticated else None
    
    ViewerHistory.objects.create(
        user=user,
        video=video,
        ip_address=ip_address,
        user_agent=user_agent,
        page_type=page_type
    )


class UserListView(ListView):
    model = YoutubeVideo
    template_name = 'tutorial/user/list.html'
    context_object_name = 'videos'
    paginate_by = 18
    
    def get_queryset(self):
        queryset = YoutubeVideo.objects.filter(is_active=True)
        query = self.request.GET.get('q', '')
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
            
            # Record search history
            ip_address = get_client_ip(self.request)
            user_agent = self.request.META.get('HTTP_USER_AGENT', '')
            user = self.request.user if self.request.user.is_authenticated else None
            
            search_history = SearchHistory.objects.create(
                user=user,
                query=query,
                ip_address=ip_address,
                user_agent=user_agent,
                results_count=queryset.count()
            )
            
            # Record search results
            for position, video in enumerate(queryset, 1):
                SearchResult.objects.create(
                    search=search_history,
                    video=video,
                    position=position
                )
        
        # Record list page view for first video if exists
        if queryset.exists() and not query:
            first_video = queryset.first()
            record_view(self.request, first_video, 'list')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class UserDetailView(DetailView):
    model = YoutubeVideo
    template_name = 'tutorial/user/detail.html'
    context_object_name = 'video'
    
    def get_queryset(self):
        # Only active videos
        return YoutubeVideo.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.object
    
        # Extract YouTube video ID
        video_url = video.youtube_link
        video_id = None
        
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1]
        
        context['video_id'] = video_id
        
        # Add tokens from cookies if they exist
        context['user_tokens'] = self.request.COOKIES.get('comment_tokens', '')
        
        return context
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        video = self.object
        record_view(request, video, 'detail')
        return response