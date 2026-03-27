from collections import Counter, defaultdict
from statistics import mean

import numpy as np
from django.utils import timezone

from analysis.services import build_portfolio_sentiment_payload, fetch_historical_data
from portfolios.models import Portfolio
from stocks.models import PortfolioStock
from stocks.services import get_stock_snapshot, get_stocks_by_sector

from .models import RecommendationSnapshot, UserPreference


def _clamp(value, lower=0.0, upper=100.0):
    return round(max(lower, min(upper, float(value))), 2)


def _label_for_score(score):
    if score >= 72:
        return 'Buy'
    if score >= 56:
        return 'Hold'
    if score >= 42:
        return 'Watch'
    return 'Sell'


def _position_metrics(holding, quote):
    buy_price = float(holding.buy_price)
    quantity = int(holding.quantity or 0)
    current_price = quote.get('current_price') or quote.get('last_value')
    current_price = float(current_price) if current_price is not None else None
    invested_amount = round(buy_price * quantity, 2)
    current_value = round(current_price * quantity, 2) if current_price is not None else None
    profit_loss = round(current_value - invested_amount, 2) if current_value is not None else None
    return_percent = round(((current_price - buy_price) / buy_price) * 100, 2) if current_price is not None and buy_price else None
    return {
        'buy_price': buy_price,
        'quantity': quantity,
        'invested_amount': invested_amount,
        'current_price': current_price,
        'current_value': current_value,
        'profit_loss': profit_loss,
        'return_percent': return_percent,
    }


def _history_metrics(symbol):
    history = fetch_historical_data(symbol=symbol, period='1y', interval='1d')
    if history.empty or 'Close' not in history:
        return {
            'forecast_direction': 'flat',
            'forecast_score': 50.0,
            'annualized_return': None,
            'annualized_volatility': None,
            'max_drawdown': None,
        }

    close_series = history['Close'].dropna()
    if len(close_series) < 10:
        return {
            'forecast_direction': 'flat',
            'forecast_score': 50.0,
            'annualized_return': None,
            'annualized_volatility': None,
            'max_drawdown': None,
        }

    returns = close_series.pct_change().dropna()
    annualized_return = ((1 + float(returns.mean())) ** 252 - 1) * 100 if not returns.empty else None
    annualized_volatility = float(returns.std()) * np.sqrt(252) * 100 if not returns.empty else None

    x = np.arange(len(close_series))
    slope = float(np.polyfit(x, close_series.to_numpy(dtype=float), 1)[0]) if len(close_series) >= 2 else 0.0
    last_price = float(close_series.iloc[-1])
    normalized_slope = (slope / last_price) * 100 if last_price else 0.0
    if normalized_slope > 0.02:
        forecast_direction = 'up'
        forecast_score = _clamp(58 + (normalized_slope * 100))
    elif normalized_slope < -0.02:
        forecast_direction = 'down'
        forecast_score = _clamp(42 + (normalized_slope * 100))
    else:
        forecast_direction = 'flat'
        forecast_score = 50.0

    running_peak = close_series.cummax()
    drawdown = ((close_series - running_peak) / running_peak).min()
    max_drawdown = round(abs(float(drawdown)) * 100, 2) if drawdown is not None else None

    return {
        'forecast_direction': forecast_direction,
        'forecast_score': round(float(forecast_score), 2),
        'annualized_return': round(float(annualized_return), 2) if annualized_return is not None else None,
        'annualized_volatility': round(float(annualized_volatility), 2) if annualized_volatility is not None else None,
        'max_drawdown': max_drawdown,
    }


def _profitability_score(return_percent, profit_loss):
    if return_percent is None:
        return 50.0
    base = 50 + (float(return_percent) * 1.2)
    if profit_loss is not None and profit_loss > 0:
        base += 6
    elif profit_loss is not None and profit_loss < 0:
        base -= 6
    return _clamp(base)


def _sentiment_score(sentiment_percent):
    return _clamp(sentiment_percent or 50)


def _risk_score(volatility, drawdown):
    if volatility is None and drawdown is None:
        return 50.0
    base = 82.0
    if volatility is not None:
        base -= min(42.0, float(volatility) * 1.1)
    if drawdown is not None:
        base -= min(28.0, float(drawdown) * 0.9)
    return _clamp(base)


