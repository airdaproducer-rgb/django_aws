"""
URL configuration for a project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.views import terms_of_use,donate_view,privacy_policy,help_center,about
from django.contrib.auth import views as auth_views
from tutorial.view.t_user import UserListView
from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from tutorial.sitemaps import YoutubeVideoSitemap

sitemaps_dict = {
    "videos": YoutubeVideoSitemap,
}


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', UserListView.as_view(), name='home' ),
    path('accounts/', include('users.urls')),
    path('t/', include('tutorial.urls')),
    path('tos/', terms_of_use, name='terms_of_use'),
    path('donate/', donate_view, name='donate'),
    path('privacy_policy/', privacy_policy, name='privacy_policy'),
    path('help_center/', help_center, name='help_center'),
    path('about/', about, name='about'),
    
    path('ckeditor5/', include('django_ckeditor_5.urls')),

    # Password reset URLs
    path('password-reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset/password-reset.html',
            email_template_name='users/password_reset/password_reset_email.html',
            subject_template_name='users/password_reset/password_reset_subject.txt'
        ), 
        name='password-reset'),
    
    path('password-reset/done/', 
        auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset/password-reset-done.html'
        ), 
        name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset/password-reset-confirm.html'
        ), 
        name='password_reset_confirm'),
    
    path('password-reset-complete/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='users/password_reset/password-reset-complete.html'
        ), 
        name='password_reset_complete'),

    path("sitemap.xml", sitemap, {"sitemaps": sitemaps_dict}, name="django.contrib.sitemaps.views.sitemap"),


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = "users.views.custom_404"
handler500 = "users.views.custom_500"
handler403 = "users.views.custom_403"
handler400 = "users.views.custom_400" 