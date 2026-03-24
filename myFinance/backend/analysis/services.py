import numpy as np
import pandas as pd
import yfinance as yf
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count
from portfolios.models import Portfolio
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from stocks.services import get_company_news
from stocks.models import PortfolioStock
from stocks.services import get_stock_snapshot

from .models import PortfolioSentimentSnapshot

def normalize_timeframe(timeframe: str):
    value = (timeframe or '').strip().upper().replace(' ', '')
    aliases = {
        '1HR': '1H',
        '1HOUR': '1H',
        '1DAY': '1D',
        '1MONTH': '1M',
        '3MONTH': '3M',
        '6MONTH': '6M',
    }
    return aliases.get(value, value or '1D')


def resolve_timeframe(timeframe: str):
    tf = normalize_timeframe(timeframe)
    mapping = {
        '1D': {
            'period': '30d',
            'interval': '1d',
            'recent_points': 7,
            'future_steps': 2,
        },
        '1H': {
            'period': '7d',
            'interval': '1h',
            'recent_points': 48,
            'future_steps': 2,
        },
        '1M': {
            'period': '24mo',
            'interval': '1mo',
            'recent_points': 12,
            'future_steps': 2,
        },
        '3M': {
            'period': '10y',
            'interval': '3mo',
            'recent_points': 16,
            'future_steps': 2,
        },
        '6M': {
            'period': '15y',
            'interval': '3mo',
            'recent_points': 12,
            'future_steps': 2,
        },
    }
    return mapping.get(tf, mapping['1D'])


def _format_timestamps(date_series: pd.Series, timeframe: str):
    tf = normalize_timeframe(timeframe)
    if tf == '1H':
        return date_series.dt.strftime('%Y-%m-%d %H:%M').tolist()
    if tf in {'1M', '3M', '6M'}:
        return date_series.dt.strftime('%Y-%m').tolist()
    return date_series.dt.strftime('%Y-%m-%d').tolist()


def fetch_historical_data(symbol: str, period: str = '1y', interval: str = '1d'):
    cache_key = f'analysis:history:{symbol}:{period}:{interval}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    history = yf.Ticker(symbol).history(period=period, interval=interval)
    if history.empty:
        return pd.DataFrame()

    frame = history.copy()
    frame = frame[['Close', 'Volume']].dropna()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()

    cache.set(cache_key, frame, timeout=getattr(settings, 'ANALYSIS_CACHE_TTL_SECONDS', 900))
    return frame
def _recent_frame(frame: pd.DataFrame, points: int):
    if points <= 0:
        return frame
    return frame.tail(points)


def _future_timestamps(last_date: pd.Timestamp, timeframe: str, steps: int):
    tf = normalize_timeframe(timeframe)
    if steps <= 0:
        return []

    future = []
    for step in range(1, steps + 1):
        if tf == '1H':
            future.append(last_date + pd.Timedelta(hours=step))
        elif tf == '1M':
            future.append(last_date + pd.DateOffset(months=step))
        elif tf == '3M':
            future.append(last_date + pd.DateOffset(months=3 * step))
        elif tf == '6M':
            future.append(last_date + pd.DateOffset(months=6 * step))
        else:
            future.append(last_date + pd.Timedelta(days=step))
    return future


def build_regression_payload(symbol: str, period: str = '1y', interval: str = '1d', timeframe: str = '1D'):
    frame = fetch_historical_data(symbol=symbol, period=period, interval=interval)
    if frame.empty or len(frame) < 2:
        return None

    config = resolve_timeframe(timeframe)
    frame = _recent_frame(frame, config['recent_points'])
    frame = frame.reset_index()
    frame['date'] = _format_timestamps(frame['Date'], timeframe=timeframe)
    frame['t_index'] = np.arange(len(frame))

    x = frame[['t_index']].values
    y = frame['Close'].values
    model = LinearRegression()
    model.fit(x, y)
    predictions_hist = model.predict(x)
    future_steps = config['future_steps']
    future_x = np.arange(len(frame), len(frame) + future_steps).reshape(-1, 1)
    predictions_future = model.predict(future_x) if future_steps > 0 else np.array([])
    future_dates = _future_timestamps(pd.to_datetime(frame['Date'].iloc[-1]), timeframe=timeframe, steps=future_steps)
    future_date_labels = _format_timestamps(pd.Series(pd.to_datetime(future_dates)), timeframe=timeframe) if future_dates else []

    dates = frame['date'].tolist() + future_date_labels
    actual_close = np.round(y, 2).tolist() + [None] * len(future_date_labels)
    predicted_close = np.round(np.concatenate([predictions_hist, predictions_future]), 2).tolist()

    return {
        'symbol': symbol,
        'timeframe': normalize_timeframe(timeframe),
        'dates': dates,
        'actual_close': actual_close,
        'predicted_close': predicted_close,
    }


