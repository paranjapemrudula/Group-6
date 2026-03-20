from django.urls import path

from .views import PortfolioDetailView, PortfolioListCreateView

urlpatterns = [
    path('portfolios/', PortfolioListCreateView.as_view(), name='portfolio_list_create'),
    path('portfolios/<int:id>/', PortfolioDetailView.as_view(), name='portfolio_detail'),
]
