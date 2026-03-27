import math
import json
import re
from difflib import SequenceMatcher
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - optional until dependency is installed
    END = None
    StateGraph = None

from portfolios.models import Portfolio
from recommendations.models import RecommendationSnapshot
from recommendations.services import build_portfolio_recommendations
from stocks.models import PortfolioStock
from stocks.services import get_market_news, get_market_overview, get_stock_snapshot, get_stock_suggestions, get_stocks_by_sector

from .models import ChatInteractionLog, ChatKnowledgeDocument, ChatPromptVersion
from .services import build_portfolio_sentiment_payload, fetch_historical_data


TOP_QUESTION_PROMPTS = [
    {'label': 'Highest returns', 'prompt': 'Which stocks or assets are generating the highest returns in my portfolio?'},
    {'label': 'Underperformers', 'prompt': 'Which investments are consistently underperforming or causing losses?'},
    {'label': 'Diversification', 'prompt': 'Is my portfolio well diversified across sectors and asset types?'},
    {'label': 'Risk level', 'prompt': 'What is the risk level of my portfolio based on volatility and drawdown?'},
    {'label': 'Sentiment', 'prompt': 'What is the current market sentiment for my invested stocks?'},
    {'label': 'Top 3 options', 'prompt': 'What are the top 3 better investment options based on my current portfolio?'},
    {'label': 'Hold buy sell', 'prompt': 'Should I hold, buy more, or sell my current investments based on market conditions?'},
    {'label': '1 year value', 'prompt': 'What would be my portfolio value after 1 year if current trends continue?'},
    {'label': 'Loss probability', 'prompt': 'What is the probability of loss in my portfolio?'},
    {'label': 'Best sector now', 'prompt': 'Which sector should I invest in right now?'},
]

FINANCE_KEYWORDS = {
    'stock', 'stocks', 'market', 'markets', 'portfolio', 'portfolios', 'invest', 'investment', 'trading',
    'finance', 'financial', 'price', 'prices', 'news', 'analysis', 'trend', 'volatility', 'risk', 'asset',
    'equity', 'diversification', 'sector', 'holding', 'holdings', 'sentiment', 'return', 'drawdown',
    'loss', 'losses', 'buy', 'sell', 'hold', 'probability',
}

SENSITIVE_PATTERNS = [
    'password', 'secret', 'token', 'refresh token', 'access token', 'api key', 'private key',
    'session cookie', 'jwt', 'database password', 'db.sqlite3', '.env', 'secret_key', 'server path',
    'filesystem', 'local path', 'admin credentials',
]

SYMBOL_PATTERN = re.compile(r'\b[A-Z]{2,10}(?:-[A-Z]{2,5}|=[A-Z])?\b')
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-\._]+")


@dataclass
class ScopeDecision:
    allowed: bool
    reason: str
    category: str


@dataclass
class RetrievalDocument:
    id: int
    title: str
    slug: str
    category: str
    source_type: str
    content: str
    score: float


def _settings_value(name: str, default: Any):
    return getattr(settings, name, default)


RECOMMENDATION_ROUTES = {
    'market_sentiment',
    'better_options',
    'hold_buy_sell',
    'best_sector_now',
    'portfolio_improvements',
    'risk_alerts',
}

MARKET_NEWS_ROUTES = {'market_news'}
MARKET_LIVE_ROUTES = {'market_news', 'market_trend'}


def _sanitize_text(value: Any, limit: int = 700):
    text = str(value or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:limit]


def sanitize_history(history: Any, limit: int | None = None):
    history_limit = limit or int(_settings_value('CHATBOT_HISTORY_LIMIT', 6))
    if not isinstance(history, list):
        return []
    cleaned = []
    for item in history[-history_limit:]:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        if role not in {'user', 'assistant'}:
            continue
        text = _sanitize_text(item.get('text'))
        if text:
            cleaned.append({'role': role, 'text': text})
    return cleaned


def _contains_sensitive_request(question: str):
    text = (question or '').strip().lower()
    return any(pattern in text for pattern in SENSITIVE_PATTERNS)


def _looks_finance_related(question: str):
    text = (question or '').strip().lower()
    if not text:
        return False
    return any(keyword in text for keyword in FINANCE_KEYWORDS) or bool(SYMBOL_PATTERN.search(question or ''))


def _guardrail_decision(question: str):
    if not question.strip():
        return ScopeDecision(False, 'Please enter a question so I can help.', 'empty')
    if _contains_sensitive_request(question):
        return ScopeDecision(False, 'I can help with market research and portfolio analysis, but I cannot expose passwords, tokens, internal paths, or private system data.', 'sensitive')
    if not _looks_finance_related(question):
        return ScopeDecision(False, 'I can help with portfolio returns, diversification, risk, market sentiment, and investment-related questions inside this app.', 'out_of_scope')
    return ScopeDecision(True, 'allowed', 'finance')


def _extract_symbols(question: str):
    symbols = list(dict.fromkeys(SYMBOL_PATTERN.findall(question or '')))
    suggestions = get_stock_suggestions(query=question or '', limit=4)
    symbols.extend([item['symbol'] for item in suggestions if item.get('symbol')])
    cleaned = []
    for symbol in symbols:
        if symbol not in cleaned:
            cleaned.append(symbol)
    return cleaned[:4]


def _tokenize(text: str):
    raw_tokens = TOKEN_PATTERN.findall((text or '').lower())
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'for', 'to', 'of', 'in', 'on',
        'my', 'me', 'with', 'what', 'how', 'can', 'you', 'about', 'right', 'now', 'please', 'tell',
        'show', 'explain', 'would', 'should', 'based', 'current', 'your',
    }
    return [token for token in raw_tokens if len(token) > 2 and token not in stop_words]


def _has_phrase(text: str, phrases: set[str]):
    return any(phrase in text for phrase in phrases)


def _has_similar_token(text: str, candidates: set[str], threshold: float = 0.76):
    tokens = _tokenize(text)
    for token in tokens:
        for candidate in candidates:
            if candidate in token or token in candidate:
                return True
            if SequenceMatcher(None, token, candidate).ratio() >= threshold:
                return True
    return False


