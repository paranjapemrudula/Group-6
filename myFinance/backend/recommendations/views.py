from rest_framework.response import Response
from rest_framework.views import APIView

from .services import build_portfolio_recommendations, build_recommendation_overview


class RecommendationOverviewView(APIView):
    def get(self, request):
        return Response(build_recommendation_overview(user=request.user))


class PortfolioRecommendationView(APIView):
    def get(self, request, portfolio_id):
        payload = build_portfolio_recommendations(portfolio_id=portfolio_id, user=request.user)
        if payload is None:
            return Response({'detail': 'Portfolio not found.'}, status=404)
        return Response(payload)
