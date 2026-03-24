from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from django.db import models

from .models import Sector, SectorAlias, SectorClassificationLog, StockUniverse

CURATED_SECTOR_TICKERS = {
    'Technology': [
        {'symbol': 'TCS.NS', 'company_name': 'Tata Consultancy Services'},
        {'symbol': 'INFY.NS', 'company_name': 'Infosys'},
        {'symbol': 'HCLTECH.NS', 'company_name': 'HCL Technologies'},
        {'symbol': 'WIPRO.NS', 'company_name': 'Wipro'},
    ],
    'Finance': [
        {'symbol': 'HDFCBANK.NS', 'company_name': 'HDFC Bank'},
        {'symbol': 'ICICIBANK.NS', 'company_name': 'ICICI Bank'},
        {'symbol': 'SBIN.NS', 'company_name': 'State Bank of India'},
        {'symbol': 'KOTAKBANK.NS', 'company_name': 'Kotak Mahindra Bank'},
    ],
    'Healthcare': [
        {'symbol': 'SUNPHARMA.NS', 'company_name': 'Sun Pharmaceutical'},
        {'symbol': 'DRREDDY.NS', 'company_name': "Dr. Reddy's Laboratories"},
        {'symbol': 'CIPLA.NS', 'company_name': 'Cipla'},
        {'symbol': 'DIVISLAB.NS', 'company_name': "Divi's Laboratories"},
    ],
    'Energy': [
        {'symbol': 'RELIANCE.NS', 'company_name': 'Reliance Industries'},
        {'symbol': 'ONGC.NS', 'company_name': 'Oil and Natural Gas Corporation'},
        {'symbol': 'BPCL.NS', 'company_name': 'Bharat Petroleum'},
        {'symbol': 'IOC.NS', 'company_name': 'Indian Oil Corporation'},
    ],
}

CURATED_SYMBOL_TO_SECTOR = {
    stock['symbol']: sector
    for sector, stocks in CURATED_SECTOR_TICKERS.items()
    for stock in stocks
}

SECTOR_NORMALIZATION = {
    'financial services': 'Finance',
    'information technology': 'Technology',
    'it': 'Technology',
    'healthcare': 'Healthcare',
    'oil gas & consumable fuels': 'Energy',
    'power': 'Energy',
    'automobile and auto components': 'Automobile',
    'fast moving consumer goods': 'FMCG',
    'consumer services': 'Consumer Services',
    'consumer durables': 'Consumer Durables',
    'capital goods': 'Industrials',
    'construction materials': 'Materials',
    'metals & mining': 'Materials',
    'telecommunication': 'Telecom',
    'realty': 'Real Estate',
    'services': 'Services',
}

SECTOR_VECTOR_READY_KEYWORDS = {
    'Technology': ['software', 'technology', 'semiconductor', 'cloud', 'ai', 'it services', 'platform'],
    'Finance': ['bank', 'insurance', 'financial', 'asset management', 'payments', 'fintech', 'lending'],
    'Healthcare': ['healthcare', 'pharma', 'biotech', 'medical', 'hospital', 'diagnostic'],
    'Energy': ['energy', 'oil', 'gas', 'power', 'renewable', 'utility'],
    'Automobile': ['automobile', 'vehicle', 'auto', 'mobility', 'ev'],
    'FMCG': ['consumer staples', 'beverages', 'packaged food', 'household', 'personal care'],
    'Consumer Services': ['retail', 'consumer services', 'travel', 'hospitality', 'entertainment'],
    'Consumer Durables': ['appliances', 'electronics', 'durables', 'home goods'],
    'Industrials': ['industrial', 'engineering', 'manufacturing', 'machinery', 'logistics'],
    'Materials': ['metals', 'mining', 'materials', 'cement', 'chemicals'],
    'Telecom': ['telecom', 'wireless', 'communications', 'network'],
    'Real Estate': ['real estate', 'property', 'housing', 'reit'],
}