def _active_prompt():
    prompt = ChatPromptVersion.objects.filter(name='finance_chatbot', is_active=True).order_by('-version').first()
    if prompt:
        return prompt
    return {
        'name': 'finance_chatbot',
        'version': 3,
        'instructions': (
            'You are a finance analysis assistant for a portfolio web application. '
            'Your job is to answer user investment questions using actual portfolio data, live market data, sentiment analysis, and forecasting outputs. '
            'Do not guess financial values. Always use portfolio records and live market data before answering. '
            'For profit and loss questions, calculate invested amount, current value, profit or loss, and return percentage. '
            'For best and worst investment questions, rank holdings by return percentage and total gain or loss. '
            'For diversification questions, analyze sector allocation and concentration risk. '
            'For sentiment questions, use recent financial news sentiment scores and summarize whether sentiment is positive, negative, or neutral. '
            'For forecasting questions, clearly state that predictions are probabilistic, not guaranteed. '
            'For recommendation questions, combine profitability, sentiment, forecast, and risk signals before suggesting hold, buy, sell, or rebalance. '
            'Always explain the reason behind the answer in simple language. If data is missing, state what data is unavailable instead of inventing an answer. '
            'Keep responses clear, investment-focused, and based on evidence.'
        ),
        'routing_config': {},
    }


def _build_portfolio_inventory(user):
    portfolios = list(Portfolio.objects.filter(user=user).order_by('-created_at'))
    holdings = list(
        PortfolioStock.objects.filter(portfolio__user=user).select_related('portfolio', 'sector').order_by('-added_at')
    )
    return portfolios, holdings


def _safe_float(value: Any):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_cached_market_news(limit: int = 4):
    cache_key = f'chatbot:market_news:{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    payload = get_market_news(limit=limit)
    cache.set(cache_key, payload, timeout=int(_settings_value('ANALYSIS_CACHE_TTL_SECONDS', 900)))
    return payload


def _get_cached_market_overview():
    cache_key = 'chatbot:market_overview'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    payload = get_market_overview()
    cache.set(cache_key, payload, timeout=int(_settings_value('ANALYSIS_CACHE_TTL_SECONDS', 900)))
    return payload


def _get_recommendation_report(*, user, portfolio_id: int | None):
    if not portfolio_id:
        return {}
    ttl_seconds = int(_settings_value('CHATBOT_RECOMMENDATION_CACHE_TTL_SECONDS', 300))
    snapshot = RecommendationSnapshot.objects.filter(user=user, portfolio_id=portfolio_id).first()
    if snapshot and snapshot.payload:
        age_seconds = max(0.0, (timezone.now() - snapshot.updated_at).total_seconds())
        if age_seconds <= ttl_seconds:
            return snapshot.payload
    return build_portfolio_recommendations(portfolio_id=portfolio_id, user=user) or {}


def _holding_market_row(holding):
    quote = get_stock_snapshot(holding.symbol)
    current_price = _safe_float(quote.get('current_price') or quote.get('last_value'))
    buy_price = _safe_float(holding.buy_price)
    quantity = int(holding.quantity or 0)
    invested_value = round((buy_price or 0) * quantity, 2)
    current_value = round((current_price or 0) * quantity, 2) if current_price is not None else None
    pnl = round(current_value - invested_value, 2) if current_value is not None else None
    return_percent = round(((current_price - buy_price) / buy_price) * 100, 2) if current_price is not None and buy_price else None
    return {
        'holding_id': holding.id,
        'portfolio_name': holding.portfolio.name,
        'symbol': holding.symbol,
        'company_name': holding.company_name,
        'sector': holding.sector.name,
        'quantity': quantity,
        'buy_price': buy_price,
        'current_price': current_price,
        'invested_value': invested_value,
        'current_value': current_value,
        'pnl': pnl,
        'return_percent': return_percent,
        'price_direction': quote.get('price_direction', 'flat'),
        'price_direction_emoji': quote.get('price_direction_emoji', '->'),
        'pe_ratio': _safe_float(quote.get('pe_ratio')),
        'discount_ratio': _safe_float(quote.get('discount_ratio')),
    }


def _max_drawdown(close_prices: list[float]):
    if not close_prices:
        return None
    peak = close_prices[0]
    worst = 0.0
    for price in close_prices:
        peak = max(peak, price)
        if peak > 0:
            worst = min(worst, (price - peak) / peak)
    return round(abs(worst) * 100, 2)


def _weighted_average(rows: list[dict[str, Any]], key: str):
    weighted_sum = 0.0
    weight_sum = 0.0
    for row in rows:
        value = row.get(key)
        weight = row.get('current_value') or row.get('invested_value') or 0
        if value is None or weight <= 0:
            continue
        weighted_sum += float(value) * float(weight)
        weight_sum += float(weight)
    if weight_sum == 0:
        return None
    return round(weighted_sum / weight_sum, 2)


