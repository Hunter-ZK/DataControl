import axios, { type AxiosRequestConfig } from 'axios'

const http = axios.create({ baseURL: '/api/v1', timeout: 12000 })
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('datacontrol_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.get<{ code: string; data: T }>(url, config)
  return response.data.data
}
async function post<T = any>(url: string, body?: unknown): Promise<T> {
  const response = await http.post<{ code: string; data: T }>(url, body)
  return response.data.data
}
async function remove<T = any>(url: string): Promise<T> {
  const response = await http.delete<{ code: string; data: T }>(url)
  return response.data.data
}

const api = { get, post, delete: remove }
export default api

export const assetApi = {
  overview: () => get('/home/overview'),
  catalogs: () => get('/catalogs'),
  tables: (params?: Record<string, unknown>) => get('/tables', { params }),
  table: (id: string) => get(`/tables/${id}`),
  columns: (params?: Record<string, unknown>) => get('/columns', { params }),
  search: (q: string) => get('/search', { params: { q } }),
  tags: (id: string) => get(`/tables/${id}/tags`),
  changes: (id: string) => get(`/tables/${id}/changes`),
  commonSql: (id: string) => get(`/tables/${id}/common-sql`),
  relations: (id: string) => get(`/relations/tables/${id}`),
  reference: (endpoint: string, keyword?: string) => get(endpoint, { params: keyword ? { keyword } : undefined }),
}

export const authApi = {
  login: (username: string, password: string) => post('/auth/login', { username, password }),
  me: () => get('/auth/me'),
}

export const activityApi = {
  favorites: () => get('/activity/favorites'),
  recent: () => get('/activity/recent-views'),
  history: () => get('/activity/search-history'),
  recordSearch: (keyword: string) => post('/activity/search-history', { keyword }),
  recordView: (assetId: string) => post('/activity/views', { assetType: 'TABLE', assetId }),
}
