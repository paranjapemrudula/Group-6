import { Navigate } from 'react-router-dom'
import { getAccessToken } from '../lib/auth'

function ProtectedRoute({ children }) {
  const token = getAccessToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default ProtectedRoute
