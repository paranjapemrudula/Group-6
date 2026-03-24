from django.conf import settings
from django.db import models

from portfolios.models import Portfolio


class UserPreference(models.Model):
    RISK_CHOICES = [
        ('conservative', 'Conservative'),
        ('balanced', 'Balanced'),
        ('aggressive', 'Aggressive'),
    ]
    HORIZON_CHOICES = [
        ('short', 'Short Term'),
        ('medium', 'Medium Term'),
        ('long', 'Long Term'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendation_preference')
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default='balanced')
    investment_horizon = models.CharField(max_length=20, choices=HORIZON_CHOICES, default='medium')
    preferred_sectors = models.JSONField(default=list, blank=True)
    avoid_sectors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']


class RecommendationSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendation_snapshots')
    portfolio = models.OneToOneField(Portfolio, on_delete=models.CASCADE, related_name='recommendation_snapshot')
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
