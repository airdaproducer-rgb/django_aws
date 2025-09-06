from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.contrib import messages
from django.utils import timezone
from tutorial.models import YoutubeVideo, ViewerHistory, SearchHistory, SearchResult
import json
from datetime import timedelta

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
        
        # Searches data
        searches_data = []
        for day in days_labels:
            searches_count = SearchHistory.objects.filter(search_date__date=day).count()
            searches_data.append(searches_count)
        
        context['days_labels'] = json.dumps(days_labels)
        context['views_data'] = json.dumps(views_data)
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
