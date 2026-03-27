from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from portfolios.models import Portfolio

from .models import PortfolioStock, Sector, StockUniverse
from .serializers import PortfolioStockSerializer, SectorSerializer, StockUniverseSerializer
import yfinance as yf
from .services import (
    get_market_news,
    get_market_overview,
    get_stock_snapshot,
    get_stock_suggestions,
    get_stocks_by_sector,
)


class SectorListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SectorSerializer

    def get_queryset(self):
        market = (self.request.query_params.get('market') or '').strip().upper()
        queryset = Sector.objects.all()
        if market and market != 'ALL':
            queryset = queryset.filter(universe_stocks__market=market)
        return queryset.annotate(
            universe_stock_count=Count(
                'universe_stocks',
                filter=Q(universe_stocks__is_active=True) & (Q(universe_stocks__market=market) if market and market != 'ALL' else Q()),
                distinct=True,
            )
        ).order_by('name')


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
        market = (request.query_params.get('market') or '').strip().upper()
        universe_queryset = StockUniverse.objects.filter(sector=sector, is_active=True).select_related('sector')
        if market and market != 'ALL':
            universe_queryset = universe_queryset.filter(market=market)
        universe_queryset = universe_queryset.order_by('company_name')

        if universe_queryset.exists():
            payload = {
                'sector': SectorSerializer(
                    Sector.objects.filter(id=sector.id).annotate(
                        universe_stock_count=Count('universe_stocks', distinct=True)
                    ).first()
                ).data,
                'stocks': StockUniverseSerializer(universe_queryset, many=True).data,
            }
            return Response(payload)

        return Response(
            {
                'sector': {'id': sector.id, 'name': sector.name, 'universe_stock_count': 0},
                'stocks': get_stocks_by_sector(sector_name=sector.name, market=market or None),
            }
        )


class QualitySectorsView(APIView):
    """
    Returns the top 10 sectors by average stock price (using yfinance last close).
    Labels each sector as Good Quality (>= median avg price) or Bad Quality.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        market = (request.query_params.get('market') or '').strip().upper()
        sectors = Sector.objects.all()
        if market:
            sectors = sectors.filter(universe_stocks__market=market)
        sectors = sectors.annotate(
            universe_stock_count=Count(
                'universe_stocks',
                filter=Q(universe_stocks__is_active=True) & (Q(universe_stocks__market=market) if market else Q()),
                distinct=True,
            )
        ).order_by('-universe_stock_count')

        payload = []
        for sector in sectors[:20]:
            stock_qs = (
                StockUniverse.objects.filter(sector=sector, is_active=True)
                .order_by('company_name')
                .values('symbol', 'company_name', 'market')[:3]
            )
            closes = []
            stock_rows = []
            for stock in stock_qs:
                symbol = stock['symbol']
                normalized = symbol
                # yfinance requires the exchange suffix for Indian tickers
                if (market or stock['market']) == StockUniverse.MARKET_INDIA and '.' not in normalized:
                    normalized = f'{symbol}.NS'
                min_price = max_price = close_price = 0.0
                try:
                    ticker = yf.Ticker(normalized)
                    history = ticker.history(period='1mo', interval='1d')
                    if not history.empty:
                        closes_series = history['Close'].dropna()
                        if not closes_series.empty:
                            min_price = float(closes_series.min())
                            max_price = float(closes_series.max())
                            close_price = float(closes_series.iloc[-1])
                            closes.append(close_price)
                except Exception:
                    pass
                stock_rows.append(
                    {
                        'symbol': symbol,
                        'company_name': stock['company_name'],
                        'market': stock['market'],
                        'min_price': round(min_price, 2) if min_price else 0.0,
                        'max_price': round(max_price, 2) if max_price else 0.0,
                        'close_price': round(close_price, 2) if close_price else 0.0,
                        # placeholder, set after we have sector-level thresholds
                        'cluster': 'No Data',
                    }
                )

            avg_price = sum(closes) / len(closes) if closes else 0.0
            payload.append(
                {
                    'id': sector.id,
                    'name': sector.name,
                    'universe_stock_count': sector.universe_stock_count or 0,
                    'avg_price': round(avg_price, 2),
                    'stocks': stock_rows,
                }
            )

        # rank by avg_price desc and take top 10
        ranked = sorted(payload, key=lambda s: s['avg_price'], reverse=True)[:10]
        non_zero = [item for item in ranked if item['avg_price'] > 0]
        if non_zero:
            median_index = len(non_zero) // 2
            threshold = sorted(non_zero, key=lambda s: s['avg_price'])[median_index]['avg_price']
        else:
            threshold = 0

        for item in ranked:
            if item['avg_price'] == 0:
                item['cluster'] = 'No Data'
            else:
                item['cluster'] = 'Good Quality' if item['avg_price'] >= threshold else 'Bad Quality'

            # cluster each stock within the sector relative to median close price
            closes = [row['close_price'] for row in item.get('stocks', []) if row['close_price'] > 0]
            if closes:
                median_idx = len(closes) // 2
                stock_threshold = sorted(closes)[median_idx]
            else:
                stock_threshold = 0
            for row in item.get('stocks', []):
                if row['close_price'] == 0:
                    row['cluster'] = 'No Data'
                else:
                    row['cluster'] = 'Good Quality' if row['close_price'] >= stock_threshold else 'Bad Quality'

        return Response(ranked)


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
