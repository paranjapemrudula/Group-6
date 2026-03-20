import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PublicNavbar from '../components/PublicNavbar'
import { signup } from '../lib/auth'

function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      await signup(form)
      navigate('/home')
    } catch (err) {
      const data = err?.response?.data
      const message =
        data?.detail ||
        data?.username?.[0] ||
        data?.password?.[0] ||
        data?.email?.[0] ||
        'Signup failed. Please verify your details.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <PublicNavbar />
      <div className="auth-wrap container">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h1>Create your account</h1>
          <p>Start tracking portfolios and unlock analysis endpoints.</p>

          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            type="text"
            value={form.username}
            onChange={handleChange}
            required
          />

          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" value={form.email} onChange={handleChange} required />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            required
            minLength={8}
          />

          {error ? <p className="form-error">{error}</p> : null}

          <button className="button" type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Sign up'}
          </button>
          <p className="auth-foot">
            Already registered? <Link to="/login">Go to login</Link>
          </p>
        </form>
      </div>
    </div>
  )
}

export default SignupPage
