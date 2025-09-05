from django.urls import path
from . import t_admin
from . import t_user

app_name = 'youtube'

urlpatterns = [
    path('', t_admin.YADashboardView.as_view(), name='dashboard'),
    path('videos/', t_admin.YAVideoListView.as_view(), name='video_list'),
    path('videos/create/', t_admin.YAVideoCreateView.as_view(), name='video_create'),
    path('videos/<int:pk>/', t_admin.YAVideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:pk>/update/', t_admin.YAVideoUpdateView.as_view(), name='video_update'),
    path('videos/<int:pk>/delete/', t_admin.YAVideoDeleteView.as_view(), name='video_delete'),
    path('videos/bulk-action/', t_admin.YAVideoBulkActionView.as_view(), name='video_bulk_action'),
    path('search-history/', t_admin.YASearchHistoryView.as_view(), name='search_history'),
    path('comments/', t_admin.YACommentListView.as_view(), name='comment_list'),
    path('comments/<int:pk>/approve/', t_admin.YACommentApproveView.as_view(), name='comment_approve'),
    path('comments/<int:pk>/delete/', t_admin.YACommentDeleteView.as_view(), name='comment_delete'),
    path('videos/<int:pk>/comment/', t_admin.YAAddCommentView.as_view(), name='add_comment'),


    path('u/video/<int:pk>/', t_user.UserDetailView.as_view(), name='detail'),
    
    # New AJAX URLs for comments
    path('comment/add/<int:video_id>/', t_user.add_comment, name='add_comment'),
    path('comment/edit/<int:comment_id>/', t_user.edit_comment, name='edit_comment'),
    path('comment/delete/<int:comment_id>/', t_user.delete_comment, name='delete_comment'),
    path('comment/replies/<int:comment_id>/', t_user.load_replies, name='load_replies'),
    
    # AJAX URLs for responses
    path('response/add/<int:comment_id>/', t_user.add_response, name='add_response'),
    path('response/edit/<int:response_id>/', t_user.edit_response, name='edit_response'),
    path('response/delete/<int:response_id>/', t_user.delete_response, name='delete_response'),
    path('response/load/<int:comment_id>/', t_user.load_responses, name='load_responses'),
    path('response/load-nested/<int:response_id>/', t_user.load_nested_responses, name='load_nested_responses'),




]