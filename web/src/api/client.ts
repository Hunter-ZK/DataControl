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

async function fallbackShortSearch(query: string, limit: number) {
  const results = await Promise.allSettled([
    get<any[]>('/tables', { params: { limit: 200, keyword: query } }),
    get<any[]>('/columns', { params: { limit: 500, keyword: query } }),
    get<any[]>('/metrics', { params: { keyword: query } }),
    get<any[]>('/code-tables', { params: { keyword: query, limit: 500 } }),
    get<any[]>('/data-standards', { params: { keyword: query } }),
    get<any[]>('/word-roots', { params: { keyword: query } }),
    get<any[]>('/stat-systems'),
  ])
  const rows = results.map((result) => result.status === 'fulfilled' ? result.value : [])
  const [tables, columns, metrics, codeTables, standards, roots, systems] = rows
  const needle = query.toLowerCase()
  const mapRows = (items: any[], assetType: string, title: (row: any) => string, technical: (row: any) => string) =>
    items.map((row) => ({
      asset_id: row.assetId,
      asset_type: assetType,
      title: title(row),
      technical_name: technical(row),
      fallbackMatch: true,
    })).filter((row) => row.asset_id && row.title && row.technical_name)
  const statMatches = systems.filter((row: any) =>
    `${row.code} ${row.name} ${row.issuer || ''} ${row.documentNo || ''} ${row.version || ''}`.toLowerCase().includes(needle),
  )
  return [
    ...mapRows(tables, 'TABLE', (row) => row.bizName, (row) => row.tableName),
    ...mapRows(columns, 'COLUMN', (row) => row.cnName || row.columnName, (row) => row.columnName),
    ...mapRows(metrics, 'METRIC', (row) => row.name, (row) => row.metricCode),
    ...mapRows(codeTables, 'CODE_TABLE', (row) => row.name, (row) => row.codeTableNo),
    ...mapRows(standards, 'DATA_STANDARD', (row) => row.name, (row) => row.standardNo),
    ...mapRows(roots, 'WORD_ROOT', (row) => row.cnName || row.root, (row) => row.root),
    ...mapRows(statMatches, 'STAT_SYSTEM', (row) => row.name, (row) => row.code),
  ].slice(0, limit)
}

export const assetApi = {
  overview: () => get('/home/overview'),
  catalogs: () => get('/catalogs'),
  tables: (params?: Record<string, unknown>) => get('/tables', { params }),
  table: (id: string) => get(`/tables/${id}`),
  columns: (params?: Record<string, unknown>) => get('/columns', { params }),
  search: (q: string, limit = 100) => {
    const query = q.trim()
    if (!query) return Promise.resolve([])
    if ([...query].length < 3) return fallbackShortSearch(query, limit)
    return get('/search', { params: { q: query, limit } })
  },
  tags: (id: string) => get(`/tables/${id}/tags`),
  changes: (id: string) => get(`/tables/${id}/changes`),
  commonSql: (id: string) => get(`/tables/${id}/common-sql`),
  relations: (id: string) => get(`/relations/tables/${id}`),
  reference: (endpoint: string, keyword?: string, extraParams?: Record<string, unknown>) => get(endpoint, { params: { ...extraParams, ...(keyword ? { keyword } : {}) } }),
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