def build_discount_payload(symbol: str, period: str = '1y', interval: str = '1d', timeframe: str = '1D'):
    frame = fetch_historical_data(symbol=symbol, period=period, interval=interval)
    if frame.empty or len(frame) < 2:
        return None

    config = resolve_timeframe(timeframe)
    df = frame.copy()
    df['avg_price'] = (df['Close'].rolling(10).mean() + df['Close']) / 2
    df = df.dropna()
    if df.empty:
        return None
    df = _recent_frame(df, config['recent_points'])

    df['discount_ratio'] = ((df['avg_price'] - df['Close']) / df['avg_price']) * 100
    df = df.reset_index()

    return {
        'symbol': symbol,
        'timeframe': normalize_timeframe(timeframe),
        'dates': _format_timestamps(df['Date'], timeframe=timeframe),
        'discount_ratio': np.round(df['discount_ratio'], 2).tolist(),
    }


def _cluster_name(avg_return: float, avg_volatility: float):
    if avg_return >= 0 and avg_volatility < 0.02:
        return 'Stable Growth'
    if avg_return >= 0 and avg_volatility >= 0.02:
        return 'Momentum High Volatility'
    if avg_return < 0 and avg_volatility < 0.02:
        return 'Slow Drawdown'
    return 'High Risk Downtrend'


def build_clustering_payload(symbol: str, period: str = '1y', interval: str = '1d', timeframe: str = '1D'):
    frame = fetch_historical_data(symbol=symbol, period=period, interval=interval)
    if frame.empty or len(frame) < 30:
        return None

    df = frame.copy()
    df['returns'] = df['Close'].pct_change()
    df['volatility'] = df['returns'].rolling(10).std()
    df['volume_change'] = df['Volume'].pct_change()
    df['ma20'] = df['Close'].rolling(20).mean()
    df['close_vs_ma20'] = (df['Close'] - df['ma20']) / df['ma20']
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    config = resolve_timeframe(timeframe)
    df = _recent_frame(df, max(config['recent_points'] * 3, 24))
    if len(df) < 6:
        return None

    features = df[['returns', 'volatility', 'volume_change', 'close_vs_ma20']]
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features.values)

    n_clusters = min(3, len(df))
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(scaled)
    df['cluster_id'] = labels

    cluster_labels = {}
    for cluster_id in sorted(df['cluster_id'].unique()):
        cluster_rows = df[df['cluster_id'] == cluster_id]
        name = _cluster_name(
            avg_return=float(cluster_rows['returns'].mean()),
            avg_volatility=float(cluster_rows['volatility'].mean()),
        )
        cluster_labels[int(cluster_id)] = name

    df = df.reset_index()
    points = []
    for idx, row in df.iterrows():
        cid = int(labels[idx])
        points.append(
            {
                'date': _format_timestamps(pd.Series([pd.to_datetime(row['Date'])]), timeframe=timeframe)[0],
                'x': round(float(row['returns']), 6),
                'y': round(float(row['volatility']), 6),
                'volume_change': round(float(row['volume_change']), 6),
                'close_vs_ma20': round(float(row['close_vs_ma20']), 6),
                'cluster_id': cid,
                'cluster_name': cluster_labels.get(cid, f'Cluster {cid}'),
            }
        )

    return {
        'symbol': symbol,
        'timeframe': normalize_timeframe(timeframe),
        'points': points,
        'cluster_id': [int(label) for label in labels.tolist()],
        'cluster_labels': cluster_labels,
    }
