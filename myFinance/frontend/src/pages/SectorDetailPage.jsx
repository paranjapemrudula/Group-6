import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api, publicApi } from '../lib/api'

function SectorDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [sector, setSector] = useState(null)
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [addingSymbol, setAddingSymbol] = useState('')
  const [portfolioOptions, setPortfolioOptions] = useState([])
  const [portfolioModal, setPortfolioModal] = useState({ open: false, stock: null, selectedPortfolioId: '' })
  const stockListRef = useRef(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await publicApi.get(`/api/sectors/${id}/stocks/`)
        setSector(res.data?.sector || null)
        setStocks(res.data?.stocks || [])
        setError('')
      } catch (err) {
        setError('Could not load this sector right now.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  useEffect(() => {
    const loadPortfolios = async () => {
      try {
        const response = await api.get('/api/portfolios/')
        setPortfolioOptions(response.data || [])
      } catch {
        setPortfolioOptions([])
      }
    }
    loadPortfolios()
  }, [])

  useEffect(() => {
    if (!loading && stockListRef.current) {
      stockListRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [loading])

  const filteredStocks = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return stocks
    return stocks.filter((stock) => {
      const symbol = String(stock.symbol || '').toLowerCase()
      const companyName = String(stock.company_name || '').toLowerCase()
      return symbol.includes(normalized) || companyName.includes(normalized)
    })
  }, [stocks, query])

  const openPortfolioModal = (stock) => {
    setPortfolioModal({ open: true, stock, selectedPortfolioId: portfolioOptions[0] ? String(portfolioOptions[0].id) : '' })
    setError('')
  }

  const closePortfolioModal = () => setPortfolioModal({ open: false, stock: null, selectedPortfolioId: '' })

  const navigateToCreatePortfolio = () => {
    if (!portfolioModal.stock) {
      navigate('/portfolios')
      return
    }
    navigate('/portfolios', {
      state: {
        pendingStock: {
          symbol: portfolioModal.stock.symbol,
          company_name: portfolioModal.stock.company_name,
          market: portfolioModal.stock.market,
          sector_id: sector?.id || null,
          sector_name: sector?.name || '',
        },
        returnTo: location.pathname,
      },
    })
  }

  const handleConfirmAddToPortfolio = async () => {
    if (!portfolioModal.stock || !portfolioModal.selectedPortfolioId) return
    const stock = portfolioModal.stock
    setAddingSymbol(stock.symbol)
    setError('')
    try {
      await api.post(`/api/portfolios/${portfolioModal.selectedPortfolioId}/stocks/`, {
        symbol: stock.symbol,
        company_name: stock.company_name,
        sector_id: sector?.id,
        buy_price: 0,
        quantity: 1,
      })
      closePortfolioModal()
    } catch (err) {
      const detail =
        err?.message ||
        err?.response?.data?.detail ||
        (typeof err?.response?.data === 'string' ? err.response.data : '') ||
        'Could not add this stock to the selected portfolio right now.'
      setError(detail)
    } finally {
      setAddingSymbol('')
    }
  }

  if (loading) {
    return (
      <AppShell title="Sector">
        <p>Loading sector...</p>
      </AppShell>
    )
  }

  if (error) {
    return (
      <AppShell title="Sector">
        <p className="form-error">{error}</p>
        <button className="button" type="button" onClick={() => navigate('/sectors')}>
          Back to Sectors
        </button>
      </AppShell>
    )
  }

  if (!sector) {
    return (
      <AppShell title="Sector">
        <p>No sector found.</p>
        <button className="button" type="button" onClick={() => navigate('/sectors')}>
          Back to Sectors
        </button>
      </AppShell>
    )
  }

  return (
    <AppShell title={`${sector.name} Stocks`}>
      <section className="dashboard-hero">
        <div>
          <h2>{sector.name} Stocks</h2>
          <p className="muted">Showing {filteredStocks.length} of {stocks.length} stocks</p>
        </div>
        <div className="actions">
          <input
            className="inline-input"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter visible stocks by name or symbol"
          />
          <Link className="button button-secondary" to="/sectors">
            Back to Sectors
          </Link>
        </div>
      </section>

      <section className="analysis-panel" ref={stockListRef}>
        <div className="stocks-table-wrap">
          <table className="stocks-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th>Market</th>
                <th>Series</th>
                <th>ISIN</th>
                <th>Source</th>
                <th>Add to Portfolio</th>
              </tr>
            </thead>
            <tbody>
              {filteredStocks.map((stock) => (
                <tr key={`${stock.market}-${stock.symbol}`}>
                  <td>{stock.symbol}</td>
                  <td>{stock.company_name}</td>
                  <td>{stock.market || '-'}</td>
                  <td>{stock.series || '-'}</td>
                  <td>{stock.isin_code || '-'}</td>
                  <td>{stock.source_file || '-'}</td>
                  <td>
                    <button
                      className="button button-secondary sector-add-button"
                      type="button"
                      onClick={() => openPortfolioModal(stock)}
                      disabled={addingSymbol === stock.symbol}
                    >
                      {addingSymbol === stock.symbol ? 'Adding...' : 'Add'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {portfolioModal.open ? (
        <div className="sector-modal-backdrop" role="presentation" onClick={closePortfolioModal}>
          <div className="sector-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <h3>Add Stock To Portfolio</h3>
            <p className="muted">
              <strong>{portfolioModal.stock?.symbol}</strong> - {portfolioModal.stock?.company_name}
            </p>
            <select
              className="inline-input"
              value={portfolioModal.selectedPortfolioId}
              onChange={(event) =>
                setPortfolioModal((prev) => ({ ...prev, selectedPortfolioId: event.target.value }))
              }
            >
              <option value="">Select portfolio</option>
              {portfolioOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            {portfolioModal.selectedPortfolioId ? (
              <p className="muted">
                Selected portfolio:{' '}
                <strong>
                  {portfolioOptions.find((item) => String(item.id) === String(portfolioModal.selectedPortfolioId))?.name ||
                    'Unknown'}
                </strong>
              </p>
            ) : null}
            <p className={portfolioOptions.length ? 'muted' : 'form-error'}>
              {portfolioOptions.length ? 'Want a different destination? ' : 'No portfolios found. '}
              <button type="button" className="button-link" onClick={navigateToCreatePortfolio}>
                Create a portfolio and add this stock there
              </button>
              .
            </p>
            <div className="actions">
              <button
                className="button"
                type="button"
                onClick={handleConfirmAddToPortfolio}
                disabled={!portfolioModal.selectedPortfolioId || addingSymbol === portfolioModal.stock?.symbol}
              >
                {addingSymbol === portfolioModal.stock?.symbol ? 'Adding...' : 'Confirm Add'}
              </button>
              <button className="button button-secondary" type="button" onClick={closePortfolioModal}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </AppShell>
  )
}

export default SectorDetailPage
