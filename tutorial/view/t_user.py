from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.template.loader import render_to_string
from tutorial.models import YoutubeVideo, ViewerHistory, SearchHistory, SearchResult, Comment
from tutorial.forms import YoutubeVideoForm, CommentForm, SearchForm
from tutorial.utils import track_video_view, track_search_query

import json
from datetime import datetime, timedelta

from django.views.generic import DetailView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404



from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q


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
        
        # Add comments to context
        context['comments'] = Comment.objects.filter(video=video, is_approved=True)
        
        # Add form to context
        context['form'] = CommentForm()
        
        # Extract YouTube video ID
        video_url = video.youtube_link
        video_id = None
        
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1]
        
        context['video_id'] = video_id
        
        return context
    

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.video = self.object
            
            if request.user.is_authenticated:
                comment.user = request.user
                if form.cleaned_data.get('is_anonymous'):
                    comment.is_anonymous = True
                    comment.name = None
                else:
                    comment.name = request.user.username
            else:
                comment.name = form.cleaned_data.get('name') or "Anonymous"
            
            comment.save()
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Return JSON response for AJAX request
                comment_html = render_to_string('tutorial/user/comment_item.html', {'comment': comment})
                return JsonResponse({
                    'success': True,
                    'comment_html': comment_html,
                    'comment_count': Comment.objects.filter(video=self.object, is_approved=True).count()
                })
            
            # For non-AJAX requests, redirect as before
            return HttpResponseRedirect(reverse('youtube:detail', args=[self.object.pk]))
        
        # If form is not valid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
            
        # For non-AJAX requests, re-render the page with form errors
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)