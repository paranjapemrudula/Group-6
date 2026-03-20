import numpy as np
import pandas as pd
import yfinance as yf
from django.conf import settings
from django.core.cache import cache
from portfolios.models import Portfolio
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from stocks.models import PortfolioStock
from stocks.services import get_stock_snapshot

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