def _portfolio_analytics_context(user):
    portfolios, holdings = _build_portfolio_inventory(user)
    holding_rows = [_holding_market_row(holding) for holding in holdings]
    total_invested = round(sum(item['invested_value'] or 0 for item in holding_rows), 2)
    total_current = round(sum(item['current_value'] or 0 for item in holding_rows if item['current_value'] is not None), 2)
    total_pnl = round(total_current - total_invested, 2) if holding_rows else 0.0
    total_return = round((total_pnl / total_invested) * 100, 2) if total_invested else None
    sector_value = defaultdict(float)
    sector_count = Counter()
    volatility_rows = []

    for row in holding_rows:
        sector_value[row['sector']] += row['current_value'] or row['invested_value'] or 0
        sector_count[row['sector']] += 1
        history = fetch_historical_data(symbol=row['symbol'], period='1y', interval='1d')
        if history.empty or 'Close' not in history:
            continue
        close_list = [float(value) for value in history['Close'].dropna().tolist() if value is not None]
        if len(close_list) < 10:
            continue
        daily_returns = history['Close'].pct_change().dropna()
        if daily_returns.empty:
            continue
        returns_list = [float(value) for value in daily_returns.tolist()]
        annualized_return = ((1 + float(daily_returns.mean())) ** 252 - 1) * 100
        annualized_volatility = float(daily_returns.std()) * math.sqrt(252) * 100
        drawdown = _max_drawdown(close_list)
        probability_of_loss = float(sum(1 for value in returns_list if value < 0) / len(returns_list) * 100)
        row.update({
            'annualized_return': round(annualized_return, 2),
            'annualized_volatility': round(annualized_volatility, 2),
            'max_drawdown': drawdown,
            'probability_of_loss': round(probability_of_loss, 2),
        })
        volatility_rows.append(row)

    sector_breakdown = []
    total_portfolio_value = sum(sector_value.values()) or 0
    for sector, value in sorted(sector_value.items(), key=lambda item: item[1], reverse=True):
        weight = round((value / total_portfolio_value) * 100, 2) if total_portfolio_value else 0
        sector_breakdown.append({'sector': sector, 'value': round(value, 2), 'weight_percent': weight, 'count': sector_count[sector]})

    diversification_score = len(sector_breakdown)
    if diversification_score >= 5:
        diversification_label = 'well diversified by sector'
    elif diversification_score >= 3:
        diversification_label = 'moderately diversified'
    elif diversification_score >= 2:
        diversification_label = 'somewhat concentrated'
    else:
        diversification_label = 'highly concentrated'

    weighted_volatility = _weighted_average(volatility_rows, 'annualized_volatility')
    weighted_drawdown = _weighted_average(volatility_rows, 'max_drawdown')
    weighted_probability_of_loss = _weighted_average(volatility_rows, 'probability_of_loss')

    risk_label = 'Moderate'
    if weighted_volatility is not None and weighted_drawdown is not None:
        if weighted_volatility >= 35 or weighted_drawdown >= 25:
            risk_label = 'High'
        elif weighted_volatility <= 18 and weighted_drawdown <= 12:
            risk_label = 'Low'

    return {
        'generated_at': timezone.now().isoformat(),
        'primary_portfolio_id': portfolios[0].id if portfolios else None,
        'portfolio_count': len(portfolios),
        'portfolio_names': [item.name for item in portfolios],
        'holding_count': len(holding_rows),
        'holdings': holding_rows,
        'total_invested': total_invested,
        'total_current': total_current,
        'total_pnl': total_pnl,
        'total_return_percent': total_return,
        'sector_breakdown': sector_breakdown,
        'diversification_label': diversification_label,
        'risk_label': risk_label,
        'weighted_volatility': weighted_volatility,
        'weighted_drawdown': weighted_drawdown,
        'weighted_probability_of_loss': weighted_probability_of_loss,
    }


def _determine_route(question: str, symbols: list[str]):
    text = (question or '').lower()
    if _has_phrase(text, {'risk alert', 'risk alerts', 'portfolio alert', 'alerts'}) or (
        _has_similar_token(text, {'risk', 'alert'}) and 'portfolio' in text
    ):
        return 'risk_alerts'
    if _has_phrase(text, {'market trend', 'trend now', 'current trend', 'market direction', 'how is market'}) or (
        _has_similar_token(text, {'market', 'trend'}) or (_has_similar_token(text, {'trend'}) and _has_similar_token(text, {'market', 'index'}))
    ):
        return 'market_trend'
    if _has_phrase(text, {'portfolio improvement', 'improve my portfolio', 'improvement suggestions', 'how can i improve'}) or (
        _has_similar_token(text, {'improve', 'rebalance', 'improvement'}) and _has_similar_token(text, {'portfolio'})
    ):
        return 'portfolio_improvements'
    if _has_phrase(text, {'new investment opportunity', 'opportunity detection', 'new investments', 'investment opportunities'}) or (
        _has_similar_token(text, {'opportunity', 'opportunities'}) and _has_similar_token(text, {'invest', 'investment'})
    ):
        return 'better_options'
    if _has_phrase(text, {
        'highest returns',
        'generating the highest returns',
        'best returns',
        'top return',
        'most profitable',
        'which stock is most profitable',
        'most profit',
        'highest profit',
        'best performing stock',
    }) or (
        ('which stock' in text or 'best stock' in text or 'more' in text or 'most' in text)
        and _has_similar_token(text, {'profit', 'profitable', 'return', 'gain', 'performing', 'performance'})
    ):
        return 'highest_returns'
    if _has_phrase(text, {
        'underperform',
        'causing losses',
        'losses',
        'worst performer',
        'worst stock',
        'dragging performance',
        'negative return',
        'negative unrealized',
    }) or _has_similar_token(text, {'underperformer', 'underperform', 'loss', 'losing', 'negative'}):
        return 'underperformers'
    if _has_phrase(text, {'diversified', 'diversification', 'sector allocation', 'asset types'}) or _has_similar_token(text, {'diversification', 'diversified', 'allocation', 'concentration'}):
        return 'diversification'
    if _has_phrase(text, {'risk level', 'volatility', 'drawdown', 'risky'}) or _has_similar_token(text, {'risk', 'volatility', 'drawdown'}):
        return 'risk_level'
    if _has_phrase(text, {'market sentiment', 'bullish', 'bearish', 'sentiment'}) or _has_similar_token(text, {'sentiment', 'bullish', 'bearish'}):
        return 'market_sentiment'
    if _has_phrase(text, {'top 3 better investment options', 'better investment options', 'top 3 options', 'investment options'}):
        return 'better_options'
    if _has_phrase(text, {'hold, buy more, or sell', 'hold buy sell', 'buy more', 'sell my current'}) or (
        _has_similar_token(text, {'hold', 'sell', 'rebalance'}) and _has_similar_token(text, {'buy'})
    ):
        return 'hold_buy_sell'
    if _has_phrase(text, {'after 1 year', 'one year value', '1 year value', 'current trends continue'}) or (
        _has_similar_token(text, {'forecast', 'future', 'year'}) and _has_similar_token(text, {'value', 'portfolio'})
    ):
        return 'forecast_one_year'
    if _has_phrase(text, {'probability of loss', 'chance of loss', 'loss probability'}) or (
        _has_similar_token(text, {'probability', 'chance'}) and _has_similar_token(text, {'loss', 'losing'})
    ):
        return 'loss_probability'
    if _has_phrase(text, {'which sector should i invest', 'best sector', 'sector should i invest', 'sector right now'}) or (
        _has_similar_token(text, {'sector'}) and _has_similar_token(text, {'invest', 'best', 'right'})
    ):
        return 'best_sector_now'
    if 'portfolio' in text or 'holding' in text:
        return 'portfolio_summary'
    if 'news' in text or 'headline' in text:
        return 'market_news'
    if symbols or 'price' in text or 'pe' in text or 'quote' in text:
        return 'stock_lookup'
    return 'knowledge'


