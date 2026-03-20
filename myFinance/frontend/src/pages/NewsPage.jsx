import { useEffect, useState } from 'react'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

const emojiByType = {
  'stock market india': '📈',
  investing: '💼',
}

function toSnippet(item) {
  if (item.summary && item.summary.trim()) return item.summary.trim()
  return `${item.title} - quick market context for investors tracking stocks and broader opportunities.`
}

function NewsPage() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadNews = async () => {
    try {
      const response = await api.get('/api/market/news/')
      setNews(response.data || [])
      setLastUpdated(new Date())
      setError('')
    } catch {
      setError('Could not fetch market news.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNews()
    const timer = setInterval(loadNews, 60 * 60 * 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <AppShell title="News">
      <section className="dashboard-hero">
        <div>
          <h2>Finance Daily</h2>
          <p>Two-column briefings on stocks and investment trends.</p>
        </div>
        <button className="button" type="button" onClick={loadNews}>
          Refresh
        </button>
      </section>

      <p className="muted">{lastUpdated ? `Updated: ${lastUpdated.toLocaleString()}` : 'Loading latest headlines...'}</p>
      {loading ? <p>Loading news...</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {!loading && !error ? (
        <section className="news-board">
          {news.map((item, index) => (
            <article key={`${item.link}-${index}`} className="news-paper-card">
              <p className="news-type">
                {emojiByType[item.type] || '📰'} {item.type || 'market'}
              </p>
              <h3>{item.title}</h3>
              {item.image_url ? <img className="news-paper-image" src={item.image_url} alt={item.title} loading="lazy" /> : null}
              <p className="news-summary">{toSnippet(item)}</p>
              <p className="muted">
                {item.publisher || 'Source'} {item.published_at ? `• ${new Date(item.published_at * 1000).toLocaleDateString()}` : ''}
              </p>
              <a href={item.link} target="_blank" rel="noreferrer">
                Read full story
              </a>
            </article>
          ))}
        </section>
      ) : null}
    </AppShell>
  )
}

export default NewsPage
