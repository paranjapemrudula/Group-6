import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

function HomePage() {
  const [portfolios, setPortfolios] = useState([])
  const [stockCount, setStockCount] = useState(0)
  const [marketOverview, setMarketOverview] = useState({ top_stocks: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [marketError, setMarketError] = useState('')

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [portfolioResponse, overviewResponse] = await Promise.all([
          api.get('/api/portfolios/'),
          api.get('/api/market/overview/'),
        ])
        const list = portfolioResponse.data
        setPortfolios(list)
        setMarketOverview(overviewResponse.data || { top_stocks: [] })
        setMarketError('')

        const stocksResponses = await Promise.all(list.map((item) => api.get(`/api/portfolios/${item.id}/stocks/`)))
        const total = stocksResponses.reduce((sum, current) => sum + current.data.length, 0)
        setStockCount(total)
      } catch {
        setError('Could not load dashboard data.')
      } finally {
        setLoading(false)
      }
    }

    const refreshLiveOverview = async () => {
      try {
        const response = await api.get('/api/market/overview/')
        setMarketOverview(response.data || { top_stocks: [] })
        setMarketError('')
      } catch {
        setMarketError('Live market feed is unavailable right now.')
      }
    }

    loadDashboard()
    const timer = setInterval(refreshLiveOverview, 20000)
    return () => clearInterval(timer)
  }, [])

  const insightText = useMemo(() => {
    if (portfolios.length === 0) return 'Create your first portfolio to start tracking ideas.'
    if (stockCount === 0) return 'Your portfolios are ready. Add stocks to begin analysis.'
    if (stockCount < portfolios.length * 2) return 'Consider adding more than one stock per portfolio for better comparisons.'
    return 'Good diversification progress. Next step: use analysis graphs for entry/exit timing.'
  }, [portfolios.length, stockCount])

  return (
    <AppShell title="Home">
      <section className="dashboard-hero">
        <div>
          <h2>Welcome to your dashboard</h2>
          <p>Track your portfolio activity and monitor progress before diving into charts.</p>
        </div>
        <Link className="button" to="/portfolios">
          Manage Portfolios
        </Link>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading dashboard...</p> : null}

      {!loading && (
        <>
          <section className="dashboard-stats">
            <article className="stat-card">
              <p>Portfolios</p>
              <h3>{portfolios.length}</h3>
            </article>
            <article className="stat-card">
              <p>Total Stocks</p>
              <h3>{stockCount}</h3>
            </article>
            <article className="stat-card">
              <p>Average Stocks / Portfolio</p>
              <h3>{portfolios.length ? (stockCount / portfolios.length).toFixed(1) : '0.0'}</h3>
            </article>
          </section>

          <section className="dashboard-grid">
            <article className="feature-card">
              <h3>Latest Portfolios</h3>
              {portfolios.length === 0 ? (
                <p>No portfolios yet.</p>
              ) : (
                <ul className="dash-list">
                  {portfolios.slice(0, 5).map((item) => (
                    <li key={item.id}>
                      <Link to={`/portfolios/${item.id}`}>{item.name}</Link>
                    </li>
                  ))}
                </ul>
              )}
            </article>
            <article className="feature-card">
              <h3>Insight</h3>
              <p>{insightText}</p>
              <p className="muted">Next phase can layer valuation and trend charts on top of these holdings.</p>
            </article>
          </section>

          <section className="dashboard-grid">
            <article className="feature-card">
              <div className="market-card-head">
                <h3>Live Market Pulse</h3>
                <span className="live-dot">LIVE</span>
              </div>
              {marketError ? <p className="form-error">{marketError}</p> : null}
              <div className="market-list">
                {(marketOverview.top_stocks || []).map((stock) => (
                  <article key={stock.symbol} className="market-item">
                    <div>
                      <strong>{stock.symbol}</strong>
                      <p>{stock.company_name}</p>
                    </div>
                    <div className="market-meta">
                      <span>Last: {stock.last_value ?? '-'}</span>
                      <span>P/E: {stock.pe_ratio ?? '-'}</span>
                    </div>
                  </article>
                ))}
              </div>
            </article>
          </section>
        </>
      )}
    </AppShell>
  )
}

export default HomePage
