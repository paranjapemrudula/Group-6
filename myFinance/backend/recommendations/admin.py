from django.contrib import admin

from .models import RecommendationSnapshot, UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'risk_level', 'investment_horizon', 'updated_at')
    search_fields = ('user__username',)


@admin.register(RecommendationSnapshot)
class RecommendationSnapshotAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'user', 'updated_at')
    search_fields = ('portfolio__name', 'user__username')