def _portfolio_cluster_name(avg_pe: float, avg_discount: float, avg_range_position: float):
    if avg_pe <= 18 and avg_discount > 0:
        return 'Value Watch'
    if avg_range_position >= 0.7:
        return 'Momentum Leaders'
    if avg_pe >= 28:
        return 'Premium Growth'
    return 'Balanced Core'


POSITIVE_NEWS_TERMS = {
    'beat',
    'beats',
    'surge',
    'surges',
    'growth',
    'grows',
    'gain',
    'gains',
    'profit',
    'profits',
    'strong',
    'bullish',
    'upgrade',
    'upgrades',
    'record',
    'records',
    'expansion',
    'expanded',
    'outperform',
    'outperforms',
    'optimistic',
    'partnership',
    'partnerships',
    'acquisition',
    'acquires',
    'rebound',
    'rebounds',
    'recovery',
}

NEGATIVE_NEWS_TERMS = {
    'miss',
    'misses',
    'drop',
    'drops',
    'fall',
    'falls',
    'loss',
    'losses',
    'weak',
    'bearish',
    'downgrade',
    'downgrades',
    'lawsuit',
    'probe',
    'investigation',
    'penalty',
    'default',
    'fraud',
    'cuts',
    'cut',
    'decline',
    'declines',
    'slump',
    'slumps',
    'risk',
    'warning',
    'warnings',
    'volatile',
    'volatility',
}


def _sentiment_label(score: float):
    if score >= 0.2:
        return 'Positive'
    if score <= -0.2:
        return 'Negative'
    return 'Neutral'


def _score_text_sentiment(text: str):
    content = (text or '').lower()
    if not content.strip():
        return 0.0

    positive_hits = sum(content.count(term) for term in POSITIVE_NEWS_TERMS)
    negative_hits = sum(content.count(term) for term in NEGATIVE_NEWS_TERMS)
    total_hits = positive_hits + negative_hits
    if total_hits == 0:
        return 0.0

    score = (positive_hits - negative_hits) / total_hits
    return round(float(max(-1.0, min(1.0, score))), 4)


def _score_news_article(article: dict, symbol: str, company_name: str):
    score = _score_text_sentiment(f"{article.get('title', '')} {article.get('summary', '')}")
    title = (article.get('title') or '').lower()
    summary = (article.get('summary') or '').lower()
    symbol_text = (symbol or '').lower().replace('.ns', '')
    company_text = (company_name or '').lower()

    mention_bonus = 0.0
    if symbol_text and symbol_text in title:
        mention_bonus += 0.1
    if company_text and company_text in title:
        mention_bonus += 0.1
    if company_text and company_text in summary:
        mention_bonus += 0.05

    adjusted = max(-1.0, min(1.0, score + mention_bonus))
    return round(float(adjusted), 4)


def _snapshot_payload(snapshot):
    if snapshot is None or not snapshot.payload:
        return None
    payload = dict(snapshot.payload)
    payload.setdefault('cached', True)
    payload.setdefault('generated_at', snapshot.updated_at.isoformat())
    return payload


def _summary_price_direction(rows):
    direction_counts = {'up': 0, 'down': 0, 'flat': 0}
    for row in rows:
        direction = row.get('price_direction') or 'flat'
        direction_counts[direction] = direction_counts.get(direction, 0) + 1

    if direction_counts['up'] > max(direction_counts['down'], direction_counts['flat']):
        return 'up', '↑'
    if direction_counts['down'] > max(direction_counts['up'], direction_counts['flat']):
        return 'down', '↓'
    return 'flat', '->'


def _confidence_score(*, stock_score: float, counts: dict, coverage_count: int):
    if coverage_count <= 0:
        return 0.0

    dominant_count = max(counts.values()) if counts else 0
    dominant_ratio = dominant_count / coverage_count if coverage_count else 0
    score_strength = abs(stock_score)

    confidence = 35.0
    confidence += min(25.0, coverage_count * 5.0)
    confidence += dominant_ratio * 25.0
    confidence += score_strength * 15.0
    return round(min(100.0, confidence), 2)


