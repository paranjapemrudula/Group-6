import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import AppShell from '../components/AppShell'
import { publicApi } from '../lib/api'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const clusterColor = (cluster) => {
  if (cluster === 'Good Quality') return 'rgba(34, 197, 94, 0.7)'
  if (cluster === 'Bad Quality') return 'rgba(239, 68, 68, 0.7)'
  return 'rgba(148, 163, 184, 0.6)'
}

function QualitySectorsPage() {
  const location = useLocation()
  const [sectors, setSectors] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [openChart, setOpenChart] = useState({})

  const market = location.state?.market || ''

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const suffix = market ? `?market=${encodeURIComponent(market)}` : ''
        const res = await publicApi.get(`/api/sectors/quality/top/${suffix}`)
        setSectors(res.data || [])
        setError('')
      } catch {
        setError('Could not load sectors for quality view.')
        setSectors([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [market])

  const clustered = useMemo(() => sectors, [sectors])

  return (
    <AppShell title="Quality Sectors">
      <section className="dashboard-hero">
        <div>
          <h2>Quality Sectors (Top 10)</h2>
          <p className="muted">
            Top sectors by average closing price of their top 3 stocks. Each stock shows min / max / latest close and
            is clustered by relative strength.
          </p>
        </div>
        <div className="actions">
          <Link className="button button-secondary" to="/sectors">
            Back to Sectors
          </Link>
        </div>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading sectors...</p> : null}

      {!loading && clustered.length ? (
        <section className="analysis-panel">
          {clustered.map((sector, index) => {
            const stockChart = {
              labels: (sector.stocks || []).map((s) => s.symbol),
              datasets: [
                {
                  label: 'Close Price',
                  data: (sector.stocks || []).map((s) => s.close_price || 0),
                  backgroundColor: (sector.stocks || []).map((s) => clusterColor(s.cluster)),
                  borderRadius: 6,
                },
              ],
            }

            return (
              <article key={sector.id} className="analysis-subpanel">
                <div className="analysis-panel-head">
                  <div>
                    <h3>
                      #{index + 1} {sector.name}
                    </h3>
                    <p className="muted">
                      {sector.universe_stock_count || 0} stocks imported • Avg close{' '}
                      {sector.avg_price?.toFixed ? sector.avg_price.toFixed(2) : sector.avg_price}
                    </p>
                  </div>
                  <div className="cluster-actions">
                    <div className="cluster-badge">{sector.cluster}</div>
                    <button
                      type="button"
                      className="button button-secondary"
                      onClick={() =>
                        setOpenChart((prev) => ({
                          ...prev,
                          [sector.id]: !prev[sector.id],
                        }))
                      }
                    >
                      {openChart[sector.id] ? 'Hide Cluster Graph' : 'Show Cluster Graph'}
                    </button>
                  </div>
                </div>

                <div className="stocks-table-wrap">
                  <table className="stocks-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Company</th>
                        <th>Market</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Close</th>
                        <th>Cluster</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(sector.stocks || []).map((stock) => (
                        <tr key={`${sector.id}-${stock.symbol}`}>
                          <td>{stock.symbol}</td>
                          <td>{stock.company_name}</td>
                          <td>{stock.market || '-'}</td>
                          <td>{stock.min_price?.toFixed ? stock.min_price.toFixed(2) : stock.min_price}</td>
                          <td>{stock.max_price?.toFixed ? stock.max_price.toFixed(2) : stock.max_price}</td>
                          <td>{stock.close_price?.toFixed ? stock.close_price.toFixed(2) : stock.close_price}</td>
                          <td>{stock.cluster}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {openChart[sector.id] ? (
                  <div className="chart-wrap">
                    <Bar data={stockChart} options={{ responsive: true, plugins: { legend: { display: false } } }} />
                  </div>
                ) : null}
              </article>
            )
          })}
        </section>
      ) : null}
    </AppShell>
  )
}

export default QualitySectorsPage
