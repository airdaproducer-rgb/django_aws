from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Max, Count, Avg, Sum
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils.timezone import now
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.views import View
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.paginator import Paginator
from django.utils import timezone
from urllib.parse import urlparse
import json
from datetime import datetime, timedelta

from .forms import CustomUserCreationForm, EmailVerificationForm
from .models import EmailVerification, VerificationAttempt, CustomUser
from .utils import create_verification_code, send_verification_email, send_welcome_email
from . import utils

User = get_user_model()



def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Create user but don't save yet
            user = form.save(commit=False)
            
            # Save user
            user.save()
            
            # Create verification code
            verification = create_verification_code(user)
            if verification:
                # Send verification email
                send_verification_email(user, verification.code)
                
                # Store user ID in session
                request.session['verification_user_id'] = user.id
                
                return redirect(reverse('accounts:verify_email'))
            else:
                messages.error(request, "Failed to create verification code. Please try again later.")
                user.delete()  # Remove user if we can't create verification
                return redirect(reverse('accounts:register'))
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/accounts/register.html', {'form': form})

def verify_email(request):
    user_id = request.session.get('verification_user_id')
    
    if not user_id:
        messages.error(request, "Verification session expired. Please register again.")
        return redirect(reverse('accounts:register'))
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found. Please register again.")
        return redirect(reverse('accounts:register'))
    
    if user.is_email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect(reverse('accounts:login'))
    
    # Check verification attempts
    today = now().date()
    attempt, created = VerificationAttempt.objects.get_or_create(
        user=user,
        date=today
    )
    
    if attempt.max_reached:
        return render(request, 'users/accounts/max_attempts.html')
    
    if request.method == 'POST':
        form = EmailVerificationForm(user=user, data=request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            
            # Find and mark verification as used
            verification = EmailVerification.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).latest('created_at')
            
            verification.is_used = True
            verification.save()
            
            # Mark user as verified
            user.is_email_verified = True
            user.save()
            
            # Send welcome email
            send_welcome_email(user)
            
            # Log the user in
            login(request, user)
            
            # Clear session
            if 'verification_user_id' in request.session:
                del request.session['verification_user_id']
                
            messages.success(request, "Email verified successfully. Welcome to MMB Tutorials!")
            return redirect(reverse('software:app_user_list'))
        
    else:
        form = EmailVerificationForm(user=user)
    
    return render(request, 'users/accounts/verify_email.html', {
        'form': form, 
        'attempts_left': 5 - attempt.count
    })

def resend_verification(request):
    user_id = request.session.get('verification_user_id')
    
    if not user_id:
        messages.error(request, "Verification session expired. Please register again.")
        return redirect(reverse('accounts:register'))
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found. Please register again.")
        return redirect(reverse('accounts:register'))
    
    # Create new verification code
    verification = create_verification_code(user)
    
    if verification:
        # Send verification email
        send_verification_email(user, verification.code)
        messages.success(request, "A new verification code has been sent to your email.")
    else:
        messages.error(request, "You've reached the maximum number of verification attempts for today. Please try again tomorrow.")
    
    return redirect(reverse('accounts:verify_email'))


class LoginView(View):
    template_name = 'users/accounts/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, self.template_name)
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # Redirect to next URL if provided and safe
            next_url = request.GET.get('next', 'youtube:dashboard')
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
                return redirect(next_url)
            return redirect('youtube:dashboard')
        else:
            messages.error(request, 'Invalid email or password')
            return render(request, self.template_name)
        

class LogoutView(View):
    template_name = 'users/accounts/logout.html'

    def get(self, request):
        logout(request)
        messages.info(request, 'You have been successfully logged out')
        return render(request, self.template_name)
    

