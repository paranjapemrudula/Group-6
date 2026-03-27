import logging
import re
from dataclasses import dataclass
from statistics import mean
from typing import Any

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from portfolios.models import Portfolio
from recommendations.services import build_portfolio_recommendations
from stocks.models import PortfolioStock, Sector, SectorAlias, StockUniverse
from stocks.services import (
    get_market_news,
    get_market_overview,
    get_stock_snapshot,
    get_stock_suggestions,
    get_stocks_by_sector,
)

from .services import (
    build_company_sentiment_payload,
    build_portfolio_analytics_payload,
    build_portfolio_sentiment_payload,
)


DEFAULT_ROUTE_PROMPTS = [
    {'label': 'Market trend', 'prompt': 'What is happening in the market right now?'},
    {'label': 'Portfolio summary', 'prompt': 'Summarize my portfolio.'},
    {'label': 'Sector ideas', 'prompt': 'Which sector looks strong right now?'},
]

FINANCE_KEYWORDS = {
    'stock', 'stocks', 'market', 'markets', 'portfolio', 'portfolios', 'invest', 'investment',
    'finance', 'financial', 'price', 'prices', 'news', 'analysis', 'pe', 'trend', 'volatility',
    'risk', 'asset', 'equity', 'sentiment', 'sector', 'quality', 'recommendation', 'buy', 'sell',
    'hold', 'cluster', 'discount',
}

SENSITIVE_PATTERNS = [
    'password', 'secret', 'token', 'refresh token', 'access token', 'api key', 'private key',
    'session cookie', 'jwt', '.env', 'secret_key', 'server path', 'filesystem', 'local path',
    'admin credentials',
]

SYMBOL_PATTERN = re.compile(r'\b[A-Z]{2,10}(?:\.[A-Z]{1,4})?\b')
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-\._]+")
logger = logging.getLogger(__name__)


@dataclass
class ScopeDecision:
    allowed: bool
    reason: str
    category: str


def _sanitize_text(value: Any, limit: int = 700):
    text = str(value or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:limit]


def sanitize_history(history: Any, limit: int = 6):
    if not isinstance(history, list):
        return []
    cleaned = []
    for item in history[-limit:]:
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
        return ScopeDecision(
            False,
            'I can help with finance analysis, but I cannot expose passwords, tokens, internal paths, or private system data.',
            'sensitive',
        )
    if not _looks_finance_related(question):
        return ScopeDecision(
            False,
            'I can help with finance, market data, portfolio questions, sectors, quality, and sentiment. Please ask a finance-related question.',
            'out_of_scope',
        )
    return ScopeDecision(True, 'allowed', 'finance')


def _tokenize(text: str):
    tokens = TOKEN_PATTERN.findall((text or '').lower())
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'and', 'or', 'for', 'to', 'of', 'in', 'on',
        'my', 'me', 'with', 'what', 'how', 'can', 'you', 'about', 'right', 'now', 'please', 'show',
        'tell', 'give', 'use',
    }
    return [token for token in tokens if len(token) > 2 and token not in stop_words]


def _has_phrase(text: str, phrases: set[str]):
    return any(phrase in text for phrase in phrases)


def _extract_symbols(question: str):
    symbols = list(dict.fromkeys(SYMBOL_PATTERN.findall(question or '')))
    try:
        suggestions = get_stock_suggestions(query=question or '', limit=4)
    except Exception:
        logger.exception('Stock suggestions lookup failed for question: %s', question)
        suggestions = []
    for item in suggestions:
        symbol = item.get('symbol')
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols[:4]


def _safe_call(builder, default, *, label: str):
    try:
        value = builder()
        return default if value is None else value
    except Exception:
        logger.exception('Chatbot data source failed: %s', label)
        return default


def _safe_cached(key: str, builder, default, timeout: int = 300):
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = _safe_call(builder, default, label=key)
    cache.set(key, payload, timeout=timeout)
    return payload