def _document_score(question_tokens: list[str], document: ChatKnowledgeDocument, route: str):
    content_text = ' '.join([document.title, document.category, document.content[:3000], ' '.join(document.keywords or [])]).lower()
    doc_tokens = set(_tokenize(content_text))
    overlap = len(set(question_tokens) & doc_tokens)
    coverage = overlap / max(1, len(set(question_tokens)))
    keyword_bonus = 0.1 * overlap
    route_bonus = 0.35 if route in {document.category, document.source_type} else 0.0
    return round(coverage + keyword_bonus + route_bonus, 4)


def _retrieve_documents(question: str, route: str):
    question_tokens = _tokenize(question)
    if not question_tokens:
        return []
    query = Q()
    for token in question_tokens[:8]:
        query |= Q(title__icontains=token)
        query |= Q(content__icontains=token)
        query |= Q(category__icontains=token)
    documents = list(ChatKnowledgeDocument.objects.filter(is_active=True).filter(query)[:24]) if query else []
    ranked = []
    for document in documents:
        score = _document_score(question_tokens, document, route)
        if score <= 0:
            continue
        ranked.append(RetrievalDocument(document.id, document.title, document.slug, document.category, document.source_type, document.content, score))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: int(_settings_value('CHATBOT_RETRIEVAL_LIMIT', 3))]


def _retrieve_positive_examples(question: str, route: str, user):
    question_tokens = set(_tokenize(question))
    if not question_tokens:
        return []
    queryset = ChatInteractionLog.objects.filter(
        user=user if getattr(user, 'is_authenticated', False) else None,
        feedback_status=ChatInteractionLog.FEEDBACK_POSITIVE,
        category='finance',
    ).order_by('-created_at')[:25]
    ranked = []
    for item in queryset:
        prior_tokens = set(_tokenize(item.question))
        overlap = len(question_tokens & prior_tokens)
        if overlap <= 0:
            continue
        route_bonus = 0.3 if item.route == route else 0.0
        score = round((overlap / max(1, len(question_tokens))) + route_bonus, 4)
        ranked.append({'question': item.question, 'answer': item.answer, 'route': item.route, 'score': score})
    ranked.sort(key=lambda row: row['score'], reverse=True)
    return ranked[:2]


def _format_currency(value: float | None):
    if value is None:
        return 'N/A'
    return f'{value:,.2f}'


def _format_percent(value: float | None):
    if value is None:
        return 'N/A'
    return f'{value:.2f}%'


def _brief_recent_stamp(context: dict[str, Any]):
    generated_at = context.get('generated_at')
    if not generated_at:
        return 'the latest available app data'
    return f'data available at {generated_at}'


def _answer_highest_returns(context: dict[str, Any]):
    rows = [row for row in context['holdings'] if row.get('return_percent') is not None]
    if not rows:
        return 'I could not calculate returns yet because live price data is missing for your holdings.'
    rows.sort(key=lambda row: (row.get('return_percent') or -9999, row.get('pnl') or -9999), reverse=True)
    top_rows = rows[:3]
    details = ' '.join(
        f"{index + 1}. {row['symbol']} in {row['portfolio_name']} is up {_format_percent(row['return_percent'])} with an unrealized gain of {_format_currency(row['pnl'])}."
        for index, row in enumerate(top_rows)
    )
    return f"Based on {_brief_recent_stamp(context)}, your strongest performers right now are {details} Across all tracked holdings, your portfolio return is {_format_percent(context.get('total_return_percent'))}."


def _answer_underperformers(context: dict[str, Any]):
    rows = [row for row in context['holdings'] if row.get('return_percent') is not None and (row.get('return_percent') or 0) < 0]
    if not rows:
        return f"Based on {_brief_recent_stamp(context)}, none of your tracked holdings are in a loss position right now."
    rows.sort(key=lambda row: (row.get('return_percent') or 0, row.get('pnl') or 0))
    worst_rows = rows[:3]
    text = ' '.join(
        f"{row['symbol']} is at {_format_percent(row['return_percent'])} with a current loss of {_format_currency(row['pnl'])}."
        for row in worst_rows
    )
    return f"Based on {_brief_recent_stamp(context)}, the main underperformers in your portfolio are {text}"


def _answer_diversification(context: dict[str, Any]):
    sectors = context.get('sector_breakdown') or []
    if not sectors:
        return 'I cannot assess diversification yet because there are no holdings in your saved portfolios.'
    top_sector = sectors[0]
    answer = (
        f"Your portfolio looks {context.get('diversification_label', 'moderately diversified')}. "
        f"It currently spans {len(sectors)} sectors, and the largest exposure is {top_sector['sector']} at {_format_percent(top_sector['weight_percent'])} of tracked value."
    )
    if top_sector['weight_percent'] >= 45:
        answer += ' That concentration is on the higher side, so adding exposure outside that sector would improve balance.'
    else:
        answer += ' No single sector is dominating too heavily, which is a healthy sign.'
    answer += ' In this app, your tracked assets are equities, so sector diversification is the main diversification signal available right now.'
    return answer


def _answer_risk_level(context: dict[str, Any]):
    if context.get('weighted_volatility') is None or context.get('weighted_drawdown') is None:
        return 'I do not have enough historical price data yet to estimate portfolio risk from volatility and drawdown.'
    level_word = 'larger' if context['risk_label'] == 'High' else 'relatively limited' if context['risk_label'] == 'Low' else 'manageable'
    return (
        f"Your portfolio risk currently looks {context['risk_label'].lower()} based on the latest available history. "
        f"Estimated annualized volatility is {_format_percent(context['weighted_volatility'])} and weighted drawdown is {_format_percent(context['weighted_drawdown'])}. "
        f"In simple terms, this means the portfolio has {level_word} recent downside swings."
    )


