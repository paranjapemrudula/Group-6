import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
})

export const publicApi = axios.create({
  baseURL: API_BASE_URL,
})

publicApi.interceptors.request.use((config) => {
  if (config.headers) {
    delete config.headers.Authorization
  }
  return config
})

export function setAuthHeader(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common.Authorization
  }
  delete publicApi.defaults.headers.common.Authorization
}

// 🆕 Add request interceptor to ALWAYS attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 🆕 Auto-refresh token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const refresh = localStorage.getItem('refreshToken')
        if (refresh) {
          const res = await publicApi.post('/api/token/refresh/', {
            refresh: refresh
          })
          const newToken = res.data.access
          localStorage.setItem('accessToken', newToken)
          setAuthHeader(newToken)
          error.config.headers.Authorization = `Bearer ${newToken}`
          return axios(error.config)
        }
      } catch (err) {
        localStorage.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)