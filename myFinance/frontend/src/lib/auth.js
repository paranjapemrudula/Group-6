import { api, publicApi, setAuthHeader } from './api'

const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_TOKEN_KEY = 'refreshToken'
const USER_KEY = 'user'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getCurrentUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearAuth() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  setAuthHeader(null)
}

export async function login(credentials) {
  const response = await publicApi.post('/api/login/', credentials)
  const { access, refresh } = response.data

  localStorage.setItem(ACCESS_TOKEN_KEY, access)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  setAuthHeader(access)

  const me = await api.get('/api/me/')
  localStorage.setItem(USER_KEY, JSON.stringify(me.data))
  return me.data
}

export async function signup(payload) {
  const response = await publicApi.post('/api/signup/', payload)
  const { access, refresh, user } = response.data

  localStorage.setItem(ACCESS_TOKEN_KEY, access)
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  setAuthHeader(access)
  return user
}

export function initializeAuth() {
  const token = getAccessToken()
  if (token) {
    setAuthHeader(token)
  }
}
