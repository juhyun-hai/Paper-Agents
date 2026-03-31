import axios from 'axios'

// Use environment variable for API base URL, fallback to /api for production
const apiBaseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 15000,
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => Promise.reject(err?.response?.data || err.message),
)

export const searchPapers = (params) => api.get('/search', { params })
export const autocomplete = (q) => api.get('/autocomplete', { params: { q } })
export const getPaper = (arxivId) => api.get(`/papers/${arxivId}`)
export const getRecommendations = (arxivId) => api.get(`/recommend/${arxivId}`)
export const getGraph = (params) => api.get('/graph', { params })
export const getMiniGraph = (arxivId) => api.get(`/graph/mini/${arxivId}`)
export const getStats = () => api.get('/stats')
export const getTrends = (days = 30) => api.get('/trends', { params: { days } })
export const getCategories = () => api.get('/categories')

export default api
