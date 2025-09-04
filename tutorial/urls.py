from django.urls import path,include
from .views import StoryListView, StoryCreateView
from .views import PDFDocumentListView, PDFDocumentCreateView, PDFDocumentDetailView
from . import views


urlpatterns = [
    path('t/', include('tutorial.view.urls')),
    path('', StoryListView.as_view(), name='story-list'),
    path('create/', StoryCreateView.as_view(), name='story-create'),



    path('d/', PDFDocumentListView.as_view(), name='document-list'),
    path('d/create/', PDFDocumentCreateView.as_view(), name='document-create'),
    path('document/<uuid:pk>/', PDFDocumentDetailView.as_view(), name='document-detail'),
    path('api/document-status/<uuid:document_id>/', views.document_status, name='document-status'),








]