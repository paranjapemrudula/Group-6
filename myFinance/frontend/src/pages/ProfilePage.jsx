import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import { getCurrentUser } from '../lib/auth'
import { api } from '../lib/api'

function ProfilePage() {
  const [user, setUser] = useState(getCurrentUser())
  const [portfolios, setPortfolios] = useState([])
  const [stockTotals, setStockTotals] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const [meResponse, portfolioResponse] = await Promise.all([api.get('/api/me/'), api.get('/api/portfolios/')])
        setUser(meResponse.data)
        setPortfolios(portfolioResponse.data)

        const stocksResponses = await Promise.all(
          portfolioResponse.data.map((item) => api.get(`/api/portfolios/${item.id}/stocks/`))
        )
        const totals = {}
        portfolioResponse.data.forEach((portfolio, index) => {
          totals[portfolio.id] = stocksResponses[index].data.length
        })
        setStockTotals(totals)
      } catch {
        setError('Could not load profile data.')
      } finally {
        setLoading(false)
      }
    }

    loadProfile()
  }, [])

  const totalStocks = useMemo(
    () => Object.values(stockTotals).reduce((sum, current) => sum + Number(current || 0), 0),
    [stockTotals]
  )

  const profileInsight = useMemo(() => {
    if (portfolios.length === 0) return 'Start by creating at least one portfolio for a focused strategy.'
    if (totalStocks < 3) return 'You are just getting started. Add more stocks to unlock richer analytics.'
    return 'Great progress. Your profile is ready for advanced chart-based analysis in the next phase.'
  }, [portfolios.length, totalStocks])

  return (
    <AppShell title="Profile">
      <section className="dashboard-hero">
        <div>
          <h2>Profile Overview</h2>
          <p>Account snapshot, portfolio health, and personalized investing notes.</p>
        </div>
        <Link className="button button-secondary" to="/portfolios">
          Open Portfolios
        </Link>
      </section>

      {error ? <p className="form-error">{error}</p> : null}
      {loading ? <p>Loading profile...</p> : null}

      {!loading && (
        <>
          <section className="dashboard-grid">
            <article className="feature-card">
              <h3>Account</h3>
              <p>
                <strong>User:</strong> {user?.username || 'N/A'}
              </p>
              <p>
                <strong>Email:</strong> {user?.email || 'N/A'}
              </p>
              <p>
                <strong>Joined:</strong>{' '}
                {user?.date_joined ? new Date(user.date_joined).toLocaleDateString() : 'N/A'}
              </p>
            </article>
            <article className="feature-card">
              <h3>My Insights</h3>
              <p>{profileInsight}</p>
              <p className="muted">Keep at least one core portfolio and one experimental portfolio for better discipline.</p>
            </article>
          </section>

          <section className="feature-card">
            <h3>Your Portfolios</h3>
            {portfolios.length === 0 ? (
              <p>No portfolios created yet.</p>
            ) : (
              <ul className="dash-list">
                {portfolios.map((item) => (
                  <li key={item.id}>
                    <Link to={`/portfolios/${item.id}`}>{item.name}</Link> <span className="muted">({stockTotals[item.id] || 0} stocks)</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </AppShell>
  )
}

export default ProfilePage
