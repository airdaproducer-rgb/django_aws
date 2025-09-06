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


    path('u/video/<int:pk>/', t_user.UserDetailView.as_view(), name='detail'),
    
    

]