def _diversification_score(sector_weight, sector_count):
    if sector_weight is None:
        return 50.0
    base = 74.0
    if sector_weight >= 45:
        base -= 30
    elif sector_weight >= 35:
        base -= 15
    elif sector_weight <= 20:
        base += 8
    if sector_count >= 5:
        base += 8
    elif sector_count <= 2:
        base -= 10
    return _clamp(base)


def _weighted_decision_score(*, profitability_score, forecast_score, sentiment_score, risk_score, diversification_score, preferred_sector, avoided_sector):
    score = (
        profitability_score * 0.28
        + forecast_score * 0.20
        + sentiment_score * 0.20
        + risk_score * 0.17
        + diversification_score * 0.15
    )
    if preferred_sector:
        score += 4
    if avoided_sector:
        score -= 8
    return _clamp(score)


def _explain_recommendation(row):
    reasons = []
    if row['return_percent'] is not None:
        if row['return_percent'] > 0:
            reasons.append(f"return is positive at {row['return_percent']}%")
        elif row['return_percent'] < 0:
            reasons.append(f"return is negative at {row['return_percent']}%")
    if row['forecast_direction'] == 'up':
        reasons.append('forecast trend is pointing upward')
    elif row['forecast_direction'] == 'down':
        reasons.append('forecast trend is pointing downward')
    else:
        reasons.append('forecast trend is mostly flat')
    if row['sentiment_percent'] >= 60:
        reasons.append('recent sentiment is positive')
    elif row['sentiment_percent'] <= 40:
        reasons.append('recent sentiment is weak')
    else:
        reasons.append('recent sentiment is mixed')
    if row['annualized_volatility'] is not None and row['annualized_volatility'] >= 35:
        reasons.append('volatility is high')
    elif row['annualized_volatility'] is not None:
        reasons.append('risk is relatively controlled')
    if row['sector_weight'] >= 45:
        reasons.append('this sector is over-concentrated in your portfolio')
    elif row['sector_weight'] <= 20:
        reasons.append('this sector is underweighted in your portfolio')
    return reasons


def _portfolio_improvement_suggestions(rows, sector_breakdown):
    suggestions = []
    overweight = [item for item in sector_breakdown if item['weight_percent'] >= 40]
    if overweight:
        sector = overweight[0]
        suggestions.append(
            {
                'type': 'rebalance',
                'title': f"Reduce concentration in {sector['sector']}",
                'detail': f"{sector['sector']} is {sector['weight_percent']}% of your portfolio, which is concentration risk.",
            }
        )

    weak_rows = [row for row in rows if row['decision_label'] in {'Sell', 'Watch'}]
    if weak_rows:
        weakest = weak_rows[0]
        suggestions.append(
            {
                'type': 'review',
                'title': f"Review {weakest['symbol']}",
                'detail': f"{weakest['symbol']} has weak combined signals from profitability, forecast, sentiment, and risk.",
            }
        )

    underweight = [item for item in sector_breakdown if item['weight_percent'] <= 20]
    if underweight:
        sector = underweight[0]
        suggestions.append(
            {
                'type': 'diversify',
                'title': f"Add exposure to {sector['sector']}",
                'detail': f"{sector['sector']} is only {sector['weight_percent']}% of your portfolio, so adding there may improve diversification.",
            }
        )
    return suggestions[:3]


def _risk_alerts(rows, sector_breakdown):
    alerts = []
    for row in rows:
        if row['annualized_volatility'] is not None and row['annualized_volatility'] >= 40:
            alerts.append(
                {
                    'level': 'high',
                    'symbol': row['symbol'],
                    'title': f"High volatility alert for {row['symbol']}",
                    'detail': f"Annualized volatility is {row['annualized_volatility']}%, which increases downside risk.",
                }
            )
        if row['max_drawdown'] is not None and row['max_drawdown'] >= 25:
            alerts.append(
                {
                    'level': 'high',
                    'symbol': row['symbol'],
                    'title': f"Drawdown alert for {row['symbol']}",
                    'detail': f"Maximum drawdown is {row['max_drawdown']}%, showing a deeper historical pullback.",
                }
            )
    if sector_breakdown and sector_breakdown[0]['weight_percent'] >= 45:
        sector = sector_breakdown[0]
        alerts.append(
            {
                'level': 'medium',
                'symbol': '',
                'title': f"Sector concentration alert: {sector['sector']}",
                'detail': f"{sector['sector']} makes up {sector['weight_percent']}% of portfolio value.",
            }
        )
    return alerts[:5]