LANDING_TOP_STOCKS = [
    {'symbol': 'TCS.NS', 'company_name': 'Tata Consultancy Services'},
    {'symbol': 'INFY.NS', 'company_name': 'Infosys'},
    {'symbol': 'RELIANCE.NS', 'company_name': 'Reliance Industries'},
    {'symbol': 'HDFCBANK.NS', 'company_name': 'HDFC Bank'},
    {'symbol': 'ICICIBANK.NS', 'company_name': 'ICICI Bank'},
]

NEWS_FALLBACK_IMAGES = {
    'stock market india': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
    'investing': 'https://images.unsplash.com/photo-1559526324-593bc073d938?auto=format&fit=crop&w=900&q=80',
}


def _as_float(value: Any):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_value(value: float | None):
    if value is None:
        return None
    return round(value, 2)


def _quote_symbol_candidates(symbol: str):
    normalized = (symbol or '').strip().upper()
    if not normalized:
        return []
    candidates = [normalized]
    if '.' not in normalized:
        inferred_markets = list(
            StockUniverse.objects.filter(symbol=normalized, is_active=True)
            .values_list('market', flat=True)
            .distinct()
        )
        if StockUniverse.MARKET_INDIA in inferred_markets:
            candidates.extend([f'{normalized}.NS', f'{normalized}.BO'])
        if StockUniverse.MARKET_USA not in inferred_markets:
            candidates.extend([f'{normalized}.NS', f'{normalized}.BO'])

    deduped = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def _extract_quote_from_candidate(symbol: str):
    empty_payload = {
        'symbol': symbol,
        'avg_price': None,
        'current_price': None,
        'last_value': None,
        'previous_close': None,
        'price_change': None,
        'price_direction': 'flat',
        'price_direction_emoji': '->',
        'pe_ratio': None,
        'high_365d': None,
        'low_365d': None,
        'discount_ratio': None,
    }

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = getattr(ticker, 'fast_info', {}) or {}
    except Exception:
        return empty_payload

    current_price = _as_float(info.get('currentPrice')) or _as_float(fast_info.get('lastPrice'))
    day_high = _as_float(info.get('dayHigh')) or _as_float(fast_info.get('dayHigh'))
    day_low = _as_float(info.get('dayLow')) or _as_float(fast_info.get('dayLow'))
    previous_close = _as_float(info.get('previousClose')) or _as_float(fast_info.get('previousClose'))
    pe_ratio = _as_float(info.get('trailingPE')) or _as_float(info.get('forwardPE'))
    high_365d = _as_float(info.get('fiftyTwoWeekHigh')) or _as_float(fast_info.get('yearHigh'))
    low_365d = _as_float(info.get('fiftyTwoWeekLow')) or _as_float(fast_info.get('yearLow'))

    if any(
        value is None
        for value in [current_price, previous_close, day_high, day_low, high_365d, low_365d]
    ):
        try:
            history = ticker.history(period='1y', interval='1d', auto_adjust=False)
        except Exception:
            history = None

        if history is not None and not history.empty:
            close_series = history['Close'].dropna() if 'Close' in history else pd.Series(dtype='float64')
            high_series = history['High'].dropna() if 'High' in history else pd.Series(dtype='float64')
            low_series = history['Low'].dropna() if 'Low' in history else pd.Series(dtype='float64')

            if current_price is None and not close_series.empty:
                current_price = _as_float(close_series.iloc[-1])
            if previous_close is None and len(close_series) > 1:
                previous_close = _as_float(close_series.iloc[-2])
            if day_high is None and not high_series.empty:
                day_high = _as_float(high_series.iloc[-1])
            if day_low is None and not low_series.empty:
                day_low = _as_float(low_series.iloc[-1])
            if high_365d is None and not high_series.empty:
                high_365d = _as_float(high_series.max())
            if low_365d is None and not low_series.empty:
                low_365d = _as_float(low_series.min())

    avg_price = None
    if day_high is not None and day_low is not None:
        avg_price = (day_high + day_low) / 2
    elif current_price is not None and previous_close is not None:
        avg_price = (current_price + previous_close) / 2

    discount_ratio = None
    if avg_price and current_price is not None:
        discount_ratio = ((avg_price - current_price) / avg_price) * 100

    price_change = None
    price_direction = 'flat'
    price_direction_emoji = '->'
    if current_price is not None and previous_close is not None:
        price_change = current_price - previous_close
        if price_change > 0:
            price_direction = 'up'
            price_direction_emoji = '↑'
        elif price_change < 0:
            price_direction = 'down'
            price_direction_emoji = '↓'

    payload = {
        'symbol': symbol,
        'avg_price': _round_value(avg_price),
        'current_price': _round_value(current_price),
        'last_value': _round_value(current_price),
        'previous_close': _round_value(previous_close),
        'price_change': _round_value(price_change),
        'price_direction': price_direction,
        'price_direction_emoji': price_direction_emoji,
        'pe_ratio': _round_value(pe_ratio),
        'high_365d': _round_value(high_365d),
        'low_365d': _round_value(low_365d),
        'discount_ratio': _round_value(discount_ratio),
    }
    return payload if payload['current_price'] is not None else empty_payload


