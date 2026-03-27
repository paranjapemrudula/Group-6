import logging

from rest_framework.response import Response
from rest_framework.views import APIView
from .chatbot import generate_chatbot_reply
from .services import (
    build_company_sentiment_payload,
    build_sentiment_overview_payload,
    build_portfolio_analytics_payload,
    build_portfolio_sentiment_payload,
    build_clustering_payload,
    build_discount_payload,
    build_regression_payload,
    resolve_timeframe,
)

logger = logging.getLogger(__name__)


class ChatbotView(APIView):
    def post(self, request):
        question = request.data.get('question', '')
        history = request.data.get('history', [])
        try:
            payload = generate_chatbot_reply(user=request.user, question=question, history=history)
            return Response(payload)
        except Exception as exc:  # pragma: no cover - protective API fallback
            logger.exception('Chatbot API failed: %s', exc)
            return Response(
                {
                    'answer': 'The chatbot hit a temporary problem, but your account data is still safe. Please try again in a moment.',
                    'model': 'api-fallback',
                    'category': 'finance',
                    'route': 'fallback',
                    'actions': [{'type': 'route', 'path': '/portfolios', 'label': 'Open Portfolios'}],
                    'quick_prompts': [],
                    'meta': {'error': str(exc)},
                },
                status=200,
            )


class PortfolioAnalyticsView(APIView):
    def get(self, request, portfolio_id):
        payload = build_portfolio_analytics_payload(portfolio_id=portfolio_id, user=request.user)
        if payload is None:
            return Response({'detail': 'Portfolio not found.'}, status=404)
        return Response(payload)


class PortfolioSentimentView(APIView):
    def get(self, request, portfolio_id):
        payload = build_portfolio_sentiment_payload(portfolio_id=portfolio_id, user=request.user)
        if payload is None:
            return Response({'detail': 'Portfolio not found.'}, status=404)
        return Response(payload)


class SentimentOverviewView(APIView):
    def get(self, request):
        payload = build_sentiment_overview_payload(user=request.user)
        return Response(payload)


class CompanySentimentView(APIView):
    def get(self, request):
        symbol = request.query_params.get('symbol', '')
        company_name = request.query_params.get('company_name', '')
        payload = build_company_sentiment_payload(symbol=symbol, company_name=company_name)
        if payload is None:
            return Response({'detail': 'Query parameter "symbol" is required.'}, status=400)
        return Response(payload)


class RegressionAnalysisView(APIView):
    def get(self, request):
        symbol = request.query_params.get('symbol')
        timeframe = request.query_params.get('timeframe', '1D').upper()
        timeframe_config = resolve_timeframe(timeframe)
        period = request.query_params.get('period', timeframe_config['period'])
        interval = request.query_params.get('interval', timeframe_config['interval'])
        if not symbol:
            return Response({'detail': 'Query parameter "symbol" is required.'}, status=400)

        payload = build_regression_payload(
            symbol=symbol,
            period=period,
            interval=interval,
            timeframe=timeframe,
        )
        if payload is None:
            return Response({'detail': 'Insufficient historical data for analysis.'}, status=404)
        return Response(payload)


class DiscountAnalysisView(APIView):
    def get(self, request):
        symbol = request.query_params.get('symbol')
        timeframe = request.query_params.get('timeframe', '1D').upper()
        timeframe_config = resolve_timeframe(timeframe)
        period = request.query_params.get('period', timeframe_config['period'])
        interval = request.query_params.get('interval', timeframe_config['interval'])
        if not symbol:
            return Response({'detail': 'Query parameter "symbol" is required.'}, status=400)

        payload = build_discount_payload(
            symbol=symbol,
            period=period,
            interval=interval,
            timeframe=timeframe,
        )
        if payload is None:
            return Response({'detail': 'Insufficient historical data for analysis.'}, status=404)
        return Response(payload)


class ClusteringAnalysisView(APIView):
    def get(self, request):
        symbol = request.query_params.get('symbol')
        timeframe = request.query_params.get('timeframe', '1D').upper()
        timeframe_config = resolve_timeframe(timeframe)
        period = request.query_params.get('period', timeframe_config['period'])
        interval = request.query_params.get('interval', timeframe_config['interval'])
        if not symbol:
            return Response({'detail': 'Query parameter "symbol" is required.'}, status=400)

        payload = build_clustering_payload(
            symbol=symbol,
            period=period,
            interval=interval,
            timeframe=timeframe,
        )
        if payload is None:
            return Response({'detail': 'Insufficient historical data for analysis.'}, status=404)
        return Response(payload)
