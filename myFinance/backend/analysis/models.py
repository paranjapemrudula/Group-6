from django.conf import settings
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


class ChatPromptVersion(models.Model):
    name = models.CharField(max_length=80)
    version = models.PositiveIntegerField()
    description = models.CharField(max_length=255, blank=True)
    instructions = models.TextField()
    routing_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', '-version']
        unique_together = ('name', 'version')

    def __str__(self):
        return f'{self.name} v{self.version}'


class ChatKnowledgeDocument(models.Model):
    SOURCE_CHOICES = [
        ('system', 'System'),
        ('faq', 'FAQ'),
        ('market', 'Market'),
        ('portfolio', 'Portfolio'),
        ('guide', 'Guide'),
    ]

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    category = models.CharField(max_length=40, default='guide')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='guide')
    content = models.TextField()
    keywords = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class ChatInteractionLog(models.Model):
    FEEDBACK_UNRATED = 'unrated'
    FEEDBACK_POSITIVE = 'positive'
    FEEDBACK_NEGATIVE = 'negative'
    FEEDBACK_CHOICES = [
        (FEEDBACK_UNRATED, 'Unrated'),
        (FEEDBACK_POSITIVE, 'Positive'),
        (FEEDBACK_NEGATIVE, 'Negative'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_interactions',
    )
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=40, default='finance')
    route = models.CharField(max_length=40, default='general')
    model = models.CharField(max_length=80, default='local-rag')
    prompt_name = models.CharField(max_length=80, blank=True)
    prompt_version = models.PositiveIntegerField(default=1)
    retrieval_count = models.PositiveIntegerField(default=0)
    confidence = models.FloatField(default=0.0)
    used_documents = models.JSONField(default=list, blank=True)
    feedback_status = models.CharField(max_length=12, choices=FEEDBACK_CHOICES, default=FEEDBACK_UNRATED)
    feedback_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.route} [{self.created_at:%Y-%m-%d %H:%M}]'