def _extract_quote(symbol: str):
    candidates = _quote_symbol_candidates(symbol)
    requested_symbol = (symbol or '').strip().upper()
    last_payload = None
    for candidate in candidates:
        payload = _extract_quote_from_candidate(candidate)
        if payload.get('current_price') is not None:
            payload['actual_symbol'] = candidate
            payload['symbol'] = requested_symbol or candidate
            return payload
        last_payload = payload
    if last_payload:
        last_payload['actual_symbol'] = last_payload.get('symbol')
        last_payload['symbol'] = requested_symbol or last_payload.get('symbol')
        return last_payload
    return {
        'symbol': requested_symbol or symbol,
        'actual_symbol': requested_symbol or symbol,
        'avg_price': None,
        'current_price': None,
        'last_value': None,
        'previous_close': None,
        'price_change': None,
        'price_direction': 'flat',
        'price_direction_emoji': '->',
        'pe_ratio': None,
        'high_365d': None,
        'low_365d': None,
        'discount_ratio': None,
    }


def get_stock_suggestions(query: str, limit: int = 10):
    q = (query or '').strip()
    if not q:
        return []

    q_upper = q.upper()
    suggestions = []
    seen_symbols = set()

    db_matches = (
        StockUniverse.objects.filter(is_active=True)
        .filter(models.Q(symbol__icontains=q) | models.Q(company_name__icontains=q))
        .select_related('sector')
        .order_by('market', 'company_name')[:limit]
    )
    for stock in db_matches:
        suggestions.append(
            {
                'symbol': stock.symbol,
                'company_name': stock.company_name,
                'sector': stock.sector.name,
                'market': stock.market,
            }
        )
        seen_symbols.add(stock.symbol)

    if suggestions:
        return suggestions[:limit]

    for sector, stocks in CURATED_SECTOR_TICKERS.items():
        for stock in stocks:
            symbol = stock['symbol']
            company_name = stock['company_name']
            if q_upper in symbol.upper() or q_upper in company_name.upper():
                suggestions.append(
                    {
                        'symbol': symbol,
                        'company_name': company_name,
                        'sector': sector,
                    }
                )
                seen_symbols.add(symbol)

    if suggestions:
        return suggestions[:limit]

    try:
        search = yf.Search(query=q, max_results=limit, news_count=0)
        quotes = getattr(search, 'quotes', []) or []
        for quote in quotes:
            symbol = quote.get('symbol')
            if not symbol or symbol in seen_symbols:
                continue
            company_name = quote.get('shortname') or quote.get('longname') or symbol
            suggestions.append(
                {
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': CURATED_SYMBOL_TO_SECTOR.get(symbol),
                }
            )
            seen_symbols.add(symbol)
            if len(suggestions) >= limit:
                break
    except Exception:
        # Curated list already covers fallback.
        pass

    return suggestions[:limit]


def get_stock_snapshot(symbol: str):
    return _extract_quote(symbol)


