import random
from ipware import get_client_ip
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import os
from django.db.models import Max
from .models import EmailVerification, VerificationAttempt

def generate_verification_code():
    return ''.join(random.choices('0123456789', k=6))

def create_verification_code(user):
    # Check if we can create a new verification code today
    today = now().date()
    attempt, created = VerificationAttempt.objects.get_or_create(
        user=user,
        date=today
    )
    
    if attempt.max_reached:
        return None
    
    # Increment attempt count
    attempt.count += 1
    attempt.save()
    
    # Create new verification code
    code = generate_verification_code()
    expires_at = now() + timedelta(minutes=5)
    
    verification = EmailVerification.objects.create(
        user=user,
        code=code,
        expires_at=expires_at
    )
    
    return verification

def send_verification_email(user, verification_code):
    subject = 'Verify your email - AirNationMusic'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email
    
    context = {
        'user': user,
        'code': verification_code,
        'site_name': 'AirNationMusic'
    }
    
    html_content = render_to_string('users/accounts/email_verification.html', context)
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send()

def send_welcome_email(user):
    subject = 'Welcome to AirNationMusic!'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email
    
    context = {
        'user': user,
        'site_name': 'AirNationMusic'
    }
    
    html_content = render_to_string('users/accounts/welcome_email.html', context)
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send()