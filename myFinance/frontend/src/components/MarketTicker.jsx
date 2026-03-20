import { useEffect, useMemo, useState } from 'react'
import { publicApi } from '../lib/api'

function MarketTicker() {
  const [overview, setOverview] = useState({ top_stocks: [] })

  useEffect(() => {
    const loadTicker = async () => {
      try {
        const response = await publicApi.get('/api/market/overview/')
        setOverview(response.data || { top_stocks: [] })
      } catch {
        setOverview({ top_stocks: [] })
      }
    }

    loadTicker()
    const timer = setInterval(loadTicker, 20000)
    return () => clearInterval(timer)
  }, [])

  const tickerItems = useMemo(() => {
    const stockItems = (overview.top_stocks || []).map((stock) => ({
      label: stock.symbol,
      value: stock.last_value ?? '-',
      meta: stock.pe_ratio !== null && stock.pe_ratio !== undefined ? `P/E ${stock.pe_ratio}` : 'Live',
    }))

    return stockItems.length
      ? stockItems
      : [
          { label: 'MARKET', value: 'Live data loading', meta: 'Please wait' },
          { label: 'STOCKS', value: 'Watch the market', meta: 'Live' },
        ]
  }, [overview])

  const doubledItems = [...tickerItems, ...tickerItems]

  return (
    <div className="market-ticker-bar" aria-label="Live market ticker">
      <div className="market-ticker-track">
        {doubledItems.map((item, index) => (
          <div key={`${item.label}-${index}`} className="market-ticker-item">
            <strong>{item.label}</strong>
            <span>{item.value}</span>
            <small>{item.meta}</small>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MarketTicker