def _find_sector_from_question(question: str):
    text = (question or '').lower()
    if not text:
        return None

    sectors = list(Sector.objects.all().only('id', 'name'))
    aliases = list(SectorAlias.objects.select_related('sector').all().only('alias_name', 'sector__id', 'sector__name'))

    for sector in sectors:
        if sector.name and sector.name.lower() in text:
            return sector

    for alias in aliases:
        if alias.alias_name and alias.alias_name.lower() in text:
            return alias.sector

    banking_aliases = {'bank', 'banks', 'banking', 'financials', 'finance'}
    if any(alias in text for alias in banking_aliases):
        for sector in sectors:
            lowered = sector.name.lower()
            if 'bank' in lowered or 'financ' in lowered:
                return sector
    return None


def _determine_route(question: str, symbols: list[str]):
    text = (question or '').lower()
    if (
        _has_phrase(text, {'most profitable', 'more profitable', 'highest return', 'best return', 'best performing', 'top performer'})
        and _find_sector_from_question(question) is not None
    ):
        return 'sector_profitability'
    if _has_phrase(text, {'market trend', 'trend now', 'market direction', 'what is happening in the market'}):
        return 'market_trend'
    if _has_phrase(text, {'sentiment', 'bullish', 'bearish', 'news tone'}):
        return 'sentiment'
    if _has_phrase(text, {'quality', 'good quality', 'bad quality', 'best quality sector'}):
        return 'quality'
    if _has_phrase(text, {'sector', 'sectors', 'which sector', 'sector route'}):
        return 'sector'
    if _has_phrase(text, {'recommendation', 'buy', 'sell', 'hold', 'rebalance', 'opportunity'}):
        return 'recommendation'
    if _has_phrase(text, {'portfolio', 'holdings', 'invested', 'return', 'profit', 'loss'}):
        return 'portfolio'
    if symbols or _has_phrase(text, {'pe ratio', 'price', 'quote', 'stock detail'}):
        return 'stock_lookup'
    if _has_phrase(text, {'news', 'headline'}):
        return 'market_news'
    return 'market_trend'


def _safe_float(value: Any):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_currency(value):
    number = _safe_float(value)
    if number is None:
        return 'N/A'
    return f'{number:.2f}'


def _format_percent(value):
    number = _safe_float(value)
    if number is None:
        return 'N/A'
    return f'{number:.2f}%'


def _cached(key: str, builder, timeout: int = 300):
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = builder()
    cache.set(key, payload, timeout=timeout)
    return payload


def _build_portfolio_summary(user):
    portfolios = list(Portfolio.objects.filter(user=user).order_by('-created_at'))
    holdings = list(
        PortfolioStock.objects.filter(portfolio__user=user)
        .select_related('portfolio', 'sector')
        .order_by('-added_at')
    )
    rows = []
    total_invested = 0.0
    total_current = 0.0
    for item in holdings:
        quote = _safe_call(lambda: get_stock_snapshot(item.symbol), {}, label=f'quote:{item.symbol}')
        buy_price = float(item.buy_price)
        quantity = int(item.quantity or 0)
        current_price = _safe_float(quote.get('current_price') or quote.get('last_value'))
        invested_amount = round(buy_price * quantity, 2)
        current_value = round((current_price or 0) * quantity, 2) if current_price is not None else None
        profit_loss = round(current_value - invested_amount, 2) if current_value is not None else None
        return_percent = round(((current_price - buy_price) / buy_price) * 100, 2) if current_price is not None and buy_price else None
        total_invested += invested_amount
        if current_value is not None:
            total_current += current_value
        rows.append(
            {
                'symbol': item.symbol,
                'company_name': item.company_name,
                'portfolio_name': item.portfolio.name,
                'sector': item.sector.name,
                'quantity': quantity,
                'buy_price': buy_price,
                'current_price': current_price,
                'invested_amount': invested_amount,
                'current_value': current_value,
                'profit_loss': profit_loss,
                'return_percent': return_percent,
            }
        )
    return {
        'portfolio_count': len(portfolios),
        'portfolio_names': [item.name for item in portfolios],
        'holding_count': len(rows),
        'holdings': rows,
        'total_invested': round(total_invested, 2),
        'total_current': round(total_current, 2),
        'total_profit_loss': round(total_current - total_invested, 2),
    }


def _build_sector_snapshot():
    sectors = list(
        Sector.objects.annotate(
            universe_stock_count=Count('universe_stocks', distinct=True)
        ).order_by('-universe_stock_count', 'name')[:12]
    )
    return [
        {
            'id': sector.id,
            'name': sector.name,
            'universe_stock_count': sector.universe_stock_count or 0,
        }
        for sector in sectors
    ]


