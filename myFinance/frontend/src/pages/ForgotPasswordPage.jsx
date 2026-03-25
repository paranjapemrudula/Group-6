import { useState } from 'react'
import { Link } from 'react-router-dom'
import PublicNavbar from '../components/PublicNavbar'
import { publicApi } from '../lib/api'

function ForgotPasswordPage() {
  const [step, setStep] = useState('start')
  const [username, setUsername] = useState('')
  const [startData, setStartData] = useState(null)
  const [verificationMode, setVerificationMode] = useState('fallback')
  const [otp, setOtp] = useState('')
  const [answers, setAnswers] = useState({})
  const [recoveryCode, setRecoveryCode] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleStart = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const response = await publicApi.post('/api/password-reset/start/', { username })
      setStartData(response.data)
      setVerificationMode(response.data.totp_enabled ? 'totp' : 'fallback')
      setStep('verify')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not start password reset.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response =
        verificationMode === 'totp'
          ? await publicApi.post('/api/password-reset/totp/', { username, otp })
          : await publicApi.post('/api/password-reset/fallback/', {
              username,
              security_answers: (startData?.security_questions || []).map((question) => ({
                question_id: question.question_id,
                answer: answers[question.question_id] || '',
              })),
              recovery_code: recoveryCode,
            })
      setResetToken(response.data.reset_token)
      setStep('confirm')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Verification failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await publicApi.post('/api/password-reset/confirm/', {
        reset_token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(response.data.message || 'Password updated successfully.')
      setStep('done')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not update password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <PublicNavbar />
      <div className="auth-wrap container">
        <div className="auth-card">
          <h1>Reset Password</h1>
          <p>Use authenticator OTP if enabled, or fall back to security questions and one recovery code.</p>

          {step === 'start' && (
            <form onSubmit={handleStart}>
              <label htmlFor="reset-username">Username</label>
              <input
                id="reset-username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
              {error && <p className="form-error">{error}</p>}
              <button className="button" type="submit" disabled={loading}>
                {loading ? 'Checking...' : 'Continue'}
              </button>
            </form>
          )}

          {step === 'verify' && (
            <form onSubmit={handleVerify}>
              {startData?.totp_enabled && (
                <div className="actions">
                  <button
                    className={`button ${verificationMode === 'totp' ? '' : 'button-secondary'}`}
                    type="button"
                    onClick={() => setVerificationMode('totp')}
                  >
                    Authenticator
                  </button>
                  <button
                    className={`button ${verificationMode === 'fallback' ? '' : 'button-secondary'}`}
                    type="button"
                    onClick={() => setVerificationMode('fallback')}
                  >
                    Questions + Recovery Code
                  </button>
                </div>
              )}

              {verificationMode === 'totp' ? (
                <>
                  <label htmlFor="reset-otp">Authenticator OTP</label>
                  <input
                    id="reset-otp"
                    type="text"
                    value={otp}
                    onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                    maxLength={6}
                    required
                  />
                </>
              ) : (
                <>
                  {(startData?.security_questions || []).map((question) => (
                    <div key={question.question_id}>
                      <label htmlFor={`question-${question.question_id}`}>
                        {question.question_text}
                      </label>
                      <input
                        id={`question-${question.question_id}`}
                        type="text"
                        value={answers[question.question_id] || ''}
                        onChange={(event) =>
                          setAnswers((prev) => ({
                            ...prev,
                            [question.question_id]: event.target.value,
                          }))
                        }
                        required
                      />
                    </div>
                  ))}

                  <label htmlFor="recovery-code">Recovery Code</label>
                  <input
                    id="recovery-code"
                    type="text"
                    value={recoveryCode}
                    onChange={(event) => setRecoveryCode(event.target.value)}
                    required
                  />
                </>
              )}

              {error && <p className="form-error">{error}</p>}
              <button className="button" type="submit" disabled={loading}>
                {loading ? 'Verifying...' : 'Verify'}
              </button>
            </form>
          )}

          {step === 'confirm' && (
            <form onSubmit={handleConfirm}>
              <label htmlFor="new-password">New Password</label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                minLength={8}
              />

              <label htmlFor="confirm-new-password">Confirm Password</label>
              <input
                id="confirm-new-password"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={8}
              />

              {error && <p className="form-error">{error}</p>}
              <button className="button" type="submit" disabled={loading}>
                {loading ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          )}

          {step === 'done' && (
            <>
              <p>{success}</p>
              <p className="auth-foot">
                Return to <Link to="/login">Login</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ForgotPasswordPage