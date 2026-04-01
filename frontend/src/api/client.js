import axios from 'axios'

// Use environment variable for API base URL, fallback to /api for production
const apiBaseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 15000,
})

api.interceptors.response.use(
  (res) => {
    console.log('✅ API Response interceptor:', res.status, res.config.url);
    return res.data;
  },
  (err) => {
    console.error('❌ API Error interceptor:', err.response?.status, err.config?.url);
    console.error('Error data:', err.response?.data);

    // Create a more detailed error object
    const error = new Error(
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Network error'
    );
    error.response = err.response;
    error.status = err.response?.status;

    return Promise.reject(error);
  }
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
