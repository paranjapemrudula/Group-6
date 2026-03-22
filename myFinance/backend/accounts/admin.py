from django.contrib import admin

from .models import PasswordResetSession, RecoveryCode, SecurityQuestion, UserProfile, UserSecurityAnswer


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'totp_enabled', 'updated_at')
    search_fields = ('user__username', 'phone_number')


@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('question_text',)


@admin.register(UserSecurityAnswer)
class UserSecurityAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'updated_at')
    search_fields = ('user__username', 'question__question_text')


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_used', 'created_at', 'used_at')
    list_filter = ('is_used',)
    search_fields = ('user__username',)


@admin.register(PasswordResetSession)
class PasswordResetSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'method', 'is_used', 'expires_at', 'created_at')
    list_filter = ('method', 'is_used')
    search_fields = ('user__username', 'token')
