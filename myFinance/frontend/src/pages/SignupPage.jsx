import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PublicNavbar from '../components/PublicNavbar'
import { publicApi } from '../lib/api'
import { signup } from '../lib/auth'

function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '',
    email: '',
    phone_number: '',
    password: '',
    confirm_password: '',
    question_one_id: '',
    question_one_answer: '',
    question_two_id: '',
    question_two_answer: '',
  })
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState([])

  useEffect(() => {
    const loadQuestions = async () => {
      try {
        const response = await publicApi.get('/api/security-questions/')
        setQuestions(response.data)
      } catch {
        setError('Could not load security questions.')
      }
    }

    loadQuestions()
  }, [])

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await signup({
        username: form.username,
        email: form.email,
        phone_number: form.phone_number,
        password: form.password,
        confirm_password: form.confirm_password,
        security_answers: [
          { question_id: Number(form.question_one_id), answer: form.question_one_answer },
          { question_id: Number(form.question_two_id), answer: form.question_two_answer },
        ],
      })
      setRecoveryCodes(response.recovery_codes || [])
    } catch (err) {
      const data = err?.response?.data
      const message =
        data?.detail ||
        data?.username?.[0] ||
        data?.password?.[0] ||
        data?.confirm_password?.[0] ||
        data?.security_answers?.[0] ||
        data?.email?.[0] ||
        'Signup failed. Please verify your details.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  if (recoveryCodes.length > 0) {
    return (
      <div className="auth-page">
        <PublicNavbar />
        <div className="auth-wrap container">
          <div className="auth-card">
            <h1>Save Your Recovery Codes</h1>
            <p>These codes are shown only once. Keep them safely for fallback password reset.</p>
            <ul className="dash-list">
              {recoveryCodes.map((code) => (
                <li key={code}>
                  <strong>{code}</strong>
                </li>
              ))}
            </ul>
            <button className="button" type="button" onClick={() => navigate('/home')}>
              Continue to Home
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <PublicNavbar />
      <div className="auth-wrap container">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h1>Create your account</h1>
          <p>Set your login, security questions, and recovery options for safer password reset.</p>

          <label htmlFor="username">Username</label>
          <input id="username" name="username" type="text" value={form.username} onChange={handleChange} required />

          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" value={form.email} onChange={handleChange} required />

          <label htmlFor="phone_number">Phone Number</label>
          <input id="phone_number" name="phone_number" type="text" value={form.phone_number} onChange={handleChange} />

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

          <label htmlFor="confirm_password">Confirm Password</label>
          <input
            id="confirm_password"
            name="confirm_password"
            type="password"
            value={form.confirm_password}
            onChange={handleChange}
            required
            minLength={8}
          />

          <label htmlFor="question_one_id">Security Question 1</label>
          <select id="question_one_id" name="question_one_id" value={form.question_one_id} onChange={handleChange} required>
            <option value="">Select question</option>
            {questions.map((question) => (
              <option key={question.id} value={question.id}>
                {question.question_text}
              </option>
            ))}
          </select>

          <label htmlFor="question_one_answer">Answer 1</label>
          <input
            id="question_one_answer"
            name="question_one_answer"
            type="text"
            value={form.question_one_answer}
            onChange={handleChange}
            required
          />

          <label htmlFor="question_two_id">Security Question 2</label>
          <select id="question_two_id" name="question_two_id" value={form.question_two_id} onChange={handleChange} required>
            <option value="">Select question</option>
            {questions.map((question) => (
              <option key={question.id} value={question.id}>
                {question.question_text}
              </option>
            ))}
          </select>

          <label htmlFor="question_two_answer">Answer 2</label>
          <input
            id="question_two_answer"
            name="question_two_answer"
            type="text"
            value={form.question_two_answer}
            onChange={handleChange}
            required
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
