from typing import Any

import yfinance as yf

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


def _extract_quote(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = getattr(ticker, 'fast_info', {}) or {}
    except Exception:
        return {
            'symbol': symbol,
            'avg_price': None,
            'current_price': None,
            'last_value': None,
            'pe_ratio': None,
            'high_365d': None,
            'low_365d': None,
            'discount_ratio': None,
        }

    current_price = _as_float(info.get('currentPrice')) or _as_float(fast_info.get('lastPrice'))
    day_high = _as_float(info.get('dayHigh')) or _as_float(fast_info.get('dayHigh'))
    day_low = _as_float(info.get('dayLow')) or _as_float(fast_info.get('dayLow'))
    previous_close = _as_float(info.get('previousClose')) or _as_float(fast_info.get('previousClose'))
    pe_ratio = _as_float(info.get('trailingPE')) or _as_float(info.get('forwardPE'))
    high_365d = _as_float(info.get('fiftyTwoWeekHigh')) or _as_float(fast_info.get('yearHigh'))
    low_365d = _as_float(info.get('fiftyTwoWeekLow')) or _as_float(fast_info.get('yearLow'))

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

    return {
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


def get_stock_suggestions(query: str, limit: int = 10):
    q = (query or '').strip()
    if not q:
        return []

    q_upper = q.upper()
    suggestions = []
    seen_symbols = set()

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
