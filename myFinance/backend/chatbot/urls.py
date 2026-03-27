from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.finance_chat, name='finance_chat'),
]