def _answer_market_sentiment(user, context: dict[str, Any]):
    recommendation_rows = (context.get('recommendation_report') or {}).get('recommendations') or []
    if recommendation_rows:
        scored_rows = [row for row in recommendation_rows if row.get('sentiment_percent') is not None]
        if scored_rows:
            scored_rows.sort(key=lambda item: item.get('sentiment_percent', 50), reverse=True)
            strongest = scored_rows[0]
            weakest = scored_rows[-1]
            avg_sentiment = mean([float(row.get('sentiment_percent') or 50) for row in scored_rows])
            tone = 'bullish' if avg_sentiment >= 55 else 'bearish' if avg_sentiment <= 45 else 'mixed to neutral'
            return (
                f"Current market sentiment for your invested stocks looks {tone}. "
                f"The average sentiment score in your recommendation report is {_format_percent(avg_sentiment)}. "
                f"{strongest['symbol']} is strongest at {_format_percent(strongest['sentiment_percent'])}, while {weakest['symbol']} is weakest at {_format_percent(weakest['sentiment_percent'])}."
            )
    portfolios, _ = _build_portfolio_inventory(user)
    if not portfolios:
        return 'I cannot measure portfolio sentiment yet because you do not have saved holdings.'
    stock_rows = []
    for portfolio in portfolios:
        payload = build_portfolio_sentiment_payload(portfolio_id=portfolio.id, user=user) or {}
        stock_rows.extend(payload.get('stocks', []))
    if not stock_rows:
        return 'I could not find enough sentiment coverage for your invested stocks right now.'
    bullish = sum(1 for row in stock_rows if row.get('sentiment_label') == 'Positive')
    bearish = sum(1 for row in stock_rows if row.get('sentiment_label') == 'Negative')
    neutral = sum(1 for row in stock_rows if row.get('sentiment_label') == 'Neutral')
    avg_sentiment = mean([float(row.get('avg_sentiment', row.get('sentiment_percent', 50))) for row in stock_rows])
    tone = 'bullish' if avg_sentiment >= 55 else 'bearish' if avg_sentiment <= 45 else 'mixed to neutral'
    return (
        f"Current market sentiment for your invested stocks looks {tone}. "
        f"The average sentiment score across covered holdings is {_format_percent(avg_sentiment)}, with {bullish} bullish, {neutral} neutral, and {bearish} bearish stock signals."
    )


def _answer_better_options(user, context: dict[str, Any]):
    recommendation_payload = context.get('recommendation_report') or {}
    opportunities = recommendation_payload.get('opportunities', [])
    current_recs = recommendation_payload.get('recommendations', [])
    if opportunities:
        text = ' '.join(
            f"{index + 1}. {row['symbol']} in {row['sector']} with opportunity score {row['opportunity_score']}, discount {_format_percent(row.get('discount_ratio'))}, and P/E {_format_currency(row['pe_ratio']) if row.get('pe_ratio') is not None else 'N/A'}."
            for index, row in enumerate(opportunities[:3])
        )
        return (
            f"Based on your latest recommendation report, the best new investment ideas right now are {text} "
            f"I prioritized underweight sectors and supportive valuation signals from your scored opportunities."
        )
    sectors = context.get('sector_breakdown') or []
    underweight_sectors = [item['sector'] for item in sectors if item['weight_percent'] <= 20][:3]
    candidate_rows = []
    for sector in underweight_sectors:
        for stock in get_stocks_by_sector(sector_name=sector)[:6]:
            current_price = _safe_float(stock.get('current_price'))
            discount_ratio = _safe_float(stock.get('discount_ratio'))
            pe_ratio = _safe_float(stock.get('pe_ratio'))
            score = 50
            if discount_ratio is not None and discount_ratio > 0:
                score += min(12, discount_ratio)
            if pe_ratio is not None and pe_ratio <= 22:
                score += 10
            if current_price is not None:
                score += 3
            candidate_rows.append({
                'symbol': stock['symbol'],
                'company_name': stock['company_name'],
                'sector': sector,
                'score': round(score, 2),
                'pe_ratio': pe_ratio,
                'discount_ratio': discount_ratio,
            })
    seen = set()
    top_candidates = []
    for row in sorted(candidate_rows, key=lambda item: item['score'], reverse=True):
        if row['symbol'] in seen:
            continue
        seen.add(row['symbol'])
        top_candidates.append(row)
        if len(top_candidates) == 3:
            break
    if top_candidates:
        text = ' '.join(
            f"{index + 1}. {row['symbol']} from {row['sector']} with score {row['score']}, P/E {_format_currency(row['pe_ratio']) if row['pe_ratio'] is not None else 'N/A'}, and discount {_format_percent(row['discount_ratio'])}."
            for index, row in enumerate(top_candidates)
        )
        return f"Based on your current portfolio mix, the most interesting additional ideas right now are {text} I prioritized underweight sectors in your portfolio and basic valuation support."
    if current_recs:
        top_current = current_recs[:3]
        text = ' '.join(f"{index + 1}. {row['symbol']} rated {row['label']} with score {row['score']}." for index, row in enumerate(top_current))
        return f"I do not have strong external replacements yet, but within your existing holdings the best current opportunities are {text}"
    return 'I could not generate strong alternative investment options from the current market data.'


