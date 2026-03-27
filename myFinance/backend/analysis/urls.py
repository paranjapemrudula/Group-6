from django.urls import path

from .views import (
    ChatbotFeedbackView,
    ChatbotView,
    ClusteringAnalysisView,
    CompanySentimentView,
    DiscountAnalysisView,
    SentimentOverviewView,
    PortfolioAnalyticsView,
    PortfolioSentimentView,
    RegressionAnalysisView,
)

urlpatterns = [
    path('chatbot/', ChatbotView.as_view(), name='chatbot'),
    path('chatbot/feedback/', ChatbotFeedbackView.as_view(), name='chatbot_feedback'),
    path('sentiment/company/', CompanySentimentView.as_view(), name='company_sentiment'),
    path('sentiment/overview/', SentimentOverviewView.as_view(), name='sentiment_overview'),
    path('portfolios/<int:portfolio_id>/analytics/', PortfolioAnalyticsView.as_view(), name='portfolio_analytics'),
    path('portfolios/<int:portfolio_id>/sentiment/', PortfolioSentimentView.as_view(), name='portfolio_sentiment'),
    path('analyze/regression/', RegressionAnalysisView.as_view(), name='analyze_regression'),
    path('analyze/discount/', DiscountAnalysisView.as_view(), name='analyze_discount'),
    path('analyze/clustering/', ClusteringAnalysisView.as_view(), name='analyze_clustering'),
]
