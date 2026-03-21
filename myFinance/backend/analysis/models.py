from django.db import models

from portfolios.models import Portfolio


class PortfolioSentimentSnapshot(models.Model):
    portfolio = models.OneToOneField(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='sentiment_snapshot',
    )
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Sentiment Snapshot for {self.portfolio.name}'
