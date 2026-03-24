from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    MeView,
    PasswordResetConfirmView,
    PasswordResetFallbackView,
    PasswordResetStartView,
    PasswordResetTotpView,
    SecurityQuestionListView,
    SignupView,
    TotpSetupView,
    TotpVerifyView,
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('security-questions/', SecurityQuestionListView.as_view(), name='security_questions'),
    path('totp/setup/', TotpSetupView.as_view(), name='totp_setup'),
    path('totp/verify/', TotpVerifyView.as_view(), name='totp_verify'),
    path('password-reset/start/', PasswordResetStartView.as_view(), name='password_reset_start'),
    path('password-reset/totp/', PasswordResetTotpView.as_view(), name='password_reset_totp'),
    path('password-reset/fallback/', PasswordResetFallbackView.as_view(), name='password_reset_fallback'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
