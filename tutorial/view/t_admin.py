from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy,reverse
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

from tutorial.models import YoutubeVideo, ViewerHistory, SearchHistory, Comment,SearchHistory, SearchResult
from tutorial.forms import YoutubeVideoForm, CommentForm, SearchForm
from tutorial.utils import track_video_view, track_search_query

import json
from datetime import datetime, timedelta
from django.utils import timezone

# views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Count, Avg
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.db.models import Q
import json

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class YADashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tutorial/admn/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get data for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Video statistics
        context['total_videos'] = YoutubeVideo.objects.count()
        context['active_videos'] = YoutubeVideo.objects.filter(is_active=True).count()
        
        # Viewer statistics
        context['total_views'] = ViewerHistory.objects.count()
        context['views_last_30days'] = ViewerHistory.objects.filter(view_date__gte=thirty_days_ago).count()
        
        # Comment statistics
        context['total_comments'] = Comment.objects.count()
        context['comments_last_30days'] = Comment.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # Search statistics
        context['total_searches'] = SearchHistory.objects.count()
        context['searches_last_30days'] = SearchHistory.objects.filter(search_date__gte=thirty_days_ago).count()
        
        # Graph data for views over time
        days_labels = [(timezone.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, -1, -1)]
        
        # Views data
        views_data = []
        for day in days_labels:
            views_count = ViewerHistory.objects.filter(view_date__date=day).count()
            views_data.append(views_count)
        
        # Comments data
        comments_data = []
        for day in days_labels:
            comments_count = Comment.objects.filter(created_at__date=day).count()
            comments_data.append(comments_count)
        
        # Searches data
        searches_data = []
        for day in days_labels:
            searches_count = SearchHistory.objects.filter(search_date__date=day).count()
            searches_data.append(searches_count)
        
        context['days_labels'] = json.dumps(days_labels)
        context['views_data'] = json.dumps(views_data)
        context['comments_data'] = json.dumps(comments_data)
        context['searches_data'] = json.dumps(searches_data)
        
        return context

class YAVideoListView(LoginRequiredMixin, ListView):
    model = YoutubeVideo
    template_name = 'tutorial/admn/video_list.html'
    context_object_name = 'videos'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(youtube_link__icontains=search_query)
            )
            
            # Track search if there's a query
            search_history = SearchHistory(
                user=self.request.user if self.request.user.is_authenticated else None,
                query=search_query,
                ip_address=get_client_ip(self.request),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                results_count=queryset.count()
            )
            search_history.save()
            
            # Track search results
            for position, video in enumerate(queryset, 1):
                SearchResult.objects.create(
                    search=search_history,
                    video=video,
                    position=position
                )
        
        # Date filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add view stats
        videos_with_stats = []
        for video in context['videos']:
            video_data = {
                'video': video,
                'view_count': ViewerHistory.objects.filter(video=video).count(),
                'comment_count': Comment.objects.filter(video=video).count()
            }
            videos_with_stats.append(video_data)
        
        context['videos_with_stats'] = videos_with_stats
        
        # Get total counts for graph data
        view_data = []
        for video in YoutubeVideo.objects.all():
            view_count = ViewerHistory.objects.filter(video=video).count()
            view_data.append({
                'title': video.title,
                'views': view_count
            })
        
        context['view_data_json'] = json.dumps(view_data)
        
        # Get search parameters for maintaining state
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

class YAVideoDetailView(DetailView):
    model = YoutubeVideo
    template_name = 'tutorial/admn/video_detail.html'
    context_object_name = 'video'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.get_object()
        
        # Add stats to context
        context['view_count'] = ViewerHistory.objects.filter(video=video).count()
        context['list_view_count'] = ViewerHistory.objects.filter(video=video, page_type='list').count()
        context['detail_view_count'] = ViewerHistory.objects.filter(video=video, page_type='detail').count()
        context['comment_count'] = Comment.objects.filter(video=video).count()
        context['comments'] = Comment.objects.filter(video=video)
        
        # Track this view
        if not self.request.user.is_staff:  # Don't track admin views
            ViewerHistory.objects.create(
                user=self.request.user if self.request.user.is_authenticated else None,
                video=video,
                ip_address=get_client_ip(self.request),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                page_type='detail'
            )
        
        # View history data for graph
        thirty_days_ago = timezone.now() - timedelta(days=30)
        days_labels = [(timezone.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, -1, -1)]
        
        views_data = []
        for day in days_labels:
            views_count = ViewerHistory.objects.filter(
                video=video,
                view_date__date=day
            ).count()
            views_data.append(views_count)
        
        context['days_labels'] = json.dumps(days_labels)
        context['views_data'] = json.dumps(views_data)
        
        return context

