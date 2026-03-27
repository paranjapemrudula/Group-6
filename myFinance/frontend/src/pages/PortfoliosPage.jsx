import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api } from '../lib/api'

function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState([])
  const [name, setName] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editingName, setEditingName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const location = useLocation()
  const navigate = useNavigate()
  const pendingStock = useMemo(() => location.state?.pendingStock || null, [location.state])

  const fetchPortfolios = async () => {
    try {
      const response = await api.get('/api/portfolios/')
      setPortfolios(response.data)
    } catch {
      setError('Failed to load portfolios.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPortfolios()
  }, [])

  const addPendingStockToPortfolio = async (portfolioId) => {
    if (!pendingStock) {
      return true
    }

    try {
      const normalizedIndiaSymbol =
        pendingStock.market === 'INDIA' && !String(pendingStock.symbol || '').includes('.')
          ? `${String(pendingStock.symbol).toUpperCase()}.NS`
          : String(pendingStock.symbol || '').toUpperCase()

      let quote = {}
      try {
        const quoteResponse = await api.get(`/api/stocks/quote/?symbol=${encodeURIComponent(normalizedIndiaSymbol)}`, {
          timeout: 5000,
        })
        quote = quoteResponse.data || {}
      } catch {
        quote = {}
      }

      await api.post(`/api/portfolios/${portfolioId}/stocks/`, {
        symbol: quote.actual_symbol || normalizedIndiaSymbol,
        company_name: pendingStock.company_name,
        sector_id: pendingStock.sector_id,
        buy_price: Number(quote.current_price || quote.avg_price || 0).toFixed(2),
        quantity: 1,
      })
      return true
    } catch {
      return false
    }
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!name.trim()) return
    try {
      const response = await api.post('/api/portfolios/', { name: name.trim() })
      setPortfolios((prev) => [response.data, ...prev])
      setName('')
      if (pendingStock) {
        const added = await addPendingStockToPortfolio(response.data.id)
        navigate(`/portfolios/${response.data.id}`, {
          state: added
            ? { actionMessage: `${pendingStock.symbol} was added to ${response.data.name}.` }
            : {
                pendingStock,
                createdFromShortcut: true,
                actionMessage: `Portfolio created, but ${pendingStock.symbol} still needs to be added.`,
              },
        })
      }
    } catch {
      setError('Could not create portfolio.')
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/portfolios/${id}/`)
      setPortfolios((prev) => prev.filter((item) => item.id !== id))
    } catch {
      setError('Could not delete portfolio.')
    }
  }

  const handleStartEdit = (portfolio) => {
    setEditingId(portfolio.id)
    setEditingName(portfolio.name)
  }

  const handleSaveEdit = async (id) => {
    try {
      const response = await api.put(`/api/portfolios/${id}/`, { name: editingName.trim() })
      setPortfolios((prev) => prev.map((item) => (item.id === id ? response.data : item)))
      setEditingId(null)
      setEditingName('')
    } catch {
      setError('Could not update portfolio.')
    }
  }

  return (
    <AppShell title="Portfolios">
      <section className="portfolio-hero">
        <div>
          <h2>Your Portfolios</h2>
          <p>Create focused baskets for goals like long-term investing, swing trades, or sector experiments.</p>
          {pendingStock ? (
            <p className="muted">
              Creating a portfolio now will continue with <strong>{pendingStock.symbol}</strong> and add it to the new portfolio.
            </p>
          ) : null}
        </div>
        <form className="portfolio-create" onSubmit={handleCreate}>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="New portfolio name"
            required
          />
          <button className="button" type="submit">
            Add Portfolio
          </button>
        </form>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading portfolios...</p> : null}

      {!loading && portfolios.length === 0 ? (
        <p>No portfolios yet. Create your first one to start adding stocks.</p>
      ) : (
        <div className="portfolio-grid">
          {portfolios.map((portfolio) => (
            <article key={portfolio.id} className="portfolio-card">
              <div>
                {editingId === portfolio.id ? (
                  <input
                    type="text"
                    value={editingName}
                    onChange={(event) => setEditingName(event.target.value)}
                    className="inline-input"
                  />
                ) : (
                  <h3>{portfolio.name}</h3>
                )}
                <p>Created: {new Date(portfolio.created_at).toLocaleDateString()}</p>
              </div>
              <div className="actions">
                <Link className="button" to={`/portfolios/${portfolio.id}`}>
                  View Stocks
                </Link>
                {editingId === portfolio.id ? (
                  <button className="button button-secondary" type="button" onClick={() => handleSaveEdit(portfolio.id)}>
                    Save
                  </button>
                ) : (
                  <button className="button button-secondary" type="button" onClick={() => handleStartEdit(portfolio)}>
                    Rename
                  </button>
                )}
                <button className="button button-danger" type="button" onClick={() => handleDelete(portfolio.id)}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  )
}

export default PortfoliosPage
