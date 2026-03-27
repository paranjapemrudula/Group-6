import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { api, publicApi } from '../lib/api'

const MARKET_OPTIONS = [
  { value: '', label: 'All Markets' },
  { value: 'INDIA', label: 'India' },
  { value: 'USA', label: 'USA' },
]

function SectorsPage() {
  const [market, setMarket] = useState('')
  const [sectors, setSectors] = useState([])
  const [selectedSector, setSelectedSector] = useState(null)
  const [stocks, setStocks] = useState([])
  const [portfolioOptions, setPortfolioOptions] = useState([])
  const [loadingSectors, setLoadingSectors] = useState(true)
  const [loadingStocks, setLoadingStocks] = useState(false)
  const [addingSymbol, setAddingSymbol] = useState('')
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [query, setQuery] = useState('')
  const [portfolioModal, setPortfolioModal] = useState({
    open: false,
    stock: null,
    selectedPortfolioId: '',
  })
  const stockListRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const loadSectors = async () => {
      setLoadingSectors(true)
      try {
        const suffix = market ? `?market=${encodeURIComponent(market)}` : ''
        const response = await publicApi.get(`/api/sectors/${suffix}`)
        const items = response.data || []
        setSectors(items)
        setSelectedSector((current) => {
          if (!current) {
            return null
          }
          const matched = items.find((item) => item.id === current.id)
          return matched || null
        })
        setError('')
      } catch {
        setSectors([])
        setSelectedSector(null)
        setError('Could not load the sectors module right now.')
      } finally {
        setLoadingSectors(false)
      }
    }

    loadSectors()
  }, [market])

  const loadPortfolios = async () => {
    try {
      const response = await api.get('/api/portfolios/')
      const items = response.data || []
      setPortfolioOptions(items)
      return items
    } catch {
      setPortfolioOptions([])
      return []
    }
  }

  useEffect(() => {
    loadPortfolios()
  }, [])

  useEffect(() => {
    if (!selectedSector?.id) {
      setStocks([])
      return
    }

    const loadSectorStocks = async () => {
      setLoadingStocks(true)
      try {
        const suffix = market ? `?market=${encodeURIComponent(market)}` : ''
        const response = await publicApi.get(`/api/sectors/${selectedSector.id}/stocks/${suffix}`)
        setStocks(response.data?.stocks || [])
        setError('')
      } catch {
        setStocks([])
        setError('Could not load stocks for the selected sector.')
      } finally {
        setLoadingStocks(false)
      }
    }

    loadSectorStocks()
  }, [selectedSector, market])

  useEffect(() => {
    if (selectedSector && !loadingStocks && stockListRef.current) {
      stockListRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [selectedSector, loadingStocks])

  const openPortfolioModal = async (stock) => {
    const items = await loadPortfolios()
    setActionMessage('')
    setError('')
    setPortfolioModal({
      open: true,
      stock,
      selectedPortfolioId: items.length ? String(items[0].id) : '',
    })
  }

  const closePortfolioModal = () => {
    setPortfolioModal({
      open: false,
      stock: null,
      selectedPortfolioId: '',
    })
  }

  const handleConfirmAddToPortfolio = async () => {
    if (!portfolioModal.stock || !portfolioModal.selectedPortfolioId) {
      return
    }

    const stock = portfolioModal.stock
    setAddingSymbol(stock.symbol)
    setActionMessage('')
    setError('')
    try {
      const targetPortfolioId = String(portfolioModal.selectedPortfolioId)
      const latestPortfolios = await loadPortfolios()
      const targetPortfolio = latestPortfolios.find((item) => String(item.id) === targetPortfolioId)
      if (!targetPortfolio) {
        throw new Error('Selected portfolio was not found. Please reopen the popup and choose a portfolio again.')
      }
      const normalizedIndiaSymbol =
        stock.market === 'INDIA' && !String(stock.symbol || '').includes('.')
          ? `${String(stock.symbol).toUpperCase()}.NS`
          : stock.symbol
      let quote = {}
      try {
        const quoteResponse = await publicApi.get(`/api/stocks/quote/?symbol=${encodeURIComponent(normalizedIndiaSymbol)}`, {
          timeout: 5000,
        })
        quote = quoteResponse.data || {}
      } catch {
        quote = {}
      }

      const resolvedSectorId = selectedSector?.id
      if (!resolvedSectorId) {
        throw new Error('Missing sector context')
      }

      await api.post(`/api/portfolios/${targetPortfolioId}/stocks/`, {
        symbol: quote.actual_symbol || normalizedIndiaSymbol,
        company_name: stock.company_name,
        sector_id: resolvedSectorId,
        buy_price: Number(quote.current_price || quote.avg_price || 0).toFixed(2),
        quantity: 1,
      })

      setActionMessage(`${quote.actual_symbol || normalizedIndiaSymbol} was added to ${targetPortfolio?.name || 'the selected portfolio'}.`)
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

  const filteredStocks = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return stocks
    }
    return stocks.filter((stock) => {
      const symbol = String(stock.symbol || '').toLowerCase()
      const companyName = String(stock.company_name || '').toLowerCase()
      return symbol.includes(normalized) || companyName.includes(normalized)
    })
  }, [stocks, query])

  return (
    <AppShell title="Sectors Module">
      <section className="dashboard-hero">
        <div>
          <h2>Sectors</h2>
          <p>Browse your imported market universe by sector. Click a sector to open the list of stocks pulled from your India and USA source files.</p>
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}

      <section className="dashboard-grid sectors-toolbar">
        <article className="feature-card">
          <h3>Market Filter</h3>
          <select value={market} onChange={(event) => setMarket(event.target.value)} className="inline-input">
            {MARKET_OPTIONS.map((option) => (
              <option key={option.value || 'all'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="muted">Switch between India and USA universes after you import both files.</p>
        </article>
        <article className="feature-card">
          <h3>Stock Search</h3>
          <input
            className="inline-input"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter visible stocks by name or symbol"
          />
          <p className="muted">Search applies only to the currently opened sector list.</p>
        </article>
      </section>

      {loadingSectors ? <p>Loading sectors...</p> : null}
      {actionMessage ? <p className="sector-success">{actionMessage}</p> : null}

      {!loadingSectors && sectors.length ? (
        <section className="portfolio-grid">
          {sectors.map((sector) => {
            const isActive = selectedSector?.id === sector.id
            return (
              <article key={sector.id} className={`portfolio-card sector-card ${isActive ? 'sector-card-active' : ''}`}>
                <div>
                  <h3>{sector.name}</h3>
                  <p>{sector.universe_stock_count || 0} imported stock{sector.universe_stock_count === 1 ? '' : 's'}</p>
                </div>
                <div className="actions">
                  <button
                    className="button"
                    type="button"
                    onClick={() => navigate(`/sectors/${sector.id}`)}
                  >
                    View Stocks
                  </button>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() =>
                      navigate('/sectors/quality/top', {
                        state: { market },
                      })
                    }
                  >
                    Quality
                  </button>
                </div>
              </article>
            )
          })}
        </section>
      ) : null}

      {!loadingSectors && !sectors.length ? (
        <section className="analysis-panel">
          <h3>No sector data imported yet</h3>
          <p className="muted">Run the stock-universe import command first, then this page will organize the imported rows into sector groups automatically.</p>
          <code className="sector-command">
            python manage.py import_stock_universe --india "C:\Users\SHREE\Downloads\ind_nifty200list.csv" --usa "C:\Users\SHREE\Downloads\USA Top 200 Stocks.xlsx"
          </code>
        </section>
      ) : null}

      {selectedSector ? (
        <section className="analysis-panel" ref={stockListRef}>
          <div className="analysis-panel-head">
            <h3>{selectedSector.name} Stocks</h3>
            <p className="muted">
              Showing {filteredStocks.length} of {stocks.length} stock{stocks.length === 1 ? '' : 's'}
            </p>
            <div className="actions">
              <button
                type="button"
                className="button button-secondary"
                  onClick={() =>
                    navigate('/quality', {
                      state: {
                        sector: selectedSector,
                        stocks: filteredStocks.slice(0, 10),
                      },
                    })
                  }
                >
                  Quality: Top 10
                </button>
              </div>
            </div>

          {loadingStocks ? <p>Loading sector stocks...</p> : null}

          {!loadingStocks && filteredStocks.length ? (
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
          ) : null}

          {!loadingStocks && !filteredStocks.length ? (
            <p className="muted">No stocks match the current filter for this sector.</p>
          ) : null}
        </section>
      ) : null}

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
            {!portfolioOptions.length ? (
              <p className="form-error">
                No portfolios found. <Link to="/portfolios">Create a portfolio first</Link>.
              </p>
            ) : null}
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

export default SectorsPage