def user_profile(request):
    if request.user.is_authenticated:
        user = request.user
        context = {
            'current_user': user,
            'email_verified': user.is_email_verified,
            'is_authenticated': True,
        }
    else:
        context = {
            'current_user': None,
            'email_verified': False,
            'is_authenticated': False,
        }
    return render(request, 'users/accounts/profile.html', context)

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        new_username = request.POST.get('username')
        new_email = request.POST.get('email')
        
        email_changed = new_email != user.email
        
        user.username = new_username
        
        if email_changed:
            verification = create_verification_code(user)
            if verification:
                request.session['pending_email'] = new_email
                send_verification_email(user, verification.code)
                return redirect('accounts:email_confirmation')
            else:
                messages.error(request, 'Maximum verification attempts reached today. Try tomorrow.')
                return redirect('accounts:profile')
        else:
            user.save()
            messages.success(request, 'Profile updated!')
            return redirect('accounts:profile')
    
    return render(request, 'users/accounts/update_profile.html', {'current_user': request.user})

@login_required
def email_confirmation(request):
    if request.method == 'POST':
        code = request.POST.get('confirmation_code')
        user = request.user
        
        try:
            verification = EmailVerification.objects.get(
                user=user,
                code=code,
                is_used=False,
                expires_at__gte=now()
            )
            
            if 'pending_email' in request.session:
                user.email = request.session['pending_email']
                user.is_email_verified = True
                user.save()
                del request.session['pending_email']
                
                verification.is_used = True
                verification.save()
                
                send_welcome_email(user)
                messages.success(request, 'Email confirmed and updated successfully!')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'No pending email change found.')
                return redirect('accounts:profile')
                
        except EmailVerification.DoesNotExist:
            messages.error(request, 'Invalid confirmation code. Please try again.')
            return redirect('accounts:email_confirmation')
    
    return render(request, 'users/accounts/email_confirmation.html', {
        'current_user': request.user,
        'email': request.session.get('pending_email', '')
    })

@login_required
def confirm_email_link(request, pk, code):
    try:
        verification = EmailVerification.objects.get(
            user_id=pk,
            code=code,
            is_used=False,
            expires_at__gte=now()
        )
        user = verification.user
        
        if 'pending_email' in request.session:
            user.email = request.session['pending_email']
            user.is_email_verified = True
            user.save()
            del request.session['pending_email']
            
            verification.is_used = True
            verification.save()
            
            send_welcome_email(user)
            messages.success(request, 'Email confirmed via link successfully!')
        else:
            messages.error(request, 'No pending email change found.')
            
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid or expired confirmation link.')
    
    return redirect('accounts:profile')

@login_required
def resend_confirmation_code(request):
    user = request.user
    if 'pending_email' not in request.session:
        messages.error(request, 'No pending email change to verify.')
        return redirect('accounts:profile')
    
    # Check attempts
    today = now().date()
    attempt, created = VerificationAttempt.objects.get_or_create(
        user=user,
        date=today
    )
    
    if attempt.max_reached:
        messages.error(request, 'Maximum confirmation attempts reached for today. Try again tomorrow.')
        return redirect('accounts:profile')
    
    # Create new code
    verification = create_verification_code(user)
    if verification:
        send_verification_email(user, verification.code)
        messages.success(request, 'New confirmation code sent successfully!')
    else:
        messages.error(request, 'Failed to send new confirmation code.')
    
    return redirect('accounts:email_confirmation')


def terms_of_use(request):
    return render(request, 'users/compliance/terms_of_use.html')

def privacy_policy(request):
    return render(request, 'users/compliance/privacy_policy.html')


def help_center(request):
    return render(request, 'users/compliance/help_center.html')


def about(request):
    return render(request, 'users/compliance/about.html')

def donate_view(request):
    share_url = 'https://MMB Tutorials.com'
    
    context = {
        'object_or_url': share_url,
    }
    return render(request, 'users/compliance/donate.html', context)


def custom_400(request, exception):
    context = {
        'error_message': str(exception)
    }
    return render(request, "users/errors/400.html", context, status=400)

def custom_403(request, exception):
    context = {
        'error_message': str(exception)
    }
    return render(request, "users/errors/403.html", context, status=403)

def custom_404(request, exception):
    context = {
        'error_message': str(exception)
    }
    return render(request, "users/errors/404.html", context, status=404)

def custom_500(request):
    context = {
        'error_message': "Internal Server Error"
    }
    return render(request, "users/errors/500.html", context, status=500)