def _answer_hold_buy_sell(user, context: dict[str, Any]):
    recommendation_payload = context.get('recommendation_report') or {}
    rows = recommendation_payload.get('recommendations', [])
    if not rows:
        return 'I could not build a hold or sell view yet because recommendation data is missing.'
    buy_more = [row for row in rows if row.get('label') == 'Buy'][:2]
    hold = [row for row in rows if row.get('label') == 'Hold'][:2]
    reduce = [row for row in rows if row.get('label') in {'Sell', 'Watch'}][:2]
    parts = []
    if buy_more:
        parts.append('Buy more candidates: ' + ', '.join(f"{row['symbol']} ({row['score']})" for row in buy_more))
    if hold:
        parts.append('Hold candidates: ' + ', '.join(f"{row['symbol']} ({row['score']})" for row in hold))
    if reduce:
        parts.append('Sell or closely watch: ' + ', '.join(f"{row['symbol']} ({row['score']})" for row in reduce))
    return 'Based on your latest recommendation report, here is the clearest action split. ' + ' '.join(parts) + '. This is signal-based guidance using profitability, forecast, sentiment, risk, and diversification scores.'


def _answer_forecast_one_year(context: dict[str, Any]):
    rows = [row for row in context['holdings'] if row.get('annualized_return') is not None and row.get('current_value') is not None]
    if not rows:
        return 'I do not have enough historical trend data to estimate your 1-year portfolio value yet.'
    projected_value = 0.0
    current_value = 0.0
    for row in rows:
        annualized_return = max(-60.0, min(80.0, float(row['annualized_return'])))
        current_position_value = float(row['current_value'])
        current_value += current_position_value
        projected_value += current_position_value * (1 + annualized_return / 100)
    projected_gain = projected_value - current_value
    return (
        f"If current historical trends continue for another year, your tracked portfolio value could move from {_format_currency(current_value)} to about {_format_currency(projected_value)}. "
        f"That implies a projected change of {_format_currency(projected_gain)}. This is a trend-following scenario, not a guaranteed prediction."
    )


def _answer_loss_probability(context: dict[str, Any]):
    probability = context.get('weighted_probability_of_loss')
    if probability is None:
        return 'I do not have enough return history yet to estimate the probability of loss.'
    level = 'high' if probability >= 55 else 'moderate' if probability >= 45 else 'low'
    return (
        f"The estimated probability of short-term loss in your portfolio is {_format_percent(probability)}, which is a {level} risk reading. "
        f"This estimate comes from historical negative-return frequency across your holdings."
    )


def _answer_best_sector_now(context: dict[str, Any]):
    recommendation_payload = context.get('recommendation_report') or {}
    opportunities = recommendation_payload.get('opportunities') or []
    if opportunities:
        sector_totals = defaultdict(list)
        for row in opportunities:
            sector_totals[row['sector']].append(float(row.get('opportunity_score') or 0))
        ranked = sorted(
            [
                {
                    'sector': sector,
                    'score': round(mean(scores), 2),
                    'idea_count': len(scores),
                }
                for sector, scores in sector_totals.items()
            ],
            key=lambda item: item['score'],
            reverse=True,
        )
        if ranked:
            best = ranked[0]
            return (
                f"Based on your latest recommendation report, {best['sector']} is the strongest sector to explore right now. "
                f"It leads your opportunity set with an average score of {best['score']} across {best['idea_count']} candidate ideas."
            )
    sectors = context.get('sector_breakdown') or []
    if not sectors:
        return 'I cannot identify a sector direction yet because there are no holdings to compare against.'
    candidates = []
    for sector_info in sectors:
        sector = sector_info['sector']
        stocks = get_stocks_by_sector(sector_name=sector)[:8]
        valid = [item for item in stocks if item.get('current_price') is not None]
        if not valid:
            continue
        avg_discount = mean([float(item.get('discount_ratio') or 0) for item in valid])
        pe_values = [float(item['pe_ratio']) for item in valid if item.get('pe_ratio') is not None]
        avg_pe = mean(pe_values) if pe_values else None
        score = avg_discount + (8 if avg_pe is not None and avg_pe <= 24 else 0)
        candidates.append({'sector': sector, 'score': round(score, 2), 'avg_discount': round(avg_discount, 2), 'avg_pe': round(avg_pe, 2) if avg_pe is not None else None})
    if not candidates:
        return 'I could not rank sectors cleanly from the current market data.'
    candidates.sort(key=lambda item: item['score'], reverse=True)
    best = candidates[0]
    return (
        f"Within the sectors relevant to your current portfolio, {best['sector']} looks the strongest right now. "
        f"It has an estimated sector score of {best['score']}, average discount {_format_percent(best['avg_discount'])}, and average P/E {_format_currency(best['avg_pe']) if best['avg_pe'] is not None else 'N/A'}."
    )


def _answer_portfolio_improvements(context: dict[str, Any]):
    recommendation_payload = context.get('recommendation_report') or {}
    improvements = recommendation_payload.get('portfolio_improvements') or []
    if not improvements:
        return 'I could not generate portfolio improvement suggestions from the latest report yet.'
    text = ' '.join(
        f"{index + 1}. {item['title']}: {item['detail']}"
        for index, item in enumerate(improvements[:3])
    )
    return f"Here are the top portfolio improvements from your latest recommendation report. {text}"


def _answer_risk_alerts(context: dict[str, Any]):
    recommendation_payload = context.get('recommendation_report') or {}
    alerts = recommendation_payload.get('risk_alerts') or []
    if not alerts:
        return 'There are no active risk alerts in your latest recommendation report right now.'
    text = ' '.join(
        f"{index + 1}. {item['title']}: {item['detail']}"
        for index, item in enumerate(alerts[:3])
    )
    return f"These are the most important current risk alerts from your recommendation analysis. {text}"


def _answer_portfolio_summary(context: dict[str, Any]):
    if not context.get('holding_count'):
        return 'You do not have any saved holdings yet, so there is nothing to analyze in the chatbot.'
    return (
        f"You currently have {context['portfolio_count']} portfolios with {context['holding_count']} tracked holdings. "
        f"Your combined invested value is {_format_currency(context['total_invested'])}, current value is {_format_currency(context['total_current'])}, and overall return is {_format_percent(context['total_return_percent'])}."
    )


def _answer_market_news(context: dict[str, Any]):
    news = context.get('market_news') or []
    if not news:
        return 'I could not find market headlines right now.'
    top_titles = '; '.join(item.get('title', 'Market update') for item in news[:3])
    return f"Recent market context from the live feed is: {top_titles}. This is the freshest headline view available in the app right now."


