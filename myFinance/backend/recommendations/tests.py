from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from portfolios.models import Portfolio
from stocks.models import PortfolioStock, Sector

User = get_user_model()


class RecommendationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='reco-user', password='StrongPass123')
        self.client.force_authenticate(user=self.user)
        self.sector, _ = Sector.objects.get_or_create(name='Technology')
        self.portfolio = Portfolio.objects.create(user=self.user, name='Growth Basket')
        PortfolioStock.objects.create(
            portfolio=self.portfolio,
            symbol='INFY.NS',
            company_name='Infosys',
            sector=self.sector,
            buy_price='1500.00',
            quantity=5,
        )

    @patch('recommendations.services.build_portfolio_sentiment_payload')
    @patch('recommendations.services.get_stock_snapshot')
    def test_portfolio_recommendations_returns_ranked_rows(self, mock_get_stock_snapshot, mock_sentiment):
        mock_sentiment.return_value = {
            'stocks': [
                {'symbol': 'INFY.NS', 'avg_sentiment': 68, 'sentiment_label': 'Positive'},
            ]
        }
        mock_get_stock_snapshot.return_value = {
            'price_direction': 'up',
            'price_direction_emoji': '↑',
            'discount_ratio': 4.0,
            'pe_ratio': 21.0,
            'current_price': 1580.0,
        }

        response = self.client.get(f'/api/portfolios/{self.portfolio.id}/recommendations/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['portfolio_name'], 'Growth Basket')
        self.assertEqual(len(response.data['recommendations']), 1)
        self.assertEqual(response.data['recommendations'][0]['symbol'], 'INFY.NS')
        self.assertIn(response.data['recommendations'][0]['label'], {'Buy', 'Hold', 'Watch', 'Reduce'})

    def test_recommendation_overview_returns_portfolios(self):
        response = self.client.get('/api/recommendations/overview/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['portfolio_count'], 1)
        self.assertEqual(len(response.data['items']), 1)