def _build_opportunities(*, current_symbols, sector_breakdown, preference):
    underweight_sectors = [item['sector'] for item in sector_breakdown if item['weight_percent'] <= 20]
    candidate_sectors = underweight_sectors[:]
    for sector in preference.preferred_sectors or []:
        if sector not in candidate_sectors:
            candidate_sectors.append(sector)

    opportunities = []
    seen = set(current_symbols)
    for sector in candidate_sectors[:4]:
        sector_rows = get_stocks_by_sector(sector_name=sector)[:10]
        for item in sector_rows:
            if item['symbol'] in seen:
                continue
            current_price = item.get('current_price')
            if current_price is None:
                continue
            discount_ratio = float(item.get('discount_ratio') or 0)
            pe_ratio = item.get('pe_ratio')
            pe_value = float(pe_ratio) if pe_ratio is not None else None
            score = 52.0
            if discount_ratio > 0:
                score += min(12.0, discount_ratio)
            if pe_value is not None and pe_value <= 22:
                score += 10.0
            if sector in (preference.preferred_sectors or []):
                score += 4.0
            if sector in (preference.avoid_sectors or []):
                score -= 12.0
            opportunities.append(
                {
                    'symbol': item['symbol'],
                    'company_name': item['company_name'],
                    'sector': sector,
                    'opportunity_score': _clamp(score),
                    'current_price': current_price,
                    'discount_ratio': round(discount_ratio, 2),
                    'pe_ratio': round(pe_value, 2) if pe_value is not None else None,
                    'reason': 'Underweight sector with supportive valuation signals.',
                }
            )
            seen.add(item['symbol'])
            if len(opportunities) >= 3:
                return opportunities
    return opportunities


def _empty_payload(portfolio, preference):
    return {
        'portfolio_id': portfolio.id,
        'portfolio_name': portfolio.name,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'recommendation_count': 0,
            'top_action': 'Watch',
            'risk_level': preference.risk_level,
            'investment_horizon': preference.investment_horizon,
            'portfolio_score': 50,
            'opportunity_count': 0,
            'risk_alert_count': 0,
        },
        'recommendations': [],
        'portfolio_improvements': [],
        'opportunities': [],
        'risk_alerts': [],
    }