def build_portfolio_sentiment_payload(*, portfolio_id: int, user):
    portfolio = Portfolio.objects.filter(id=portfolio_id, user=user).first()
    if portfolio is None:
        return None

    snapshot = PortfolioSentimentSnapshot.objects.filter(portfolio=portfolio).first()

    holdings = list(
        PortfolioStock.objects.filter(portfolio=portfolio)
        .select_related('sector')
        .order_by('-added_at')
    )
    if not holdings:
        empty_payload = {
            'portfolio_id': portfolio.id,
            'portfolio_name': portfolio.name,
            'generated_at': timezone.now().isoformat(),
            'cached': False,
            'summary': {
                'average_sentiment_score': 0,
                'average_sentiment_percent': 50,
                'avg_sentiment': 50,
                'label': 'Neutral',
                'tracked_stocks': 0,
                'total_articles': 0,
                'positive_stocks': 0,
                'negative_stocks': 0,
                'neutral_stocks': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'price_direction': 'flat',
                'price_direction_emoji': '->',
            },
            'stocks': [],
            'headlines': [],
        }
        PortfolioSentimentSnapshot.objects.update_or_create(
            portfolio=portfolio,
            defaults={'payload': empty_payload},
        )
        return empty_payload

    stock_rows = []
    headline_rows = []
    successful_article_fetch = False
    overall_article_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}

    for holding in holdings:
        articles = get_company_news(symbol=holding.symbol, company_name=holding.company_name, limit=5)
        quote = get_stock_snapshot(holding.symbol)
        if articles:
            successful_article_fetch = True
        scored_articles = []
        stock_scores = []
        counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}

        for article in articles:
            sentiment_score = _score_news_article(article, symbol=holding.symbol, company_name=holding.company_name)
            label = _sentiment_label(sentiment_score)
            counts[label] += 1
            overall_article_counts[label] += 1
            stock_scores.append(sentiment_score)
            scored_article = {
                **article,
                'sentiment_score': sentiment_score,
                'sentiment_percent': round(((sentiment_score + 1) / 2) * 100, 2),
                'sentiment_label': label,
            }
            scored_articles.append(scored_article)
            headline_rows.append(
                {
                    'symbol': holding.symbol,
                    'company_name': holding.company_name,
                    **scored_article,
                }
            )

        stock_score = round(float(np.mean(stock_scores)), 4) if stock_scores else 0.0
        stock_label = _sentiment_label(stock_score)
        confidence_score = _confidence_score(
            stock_score=stock_score,
            counts=counts,
            coverage_count=len(scored_articles),
        )
        stock_rows.append(
            {
                'stock_id': holding.id,
                'symbol': holding.symbol,
                'company_name': holding.company_name,
                'sector': holding.sector.name,
                'sentiment_score': stock_score,
                'sentiment_percent': round(((stock_score + 1) / 2) * 100, 2),
                'sentiment_label': stock_label,
                'avg_sentiment': round(((stock_score + 1) / 2) * 100, 2),
                'coverage_count': len(scored_articles),
                'positive_articles': counts['Positive'],
                'negative_articles': counts['Negative'],
                'neutral_articles': counts['Neutral'],
                'positive_count': counts['Positive'],
                'negative_count': counts['Negative'],
                'neutral_count': counts['Neutral'],
                'confidence_score': confidence_score,
                'current_price': quote.get('current_price'),
                'previous_close': quote.get('previous_close'),
                'price_change': quote.get('price_change'),
                'price_direction': quote.get('price_direction'),
                'price_direction_emoji': quote.get('price_direction_emoji'),
                'articles': scored_articles,
            }
        )

    total_articles = sum(row['coverage_count'] for row in stock_rows)
    if not successful_article_fetch and snapshot is not None:
        cached = _snapshot_payload(snapshot)
        if cached:
            return cached

    average_score = round(float(np.mean([row['sentiment_score'] for row in stock_rows])), 4) if stock_rows else 0.0
    average_confidence_score = round(float(np.mean([row['confidence_score'] for row in stock_rows])), 2) if stock_rows else 0.0
    summary_label = _sentiment_label(average_score)
    positive_stocks = sum(1 for row in stock_rows if row['sentiment_label'] == 'Positive')
    negative_stocks = sum(1 for row in stock_rows if row['sentiment_label'] == 'Negative')
    neutral_stocks = sum(1 for row in stock_rows if row['sentiment_label'] == 'Neutral')
    summary_price_direction, summary_price_direction_emoji = _summary_price_direction(stock_rows)

    stock_rows.sort(key=lambda row: (row['sentiment_score'], row['coverage_count']), reverse=True)
    headline_rows.sort(
        key=lambda row: (
            abs(row.get('sentiment_score') or 0),
            row.get('published_at') or 0,
        ),
        reverse=True,
    )

    payload = {
        'portfolio_id': portfolio.id,
        'portfolio_name': portfolio.name,
        'generated_at': timezone.now().isoformat(),
        'cached': False,
        'summary': {
            'average_sentiment_score': average_score,
            'average_sentiment_percent': round(((average_score + 1) / 2) * 100, 2),
            'avg_sentiment': round(((average_score + 1) / 2) * 100, 2),
            'average_confidence_score': average_confidence_score,
            'label': summary_label,
            'tracked_stocks': len(stock_rows),
            'total_articles': total_articles,
            'positive_stocks': positive_stocks,
            'negative_stocks': negative_stocks,
            'neutral_stocks': neutral_stocks,
            'positive_count': overall_article_counts['Positive'],
            'negative_count': overall_article_counts['Negative'],
            'neutral_count': overall_article_counts['Neutral'],
            'price_direction': summary_price_direction,
            'price_direction_emoji': summary_price_direction_emoji,
        },
        'stocks': stock_rows,
        'headlines': headline_rows[:12],
    }
    PortfolioSentimentSnapshot.objects.update_or_create(
        portfolio=portfolio,
        defaults={'payload': payload},
    )
    return payload


