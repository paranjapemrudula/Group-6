from django.urls import path

from .views import PortfolioRecommendationView, RecommendationOverviewView

urlpatterns = [
    path('recommendations/overview/', RecommendationOverviewView.as_view(), name='recommendation_overview'),
    path('portfolios/<int:portfolio_id>/recommendations/', PortfolioRecommendationView.as_view(), name='portfolio_recommendations'),
]
