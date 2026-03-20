from django.urls import path

from .views import (
    ChatbotView,
    ClusteringAnalysisView,
    DiscountAnalysisView,
    PortfolioAnalyticsView,
    RegressionAnalysisView,
)

urlpatterns = [
    path('chatbot/', ChatbotView.as_view(), name='chatbot'),
    path('portfolios/<int:portfolio_id>/analytics/', PortfolioAnalyticsView.as_view(), name='portfolio_analytics'),
    path('analyze/regression/', RegressionAnalysisView.as_view(), name='analyze_regression'),
    path('analyze/discount/', DiscountAnalysisView.as_view(), name='analyze_discount'),
    path('analyze/clustering/', ClusteringAnalysisView.as_view(), name='analyze_clustering'),
]
