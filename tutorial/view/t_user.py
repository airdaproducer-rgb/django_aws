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
from tutorial.models import YoutubeVideo,CommentResponse, ViewerHistory, SearchHistory, SearchResult, Comment
from tutorial.forms import YoutubeVideoForm, CommentForm, SearchForm,CommentResponseForm
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

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.decorators import method_decorator
from django.db.models import Q
import json
import secrets

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
        
        # Add top-level comments to context (no parent)
        context['comments'] = Comment.objects.filter(video=video, is_approved=True, parent=None)
        
        # Add forms to context
        context['comment_form'] = CommentForm()
        context['response_form'] = CommentResponseForm()
        
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


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.db.models import Count
import json

@require_POST
def add_comment(request, video_id):
    video = get_object_or_404(YoutubeVideo.objects.select_related('user'), id=video_id, is_active=True)
    form = CommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.video = video
        
        parent_id = request.POST.get('parent_id')
        if parent_id:
            comment.parent = get_object_or_404(Comment.objects.select_related('video'), id=parent_id)
        
        if request.user.is_authenticated:
            comment.user = request.user
            comment.name = None if form.cleaned_data.get('is_anonymous') else request.user.username
            comment.is_anonymous = form.cleaned_data.get('is_anonymous')
        else:
            comment.name = form.cleaned_data.get('name') or "Anonymous"
            comment.ip_address = get_client_ip(request)
            comment.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if not request.user.is_authenticated and not comment.edit_token:
            comment.edit_token = secrets.token_hex(32)
        
        comment.save()
        
        comment_count = Comment.objects.filter(video=video, is_approved=True).aggregate(count=Count('id'))['count']
        
        context = {
            'comment': comment,
            'user': request.user,
            'user_tokens': request.COOKIES.get('comment_tokens', '')
        }
        
        template = 'tutorial/user/reply_item.html' if comment.parent else 'tutorial/user/comment_item.html'
        html = render_to_string(template, context, request=request)  # Ensure request context
        
        response = JsonResponse({
            'success': True,
            'comment_html': html,
            'comment_id': comment.id,
            'comment_count': comment_count,
            'edit_token': comment.edit_token
        })
        
        if not request.user.is_authenticated and comment.edit_token:
            tokens_dict = {}
            tokens = request.COOKIES.get('comment_tokens', '')
            if tokens:
                try:
                    tokens_dict = json.loads(tokens)
                except json.JSONDecodeError:
                    tokens_dict = {}
            
            tokens_dict[str(comment.id)] = comment.edit_token
            response.set_cookie('comment_tokens', json.dumps(tokens_dict), max_age=60*60*24*365)
        
        return response
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })

@require_POST
def add_response(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, is_approved=True)
    form = CommentResponseForm(request.POST)
    
    if form.is_valid():
        response = form.save(commit=False)
        response.comment = comment
        
        # Get parent response if it exists
        parent_id = request.POST.get('parent_id')
        if parent_id:
            response.parent = get_object_or_404(CommentResponse, id=parent_id)
        
        # Set user or name
        if request.user.is_authenticated:
            response.user = request.user
            if form.cleaned_data.get('is_anonymous'):
                response.is_anonymous = True
                response.name = None
            else:
                response.name = request.user.username
        else:
            response.name = form.cleaned_data.get('name') or "Anonymous"
        
        # Record IP and user agent for non-auth users
        if not request.user.is_authenticated:
            response.ip_address = get_client_ip(request)
            response.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        response.save()
        
        # Return JSON response with HTML
        context = {
            'response': response,
            'user': request.user,
            'user_tokens': request.COOKIES.get('comment_tokens', '')
        }
        
        if response.parent:
            html = render_to_string('tutorial/user/nested_response_item.html', context)
        else:
            html = render_to_string('tutorial/user/response_item.html', context)
        
        response_json = JsonResponse({
            'success': True,
            'response_html': html,
            'response_id': response.id,
            'edit_token': response.edit_token
        })
        
        # Set cookie with token for non-auth users
        if not request.user.is_authenticated and response.edit_token:
            tokens = request.COOKIES.get('comment_tokens', '')
            if tokens:
                tokens_dict = json.loads(tokens)
            else:
                tokens_dict = {}
            
            tokens_dict[f"response_{response.id}"] = response.edit_token
            response_json.set_cookie('comment_tokens', json.dumps(tokens_dict), max_age=60*60*24*365)
        
        return response_json
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })

# Updated edit_comment view
@require_http_methods(["GET", "POST"])
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user has permission to edit
    if request.user.is_authenticated:
        if comment.user != request.user:
            return HttpResponseForbidden("You don't have permission to edit this comment")
    else:
        # Check token for non-auth users
        tokens = request.COOKIES.get('comment_tokens', '')
        if not tokens:
            return HttpResponseForbidden("You don't have permission to edit this comment")
        
        tokens_dict = json.loads(tokens)
        if str(comment_id) not in tokens_dict or tokens_dict[str(comment_id)] != comment.edit_token:
            return HttpResponseForbidden("You don't have permission to edit this comment")
    
    if request.method == "GET":
        # Return form with comment data
        form_html = render_to_string('tutorial/user/edit_comment_form.html', {
            'comment': comment,
            'form': CommentForm(instance=comment)
        }, request=request)  # Added request=request to enable CSRF token rendering
        
        return JsonResponse({
            'success': True,
            'form_html': form_html
        })
    else:
        # Process form submission
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            comment = form.save()
            
            # Return updated comment HTML
            context = {
                'comment': comment,
                'user': request.user,
                'user_tokens': request.COOKIES.get('comment_tokens', '')
            }
            
            if comment.parent:
                html = render_to_string('tutorial/user/reply_item.html', context, request=request)  # Added request=request for consistency
            else:
                html = render_to_string('tutorial/user/comment_item.html', context, request=request)  # Added request=request for consistency
            
            return JsonResponse({
                'success': True,
                'comment_html': html,
                'comment_id': comment.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })


@require_http_methods(["GET", "POST"])
def edit_response(request, response_id):
    response = get_object_or_404(CommentResponse, id=response_id)
    
    # Check if user has permission to edit
    if request.user.is_authenticated:
        if response.user != request.user:
            return HttpResponseForbidden("You don't have permission to edit this response")
    else:
        # Check token for non-auth users
        tokens = request.COOKIES.get('comment_tokens', '')
        if not tokens:
            return HttpResponseForbidden("You don't have permission to edit this response")
        
        tokens_dict = json.loads(tokens)
        if f"response_{response_id}" not in tokens_dict or tokens_dict[f"response_{response_id}"] != response.edit_token:
            return HttpResponseForbidden("You don't have permission to edit this response")
    
    if request.method == "GET":
        # Return form with response data
        form_html = render_to_string('tutorial/user/edit_response_form.html', {
            'response': response,
            'form': CommentResponseForm(instance=response)
        }, request=request)  # Added request=request to enable CSRF token rendering
        
        return JsonResponse({
            'success': True,
            'form_html': form_html
        })
    else:
        # Process form submission
        form = CommentResponseForm(request.POST, instance=response)
        if form.is_valid():
            response = form.save()
            
            # Return updated response HTML
            context = {
                'response': response,
                'user': request.user,
                'user_tokens': request.COOKIES.get('comment_tokens', '')
            }
            
            if response.parent:
                html = render_to_string('tutorial/user/nested_response_item.html', context, request=request)  # Added request=request for consistency
            else:
                html = render_to_string('tutorial/user/response_item.html', context, request=request)  # Added request=request for consistency
            
            return JsonResponse({
                'success': True,
                'response_html': html,
                'response_id': response.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })


@require_http_methods(["GET", "POST"])
def edit_response(request, response_id):
    response = get_object_or_404(CommentResponse, id=response_id)
    
    # Check if user has permission to edit
    if request.user.is_authenticated:
        if response.user != request.user:
            return HttpResponseForbidden("You don't have permission to edit this response")
    else:
        # Check token for non-auth users
        tokens = request.COOKIES.get('comment_tokens', '')
        if not tokens:
            return HttpResponseForbidden("You don't have permission to edit this response")
        
        tokens_dict = json.loads(tokens)
        if f"response_{response_id}" not in tokens_dict or tokens_dict[f"response_{response_id}"] != response.edit_token:
            return HttpResponseForbidden("You don't have permission to edit this response")
    
    if request.method == "GET":
        # Return form with response data
        form_html = render_to_string('tutorial/user/edit_response_form.html', {
            'response': response,
            'form': CommentResponseForm(instance=response)
        })
        return JsonResponse({
            'success': True,
            'form_html': form_html
        })
    else:
        # Process form submission
        form = CommentResponseForm(request.POST, instance=response)
        if form.is_valid():
            response = form.save()
            
            # Return updated response HTML
            context = {
                'response': response,
                'user': request.user,
                'user_tokens': request.COOKIES.get('comment_tokens', '')
            }
            
            if response.parent:
                html = render_to_string('tutorial/user/nested_response_item.html', context)
            else:
                html = render_to_string('tutorial/user/response_item.html', context)
            
            return JsonResponse({
                'success': True,
                'response_html': html,
                'response_id': response.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user has permission to delete
    if request.user.is_authenticated:
        if comment.user != request.user:
            return HttpResponseForbidden("You don't have permission to delete this comment")
    else:
        # Check token for non-auth users
        tokens = request.COOKIES.get('comment_tokens', '')
        if not tokens:
            return HttpResponseForbidden("You don't have permission to delete this comment")
        
        tokens_dict = json.loads(tokens)
        if str(comment_id) not in tokens_dict or tokens_dict[str(comment_id)] != comment.edit_token:
            return HttpResponseForbidden("You don't have permission to delete this comment")
    
    video = comment.video
    comment.delete()
    
    return JsonResponse({
        'success': True,
        'comment_count': Comment.objects.filter(video=video, is_approved=True).count()
    })

@require_POST
def delete_response(request, response_id):
    response = get_object_or_404(CommentResponse, id=response_id)
    
    # Check if user has permission to delete
    if request.user.is_authenticated:
        if response.user != request.user:
            return HttpResponseForbidden("You don't have permission to delete this response")
    else:
        # Check token for non-auth users
        tokens = request.COOKIES.get('comment_tokens', '')
        if not tokens:
            return HttpResponseForbidden("You don't have permission to delete this response")
        
        tokens_dict = json.loads(tokens)
        if f"response_{response_id}" not in tokens_dict or tokens_dict[f"response_{response_id}"] != response.edit_token:
            return HttpResponseForbidden("You don't have permission to delete this response")
    
    response.delete()
    
    return JsonResponse({
        'success': True
    })

@require_POST
def load_replies(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, is_approved=True)
    replies = Comment.objects.filter(parent=comment, is_approved=True)
    
    replies_html = ''
    for reply in replies:
        context = {
            'comment': reply,
            'user': request.user,
            'user_tokens': request.COOKIES.get('comment_tokens', '')
        }
        replies_html += render_to_string('tutorial/user/reply_item.html', context)
    
    return JsonResponse({
        'success': True,
        'replies_html': replies_html,
        'replies_count': replies.count()
    })

@require_POST
def load_responses(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, is_approved=True)
    responses = CommentResponse.objects.filter(comment=comment, parent=None, is_approved=True)
    
    responses_html = ''
    for response in responses:
        context = {
            'response': response,
            'user': request.user,
            'user_tokens': request.COOKIES.get('comment_tokens', '')
        }
        responses_html += render_to_string('tutorial/user/response_item.html', context)
    
    return JsonResponse({
        'success': True,
        'responses_html': responses_html,
        'responses_count': responses.count()
    })

@require_POST
def load_nested_responses(request, response_id):
    parent_response = get_object_or_404(CommentResponse, id=response_id, is_approved=True)
    responses = CommentResponse.objects.filter(parent=parent_response, is_approved=True)
    
    responses_html = ''
    for response in responses:
        context = {
            'response': response,
            'user': request.user,
            'user_tokens': request.COOKIES.get('comment_tokens', '')
        }
        responses_html += render_to_string('tutorial/user/nested_response_item.html', context)
    
    return JsonResponse({
        'success': True,
        'responses_html': responses_html,
        'responses_count': responses.count()
    })