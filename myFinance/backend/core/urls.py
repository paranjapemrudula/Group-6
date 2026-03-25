from django.urls import path
from .views import healthcheck

urlpatterns = [
    path('', healthcheck, name='healthcheck'),  # now /api/ will work
    path('health/', healthcheck, name='healthcheck_health'),  # optional /api/health/
]