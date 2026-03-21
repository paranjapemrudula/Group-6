import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

function SentimentPage() {
  const [overview, setOverview] = useState({ portfolio_count: 0, items: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestionState, setShowSuggestionState] = useState(false)
  const [searchLocked, setSearchLocked] = useState(false)
  const [companyReport, setCompanyReport] = useState(null)
  const [companyLoading, setCompanyLoading] = useState(false)
  const [companyError, setCompanyError] = useState('')

  useEffect(() => {
    const loadOverview = async () => {
      setLoading(true)
      try {
        const response = await api.get('/api/sentiment/overview/')
        setOverview(response.data)
        setError('')
      } catch {
        setError('Could not load the sentiment module right now.')
      } finally {
        setLoading(false)
      }
    }

    loadOverview()
  }, [])

  useEffect(() => {
    if (searchLocked) {
      setSuggestions([])
      setShowSuggestionState(false)
      return
    }

    if (query.trim().length < 1) {
      setSuggestions([])
      setShowSuggestionState(false)
      return
    }

    setShowSuggestionState(true)
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

  const handleSelectCompany = async (item) => {
    setSearchLocked(true)
    setQuery(`${item.symbol} - ${item.company_name}`)
    setSuggestions([])
    setShowSuggestionState(false)
    setCompanyLoading(true)
    setCompanyError('')

    try {
      const response = await api.get(
        `/api/sentiment/company/?symbol=${encodeURIComponent(item.symbol)}&company_name=${encodeURIComponent(
          item.company_name
        )}`
      )
      setCompanyReport(response.data)
    } catch {
      setCompanyReport(null)
      setCompanyError('Could not load company sentiment right now.')
    } finally {
      setCompanyLoading(false)
    }
  }

  return (
    <AppShell title="Sentiment Module">
      <section className="portfolio-hero">
        <div>
          <h2>Sentiment Analysis</h2>
          <p>Search any company by symbol or name to open a news-based sentiment report, or jump into portfolio reports below.</p>
        </div>
      </section>

      <section className="stock-search-panel">
        <div className="search-wrap">
          <input
            name="sentiment-query"
            type="text"
            value={query}
            onChange={(event) => {
              setSearchLocked(false)
              setQuery(event.target.value)
              setShowSuggestionState(true)
            }}
            placeholder="Search company or symbol for sentiment report (e.g., TCS, INFY, Reliance)"
          />
          {suggestions.length > 0 ? (
            <div className="suggestions-box">
              {suggestions.map((item) => (
                <button
                  key={`${item.symbol}-${item.company_name}`}
                  type="button"
                  className="suggestion-item suggestion-item-rich"
                  onClick={() => handleSelectCompany(item)}
                >
                  <div>
                    <strong>{item.symbol}</strong>
                    <span>{item.company_name}</span>
                  </div>
                  <div className="suggestion-meta">{item.sector || 'Search result'}</div>
                </button>
              ))}
            </div>
          ) : query && showSuggestionState ? (
            <div className="suggestions-box">
              <div className="suggestion-empty">No suggestions found.</div>
            </div>
          ) : null}
        </div>
      </section>

      {companyLoading ? <p>Loading company sentiment report...</p> : null}
      {companyError ? <p className="form-error">{companyError}</p> : null}

      {companyReport ? (
        <>
          <section className="sentiment-report-meta">
            <article className="sentiment-summary-card">
              <p className="muted">Company</p>
              <h4>{companyReport.company_name}</h4>
              <strong>{companyReport.symbol}</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Avg. sentiment</p>
              <h4>{companyReport.summary?.label || 'Neutral'}</h4>
              <strong>{companyReport.summary?.avg_sentiment ?? 50}%</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Price direction</p>
              <h4>
                {companyReport.summary?.price_direction_emoji || '->'}{' '}
                {(companyReport.summary?.price_direction || 'flat').toUpperCase()}
              </h4>
              <strong>Current: {companyReport.summary?.current_price ?? '-'}</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Positive count</p>
              <h4>{companyReport.summary?.positive_count || 0}</h4>
              <strong>News matches</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Neutral count</p>
              <h4>{companyReport.summary?.neutral_count || 0}</h4>
              <strong>News matches</strong>
            </article>
            <article className="sentiment-summary-card">
              <p className="muted">Negative count</p>
              <h4>{companyReport.summary?.negative_count || 0}</h4>
              <strong>News matches</strong>
            </article>
          </section>

          <section className="analysis-panel">
            <div className="analysis-panel-head">
              <h3>Company Sentiment Report</h3>
              <button className="button button-secondary" type="button" onClick={() => window.print()}>
                Print / Save PDF
              </button>
            </div>
            <p className="muted">
              Total articles: {companyReport.summary?.total_articles || 0} | Previous close:{' '}
              {companyReport.summary?.previous_close ?? '-'} | Price change: {companyReport.summary?.price_change ?? '-'}
            </p>
            {companyReport.articles?.length ? (
              <div className="sentiment-headline-list">
                {companyReport.articles.map((article) => (
                  <a
                    key={article.link}
                    href={article.link}
                    target="_blank"
                    rel="noreferrer"
                    className="sentiment-headline-item"
                  >
                    <strong>{article.title}</strong>
                    <span>
                      {article.publisher || 'Source'} | {article.sentiment_label} |{' '}
                      {article.published_at ? new Date(article.published_at * 1000).toLocaleDateString() : 'Recent'}
                    </span>
                  </a>
                ))}
              </div>
            ) : (
              <p className="muted">No recent company news was available for sentiment scoring.</p>
            )}
          </section>
        </>
      ) : null}

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading sentiment portfolios...</p> : null}

      {!loading && !overview.items.length ? (
        <p>No portfolios are ready for sentiment analysis yet. Create a portfolio and add stocks first.</p>
      ) : null}

      {!loading && overview.items.length ? (
        <section
          className={`portfolio-grid ${suggestions.length > 0 || (query && showSuggestionState) ? 'sentiment-results-offset' : ''}`}
        >
          {overview.items.map((item) => (
            <article key={item.portfolio_id} className="portfolio-card">
              <div>
                <h3>{item.portfolio_name}</h3>
                <p>{item.stock_count} stock{item.stock_count === 1 ? '' : 's'} in this portfolio</p>
                <p>
                  Avg. Sentiment: <strong>{item.summary?.avg_sentiment ?? 50}%</strong> | {item.summary?.label || 'Neutral'}
                </p>
                <p>
                  Counts: +{item.summary?.positive_count || 0} / ={item.summary?.neutral_count || 0} / -
                  {item.summary?.negative_count || 0}
                </p>
                <p>
                  Price Direction: {item.summary?.price_direction_emoji || '->'}{' '}
                  {(item.summary?.price_direction || 'flat').toUpperCase()}
                </p>
                <p>Snapshot: {item.has_snapshot ? 'Available' : 'Generate on first report open'}</p>
              </div>
              <div className="actions">
                <Link className="button" to={`/portfolios/${item.portfolio_id}/sentiment-report`}>
                  Open Sentiment Report
                </Link>
                <Link className="button button-secondary" to={`/portfolios/${item.portfolio_id}`}>
                  View Portfolio
                </Link>
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  )
}

export default SentimentPage