def build_sentiment_overview_payload(*, user):
    portfolios = (
        Portfolio.objects.filter(user=user)
        .annotate(stock_count=Count('stocks'))
        .order_by('-created_at')
    )

    items = []
    for portfolio in portfolios:
        snapshot = getattr(portfolio, 'sentiment_snapshot', None)
        payload = snapshot.payload if snapshot and snapshot.payload else {}
        summary = payload.get('summary', {})
        items.append(
            {
                'portfolio_id': portfolio.id,
                'portfolio_name': portfolio.name,
                'created_at': portfolio.created_at.isoformat(),
                'stock_count': portfolio.stock_count,
                'has_snapshot': bool(payload),
                'generated_at': payload.get('generated_at'),
                'summary': {
                    'label': summary.get('label', 'Neutral'),
                    'avg_sentiment': summary.get('avg_sentiment', summary.get('average_sentiment_percent', 50)),
                    'positive_count': summary.get('positive_count', 0),
                    'neutral_count': summary.get('neutral_count', 0),
                    'negative_count': summary.get('negative_count', 0),
                    'price_direction': summary.get('price_direction', 'flat'),
                    'price_direction_emoji': summary.get('price_direction_emoji', '->'),
                    'tracked_stocks': summary.get('tracked_stocks', portfolio.stock_count),
                    'total_articles': summary.get('total_articles', 0),
                },
            }
        )

    return {
        'portfolio_count': len(items),
        'items': items,
    }


def build_company_sentiment_payload(*, symbol: str, company_name: str = ''):
    normalized_symbol = (symbol or '').strip().upper()
    normalized_company_name = (company_name or '').strip()
    if not normalized_symbol:
        return None

    articles = get_company_news(symbol=normalized_symbol, company_name=normalized_company_name, limit=8)
    quote = get_stock_snapshot(normalized_symbol)

    scored_articles = []
    counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    stock_scores = []

    for article in articles:
        sentiment_score = _score_news_article(article, symbol=normalized_symbol, company_name=normalized_company_name)
        label = _sentiment_label(sentiment_score)
        counts[label] += 1
        stock_scores.append(sentiment_score)
        scored_articles.append(
            {
                **article,
                'sentiment_score': sentiment_score,
                'sentiment_percent': round(((sentiment_score + 1) / 2) * 100, 2),
                'sentiment_label': label,
            }
        )

    average_score = round(float(np.mean(stock_scores)), 4) if stock_scores else 0.0
    summary_label = _sentiment_label(average_score)
    confidence_score = _confidence_score(
        stock_score=average_score,
        counts=counts,
        coverage_count=len(scored_articles),
    )
    scored_articles.sort(
        key=lambda row: (
            abs(row.get('sentiment_score') or 0),
            row.get('published_at') or 0,
        ),
        reverse=True,
    )

    return {
        'symbol': normalized_symbol,
        'company_name': normalized_company_name or normalized_symbol,
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'label': summary_label,
            'avg_sentiment': round(((average_score + 1) / 2) * 100, 2),
            'average_sentiment_score': average_score,
            'confidence_score': confidence_score,
            'positive_count': counts['Positive'],
            'neutral_count': counts['Neutral'],
            'negative_count': counts['Negative'],
            'total_articles': len(scored_articles),
            'price_direction': quote.get('price_direction', 'flat'),
            'price_direction_emoji': quote.get('price_direction_emoji', '->'),
            'current_price': quote.get('current_price'),
            'previous_close': quote.get('previous_close'),
            'price_change': quote.get('price_change'),
        },
        'articles': scored_articles,
    }


