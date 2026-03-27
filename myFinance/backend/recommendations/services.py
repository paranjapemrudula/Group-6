from collections import Counter

from django.utils import timezone

from analysis.services import build_portfolio_sentiment_payload
from portfolios.models import Portfolio
from stocks.models import PortfolioStock
from stocks.services import get_stock_snapshot

from .models import RecommendationSnapshot, UserPreference


def _label_for_score(score):
    if score >= 70:
        return 'Buy'
    if score >= 55:
        return 'Hold'
    if score >= 40:
        return 'Watch'
    return 'Reduce'


def _explain_recommendation(*, sentiment_percent, price_direction, discount_ratio, sector_pressure, preferred_sector, avoided_sector):
    reasons = []
    if sentiment_percent >= 60:
        reasons.append('recent sentiment is supportive')
    elif sentiment_percent <= 40:
        reasons.append('recent sentiment is weak')
    else:
        reasons.append('sentiment is mixed')

    if price_direction == 'up':
        reasons.append('price direction is trending up')
    elif price_direction == 'down':
        reasons.append('price direction is trending down')
    else:
        reasons.append('price direction is stable')

    if discount_ratio is not None:
        if discount_ratio > 0:
            reasons.append('current price is trading below the short-term average')
        elif discount_ratio < 0:
            reasons.append('current price is trading above the short-term average')

    if sector_pressure == 'underweight':
        reasons.append('this sector is underweight in your portfolio')
    elif sector_pressure == 'overweight':
        reasons.append('this sector already has heavy exposure in your portfolio')

    if preferred_sector:
        reasons.append('this sector matches your stated preference')
    if avoided_sector:
        reasons.append('this sector is on your avoid list')

    return reasons


def build_portfolio_recommendations(*, portfolio_id, user):
    portfolio = Portfolio.objects.filter(id=portfolio_id, user=user).first()
    if portfolio is None:
        return None

    preference, _ = UserPreference.objects.get_or_create(user=user)
    holdings = list(PortfolioStock.objects.filter(portfolio=portfolio).select_related('sector').order_by('-added_at'))
    if not holdings:
        payload = {
            'portfolio_id': portfolio.id,
            'portfolio_name': portfolio.name,
            'generated_at': timezone.now().isoformat(),
            'summary': {
                'recommendation_count': 0,
                'top_action': 'Watch',
                'risk_level': preference.risk_level,
                'investment_horizon': preference.investment_horizon,
            },
            'recommendations': [],
        }
        RecommendationSnapshot.objects.update_or_create(
            portfolio=portfolio,
            defaults={'user': user, 'payload': payload},
        )
        return payload

    sentiment_payload = build_portfolio_sentiment_payload(portfolio_id=portfolio_id, user=user) or {}
    sentiment_by_symbol = {item['symbol']: item for item in sentiment_payload.get('stocks', [])}
    sector_counts = Counter(holding.sector.name for holding in holdings)
    total_holdings = len(holdings)

    recommendation_rows = []
    for holding in holdings:
        quote = get_stock_snapshot(holding.symbol)
        sentiment_row = sentiment_by_symbol.get(holding.symbol, {})
        sentiment_percent = float(sentiment_row.get('avg_sentiment', 50))
        price_direction = quote.get('price_direction', 'flat')
        discount_ratio = quote.get('discount_ratio')
        pe_ratio = quote.get('pe_ratio')
        sector_name = holding.sector.name

        score = 50.0
        score += (sentiment_percent - 50) * 0.5
        if price_direction == 'up':
            score += 10
        elif price_direction == 'down':
            score -= 10

        if discount_ratio is not None:
            score += max(-8, min(8, float(discount_ratio)))

        if pe_ratio is not None:
            pe_value = float(pe_ratio)
            if pe_value <= 18:
                score += 8
            elif pe_value >= 30:
                score -= 8

        sector_share = sector_counts[sector_name] / max(total_holdings, 1)
        sector_pressure = 'balanced'
        if sector_share >= 0.45:
            score -= 8
            sector_pressure = 'overweight'
        elif sector_share <= 0.2:
            score += 5
            sector_pressure = 'underweight'

        preferred_sector = sector_name in (preference.preferred_sectors or [])
        avoided_sector = sector_name in (preference.avoid_sectors or [])
        if preferred_sector:
            score += 6
        if avoided_sector:
            score -= 12

        score = round(max(0, min(100, score)), 2)
        label = _label_for_score(score)
        recommendation_rows.append(
            {
                'stock_id': holding.id,
                'symbol': holding.symbol,
                'company_name': holding.company_name,
                'sector': sector_name,
                'score': score,
                'label': label,
                'sentiment_percent': sentiment_percent,
                'price_direction': price_direction,
                'price_direction_emoji': quote.get('price_direction_emoji', '->'),
                'discount_ratio': discount_ratio,
                'pe_ratio': pe_ratio,
                'current_price': quote.get('current_price'),
                'reasons': _explain_recommendation(
                    sentiment_percent=sentiment_percent,
                    price_direction=price_direction,
                    discount_ratio=discount_ratio,
                    sector_pressure=sector_pressure,
                    preferred_sector=preferred_sector,
                    avoided_sector=avoided_sector,
                ),
            }
        )

    recommendation_rows.sort(key=lambda row: row['score'], reverse=True)
    top_action = recommendation_rows[0]['label'] if recommendation_rows else 'Watch'

    payload = {
        'portfolio_id': portfolio.id,
        'portfolio_name': portfolio.name,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'recommendation_count': len(recommendation_rows),
            'top_action': top_action,
            'risk_level': preference.risk_level,
            'investment_horizon': preference.investment_horizon,
        },
        'recommendations': recommendation_rows,
    }
    RecommendationSnapshot.objects.update_or_create(
        portfolio=portfolio,
        defaults={'user': user, 'payload': payload},
    )
    return payload


def build_recommendation_overview(*, user):
    portfolios = Portfolio.objects.filter(user=user).order_by('-created_at')
    items = []
    for portfolio in portfolios:
        snapshot = getattr(portfolio, 'recommendation_snapshot', None)
        payload = snapshot.payload if snapshot and snapshot.payload else {}
        summary = payload.get('summary', {})
        items.append(
            {
                'portfolio_id': portfolio.id,
                'portfolio_name': portfolio.name,
                'generated_at': payload.get('generated_at'),
                'has_snapshot': bool(payload),
                'summary': {
                    'recommendation_count': summary.get('recommendation_count', 0),
                    'top_action': summary.get('top_action', 'Watch'),
                    'risk_level': summary.get('risk_level', 'balanced'),
                    'investment_horizon': summary.get('investment_horizon', 'medium'),
                },
            }
        )

    preference, _ = UserPreference.objects.get_or_create(user=user)
    return {
        'portfolio_count': len(items),
        'preference': {
            'risk_level': preference.risk_level,
            'investment_horizon': preference.investment_horizon,
            'preferred_sectors': preference.preferred_sectors,
            'avoid_sectors': preference.avoid_sectors,
        },
        'items': items,
    }
