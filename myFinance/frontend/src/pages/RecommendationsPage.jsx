import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

function RecommendationsPage() {
  const [overview, setOverview] = useState({ portfolio_count: 0, items: [], preference: null })
  const [selectedPortfolioId, setSelectedPortfolioId] = useState('')
  const [report, setReport] = useState(null)
  const [loadingOverview, setLoadingOverview] = useState(true)
  const [loadingReport, setLoadingReport] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadOverview = async () => {
      setLoadingOverview(true)
      try {
        const response = await api.get('/api/recommendations/overview/')
        setOverview(response.data)
        setError('')
        if (response.data.items?.length) {
          setSelectedPortfolioId(String(response.data.items[0].portfolio_id))
        }
      } catch {
        setError('Could not load the recommendation module right now.')
      } finally {
        setLoadingOverview(false)
      }
    }
    loadOverview()
  }, [])

  useEffect(() => {
    if (!selectedPortfolioId) {
      setReport(null)
      return
    }
    const loadReport = async () => {
      setLoadingReport(true)
      try {
        const response = await api.get(`/api/portfolios/${selectedPortfolioId}/recommendations/`)
        setReport(response.data)
        setError('')
      } catch {
        setError('Could not load recommendations for this portfolio.')
      } finally {
        setLoadingReport(false)
      }
    }
    loadReport()
  }, [selectedPortfolioId])

  const selectedPortfolio = useMemo(
    () => overview.items.find((item) => String(item.portfolio_id) === String(selectedPortfolioId)),
    [overview, selectedPortfolioId]
  )

  return (
    <AppShell title="Recommendation Module">
      <section className="dashboard-hero">
        <div>
          <h2>Recommendations</h2>
          <p>Explainable stock recommendations built from portfolio holdings, sentiment, live market signals, and diversification logic.</p>
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loadingOverview ? <p>Loading recommendation overview...</p> : null}

      {!loadingOverview ? (
        <>
          <section className="dashboard-grid">
            <article className="feature-card">
              <h3>Portfolio Scope</h3>
              <p><strong>Tracked portfolios:</strong> {overview.portfolio_count || 0}</p>
              <p><strong>Risk profile:</strong> {overview.preference?.risk_level || 'balanced'}</p>
              <p><strong>Horizon:</strong> {overview.preference?.investment_horizon || 'medium'}</p>
            </article>
            <article className="feature-card">
              <h3>Select Portfolio</h3>
              <select
                value={selectedPortfolioId}
                onChange={(event) => setSelectedPortfolioId(event.target.value)}
                className="inline-input"
              >
                <option value="">Choose portfolio</option>
                {overview.items.map((item) => (
                  <option key={item.portfolio_id} value={item.portfolio_id}>
                    {item.portfolio_name}
                  </option>
                ))}
              </select>
              {selectedPortfolio ? (
                <p className="muted">
                  Last top action: {selectedPortfolio.summary?.top_action || 'Watch'} | Existing snapshot:{' '}
                  {selectedPortfolio.has_snapshot ? 'Yes' : 'No'}
                </p>
              ) : null}
            </article>
          </section>

          <section className="portfolio-grid">
            {overview.items.map((item) => (
              <article key={item.portfolio_id} className="portfolio-card">
                <div>
                  <h3>{item.portfolio_name}</h3>
                  <p>Top action: {item.summary?.top_action || 'Watch'}</p>
                  <p>{item.summary?.recommendation_count || 0} recommendation{item.summary?.recommendation_count === 1 ? '' : 's'}</p>
                </div>
                <div className="actions">
                  <button className="button" type="button" onClick={() => setSelectedPortfolioId(String(item.portfolio_id))}>
                    Open Recommendations
                  </button>
                  <Link className="button button-secondary" to={`/portfolios/${item.portfolio_id}`}>
                    View Portfolio
                  </Link>
                </div>
              </article>
            ))}
          </section>

          {loadingReport ? <p>Loading recommendation report...</p> : null}

          {report ? (
            <section className="analysis-panel">
              <div className="analysis-panel-head">
                <h3>{report.portfolio_name} Recommendation Report</h3>
                <p className="muted">
                  Top action: <strong>{report.summary?.top_action || 'Watch'}</strong>
                </p>
              </div>
              <div className="recommendation-list">
                {report.recommendations?.map((item) => (
                  <article key={item.stock_id} className="recommendation-card">
                    <div className="recommendation-card-head">
                      <div>
                        <h4>{item.symbol} <span>{item.company_name}</span></h4>
                        <p className="muted">{item.sector}</p>
                      </div>
                      <div className={`sentiment-badge recommendation-${item.label.toLowerCase()}`}>{item.label} {item.score}</div>
                    </div>
                    <p className="muted">
                      Sentiment {item.sentiment_percent}% | Price {item.price_direction_emoji || '->'} {(item.price_direction || 'flat').toUpperCase()} |
                      P/E {item.pe_ratio ?? '-'} | Discount {item.discount_ratio ?? '-'}
                    </p>
                    <ul className="dash-list">
                      {(item.reasons || []).map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </AppShell>
  )
}

export default RecommendationsPage
