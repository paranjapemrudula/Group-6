from django.urls import path

from .views import (
    MarketNewsView,
    MarketOverviewView,
    PortfolioStockDetailView,
    PortfolioStockListCreateView,
    SectorListView,
    StockQuoteView,
    StocksBySectorView,
    StockSuggestionView,
)

urlpatterns = [
    path('sectors/', SectorListView.as_view(), name='sector_list'),
    path('market/overview/', MarketOverviewView.as_view(), name='market_overview'),
    path('market/news/', MarketNewsView.as_view(), name='market_news'),
    path('stocks/suggest/', StockSuggestionView.as_view(), name='stock_suggest'),
    path('stocks/quote/', StockQuoteView.as_view(), name='stock_quote'),
    path('stocks/by-sector/<int:sector_id>/', StocksBySectorView.as_view(), name='stocks_by_sector'),
    path('portfolios/<int:id>/stocks/', PortfolioStockListCreateView.as_view(), name='portfolio_stock_list_create'),
    path(
        'portfolios/<int:id>/stocks/<int:stock_id>/',
        PortfolioStockDetailView.as_view(),
        name='portfolio_stock_detail',
    ),
]
