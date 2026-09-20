import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 12000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('datacontrol_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use((response) => response.data.data)

export default api

export const assetApi = {
  overview: () => api.get('/home/overview'),
  catalogs: () => api.get('/catalogs'),
  tables: (params?: Record<string, unknown>) => api.get('/tables', { params }),
  table: (id: string) => api.get(`/tables/${id}`),
  columns: (params?: Record<string, unknown>) => api.get('/columns', { params }),
  search: (q: string) => api.get('/search', { params: { q } }),
  tags: (id: string) => api.get(`/tables/${id}/tags`),
  changes: (id: string) => api.get(`/tables/${id}/changes`),
  commonSql: (id: string) => api.get(`/tables/${id}/common-sql`),
  relations: (id: string) => api.get(`/relations/tables/${id}`),
  reference: (endpoint: string, keyword?: string) => api.get(endpoint, { params: keyword ? { keyword } : undefined }),
}

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
}

export const activityApi = {
  favorites: () => api.get('/activity/favorites'),
  recent: () => api.get('/activity/recent-views'),
  history: () => api.get('/activity/search-history'),
  recordSearch: (keyword: string) => api.post('/activity/search-history', { keyword }),
  recordView: (assetId: string) => api.post('/activity/views', { assetType: 'TABLE', assetId }),
}
