import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Bar, Line, Scatter } from 'react-chartjs-2'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend)

function PortfolioDetailPage() {
  const timeframeOptions = ['1D', '1H', '1M']
  const { id } = useParams()
  const portfolioInsightsRef = useRef(null)
  const [portfolio, setPortfolio] = useState(null)
  const [stocks, setStocks] = useState([])
  const [sectors, setSectors] = useState([])
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [editingStockId, setEditingStockId] = useState(null)
  const [quoteBySymbol, setQuoteBySymbol] = useState({})
  const [analysisPanel, setAnalysisPanel] = useState({
    symbol: '',
    type: '',
    loading: false,
    error: '',
    payload: null,
  })
  const [analysisTimeframe, setAnalysisTimeframe] = useState('1D')
  const [portfolioInsights, setPortfolioInsights] = useState({
    section: '',
    loading: false,
    error: '',
    payload: null,
  })
  const [editingForm, setEditingForm] = useState({
    symbol: '',
    company_name: '',
    sector_id: '',
    buy_price: '',
    quantity: '',
  })
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const sectorMap = useMemo(() => {
    const map = {}
    sectors.forEach((sector) => {
      map[sector.name] = sector.id
    })
    return map
  }, [sectors])

  const loadData = async () => {
    try {
      const [portfolioResponse, stocksResponse, sectorsResponse] = await Promise.all([
        api.get(`/api/portfolios/${id}/`),
        api.get(`/api/portfolios/${id}/stocks/`),
        api.get('/api/sectors/'),
      ])
      setPortfolio(portfolioResponse.data)
      setStocks(stocksResponse.data)
      setSectors(sectorsResponse.data)
    } catch {
      setError('Failed to load portfolio details.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id])

  useEffect(() => {
    const fetchQuotes = async () => {
      const uniqueSymbols = [...new Set(stocks.map((stock) => stock.symbol).filter(Boolean))]
      if (uniqueSymbols.length === 0) {
        setQuoteBySymbol({})
        return
      }

      try {
        const responses = await Promise.all(
          uniqueSymbols.map((symbol) => api.get(`/api/stocks/quote/?symbol=${encodeURIComponent(symbol)}`))
        )
        const nextMap = {}
        responses.forEach((response) => {
          if (response?.data?.symbol) {
            nextMap[response.data.symbol] = response.data
          }
        })
        setQuoteBySymbol(nextMap)
      } catch {
        setQuoteBySymbol({})
      }
    }

    fetchQuotes()
  }, [stocks])

  useEffect(() => {
    if (query.trim().length < 1) {
      setSuggestions([])
      return
    }

    const timer = setTimeout(async () => {
      try {
        const response = await api.get(`/api/stocks/suggest/?q=${encodeURIComponent(query.trim())}`)
        setSuggestions(response.data)
      } catch {
        setSuggestions([])
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [query])

  const handleAddFromSuggestion = async (item) => {
    setAdding(true)
    setError('')
    try {
      let resolvedSectorId = item.sector && sectorMap[item.sector] ? Number(sectorMap[item.sector]) : null
      if (!resolvedSectorId && sectors.length > 0) {
        resolvedSectorId = Number(sectors[0].id)
      }

      const quoteResponse = await api.get(`/api/stocks/quote/?symbol=${encodeURIComponent(item.symbol)}`)
      const quotePrice = quoteResponse.data.current_price || quoteResponse.data.avg_price || 0

      const payload = {
        symbol: item.symbol.trim().toUpperCase(),
        company_name: item.company_name,
        sector_id: resolvedSectorId,
        buy_price: Number(quotePrice).toFixed(2),
        quantity: 1,
      }

      const response = await api.post(`/api/portfolios/${id}/stocks/`, payload)
      setStocks((prev) => [response.data, ...prev])
      setQuery('')
      setSuggestions([])
    } catch {
      setError('Could not add stock from suggestion.')
    } finally {
      setAdding(false)
    }
  }

  const handleDeleteStock = async (stockId) => {
    try {
      await api.delete(`/api/portfolios/${id}/stocks/${stockId}/`)
      setStocks((prev) => prev.filter((item) => item.id !== stockId))
    } catch {
      setError('Could not delete stock.')
    }
  }

  const handleStartEdit = (stock) => {
    setEditingStockId(stock.id)
    setEditingForm({
      symbol: stock.symbol,
      company_name: stock.company_name,
      sector_id: String(sectorMap[stock.sector_name] || ''),
      buy_price: String(stock.buy_price),
      quantity: String(stock.quantity),
    })
  }

  const handleSaveEdit = async (stockId) => {
    try {
      const payload = {
        symbol: editingForm.symbol.trim().toUpperCase(),
        company_name: editingForm.company_name.trim(),
        sector_id: Number(editingForm.sector_id),
        buy_price: editingForm.buy_price,
        quantity: Number(editingForm.quantity),
      }
      const response = await api.put(`/api/portfolios/${id}/stocks/${stockId}/`, payload)
      setStocks((prev) => prev.map((item) => (item.id === stockId ? response.data : item)))
      setEditingStockId(null)
    } catch {
      setError('Could not update stock.')
    }
  }

  const handleOpenAnalysis = async (symbol, type, timeframe = analysisTimeframe) => {
    const typeToEndpoint = {
      regression: '/api/analyze/regression/',
      discount: '/api/analyze/discount/',
      clustering: '/api/analyze/clustering/',
    }
    const endpoint = typeToEndpoint[type]
    if (!endpoint) return

    setAnalysisPanel({
      symbol,
      type,
      loading: true,
      error: '',
      payload: null,
    })

    try {
      const response = await api.get(
        `${endpoint}?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`
      )
      setAnalysisPanel({
        symbol,
        type,
        loading: false,
        error: '',
        payload: response.data,
      })
    } catch {
      setAnalysisPanel({
        symbol,
        type,
        loading: false,
        error: 'Could not load analysis data for this stock.',
        payload: null,
      })
    }
  }

  useEffect(() => {
    if (!analysisPanel.symbol || !analysisPanel.type) return
    handleOpenAnalysis(analysisPanel.symbol, analysisPanel.type, analysisTimeframe)
  }, [analysisTimeframe])

  useEffect(() => {
    if (!portfolioInsights.section || !portfolioInsightsRef.current) return
    portfolioInsightsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [portfolioInsights.section, portfolioInsights.loading, portfolioInsights.payload, portfolioInsights.error])

  const loadPortfolioInsights = async (section) => {
    setPortfolioInsights((prev) => ({
      section,
      loading: true,
      error: '',
      payload: prev.payload,
    }))

    try {
      const response = await api.get(`/api/portfolios/${id}/analytics/`)
      setPortfolioInsights({
        section,
        loading: false,
        error: '',
        payload: response.data,
      })
    } catch {
      setPortfolioInsights({
        section,
        loading: false,
        error: 'Could not load portfolio comparison charts.',
        payload: null,
      })
    }
  }

  const regressionChartData = useMemo(() => {
    if (analysisPanel.type !== 'regression' || !analysisPanel.payload) return null
    return {
      labels: analysisPanel.payload.dates || [],
      datasets: [
        {
          label: 'Actual Close',
          data: analysisPanel.payload.actual_close || [],
          borderColor: '#0a9396',
          backgroundColor: 'rgba(10, 147, 150, 0.2)',
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: 'Predicted Close',
          data: analysisPanel.payload.predicted_close || [],
          borderColor: '#ee9b00',
          backgroundColor: 'rgba(238, 155, 0, 0.2)',
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    }
  }, [analysisPanel])

  const discountChartData = useMemo(() => {
    if (analysisPanel.type !== 'discount' || !analysisPanel.payload) return null
    return {
      labels: analysisPanel.payload.dates || [],
      datasets: [
        {
          label: 'Discount Ratio (%)',
          data: analysisPanel.payload.discount_ratio || [],
          borderColor: '#005f73',
          backgroundColor: 'rgba(0, 95, 115, 0.15)',
          pointRadius: 0,
          borderWidth: 2,
          fill: true,
        },
      ],
    }
  }, [analysisPanel])

  const clusterChartData = useMemo(() => {
    if (portfolioInsights.section !== 'cluster' || !portfolioInsights.payload?.clustering?.points?.length) return null
    const colors = ['#0a9396', '#ee9b00', '#bb3e03', '#6d597a']
    const grouped = {}
    portfolioInsights.payload.clustering.points.forEach((point) => {
      const key = point.cluster_id ?? 0
      if (!grouped[key]) grouped[key] = []
      grouped[key].push({
        x: point.x,
        y: point.y,
        company_name: point.company_name,
        symbol: point.symbol,
      })
    })

    return {
      datasets: Object.keys(grouped).map((clusterId, index) => ({
        label:
          portfolioInsights.payload?.clustering?.cluster_labels?.[clusterId] ||
          portfolioInsights.payload?.clustering?.cluster_labels?.[Number(clusterId)] ||
          `Cluster ${clusterId}`,
        data: grouped[clusterId],
        backgroundColor: colors[index % colors.length],
      })),
    }
  }, [portfolioInsights])

  const peBarChartData = useMemo(() => {
    if (portfolioInsights.section !== 'pe' || !portfolioInsights.payload?.pe_comparison?.length) return null
    const rows = portfolioInsights.payload.pe_comparison.filter((item) => item.pe_ratio !== null)
    if (!rows.length) return null
    return {
      labels: rows.map((item) => item.symbol),
      datasets: [
        {
          label: 'P/E Ratio',
          data: rows.map((item) => item.pe_ratio),
          backgroundColor: ['#0a9396', '#94d2bd', '#ee9b00', '#ca6702', '#005f73', '#bb3e03'],
          borderRadius: 8,
        },
      ],
    }
  }, [portfolioInsights])

  return (
    <AppShell title={portfolio?.name || `Portfolio ${id}`}>
      <section className="portfolio-header-grid">
        <section className="portfolio-hero portfolio-hero-rich">
          <div>
            <h2>{portfolio?.name || 'Portfolio'}</h2>
            <p>Add stocks using only search. Click any suggestion to add instantly with live quote defaults.</p>
          </div>
          <Link className="button button-secondary" to="/portfolios">
            Back to Portfolios
          </Link>
        </section>

        {!loading && stocks.length > 0 ? (
          <section className="portfolio-insights-ribbon">
            <div className="portfolio-insights-actions">
              <button
              className={`button portfolio-action-button portfolio-action-pe ${
                  portfolioInsights.section === 'pe' ? 'portfolio-action-active' : ''
                }`}
                type="button"
                onClick={() => loadPortfolioInsights('pe')}
              >
                Stock Comparison on P/E Ratio
              </button>
              <button
                className={`button portfolio-action-button portfolio-action-cluster ${
                  portfolioInsights.section === 'cluster' ? 'portfolio-action-active' : ''
                }`}
                type="button"
                onClick={() => loadPortfolioInsights('cluster')}
              >
                Stock Comparison on Clustering
              </button>
            </div>
          </section>
        ) : null}
      </section>

      <section className="stock-search-panel">
        <div className="search-wrap">
          <input
            name="query"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by symbol or company name (e.g., TCS, Infosys, Reliance)"
          />
          {suggestions.length > 0 ? (
            <div className="suggestions-box">
              {suggestions.map((item) => (
                <button
                  key={`${item.symbol}-${item.company_name}`}
                  type="button"
                  className="suggestion-item suggestion-item-rich"
                  onClick={() => handleAddFromSuggestion(item)}
                  disabled={adding}
                >
                  <div>
                    <strong>{item.symbol}</strong>
                    <span>{item.company_name}</span>
                  </div>
                  <div className="suggestion-meta">{item.sector || 'Sector mapped on add'}</div>
                </button>
              ))}
            </div>
          ) : query ? (
            <div className="suggestions-box">
              <div className="suggestion-empty">No suggestions found.</div>
            </div>
          ) : null}
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading stocks...</p> : null}

      {!loading && (
        <div className="stocks-table-wrap">
          <table className="stocks-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th>Sector</th>
                <th>Buy Price</th>
                <th>Last Value</th>
                <th>P/E Ratio</th>
                <th>365D High</th>
                <th>365D Low</th>
                <th>Qty</th>
                <th>Graphs</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((stock) => (
                <tr key={stock.id}>
                  <td>
                    {editingStockId === stock.id ? (
                      <input
                        value={editingForm.symbol}
                        onChange={(event) => setEditingForm((prev) => ({ ...prev, symbol: event.target.value }))}
                      />
                    ) : (
                      stock.symbol
                    )}
                  </td>
                  <td>
                    {editingStockId === stock.id ? (
                      <input
                        value={editingForm.company_name}
                        onChange={(event) =>
                          setEditingForm((prev) => ({ ...prev, company_name: event.target.value }))
                        }
                      />
                    ) : (
                      stock.company_name
                    )}
                  </td>
                  <td>
                    {editingStockId === stock.id ? (
                      <select
                        value={editingForm.sector_id}
                        onChange={(event) => setEditingForm((prev) => ({ ...prev, sector_id: event.target.value }))}
                      >
                        <option value="">Select sector</option>
                        {sectors.map((sector) => (
                          <option key={sector.id} value={sector.id}>
                            {sector.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      stock.sector_name
                    )}
                  </td>
                  <td>
                    {editingStockId === stock.id ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editingForm.buy_price}
                        onChange={(event) => setEditingForm((prev) => ({ ...prev, buy_price: event.target.value }))}
                      />
                    ) : (
                      stock.buy_price
                    )}
                  </td>
                  <td>{quoteBySymbol[stock.symbol]?.last_value ?? '-'}</td>
                  <td>{quoteBySymbol[stock.symbol]?.pe_ratio ?? '-'}</td>
                  <td>{quoteBySymbol[stock.symbol]?.high_365d ?? '-'}</td>
                  <td>{quoteBySymbol[stock.symbol]?.low_365d ?? '-'}</td>
                  <td>
                    {editingStockId === stock.id ? (
                      <input
                        type="number"
                        min="1"
                        value={editingForm.quantity}
                        onChange={(event) => setEditingForm((prev) => ({ ...prev, quantity: event.target.value }))}
                      />
                    ) : (
                      stock.quantity
                    )}
                  </td>
                  <td>
                    <div className="analysis-actions">
                      <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => handleOpenAnalysis(stock.symbol, 'regression')}
                      >
                        Price Trend
                      </button>
                      <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => handleOpenAnalysis(stock.symbol, 'discount')}
                      >
                        Discount
                      </button>
                    </div>
                  </td>
                  <td>
                    <div className="actions">
                      {editingStockId === stock.id ? (
                        <button className="button button-secondary" type="button" onClick={() => handleSaveEdit(stock.id)}>
                          Save
                        </button>
                      ) : (
                        <button className="button button-secondary" type="button" onClick={() => handleStartEdit(stock)}>
                          Edit
                        </button>
                      )}
                      <button className="button button-danger" type="button" onClick={() => handleDeleteStock(stock.id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {stocks.length === 0 ? (
                <tr>
                  <td colSpan={11}>No stocks yet. Start typing in search and click a suggestion to add.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}

      {(analysisPanel.loading || analysisPanel.payload || analysisPanel.error) && (
        <section className="analysis-panel">
          <div className="analysis-panel-head">
            <h3>
              Analysis: {analysisPanel.symbol} ({analysisPanel.type || 'N/A'})
            </h3>
            <div className="analysis-timeframe">
              <label htmlFor="analysis-timeframe">Range</label>
              <select
                id="analysis-timeframe"
                value={analysisTimeframe}
                onChange={(event) => setAnalysisTimeframe(event.target.value)}
              >
                {timeframeOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {analysisPanel.loading ? <p>Loading analysis data...</p> : null}
          {analysisPanel.error ? <p className="form-error">{analysisPanel.error}</p> : null}
          {analysisPanel.payload ? (
            <div className="analysis-meta">
              {analysisPanel.type === 'regression' ? (
                <>
                  <p>Regression data loaded: {analysisPanel.payload?.dates?.length || 0} points.</p>
                  {regressionChartData ? (
                    <div className="chart-wrap">
                      <Line
                        data={regressionChartData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: { legend: { position: 'top' } },
                          scales: { x: { ticks: { maxTicksLimit: 8 } } },
                        }}
                      />
                    </div>
                  ) : null}
                </>
              ) : null}
              {analysisPanel.type === 'discount' ? (
                <>
                  <p>Discount ratio data loaded: {analysisPanel.payload?.dates?.length || 0} points.</p>
                  {discountChartData ? (
                    <div className="chart-wrap">
                      <Line
                        data={discountChartData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: { legend: { position: 'top' } },
                          scales: { x: { ticks: { maxTicksLimit: 8 } } },
                        }}
                      />
                    </div>
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}
        </section>
      )}

      {(portfolioInsights.section || portfolioInsights.loading || portfolioInsights.error) && (
        <section ref={portfolioInsightsRef} className="analysis-panel">
          <div className="analysis-panel-head">
            <h3>
              {portfolioInsights.section === 'cluster'
                ? 'Stock Comparison on Clustering'
                : 'Stock Comparison on P/E Ratio'}
            </h3>
          </div>
          {portfolioInsights.loading ? <p>Loading portfolio chart...</p> : null}
          {portfolioInsights.error ? <p className="form-error">{portfolioInsights.error}</p> : null}
          {!portfolioInsights.loading && portfolioInsights.section === 'pe' ? (
            <>
              {peBarChartData ? (
                <div className="chart-wrap">
                  <Bar
                    data={peBarChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { position: 'top' } },
                    }}
                  />
                </div>
              ) : (
                <p className="muted">P/E ratio data is not available yet for the stocks in this portfolio.</p>
              )}
            </>
          ) : null}
          {!portfolioInsights.loading && portfolioInsights.section === 'cluster' ? (
            <>
              {portfolioInsights.payload?.clustering?.cluster_labels ? (
                <ul className="cluster-legend">
                  {Object.entries(portfolioInsights.payload.clustering.cluster_labels).map(([clusterId, clusterName]) => (
                    <li key={clusterId}>
                      <strong>Cluster {clusterId}:</strong> {clusterName}
                    </li>
                  ))}
                </ul>
              ) : null}
              {clusterChartData ? (
                <div className="chart-wrap">
                  <Scatter
                    data={clusterChartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                          callbacks: {
                            label(context) {
                              const point = context.raw || {}
                              return `${point.symbol || ''} | PE ${point.x ?? '-'} | Discount ${point.y ?? '-'}`
                            },
                          },
                        },
                      },
                      scales: {
                        x: { title: { display: true, text: 'P/E Ratio' } },
                        y: { title: { display: true, text: 'Discount Ratio (%)' } },
                      },
                    }}
                  />
                </div>
              ) : (
                <p className="muted">At least two stocks with usable live data are needed for portfolio clustering.</p>
              )}
            </>
          ) : null}
        </section>
      )}
    </AppShell>
  )
}

export default PortfolioDetailPage