def get_stocks_by_sector(sector_name: str):
    db_rows = list(
        StockUniverse.objects.filter(sector__name=sector_name, is_active=True)
        .select_related('sector')
        .order_by('company_name')
        .values('symbol', 'company_name', 'market')
    )
    if db_rows:
        rows = []
        for stock in db_rows:
            quote = _extract_quote(stock['symbol'])
            rows.append(
                {
                    'symbol': stock['symbol'],
                    'company_name': stock['company_name'],
                    'sector': sector_name,
                    'market': stock['market'],
                    'avg_price': quote['avg_price'],
                    'current_price': quote['current_price'],
                    'pe_ratio': quote['pe_ratio'],
                    'discount_ratio': quote['discount_ratio'],
                }
            )
        return rows

    rows = []
    for stock in CURATED_SECTOR_TICKERS.get(sector_name, []):
        quote = _extract_quote(stock['symbol'])
        rows.append(
            {
                'symbol': stock['symbol'],
                'company_name': stock['company_name'],
                'sector': sector_name,
                'avg_price': quote['avg_price'],
                'current_price': quote['current_price'],
                'pe_ratio': quote['pe_ratio'],
                'discount_ratio': quote['discount_ratio'],
            }
        )
    return rows


def get_market_overview():
    top_stocks = []
    for stock in LANDING_TOP_STOCKS:
        quote = _extract_quote(stock['symbol'])
        top_stocks.append(
            {
                'symbol': stock['symbol'],
                'company_name': stock['company_name'],
                'last_value': quote['last_value'],
                'pe_ratio': quote['pe_ratio'],
                'high_365d': quote['high_365d'],
                'low_365d': quote['low_365d'],
            }
        )

    return {'top_stocks': top_stocks}


def get_market_news(limit: int = 12):
    queries = ['stock market india', 'investing']
    items = []
    seen_links = set()

    for query in queries:
        try:
            search = yf.Search(query=query, news_count=10)
            news = getattr(search, 'news', []) or []
            for item in news:
                link = item.get('link')
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                image_url = None
                thumbnail = item.get('thumbnail') or {}
                resolutions = thumbnail.get('resolutions') or []
                if resolutions:
                    image_url = resolutions[-1].get('url')
                if not image_url:
                    image_url = NEWS_FALLBACK_IMAGES.get(query)
                items.append(
                    {
                        'title': item.get('title') or 'Market update',
                        'summary': item.get('summary') or item.get('description') or '',
                        'publisher': item.get('publisher') or 'Market Source',
                        'link': link,
                        'published_at': item.get('providerPublishTime'),
                        'type': query,
                        'image_url': image_url,
                    }
                )
        except Exception:
            continue

    items = sorted(items, key=lambda row: row.get('published_at') or 0, reverse=True)
    return items[:limit]


def get_company_news(symbol: str, company_name: str = '', limit: int = 6):
    queries = [symbol]
    if company_name:
        queries.append(company_name)

    items = []
    seen_links = set()

    for query in queries:
        try:
            search = yf.Search(query=query, news_count=max(limit, 8))
            news = getattr(search, 'news', []) or []
        except Exception:
            continue

        for item in news:
            link = item.get('link')
            if not link or link in seen_links:
                continue

            seen_links.add(link)
            thumbnail = item.get('thumbnail') or {}
            resolutions = thumbnail.get('resolutions') or []
            image_url = resolutions[-1].get('url') if resolutions else None

            items.append(
                {
                    'symbol': symbol,
                    'company_name': company_name or symbol,
                    'title': item.get('title') or f'{symbol} market update',
                    'summary': item.get('summary') or item.get('description') or '',
                    'publisher': item.get('publisher') or 'Market Source',
                    'link': link,
                    'published_at': item.get('providerPublishTime'),
                    'image_url': image_url,
                }
            )
            if len(items) >= limit:
                break

        if len(items) >= limit:
            break

    items = sorted(items, key=lambda row: row.get('published_at') or 0, reverse=True)
    return items[:limit]


def normalize_sector_name(raw_value: str):
    value = (raw_value or '').strip()
    if not value:
        return 'Uncategorized'
    normalized = SECTOR_NORMALIZATION.get(value.lower())
    return normalized or value