def _build_quality_snapshot():
    cache_key = 'chatbot:quality:sectors'

    def builder():
        results = []
        for sector in Sector.objects.annotate(universe_stock_count=Count('universe_stocks', distinct=True)).order_by('-universe_stock_count', 'name')[:10]:
            rows = get_stocks_by_sector(sector.name)[:3]
            close_values = [float(item.get('current_price') or 0) for item in rows if item.get('current_price') is not None]
            avg_price = round(mean(close_values), 2) if close_values else 0.0
            results.append(
                {
                    'id': sector.id,
                    'name': sector.name,
                    'universe_stock_count': sector.universe_stock_count or 0,
                    'avg_price': avg_price,
                    'stocks': rows,
                }
            )
        ranked = sorted(results, key=lambda item: item['avg_price'], reverse=True)
        non_zero = [item for item in ranked if item['avg_price'] > 0]
        threshold = non_zero[len(non_zero) // 2]['avg_price'] if non_zero else 0
        for item in ranked:
            item['cluster'] = 'Good Quality' if item['avg_price'] and item['avg_price'] >= threshold else 'Bad Quality'
        return ranked[:10]

    return _cached(cache_key, builder, timeout=600)


def _build_context(question: str, user, route: str):
    symbols = _extract_symbols(question)
    portfolio = _safe_cached(
        f'chatbot:portfolio:{getattr(user, "id", "anon")}',
        lambda: _build_portfolio_summary(user),
        {'portfolio_count': 0, 'portfolio_names': [], 'holding_count': 0, 'holdings': [], 'total_invested': 0.0, 'total_current': 0.0, 'total_profit_loss': 0.0},
        timeout=180,
    )
    primary_portfolio = Portfolio.objects.filter(user=user).order_by('-created_at').first()
    sentiment = {}
    recommendations = {}
    analytics = {}
    if primary_portfolio and route in {'portfolio', 'sentiment', 'recommendation', 'quality'}:
        if route in {'sentiment', 'recommendation'}:
            sentiment = _safe_call(
                lambda: build_portfolio_sentiment_payload(portfolio_id=primary_portfolio.id, user=user) or {},
                {},
                label='portfolio_sentiment',
            )
        if route == 'recommendation':
            recommendations = _safe_call(
                lambda: build_portfolio_recommendations(portfolio_id=primary_portfolio.id, user=user) or {},
                {},
                label='portfolio_recommendations',
            )
        if route == 'quality':
            analytics = _safe_call(
                lambda: build_portfolio_analytics_payload(portfolio_id=primary_portfolio.id, user=user) or {},
                {},
                label='portfolio_analytics',
            )
    company_sentiment = {}
    if symbols and route == 'sentiment':
        first_symbol = symbols[0]
        company_sentiment = _safe_call(
            lambda: build_company_sentiment_payload(symbol=first_symbol, company_name='') or {},
            {},
            label=f'company_sentiment:{first_symbol}',
        )
    market_overview = {}
    market_news = []
    if route in {'market_trend', 'market_news', 'sentiment'}:
        market_overview = _safe_cached('chatbot:market_overview', get_market_overview, {}, timeout=300)
        market_news = _safe_cached('chatbot:market_news', lambda: get_market_news(limit=4), [], timeout=300)
    symbol_snapshots = {}
    if symbols:
        for symbol in symbols:
            symbol_snapshots[symbol] = _safe_call(lambda symbol=symbol: get_stock_snapshot(symbol), {}, label=f'symbol_snapshot:{symbol}')
    sector_snapshot = []
    if route in {'sector', 'sector_profitability', 'quality'}:
        sector_snapshot = _safe_cached('chatbot:sector_snapshot', _build_sector_snapshot, [], timeout=600)
    quality_snapshot = []
    if route == 'quality':
        quality_snapshot = _safe_call(_build_quality_snapshot, [], label='quality_snapshot')
    return {
        'generated_at': timezone.now().isoformat(),
        'route': route,
        'symbols': symbol_snapshots,
        'portfolio': portfolio,
        'primary_portfolio_id': primary_portfolio.id if primary_portfolio else None,
        'portfolio_sentiment': sentiment,
        'company_sentiment': company_sentiment,
        'recommendations': recommendations,
        'portfolio_analytics': analytics,
        'market_overview': market_overview,
        'market_news': market_news,
        'sector_snapshot': sector_snapshot,
        'quality_snapshot': quality_snapshot,
        'matched_sector': _find_sector_from_question(question),
    }


def _answer_market_trend(context: dict[str, Any]):
    top_stocks = (context.get('market_overview') or {}).get('top_stocks') or []
    news = context.get('market_news') or []
    if top_stocks:
        summary = '; '.join(
            f"{item['symbol']} at {_format_currency(item.get('last_value'))} with P/E {_format_currency(item.get('pe_ratio'))}"
            for item in top_stocks[:3]
        )
        headline = news[0].get('title') if news else 'No headline available'
        return f"Current market trend looks mixed but active. Key tracked stocks are {summary}. Latest market signal: {headline}."
    return 'I could not read the market trend right now because live market data is unavailable.'


def _answer_market_news(context: dict[str, Any]):
    news = context.get('market_news') or []
    if not news:
        return 'I could not find market headlines right now.'
    text = ' '.join(f"{index + 1}. {item.get('title', 'Market update')}" for index, item in enumerate(news[:3]))
    return f"Here are the latest market headlines from the live feed. {text}"


def _answer_portfolio(context: dict[str, Any]):
    portfolio = context.get('portfolio') or {}
    if not portfolio.get('holding_count'):
        return 'You do not have any tracked holdings yet. Create a portfolio and add stocks first so I can analyze returns, sectors, sentiment, and recommendations.'
    holdings = portfolio.get('holdings') or []
    best = max(
        [item for item in holdings if item.get('return_percent') is not None],
        key=lambda item: item.get('return_percent', -10**9),
        default=None,
    )
    worst = min(
        [item for item in holdings if item.get('return_percent') is not None],
        key=lambda item: item.get('return_percent', 10**9),
        default=None,
    )
    parts = [
        f"You currently have {portfolio.get('portfolio_count', 0)} portfolios and {portfolio.get('holding_count', 0)} tracked holdings.",
        f"Total invested value is {_format_currency(portfolio.get('total_invested'))} and current tracked value is {_format_currency(portfolio.get('total_current'))}.",
    ]
    if best:
        parts.append(f"Best current performer is {best['symbol']} at {_format_percent(best.get('return_percent'))}.")
    if worst:
        parts.append(f"Weakest current performer is {worst['symbol']} at {_format_percent(worst.get('return_percent'))}.")
    return ' '.join(parts)


def _answer_sentiment(context: dict[str, Any]):
    company_payload = context.get('company_sentiment') or {}
    if company_payload.get('summary'):
        summary = company_payload['summary']
        return (
            f"Sentiment for {company_payload.get('symbol')} is {summary.get('label', 'Neutral')} with average sentiment "
            f"{_format_percent(summary.get('avg_sentiment'))}. Recent article count is {summary.get('total_articles', 0)}."
        )
    payload = context.get('portfolio_sentiment') or {}
    summary = payload.get('summary') or {}
    if summary:
        return (
            f"Your portfolio sentiment is {summary.get('label', 'Neutral')} with average sentiment "
            f"{_format_percent(summary.get('avg_sentiment', summary.get('average_sentiment_percent')))}. "
            f"Tracked stocks: {summary.get('tracked_stocks', 0)}, articles analyzed: {summary.get('total_articles', 0)}."
        )
    return 'I could not build a sentiment answer yet because sentiment data is unavailable.'


def _answer_recommendation(context: dict[str, Any]):
    payload = context.get('recommendations') or {}
    rows = payload.get('recommendations') or []
    if not rows:
        return 'I do not have recommendation data yet. Please add holdings to a portfolio first.'
    top = rows[:3]
    text = ' '.join(
        f"{index + 1}. {row['symbol']} is {row['label']} with score {_format_currency(row.get('score'))} because {', '.join(row.get('reasons', [])[:2])}."
        for index, row in enumerate(top)
    )
    return f"Here are the strongest recommendation signals from your portfolio. {text}"


def _answer_sector(question: str, context: dict[str, Any]):
    sectors = context.get('sector_snapshot') or []
    text = (question or '').lower()
    for sector in sectors:
        if sector['name'].lower() in text:
            stocks = get_stocks_by_sector(sector['name'])[:3]
            if stocks:
                stock_text = '; '.join(
                    f"{item['symbol']} at {_format_currency(item.get('current_price'))}"
                    for item in stocks
                )
                return f"{sector['name']} has {sector['universe_stock_count']} mapped stocks in your database. Sample names: {stock_text}."
            return f"{sector['name']} exists in your sector database with {sector['universe_stock_count']} mapped stocks."
    if sectors:
        lead = ', '.join(f"{item['name']} ({item['universe_stock_count']})" for item in sectors[:5])
        return f"Top sectors in your database right now are {lead}. Ask about a specific sector to drill into its stocks."
    return 'I could not find sector data yet. Import or map stock-universe data first.'


def _answer_sector_profitability(question: str, context: dict[str, Any]):
    portfolio = context.get('portfolio') or {}
    holdings = portfolio.get('holdings') or []
    matched_sector = context.get('matched_sector')
    if not matched_sector:
        return 'Please mention a sector like banking, technology, pharma, or energy so I can compare profitability inside that group.'

    sector_holdings = [item for item in holdings if (item.get('sector') or '').lower() == matched_sector.name.lower()]
    if not sector_holdings:
        sample_rows = _safe_call(lambda: get_stocks_by_sector(matched_sector.name)[:3], [], label=f'sector_stocks:{matched_sector.name}')
        if sample_rows:
            sample_text = ', '.join(item.get('symbol') or 'Unknown' for item in sample_rows[:3])
            return (
                f"I could not find any {matched_sector.name} holdings in your portfolio yet. "
                f"Your database does track {matched_sector.name} stocks such as {sample_text}. "
                f"Add one of them to a portfolio and I can rank profitability for you."
            )
        return f"I could not find any {matched_sector.name} holdings in your portfolio yet, so there is nothing to rank by profitability."

    ranked = [item for item in sector_holdings if item.get('profit_loss') is not None or item.get('return_percent') is not None]
    if not ranked:
        return f"I found your {matched_sector.name} holdings, but current price data is missing, so I cannot rank profitability yet."

    best = max(
        ranked,
        key=lambda item: (
            _safe_float(item.get('profit_loss')) if item.get('profit_loss') is not None else float('-inf'),
            _safe_float(item.get('return_percent')) if item.get('return_percent') is not None else float('-inf'),
        ),
    )
    current_price_text = _format_currency(best.get('current_price'))
    reason_bits = []
    if best.get('profit_loss') is not None:
        reason_bits.append(f"unrealized gain {_format_currency(best.get('profit_loss'))}")
    if best.get('return_percent') is not None:
        reason_bits.append(f"return {_format_percent(best.get('return_percent'))}")
    reason_text = ' and '.join(reason_bits) if reason_bits else 'the strongest available performance in that sector'
    return (
        f"In your {matched_sector.name} holdings, {best.get('symbol')} ({best.get('company_name')}) is currently the most profitable stock. "
        f"It has current price {current_price_text}, invested amount {_format_currency(best.get('invested_amount'))}, "
        f"current value {_format_currency(best.get('current_value'))}, and {reason_text}."
    )


def _answer_quality(context: dict[str, Any]):
    quality = context.get('quality_snapshot') or []
    if quality:
        lead = quality[0]
        return (
            f"Based on the current quality view, {lead['name']} ranks strongest with average stock price "
            f"{_format_currency(lead.get('avg_price'))} and cluster {lead.get('cluster')}. "
            f"I can also compare quality by sector or explain specific stocks in that sector."
        )
    analytics = context.get('portfolio_analytics') or {}
    pe_rows = analytics.get('pe_comparison') or []
    if pe_rows:
        valid_rows = [item for item in pe_rows if item.get('pe_ratio') is not None]
        if valid_rows:
            best = min(valid_rows, key=lambda item: item.get('pe_ratio'))
            return f"Within your portfolio quality data, {best['symbol']} has the lowest tracked P/E at {_format_currency(best.get('pe_ratio'))}."
    return 'I could not build the quality answer right now because quality data is unavailable.'


def _answer_stock_lookup(context: dict[str, Any]):
    symbols = context.get('symbols') or {}
    if not symbols:
        return 'I could not identify a stock symbol from your question. Try a symbol like INFY.NS, TCS.NS, or RELIANCE.NS.'
    parts = []
    for symbol, snapshot in list(symbols.items())[:3]:
        parts.append(
            f"{symbol} is at {_format_currency(snapshot.get('current_price') or snapshot.get('last_value'))}, "
            f"P/E {_format_currency(snapshot.get('pe_ratio'))}, and 52-week range {_format_currency(snapshot.get('low_365d'))} to {_format_currency(snapshot.get('high_365d'))}."
        )
    return ' '.join(parts)


def _resolve_answer(question: str, route: str, context: dict[str, Any]):
    answer_map = {
        'market_trend': lambda: _answer_market_trend(context),
        'market_news': lambda: _answer_market_news(context),
        'portfolio': lambda: _answer_portfolio(context),
        'sentiment': lambda: _answer_sentiment(context),
        'recommendation': lambda: _answer_recommendation(context),
        'sector': lambda: _answer_sector(question, context),
        'sector_profitability': lambda: _answer_sector_profitability(question, context),
        'quality': lambda: _answer_quality(context),
        'stock_lookup': lambda: _answer_stock_lookup(context),
    }
    return answer_map.get(route, lambda: _answer_market_trend(context))()


def _route_actions(question: str, route: str):
    actions = []
    if route == 'portfolio':
        actions.append({'type': 'route', 'path': '/portfolios', 'label': 'Open Portfolios'})
    if route == 'sentiment':
        actions.append({'type': 'route', 'path': '/sentiment', 'label': 'Open Sentiment'})
    if route in {'sector', 'quality'}:
        actions.append({'type': 'route', 'path': '/sectors', 'label': 'Open Sectors'})
    if route == 'recommendation':
        actions.append({'type': 'route', 'path': '/recommendations', 'label': 'Open Recommendations'})
    if 'news' in (question or '').lower() or route == 'market_news':
        actions.append({'type': 'route', 'path': '/news', 'label': 'Open News'})
    return actions[:2]


def _fallback_answer(user):
    portfolio_count = Portfolio.objects.filter(user=user).count()
    holding_count = PortfolioStock.objects.filter(portfolio__user=user).count()
    if portfolio_count or holding_count:
        return (
            f"I could not complete the full analysis right now, but I can still see {portfolio_count} portfolios and "
            f"{holding_count} tracked holdings in your account. Please try the question again in a moment."
        )
    return 'I could not complete the full analysis right now. Please try again in a moment, or create a portfolio first so I can analyze your data.'


def generate_chatbot_reply(*, user, question: str, history: Any):
    clean_question = _sanitize_text(question, limit=700)
    clean_history = sanitize_history(history)
    decision = _guardrail_decision(clean_question)
    if not decision.allowed:
        return {
            'answer': decision.reason,
            'model': 'local-guardrail',
            'category': decision.category,
            'actions': [],
            'quick_prompts': DEFAULT_ROUTE_PROMPTS,
            'meta': {'history_used': len(clean_history)},
        }

    try:
        symbols = _extract_symbols(clean_question)
        route = _determine_route(clean_question, symbols)
        context = _build_context(clean_question, user, route)
        answer = _resolve_answer(clean_question, route, context)
        return {
            'answer': answer,
            'model': 'local-data-router',
            'category': 'finance',
            'route': route,
            'actions': _route_actions(clean_question, route),
            'quick_prompts': DEFAULT_ROUTE_PROMPTS,
            'meta': {
                'history_used': len(clean_history),
                'generated_at': timezone.now().isoformat(),
                'symbols': symbols,
            },
        }
    except Exception as exc:  # pragma: no cover - protective runtime fallback
        logger.exception('Chatbot generation failed: %s', exc)
        return {
            'answer': _fallback_answer(user),
            'model': 'local-fallback',
            'category': 'finance',
            'route': 'fallback',
            'actions': [{'type': 'route', 'path': '/portfolios', 'label': 'Open Portfolios'}],
            'quick_prompts': DEFAULT_ROUTE_PROMPTS,
            'meta': {
                'history_used': len(clean_history),
                'generated_at': timezone.now().isoformat(),
                'error': str(exc),
            },
        }
