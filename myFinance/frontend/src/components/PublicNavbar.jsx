import { Link } from 'react-router-dom'
import MarketTicker from './MarketTicker'

function PublicNavbar() {
  return (
    <>
      <MarketTicker />
      <header className="topbar">
        <div className="brand-block">
          <Link className="brand-link" to="/">
            MyFinance
          </Link>
          <span className="brand-tagline">Smart investing workspace</span>
        </div>
        <nav className="topnav-links">
          <a className="topnav-link" href="/">
            Markets
          </a>
          <Link className="topnav-link" to="/login">
            Login
          </Link>
          <Link className="topnav-link topnav-cta" to="/signup">
            Start Free
          </Link>
        </nav>
      </header>
    </>
  )
}

export default PublicNavbar