def classify_sector_label(*, raw_label: str = '', company_name: str = '', summary_text: str = ''):
    raw_label = (raw_label or '').strip()
    normalized_input = raw_label.lower()

    if raw_label:
        alias = SectorAlias.objects.filter(alias_name__iexact=raw_label).select_related('sector').first()
        if alias:
            return {
                'sector_name': alias.sector.name,
                'classification_source': StockUniverse.CLASSIFICATION_ALIAS,
                'classification_confidence': 98.0,
                'raw_sector_label': raw_label,
                'notes': f'Alias match for "{raw_label}".',
            }

        normalized_name = SECTOR_NORMALIZATION.get(normalized_input)
        if normalized_name:
            return {
                'sector_name': normalized_name,
                'classification_source': StockUniverse.CLASSIFICATION_RULE,
                'classification_confidence': 94.0,
                'raw_sector_label': raw_label,
                'notes': f'Normalized source label "{raw_label}".',
            }

    combined_text = f'{company_name} {raw_label} {summary_text}'.strip().lower()
    best_sector = None
    best_score = 0
    for sector_name, keywords in SECTOR_VECTOR_READY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in combined_text)
        if score > best_score:
            best_score = score
            best_sector = sector_name

    if best_sector:
        confidence = min(85.0, 55.0 + (best_score * 8.0))
        return {
            'sector_name': best_sector,
            'classification_source': StockUniverse.CLASSIFICATION_VECTOR,
            'classification_confidence': confidence,
            'raw_sector_label': raw_label,
            'notes': 'Keyword-based semantic fallback that is ready to be replaced with vector similarity later.',
        }

    return {
        'sector_name': 'Uncategorized',
        'classification_source': StockUniverse.CLASSIFICATION_UNKNOWN,
        'classification_confidence': 20.0 if raw_label else 0.0,
        'raw_sector_label': raw_label,
        'notes': 'No reliable sector signal was available.',
    }


def import_stock_universe_file(*, file_path: str, market: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f'File not found: {file_path}')

    suffix = path.suffix.lower()
    if suffix == '.csv':
        frame = pd.read_csv(path)
    elif suffix in {'.xlsx', '.xls'}:
        frame = pd.read_excel(path)
    else:
        raise ValueError('Unsupported file type. Use CSV or Excel.')

    frame.columns = [str(col).strip() for col in frame.columns]
    records = frame.to_dict(orient='records')
    imported_count = 0

    for row in records:
        symbol = (
            row.get('Symbol')
            or row.get('SYMBOL')
            or row.get('Ticker')
            or row.get('ticker')
        )
        company_name = (
            row.get('Company Name')
            or row.get('Company')
            or row.get('company_name')
            or row.get('Name')
        )
        sector_raw = (
            row.get('Industry')
            or row.get('Sector')
            or row.get('sector')
            or row.get('industry')
        )

        if not symbol or not company_name:
            continue

        classification = classify_sector_label(
            raw_label=str(sector_raw or '').strip(),
            company_name=str(company_name).strip(),
        )
        sector_name = classification['sector_name']
        sector, _ = Sector.objects.get_or_create(name=sector_name)

        stock, _ = StockUniverse.objects.update_or_create(
            symbol=str(symbol).strip().upper(),
            market=market,
            defaults={
                'company_name': str(company_name).strip(),
                'sector': sector,
                'raw_sector_label': classification['raw_sector_label'],
                'series': str(row.get('Series') or row.get('series') or '').strip(),
                'isin_code': str(row.get('ISIN Code') or row.get('ISIN') or '').strip(),
                'source_file': path.name,
                'classification_source': classification['classification_source'],
                'classification_confidence': classification['classification_confidence'],
                'is_active': True,
            },
        )
        SectorClassificationLog.objects.create(
            stock_symbol=stock.symbol,
            company_name=stock.company_name,
            market=stock.market,
            raw_label=classification['raw_sector_label'],
            predicted_sector=sector,
            classification_source=classification['classification_source'],
            confidence=classification['classification_confidence'],
            notes=classification['notes'],
        )
        imported_count += 1

    return {
        'market': market,
        'source_file': path.name,
        'imported_count': imported_count,
    }