def build_portfolio_recommendations(*, portfolio_id, user):
    portfolio = Portfolio.objects.filter(id=portfolio_id, user=user).first()
    if portfolio is None:
        return None

    preference, _ = UserPreference.objects.get_or_create(user=user)
    holdings = list(PortfolioStock.objects.filter(portfolio=portfolio).select_related('sector').order_by('-added_at'))
    if not holdings:
        payload = _empty_payload(portfolio, preference)
        RecommendationSnapshot.objects.update_or_create(
            portfolio=portfolio,
            defaults={'user': user, 'payload': payload},
        )
        return payload

    sentiment_payload = build_portfolio_sentiment_payload(portfolio_id=portfolio_id, user=user) or {}
    sentiment_by_symbol = {item['symbol']: item for item in sentiment_payload.get('stocks', [])}
    sector_counts = Counter(holding.sector.name for holding in holdings)
    current_values = defaultdict(float)
    current_symbols = []
    precomputed_rows = []

    for holding in holdings:
        quote = get_stock_snapshot(holding.symbol)
        current_symbols.append(holding.symbol)
        position = _position_metrics(holding, quote)
        current_values[holding.sector.name] += position['current_value'] or position['invested_amount']
        precomputed_rows.append((holding, quote, position))

    total_value = sum(current_values.values()) or 0.0
    sector_breakdown = []
    for sector_name, value in sorted(current_values.items(), key=lambda item: item[1], reverse=True):
        weight_percent = round((value / total_value) * 100, 2) if total_value else 0.0
        sector_breakdown.append(
            {
                'sector': sector_name,
                'value': round(value, 2),
                'weight_percent': weight_percent,
                'holding_count': sector_counts[sector_name],
            }
        )

    recommendation_rows = []
    for holding, quote, position in precomputed_rows:
        sentiment_row = sentiment_by_symbol.get(holding.symbol, {})
        sentiment_percent = float(sentiment_row.get('avg_sentiment', 50))
        history_metrics = _history_metrics(holding.symbol)
        sector_name = holding.sector.name
        sector_weight = next((item['weight_percent'] for item in sector_breakdown if item['sector'] == sector_name), 0.0)
        profitability_score = _profitability_score(position['return_percent'], position['profit_loss'])
        forecast_score = history_metrics['forecast_score']
        sentiment_score = _sentiment_score(sentiment_percent)
        risk_score = _risk_score(history_metrics['annualized_volatility'], history_metrics['max_drawdown'])
        diversification_score = _diversification_score(sector_weight, len(sector_breakdown))
        preferred_sector = sector_name in (preference.preferred_sectors or [])
        avoided_sector = sector_name in (preference.avoid_sectors or [])
        decision_score = _weighted_decision_score(
            profitability_score=profitability_score,
            forecast_score=forecast_score,
            sentiment_score=sentiment_score,
            risk_score=risk_score,
            diversification_score=diversification_score,
            preferred_sector=preferred_sector,
            avoided_sector=avoided_sector,
        )
        label = _label_for_score(decision_score)

        row = {
            'stock_id': holding.id,
            'symbol': holding.symbol,
            'company_name': holding.company_name,
            'sector': sector_name,
            'decision_score': decision_score,
            'score': decision_score,
            'decision_label': label,
            'label': label,
            'buy_price': position['buy_price'],
            'current_price': position['current_price'],
            'quantity': position['quantity'],
            'invested_amount': position['invested_amount'],
            'current_value': position['current_value'],
            'profit_loss': position['profit_loss'],
            'return_percent': position['return_percent'],
            'profitability_score': profitability_score,
            'forecast_direction': history_metrics['forecast_direction'],
            'forecast_score': forecast_score,
            'annualized_return': history_metrics['annualized_return'],
            'sentiment_percent': sentiment_percent,
            'sentiment_score': sentiment_score,
            'risk_score': risk_score,
            'annualized_volatility': history_metrics['annualized_volatility'],
            'max_drawdown': history_metrics['max_drawdown'],
            'diversification_score': diversification_score,
            'sector_weight': sector_weight,
            'price_direction': quote.get('price_direction', 'flat'),
            'price_direction_emoji': quote.get('price_direction_emoji', '->'),
            'discount_ratio': quote.get('discount_ratio'),
            'pe_ratio': quote.get('pe_ratio'),
        }
        row['reasons'] = _explain_recommendation(row)
        recommendation_rows.append(row)

    recommendation_rows.sort(key=lambda row: row['decision_score'], reverse=True)
    top_action = recommendation_rows[0]['decision_label'] if recommendation_rows else 'Watch'
    improvements = _portfolio_improvement_suggestions(recommendation_rows, sector_breakdown)
    opportunities = _build_opportunities(current_symbols=set(current_symbols), sector_breakdown=sector_breakdown, preference=preference)
    risk_alerts = _risk_alerts(recommendation_rows, sector_breakdown)
    portfolio_score = round(mean([row['decision_score'] for row in recommendation_rows]), 2) if recommendation_rows else 50.0

    payload = {
        'portfolio_id': portfolio.id,
        'portfolio_name': portfolio.name,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'recommendation_count': len(recommendation_rows),
            'top_action': top_action,
            'risk_level': preference.risk_level,
            'investment_horizon': preference.investment_horizon,
            'portfolio_score': portfolio_score,
            'opportunity_count': len(opportunities),
            'risk_alert_count': len(risk_alerts),
        },
        'recommendations': recommendation_rows,
        'portfolio_improvements': improvements,
        'opportunities': opportunities,
        'risk_alerts': risk_alerts,
        'sector_breakdown': sector_breakdown,
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
                    'portfolio_score': summary.get('portfolio_score', 50),
                    'opportunity_count': summary.get('opportunity_count', 0),
                    'risk_alert_count': summary.get('risk_alert_count', 0),
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
