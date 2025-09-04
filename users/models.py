from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from datetime import timedelta
from django.utils.timezone import now


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[\w\s]+$')]
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.expires_at:
            self.expires_at = now() + timedelta(minutes=5)

    def is_valid(self):
        return not self.is_used and now() <= self.expires_at


class VerificationAttempt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    @property
    def max_reached(self):
        return self.count >= 5