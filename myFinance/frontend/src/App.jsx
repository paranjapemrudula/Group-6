import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import NewsPage from './pages/NewsPage'
import PortfolioDetailPage from './pages/PortfolioDetailPage'
import PortfolioSentimentReportPage from './pages/PortfolioSentimentReportPage'
import PortfoliosPage from './pages/PortfoliosPage'
import ProfilePage from './pages/ProfilePage'
import RecommendationsPage from './pages/RecommendationsPage'
import SectorsPage from './pages/SectorsPage'
import SentimentPage from './pages/SentimentPage'
import SignupPage from './pages/SignupPage'
import './index.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/news"
        element={
          <ProtectedRoute>
            <NewsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sectors"
        element={
          <ProtectedRoute>
            <SectorsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sentiment"
        element={
          <ProtectedRoute>
            <SentimentPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/recommendations"
        element={
          <ProtectedRoute>
            <RecommendationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/portfolios"
        element={
          <ProtectedRoute>
            <PortfoliosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/portfolios/:id"
        element={
          <ProtectedRoute>
            <PortfolioDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/portfolios/:id/sentiment-report"
        element={
          <ProtectedRoute>
            <PortfolioSentimentReportPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
