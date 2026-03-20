import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicNavbar from '../components/PublicNavbar'
import { publicApi } from '../lib/api'

function LandingPage() {
  const [overview, setOverview] = useState({ top_stocks: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadOverview = async () => {
    try {
      const response = await publicApi.get('/api/market/overview/')
      setOverview(response.data)
      setLastUpdated(new Date())
      setError('')
    } catch {
      setError('Live market feed unavailable right now.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
    const timer = setInterval(loadOverview, 20000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="landing-page">
      <PublicNavbar />

      <section className="landing-live container">
        <div className="landing-auth-card">
          <p className="badge">Live market enabled</p>
          <h1>Plan tomorrow’s wealth today with AI-backed market intelligence.</h1>
          <p className="hero-copy">
            MyFinance analyzes live market behavior and turns it into signals you can use for portfolio
            planning, risk balance, and smarter long-term investing decisions.
          </p>
          <div className="actions">
            <Link className="button" to="/login">
              Sign in
            </Link>
            <Link className="button button-secondary" to="/signup">
              Create account
            </Link>
          </div>
          <p className="muted">
            {lastUpdated ? `Updated: ${lastUpdated.toLocaleTimeString()}` : 'Connecting live feed...'}
          </p>
        </div>

        <div className="landing-market-card">
          <div className="market-card-head">
            <h3>📈 Top 5 Stocks</h3>
            <span className="live-dot">LIVE</span>
          </div>
          {loading ? <p>Loading market data...</p> : null}
          {error ? <p className="form-error">{error}</p> : null}
          {!loading && !error ? (
            <div className="market-list">
              {overview.top_stocks.map((stock) => (
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
          ) : null}
        </div>
      </section>
    </div>
  )
}

export default LandingPage
