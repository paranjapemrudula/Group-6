import { Link, useNavigate } from 'react-router-dom'
import AssistantChatbot from './AssistantChatbot'
import MarketTicker from './MarketTicker'
import { clearAuth, getCurrentUser } from '../lib/auth'

const protectedLinks = [
  { to: '/home', label: 'Home' },
  { to: '/news', label: 'News' },
  { to: '/sentiment', label: 'Sentiment' },
  { to: '/portfolios', label: 'Portfolios' },
  { to: '/profile', label: 'Profile' },
]

function AppShell({ title, children }) {
  const navigate = useNavigate()
  const user = getCurrentUser()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <div className="app-page">
      <MarketTicker />
      <header className="topbar">
        <div className="brand-block">
          <Link className="brand-link" to="/home">
            MyFinance
          </Link>
          <span className="brand-tagline">{title}</span>
        </div>
        <nav className="topnav-links">
          {protectedLinks.map((link) => (
            <Link key={link.to} to={link.to} className="topnav-link">
              {link.label}
            </Link>
          ))}
          <button type="button" className="topnav-link topnav-logout" onClick={handleLogout}>
            Logout
          </button>
        </nav>
        <div className="user-chip">{user?.username || 'User'}</div>
      </header>
      <main className="container content">{children}</main>
      <AssistantChatbot />
    </div>
  )
}

export default AppShell
