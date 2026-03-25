from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):

    user = models.OneToOneField(
        settings.                                                                         AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')

    phone_number = models.CharField(max_length=32, blank=True)
    totp_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f'Profile for {self.user.username}'


class SecurityQuestion(models.Model):
    question_text = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.question_text


class UserSecurityAnswer(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='security_answers',
    )
    question = models.ForeignKey(
        SecurityQuestion,
        on_delete=models.CASCADE,
        related_name='user_answers',
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='security_answers')
    question = models.ForeignKey(SecurityQuestion, on_delete=models.CASCADE, related_name='user_answers')
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
    answer_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['question_id']
        unique_together = [('user', 'question')]

#<<<<<< HEAD
    def __str__(self):
        return f'{self.user.username} -> {self.question_id}'


class RecoveryCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recovery_codes',
    )
#=======

class RecoveryCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recovery_codes')
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
    code_hash = models.CharField(max_length=128)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def mark_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class PasswordResetSession(models.Model):
    METHOD_TOTP = 'totp'
    METHOD_FALLBACK = 'fallback'
#<<<<<<< HEAD
    METHOD_CHOICES = [
        (METHOD_TOTP, 'Authenticator'),
        (METHOD_FALLBACK, 'Fallback'),
    ]
#=======
    METHOD_CHOICES = [(METHOD_TOTP, 'Authenticator'), (METHOD_FALLBACK, 'Fallback')]
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_sessions',
    )
    token = models.CharField(max_length=128, unique=True)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=15)

    def is_valid(self):
        return (not self.is_used) and self.expires_at > timezone.now()

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=['is_used'])