def _answer_market_trend(context: dict[str, Any]):
    overview = context.get('market_overview') or {}
    top_stocks = overview.get('top_stocks') or []
    news = context.get('market_news') or []
    valid_rows = [row for row in top_stocks if row.get('last_value') is not None]
    if valid_rows:
        text = '; '.join(
            f"{row['symbol']} at {_format_currency(row.get('last_value'))} with P/E {_format_currency(row.get('pe_ratio')) if row.get('pe_ratio') is not None else 'N/A'}"
            for row in valid_rows[:3]
        )
        lead = news[0].get('title') if news else None
        if lead:
            return f"Current market trend looks active but mixed. Key tracked stocks are {text}. The latest headline signal is: {lead}."
        return f"Current market trend looks active but mixed. Key tracked stocks are {text}."
    if news:
        return f"Current market trend is best described from the live news feed right now: {news[0].get('title', 'Market update')}."
    return 'I could not read the current market trend right now because live market context is unavailable.'


def _answer_stock_lookup(context: dict[str, Any]):
    symbols = context.get('symbols') or {}
    if not symbols:
        return 'I could not identify a stock symbol from your question. Try using a clear symbol like TCS, INFY, RELIANCE, or AAPL.'
    return ' '.join(
        f"{symbol} is at {snapshot.get('current_price') or snapshot.get('last_value') or 'N/A'}, with price change {snapshot.get('price_change') if snapshot.get('price_change') is not None else 'N/A'} and P/E {snapshot.get('pe_ratio') if snapshot.get('pe_ratio') is not None else 'N/A'}."
        for symbol, snapshot in list(symbols.items())[:3]
    )


def _answer_knowledge(documents: list[RetrievalDocument]):
    safe_documents = [
        item for item in documents
        if item.source_type != 'system'
        and not item.content.strip().lower().startswith('you are ')
        and 'when the user asks' not in item.content.strip().lower()
    ]
    if not safe_documents:
        return 'I do not have a matching guidance document for that question yet.'
    lead = safe_documents[0]
    sentences = re.split(r'(?<=[.!?])\s+', lead.content.strip())
    return ' '.join(sentence.strip() for sentence in sentences[:4] if sentence.strip())


def _ollama_rewrite_answer(*, question: str, route: str, draft_answer: str, context: dict[str, Any], positive_examples: list[dict[str, Any]], prompt_instructions: str):
    if not getattr(settings, 'CHATBOT_USE_OLLAMA', False):
        return draft_answer, False

    prompt = {
        'question': question,
        'route': route,
        'draft_answer': draft_answer,
        'generated_at': context.get('generated_at'),
        'portfolio_summary': {
            'portfolio_count': context.get('portfolio_count'),
            'holding_count': context.get('holding_count'),
            'total_invested': context.get('total_invested'),
            'total_current': context.get('total_current'),
            'total_return_percent': context.get('total_return_percent'),
            'risk_label': context.get('risk_label'),
            'diversification_label': context.get('diversification_label'),
        },
        'positive_examples': positive_examples,
        'instructions': (
            prompt_instructions + ' '
            + 'Rewrite the draft answer into a clear finance assistant response. '
            'Keep it factual, relevant, and brief-but-complete. '
            'Do not invent data. Do not add generic follow-up suggestions. '
            'If the draft already has enough information, improve wording only.'
        ),
    }
    payload = {
        'model': getattr(settings, 'CHATBOT_OLLAMA_MODEL', 'qwen2.5:7b'),
        'prompt': json.dumps(prompt, ensure_ascii=True),
        'stream': False,
    }
    req = urllib_request.Request(
        getattr(settings, 'CHATBOT_OLLAMA_URL', 'http://127.0.0.1:11434/api/generate'),
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode('utf-8'))
            text = _sanitize_text(body.get('response') or draft_answer, limit=2400)
            return text or draft_answer, True
    except (urllib_error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return draft_answer, False


def _route_actions(question: str):
    text = (question or '').lower()
    mapping = [('portfolio', '/portfolios', 'Open Portfolios'), ('news', '/news', 'Open News'), ('profile', '/profile', 'Open Profile'), ('home', '/home', 'Open Home')]
    actions = []
    for keyword, path, label in mapping:
        if keyword in text:
            actions.append({'type': 'route', 'path': path, 'label': label})
    return actions[:2]


def _confidence(route: str, context: dict[str, Any], documents: list[RetrievalDocument]):
    base = 0.55
    if context.get('holding_count'):
        base += 0.15
    if route in {'risk_level', 'forecast_one_year', 'loss_probability'} and context.get('weighted_volatility') is not None:
        base += 0.15
    if route == 'market_sentiment':
        base += 0.1
    if documents:
        base += min(0.1, documents[0].score / 5)
    return round(min(0.99, base), 2)


def _log_interaction(*, user, question: str, answer: str, route: str, prompt, documents: list[RetrievalDocument], confidence: float, actions: list[dict[str, Any]]):
    prompt_name = prompt.name if hasattr(prompt, 'name') else prompt.get('name', 'finance_chatbot')
    prompt_version = prompt.version if hasattr(prompt, 'version') else prompt.get('version', 1)
    return ChatInteractionLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        question=question,
        answer=answer,
        category='finance',
        route=route,
        model='local-portfolio-analyst',
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        retrieval_count=len(documents),
        confidence=confidence,
        used_documents=[{'id': item.id, 'title': item.title, 'slug': item.slug, 'score': item.score} for item in documents],
        metadata={'actions': actions},
    )


def _resolve_answer(route: str, *, user, context: dict[str, Any], documents: list[RetrievalDocument]):
    answer_map = {
        'highest_returns': lambda: _answer_highest_returns(context),
        'underperformers': lambda: _answer_underperformers(context),
        'diversification': lambda: _answer_diversification(context),
        'risk_level': lambda: _answer_risk_level(context),
        'market_sentiment': lambda: _answer_market_sentiment(user, context),
        'better_options': lambda: _answer_better_options(user, context),
        'hold_buy_sell': lambda: _answer_hold_buy_sell(user, context),
        'forecast_one_year': lambda: _answer_forecast_one_year(context),
        'loss_probability': lambda: _answer_loss_probability(context),
        'best_sector_now': lambda: _answer_best_sector_now(context),
        'market_trend': lambda: _answer_market_trend(context),
        'portfolio_improvements': lambda: _answer_portfolio_improvements(context),
        'risk_alerts': lambda: _answer_risk_alerts(context),
        'portfolio_summary': lambda: _answer_portfolio_summary(context),
        'market_news': lambda: _answer_market_news(context),
        'stock_lookup': lambda: _answer_stock_lookup(context),
        'knowledge': lambda: _answer_knowledge(documents),
    }
    return answer_map.get(route, lambda: _answer_knowledge(documents))()


