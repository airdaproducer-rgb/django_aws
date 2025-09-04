from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('confirm-code/', views.email_confirmation, name='email_confirmation'),  
    path('confirm-email/<int:pk>/<str:code>/', views.confirm_email_link, name='confirm_email_link'),
    path('resend-code/', views.resend_confirmation_code, name='resend_code'),








]