class YAVideoCreateView(LoginRequiredMixin, CreateView):
    model = YoutubeVideo
    template_name = 'tutorial/admn/video_form.html'
    fields = ['title', 'description', 'youtube_link', 'is_active', 'password', 'admin_notes']
    success_url = reverse_lazy('youtube:video_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Video successfully created!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = False
        context['instructions'] = """
        <h3>Instructions for Creating a Video</h3>
        <ul>
            <li>Enter a clear and descriptive title</li>
            <li>Provide a detailed description</li>
            <li>YouTube Link must be a valid URL</li>
            <li>Add a password if you want to restrict access</li>
            <li>Admin notes are only visible to administrators</li>
        </ul>
        """
        return context

class YAVideoUpdateView(LoginRequiredMixin, UpdateView):
    model = YoutubeVideo
    template_name = 'tutorial/admn/video_form.html'
    fields = ['title', 'description', 'youtube_link', 'is_active', 'password', 'admin_notes']
    
    def get_success_url(self):
        return reverse_lazy('youtube:video_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Video successfully updated!")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        context['instructions'] = """
        <h3>Instructions for Updating a Video</h3>
        <ul>
            <li>Modify any field as needed</li>
            <li>Toggle is_active to control visibility</li>
            <li>Update the password or leave it blank to remove password protection</li>
            <li>Add or modify admin notes as needed</li>
        </ul>
        """
        return context

class YAVideoDeleteView(LoginRequiredMixin, DeleteView):
    model = YoutubeVideo
    template_name = 'tutorial/admn/video_confirm_delete.html'
    success_url = reverse_lazy('youtube:video_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Video successfully deleted!")
        return super().delete(request, *args, **kwargs)

class YAVideoBulkActionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        video_ids = request.POST.getlist('video_ids')
        action = request.POST.get('action')
        
        if not video_ids:
            messages.error(request, "No videos selected!")
            return redirect('youtube:video_list')
        
        videos = YoutubeVideo.objects.filter(id__in=video_ids)
        
        if action == 'activate':
            videos.update(is_active=True)
            messages.success(request, f"{len(video_ids)} videos activated successfully!")
        elif action == 'deactivate':
            videos.update(is_active=False)
            messages.success(request, f"{len(video_ids)} videos deactivated successfully!")
        elif action == 'delete':
            videos.delete()
            messages.success(request, f"{len(video_ids)} videos deleted successfully!")
        
        return redirect('youtube:video_list')

class YASearchHistoryView(LoginRequiredMixin, ListView):
    model = SearchHistory
    template_name = 'tutorial/admn/search_history.html'
    context_object_name = 'searches'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Date filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(search_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(search_date__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get total counts and statistics
        context['total_searches'] = SearchHistory.objects.count()
        context['avg_results'] = SearchHistory.objects.aggregate(Avg('results_count'))['results_count__avg'] or 0
        context['unique_queries'] = SearchHistory.objects.values('query').distinct().count()
        
        # Popular searches
        popular_searches = SearchHistory.objects.values('query').annotate(
            count=Count('query')
        ).order_by('-count')[:10]
        context['popular_searches'] = popular_searches
        
        # Graph data for searches over time
        thirty_days_ago = timezone.now() - timedelta(days=30)
        days_labels = [(timezone.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, -1, -1)]
        
        searches_data = []
        for day in days_labels:
            searches_count = SearchHistory.objects.filter(search_date__date=day).count()
            searches_data.append(searches_count)
        
        context['days_labels'] = json.dumps(days_labels)
        context['searches_data'] = json.dumps(searches_data)
        
        # Get search parameters for maintaining state
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

class YACommentListView(LoginRequiredMixin, ListView):
    model = Comment
    template_name = 'tutorial/admn/comment_list.html'
    context_object_name = 'comments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Date filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['total_comments'] = Comment.objects.count()
        context['approved_comments'] = Comment.objects.filter(is_approved=True).count()
        context['pending_comments'] = Comment.objects.filter(is_approved=False).count()
        context['anonymous_comments'] = Comment.objects.filter(is_anonymous=True).count()
        
        # Average comments per video
        video_count = YoutubeVideo.objects.count()
        if video_count > 0:
            context['avg_comments_per_video'] = context['total_comments'] / video_count
        else:
            context['avg_comments_per_video'] = 0
        
        # Graph data for comments over time
        thirty_days_ago = timezone.now() - timedelta(days=30)
        days_labels = [(timezone.now() - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(30, -1, -1)]
        
        comments_data = []
        for day in days_labels:
            comments_count = Comment.objects.filter(created_at__date=day).count()
            comments_data.append(comments_count)
        
        context['days_labels'] = json.dumps(days_labels)
        context['comments_data'] = json.dumps(comments_data)
        
        # Get search parameters for maintaining state
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

class YACommentApproveView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=kwargs['pk'])
        comment.is_approved = not comment.is_approved
        comment.save()
        
        if comment.is_approved:
            messages.success(request, "Comment approved successfully!")
        else:
            messages.success(request, "Comment unapproved successfully!")
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse_lazy('youtube:comment_list')))

class YACommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'tutorial/admn/comment_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('youtube:comment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Comment deleted successfully!")
        return super().delete(request, *args, **kwargs)

class YAAddCommentView(View):
    def post(self, request, *args, **kwargs):
        video = get_object_or_404(YoutubeVideo, pk=kwargs['pk'])
        content = request.POST.get('content', '')
        is_anonymous = request.POST.get('is_anonymous', False) == 'on'
        
        if not content:
            messages.error(request, "Comment cannot be empty!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
        if request.user.is_authenticated:
            # Authenticated user
            name = None if is_anonymous else request.user.get_full_name() or request.user.username
            comment = Comment(
                video=video,
                user=None if is_anonymous else request.user,
                name=name,
                content=content,
                is_anonymous=is_anonymous
            )
        else:
            # Anonymous user
            name = request.POST.get('name', '')
            comment = Comment(
                video=video,
                user=None,
                name=name,
                content=content,
                is_anonymous=True
            )
        
        comment.save()
        messages.success(request, "Comment added successfully!")
        return HttpResponseRedirect(reverse_lazy('youtube:video_detail', kwargs={'pk': video.pk}))