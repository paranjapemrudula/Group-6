from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .chatbot import generate_chatbot_reply
from .models import ChatInteractionLog
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


class ChatbotView(APIView):
    def post(self, request):
        question = request.data.get('question', '')
        history = request.data.get('history', [])
        payload = generate_chatbot_reply(user=request.user, question=question, history=history)
        return Response(payload)


class ChatbotFeedbackView(APIView):
    def post(self, request):
        interaction_id = request.data.get('interaction_id')
        feedback_status = (request.data.get('feedback_status') or '').strip().lower()
        feedback_note = request.data.get('feedback_note', '')

        if feedback_status not in {
            ChatInteractionLog.FEEDBACK_POSITIVE,
            ChatInteractionLog.FEEDBACK_NEGATIVE,
            ChatInteractionLog.FEEDBACK_UNRATED,
        }:
            return Response({'detail': 'feedback_status must be positive, negative, or unrated.'}, status=status.HTTP_400_BAD_REQUEST)

        interaction = ChatInteractionLog.objects.filter(id=interaction_id).first()
        if interaction is None:
            return Response({'detail': 'Chat interaction not found.'}, status=status.HTTP_404_NOT_FOUND)
        if interaction.user_id is not None and interaction.user_id != request.user.id:
            return Response({'detail': 'You cannot rate another user interaction.'}, status=status.HTTP_403_FORBIDDEN)

        interaction.feedback_status = feedback_status
        interaction.feedback_note = str(feedback_note or '').strip()
        interaction.save(update_fields=['feedback_status', 'feedback_note'])
        return Response(
            {
                'id': interaction.id,
                'feedback_status': interaction.feedback_status,
                'feedback_note': interaction.feedback_note,
            }
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