def build_portfolio_analytics_payload(*, portfolio_id: int, user):
    portfolio = Portfolio.objects.filter(id=portfolio_id, user=user).first()
    if portfolio is None:
        return None

    holdings = list(
        PortfolioStock.objects.filter(portfolio=portfolio)
        .select_related('sector')
        .order_by('-added_at')
    )
    if not holdings:
        return {
            'portfolio_id': portfolio.id,
            'portfolio_name': portfolio.name,
            'pe_comparison': [],
            'clustering': {'points': [], 'cluster_labels': {}},
        }

    pe_rows = []
    cluster_rows = []

    for holding in holdings:
        quote = get_stock_snapshot(holding.symbol)
        pe_ratio = quote.get('pe_ratio')
        last_value = quote.get('last_value')
        discount_ratio = quote.get('discount_ratio')
        high_365d = quote.get('high_365d')
        low_365d = quote.get('low_365d')

        pe_rows.append(
            {
                'symbol': holding.symbol,
                'company_name': holding.company_name,
                'sector': holding.sector.name,
                'pe_ratio': pe_ratio,
            }
        )

        if last_value is None:
            continue

        range_position = 0.5
        if high_365d is not None and low_365d is not None and high_365d > low_365d:
            range_position = (last_value - low_365d) / (high_365d - low_365d)

        cluster_rows.append(
            {
                'symbol': holding.symbol,
                'company_name': holding.company_name,
                'sector': holding.sector.name,
                'pe_ratio': float(pe_ratio) if pe_ratio is not None else 0.0,
                'discount_ratio': float(discount_ratio) if discount_ratio is not None else 0.0,
                'last_value': float(last_value),
                'range_position': float(range_position),
            }
        )

    if len(cluster_rows) >= 2:
        frame = pd.DataFrame(cluster_rows)
        features = frame[['pe_ratio', 'discount_ratio', 'range_position', 'last_value']]
        scaled = StandardScaler().fit_transform(features)
        cluster_count = min(3, len(frame))
        labels = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit_predict(scaled)
        frame['cluster_id'] = labels

        cluster_labels = {}
        for cluster_id in sorted(frame['cluster_id'].unique()):
            rows = frame[frame['cluster_id'] == cluster_id]
            cluster_labels[int(cluster_id)] = _portfolio_cluster_name(
                avg_pe=float(rows['pe_ratio'].mean()),
                avg_discount=float(rows['discount_ratio'].mean()),
                avg_range_position=float(rows['range_position'].mean()),
            )

        points = []
        for row in frame.to_dict(orient='records'):
            cluster_id = int(row['cluster_id'])
            points.append(
                {
                    'symbol': row['symbol'],
                    'company_name': row['company_name'],
                    'sector': row['sector'],
                    'x': round(float(row['pe_ratio']), 4),
                    'y': round(float(row['discount_ratio']), 4),
                    'last_value': round(float(row['last_value']), 2),
                    'range_position': round(float(row['range_position']), 4),
                    'cluster_id': cluster_id,
                    'cluster_name': cluster_labels[cluster_id],
                }
            )
    else:
        points = []
        cluster_labels = {}

    return {
        'portfolio_id': portfolio.id,
        'portfolio_name': portfolio.name,
        'pe_comparison': pe_rows,
        'clustering': {
            'points': points,
            'cluster_labels': cluster_labels,
        },
    }
