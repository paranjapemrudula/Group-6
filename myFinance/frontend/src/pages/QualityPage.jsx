import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { publicApi } from '../lib/api'

function QualityPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const sector = location.state?.sector
  const stocks = location.state?.stocks || []

  const [aiLoading, setAiLoading] = useState(false)
  const [aiAnswer, setAiAnswer] = useState('')
  const [chatError, setChatError] = useState('')

  useEffect(() => {
    if (!sector) {
      navigate('/sectors')
    }
  }, [sector, navigate])

  const qualityStocks = useMemo(() => stocks.slice(0, 10), [stocks])

  useEffect(() => {
    const loadInsight = async () => {
      if (!sector) return
      setAiLoading(true)
      setChatError('')
      try {
        const res = await publicApi.post('/api/chat/', {
          message: `Give a concise outlook for the ${sector.name} sector and highlight any quality large/mid-cap names.`,
          session_id: `quality-${sector.id}`,
        })
        setAiAnswer(res.data?.reply || '')
      } catch (err) {
        setChatError('Could not load LangGraph insight right now.')
      } finally {
        setAiLoading(false)
      }
    }
    loadInsight()
  }, [sector])

  if (!sector) {
    return null
  }

  return (
    <AppShell title="Quality Stocks">
      <section className="dashboard-hero">
        <div>
          <h2>{sector.name} Quality Stocks</h2>
          <p className="muted">Showing the top 10 stocks from this sector plus a LangGraph insight.</p>
        </div>
        <div className="actions">
          <Link className="button button-secondary" to="/sectors">
            Back to Sectors
          </Link>
        </div>
      </section>

      <section className="analysis-panel">
        <div className="analysis-panel-head">
          <h3>Top 10 Stocks</h3>
          <p className="muted">Showing {qualityStocks.length} of {stocks.length} provided stocks</p>
        </div>
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
              </tr>
            </thead>
            <tbody>
              {qualityStocks.map((stock) => (
                <tr key={`${stock.market}-${stock.symbol}`}>
                  <td>{stock.symbol}</td>
                  <td>{stock.company_name}</td>
                  <td>{stock.market || '-'}</td>
                  <td>{stock.series || '-'}</td>
                  <td>{stock.isin_code || '-'}</td>
                  <td>{stock.source_file || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="analysis-panel">
        <div className="analysis-panel-head">
          <h3>LangGraph Insight</h3>
          <p className="muted">AI summary tailored to this sector</p>
        </div>
        {aiLoading ? <p>Loading insight...</p> : null}
        {chatError ? <p className="form-error">{chatError}</p> : null}
        {!aiLoading && !chatError ? <p className="sector-success">{aiAnswer || 'No insight yet.'}</p> : null}
      </section>
    </AppShell>
  )
}

export default QualityPage
