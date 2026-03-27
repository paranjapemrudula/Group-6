from django.contrib import admin

from .models import (
    ChatInteractionLog,
    ChatKnowledgeDocument,
    ChatPromptVersion,
    PortfolioSentimentSnapshot,
)


@admin.register(PortfolioSentimentSnapshot)
class PortfolioSentimentSnapshotAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'updated_at')
    search_fields = ('portfolio__name',)


@admin.register(ChatPromptVersion)
class ChatPromptVersionAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'is_active', 'updated_at')
    list_filter = ('name', 'is_active')
    search_fields = ('name', 'description', 'instructions')


@admin.register(ChatKnowledgeDocument)
class ChatKnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'source_type', 'is_active', 'updated_at')
    list_filter = ('category', 'source_type', 'is_active')
    search_fields = ('title', 'slug', 'content')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ChatInteractionLog)
class ChatInteractionLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'route', 'category', 'model', 'confidence', 'feedback_status')
    list_filter = ('route', 'category', 'model', 'feedback_status')
    search_fields = ('question', 'answer', 'prompt_name')
    readonly_fields = ('created_at',)
