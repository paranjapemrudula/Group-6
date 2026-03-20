from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from portfolios.models import Portfolio

from .models import PortfolioStock, Sector
from .serializers import PortfolioStockSerializer, SectorSerializer
from .services import (
    get_market_news,
    get_market_overview,
    get_stock_snapshot,
    get_stock_suggestions,
    get_stocks_by_sector,
)


class SectorListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


class StockSuggestionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        return Response(get_stock_suggestions(query=query))


class StockQuoteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get('symbol')
        if not symbol:
            return Response({'detail': 'Query parameter "symbol" is required.'}, status=400)
        return Response(get_stock_snapshot(symbol=symbol))


class StocksBySectorView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sector_id):
        sector = get_object_or_404(Sector, id=sector_id)
        return Response(get_stocks_by_sector(sector_name=sector.name))


class MarketOverviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_market_overview())


class MarketNewsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_market_news())


class PortfolioStockListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioStockSerializer

    def _get_portfolio(self):
        return get_object_or_404(
            Portfolio,
            id=self.kwargs['id'],
            user=self.request.user,
        )

    def get_queryset(self):
        portfolio = self._get_portfolio()
        return PortfolioStock.objects.filter(portfolio=portfolio)

    def perform_create(self, serializer):
        portfolio = self._get_portfolio()
        serializer.save(portfolio=portfolio)


class PortfolioStockDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PortfolioStockSerializer
    lookup_url_kwarg = 'stock_id'

    def get_queryset(self):
        return PortfolioStock.objects.filter(
            portfolio__id=self.kwargs['id'],
            portfolio__user=self.request.user,
        )