def _run_chatbot_graph(*, user, clean_question: str, clean_history: list[dict[str, str]], prompt, prompt_instructions: str):
    initial_state = {
        'user': user,
        'question': clean_question,
        'history': clean_history,
        'prompt': prompt,
        'prompt_instructions': prompt_instructions,
        'symbols': [],
        'route': 'knowledge',
        'documents': [],
        'positive_examples': [],
        'portfolio_context': {},
        'market_context': {},
        'context': {},
        'draft_answer': '',
        'answer': '',
        'used_ollama': False,
    }

    def classify_node(state):
        symbols = _extract_symbols(state['question'])
        route = _determine_route(state['question'], symbols)
        return {**state, 'symbols': symbols, 'route': route}

    def retrieve_node(state):
        documents = _retrieve_documents(state['question'], state['route'])
        positive_examples = _retrieve_positive_examples(state['question'], state['route'], state['user'])
        return {**state, 'documents': documents, 'positive_examples': positive_examples}

    def finance_node(state):
        portfolio_context = _portfolio_analytics_context(state['user'])
        route = state.get('route')
        recommendation_report = {}
        primary_portfolio_id = portfolio_context.get('primary_portfolio_id')
        if route in RECOMMENDATION_ROUTES:
            recommendation_report = _get_recommendation_report(
                user=state['user'],
                portfolio_id=primary_portfolio_id,
            )
        market_context = {
            'market_news': _get_cached_market_news(limit=4) if route in MARKET_LIVE_ROUTES else [],
            'market_overview': _get_cached_market_overview() if route in MARKET_LIVE_ROUTES else {},
            'symbols': {symbol: get_stock_snapshot(symbol) for symbol in state['symbols']} if state['symbols'] else {},
            'recommendation_report': recommendation_report,
        }
        context = {**portfolio_context, **market_context, 'history': state['history']}
        return {**state, 'portfolio_context': portfolio_context, 'market_context': market_context, 'context': context}

    def answer_node(state):
        draft_answer = _resolve_answer(state['route'], user=state['user'], context=state['context'], documents=state['documents'])
        answer, used_ollama = _ollama_rewrite_answer(
            question=state['question'],
            route=state['route'],
            draft_answer=draft_answer,
            context=state['context'],
            positive_examples=state['positive_examples'],
            prompt_instructions=state['prompt_instructions'],
        )
        return {**state, 'draft_answer': draft_answer, 'answer': answer, 'used_ollama': used_ollama}

    if StateGraph is None:
        state = classify_node(initial_state)
        state = retrieve_node(state)
        state = finance_node(state)
        return answer_node(state)

    workflow = StateGraph(dict)
    workflow.add_node('classify', classify_node)
    workflow.add_node('retrieve', retrieve_node)
    workflow.add_node('finance', finance_node)
    workflow.add_node('answer', answer_node)
    workflow.set_entry_point('classify')
    workflow.add_edge('classify', 'retrieve')
    workflow.add_edge('retrieve', 'finance')
    workflow.add_edge('finance', 'answer')
    workflow.add_edge('answer', END)
    graph = workflow.compile()
    return graph.invoke(initial_state)


def generate_chatbot_reply(*, user, question: str, history: Any):
    clean_question = _sanitize_text(question, limit=700)
    clean_history = sanitize_history(history)
    decision = _guardrail_decision(clean_question)
    if not decision.allowed:
        return {
            'answer': decision.reason,
            'model': 'local-guardrail',
            'category': decision.category,
            'route': 'blocked',
            'actions': [],
            'quick_prompts': TOP_QUESTION_PROMPTS,
            'citations': [],
            'meta': {'history_used': len(clean_history), 'confidence': 0.0},
        }

    prompt = _active_prompt()
    prompt_instructions = prompt.instructions if hasattr(prompt, 'instructions') else prompt.get('instructions', '')
    state = _run_chatbot_graph(
        user=user,
        clean_question=clean_question,
        clean_history=clean_history,
        prompt=prompt,
        prompt_instructions=prompt_instructions,
    )
    route = state['route']
    documents = state['documents']
    positive_examples = state['positive_examples']
    context = state['context']
    answer = state['answer']
    used_ollama = state['used_ollama']
    actions = _route_actions(clean_question)
    confidence = _confidence(route, context, documents)
    interaction = _log_interaction(user=user, question=clean_question, answer=answer, route=route, prompt=prompt, documents=documents, confidence=confidence, actions=actions)
    prompt_name = prompt.name if hasattr(prompt, 'name') else prompt.get('name', 'finance_chatbot')
    prompt_version = prompt.version if hasattr(prompt, 'version') else prompt.get('version', 1)
    citations = [{'id': item.id, 'title': item.title, 'slug': item.slug, 'category': item.category, 'score': item.score} for item in documents]
    return {
        'answer': answer,
        'model': getattr(settings, 'CHATBOT_OLLAMA_MODEL', 'local-portfolio-analyst') if used_ollama else 'local-portfolio-analyst',
        'category': 'finance',
        'route': route,
        'actions': actions,
        'quick_prompts': TOP_QUESTION_PROMPTS,
        'citations': citations,
        'meta': {
            'interaction_id': interaction.id,
            'history_used': len(clean_history),
            'prompt_name': prompt_name,
            'prompt_version': prompt_version,
            'confidence': confidence,
            'used_ollama': used_ollama,
            'positive_examples_used': len(positive_examples),
            'generated_at': timezone.now().isoformat(),
        },
    }
