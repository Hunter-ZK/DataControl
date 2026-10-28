import axios, { type AxiosRequestConfig } from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  paramsSerializer: { indexes: null },
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('datacontrol_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.get<{ code: string; data: T }>(url, config)
  return response.data.data
}

async function post<T>(url: string, body?: unknown): Promise<T> {
  const response = await http.post<{ code: string; data: T }>(url, body)
  return response.data.data
}

async function remove<T>(url: string): Promise<T> {
  const response = await http.delete<{ code: string; data: T }>(url)
  return response.data.data
}

export interface DatasetBrief {
  assetId: string
  tableName: string
  bizName: string
  layerCode: string
  workspaceCode?: string | null
  catalogCode: string
  status: string
  isCommon?: boolean
  techOwner?: string | null
  updateFreq?: string | null
  dataUpdatedAt?: string | null
}

export interface DatasetPage {
  total: number
  offset: number
  limit: number
  items: DatasetBrief[]
}

export interface SearchItem {
  assetId: string
  assetType: string
  title: string
  technicalName: string
  titleHighlight: string
  technicalNameHighlight: string
  snippet: string
  score: number
  catalogCode?: string | null
  layerCode?: string | null
  status?: string | null
  parentAssetId?: string | null
}

export interface SearchResponse {
  query: string
  total: number
  offset: number
  limit: number
  items: SearchItem[]
  facets: {
    assetTypes: Record<string, number>
    layers: Record<string, number>
    catalogs: Record<string, number>
    statuses: Record<string, number>
  }
}

export interface SearchSuggestion {
  assetId: string
  assetType: string
  title: string
  technicalName: string
}

export interface RelationNode {
  assetId: string
  name: string
  tableName?: string | null
  layerCode?: string | null
  catalogCode?: string | null
  status?: string | null
  isCenter?: boolean
  level?: number
  datasetId?: string
  datasetName?: string
  columnName?: string
  dataType?: string
}

export interface RelationEdge {
  id: number
  source: string
  target: string
  taskName?: string | null
  evidence: string
  transformation?: string | null
  relationType?: string
  sourceDatasetId?: string
  targetDatasetId?: string
}

export interface RelationGraph {
  centerAssetId: string
  centerDatasetId?: string
  depth: number
  direction: string
  truncated: boolean
  nodes: RelationNode[]
  edges: RelationEdge[]
  impactCount?: number
  impactByLayer?: Record<string, number>
}

export interface TableFieldLineage {
  datasetId: string
  nodes: RelationNode[]
  edges: RelationEdge[]
}

export interface SemanticDimension {
  name: string
  label: string
  dataType?: string | null
  codeTableNo?: string | null
  standardNo?: string | null
}

export interface SemanticMetric {
  assetId: string
  metricCode: string
  name: string
  aliases: string[]
  definition?: string | null
  metricKind: string
  aggregation: string
  measureColumn: string
  formula?: string | null
  numeratorMetricCode?: string | null
  denominatorMetricCode?: string | null
  source: {
    assetId: string
    name: string
    tableName?: string | null
    layerCode?: string | null
  }
  time: {
    field: string
    grain?: string | null
    additivity: string
    latestStrategy: string
  }
  validDimensions: SemanticDimension[]
  mandatoryFilters: Array<Record<string, unknown>>
  statSystemCode?: string | null
  caliber?: string | null
  semanticNotes?: string | null
  status: string
  researchPolicy: 'internal_only'
}

export type AgentModelMode = 'deepseek' | 'free-test'

export interface ServerAgentConversation {
  id: string
  serverId?: string | null
  title: string
  sessionId: string | null
  modelMode: AgentModelMode
  pinned: boolean
  createdAt: number
  updatedAt: number
  messages: Array<Record<string, unknown>>
  contextAsset?: Record<string, unknown> | null
  lastRunStatus?: string | null
}

export interface AgentStatus {
  modelMode?: AgentModelMode
  ready: boolean
  mode: string
  source: string
  gatewayUrl: string
  provider: string
  model: string
  sourceMigrated: boolean
  sessionBridgeImplemented: boolean
  integrated: boolean
  realModelAccepted: boolean
  serviceReachable: boolean
  nextGate?: string | null
  reason?: string | null
  sqlExecutionEnabled: boolean
  hiddenReasoningExposed: boolean
}

export type AgentStreamEvent =
  | { type: 'started'; runId: string }
  | { type: 'activity'; event: AgentActivity }
  | { type: 'result'; result: AgentResult }
  | { type: 'cancelled' }
  | { type: 'error'; message: string }

export class AgentTurnCancelledError extends Error {
  constructor() {
    super('Agent run cancelled')
    this.name = 'AgentTurnCancelledError'
  }
}

/** Fetch the actual newline-delimited Agent stream; no simulated progress. */
export async function streamAgentTurn(
  question: string,
  _sessionId: string | null,
  runId: string,
  onEvent: (event: AgentStreamEvent) => void,
  signal: AbortSignal,
  modelMode: AgentModelMode = 'deepseek',
  conversationId: string | null = null,
  displayQuestion: string | null = null,
): Promise<AgentResult> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('datacontrol_token')
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch('/api/v1/agent/query/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      question, runId, modelMode,
      conversationId: conversationId || undefined,
      displayQuestion: displayQuestion || undefined,
      publicGatewayConsent: false,
    }),
    signal,
  })
  if (!response.ok) throw new Error(`Agent streaming request failed (HTTP ${response.status})`)
  if (!response.body) throw new Error('Agent stream is unavailable in this browser')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''
  let result: AgentResult | null = null
  const parseLine = (line: string) => {
    if (!line.trim()) return
    const event = JSON.parse(line) as AgentStreamEvent
    if (event.type === 'error') throw new Error(event.message)
    if (event.type === 'cancelled') throw new AgentTurnCancelledError()
    if (event.type === 'result') result = event.result
    onEvent(event)
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      pending += decoder.decode(value, { stream: true })
      const lines = pending.split('\n')
      pending = lines.pop() || ''
      for (const line of lines) parseLine(line)
    }
    pending += decoder.decode()
    if (pending.trim()) parseLine(pending)
    if (!result) throw new Error('Agent stream ended without a final result')
    return result
  } finally {
    reader.releaseLock()
  }
}

export interface AgentActivity {
  type: string
  phase?: string
  callId?: string
  tool?: string
  status?: string
  input?: unknown
  reason?: string
}

export interface AgentMetricEvidence {
  code?: string | null
  name?: string | null
  sourceEntity?: string | null
  measure?: string | null
  timeField?: string | null
  validDimensions?: string[]
}

export interface AgentDatasetEvidence {
  tableName?: string | null
  name?: string | null
}

export interface AgentEvidence {
  assets?: Array<{ assetId: string; assetType: string; title: string; technicalName?: string; sourceCallId?: string }>
  metrics?: AgentMetricEvidence[]
  datasets?: AgentDatasetEvidence[]
  dimensions?: string[]
  period?: { label: string; resolved: string } | null
  caliber?: string | null
  warnings?: string[]
}

export interface AgentClarificationOption {
  id: string
  label: string
  description: string
  value: string
  metadata?: Record<string, unknown> | null
}

export interface AgentClarification {
  id: string
  question: string
  selection_mode: 'single' | 'multiple'
  options: AgentClarificationOption[]
  allow_custom_input?: boolean
}

export type AgentValidationState = 'passed' | 'failed' | 'not_validated' | 'not_applicable' | 'unknown'
export type AgentSqlOperation = 'query' | 'dml' | 'ddl' | 'access_control' | 'unknown'
export type AgentSqlRiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface AgentValidationIssue {
  code: string
  severity: 'error' | 'warning' | 'info'
  message: string
  suggestion?: string | null
  metadata?: Record<string, unknown> | null
  action?: string
  blocking?: boolean
  auto_fixable?: boolean
}

export interface AgentValidation {
  valid: boolean
  dialect?: string
  issues?: AgentValidationIssue[]
  normalized_sql?: string | null
  statement_type?: string | null
  operation?: AgentSqlOperation
  risk_level?: AgentSqlRiskLevel
  execution_allowed?: boolean
}

export interface AgentResult {
  durationMs?: number
  toolCallCount?: number
  sessionId?: string | null
  answer: string
  summary?: string | null
  stopReason?: string | null
  events?: AgentActivity[]
  sql?: string | null
  validation?: AgentValidation | null
  validationState?: AgentValidationState
  sqlSourceCallId?: string | null
  validationCallId?: string | null
  clarification?: AgentClarification | null
  researchPolicy?: 'internal_only'
  evidence?: AgentEvidence
  sqlExecuted: boolean
  hiddenReasoningExposed: boolean
}

const api = { get, post, delete: remove }
export default api

export const assetApi = {
  overview: () => get<Record<string, unknown>>('/home/overview'),
  catalogs: () => get<unknown[]>('/catalogs'),
  tables: (params?: Record<string, unknown>) => get<unknown[]>('/tables', { params }),
  tablePage: (params?: Record<string, unknown>) => get<DatasetPage>('/tables/page', { params }),
  table: (id: string) => get<Record<string, any>>(`/tables/${id}`),
  columns: (params?: Record<string, unknown>) => get<unknown[]>('/columns', { params }),
  search: (q: string, params?: Record<string, unknown>) =>
    get<SearchResponse>('/search', { params: { q, ...params } }),
  suggest: (q: string, limit = 8) =>
    get<SearchSuggestion[]>('/search/suggest', { params: { q, limit } }),
  tags: (id: string) => get<unknown[]>(`/tables/${id}/tags`),
  changes: (id: string) => get<unknown[]>(`/tables/${id}/changes`),
  commonSql: (id: string) => get<unknown[]>(`/tables/${id}/common-sql`),
  relations: (id: string) => get<unknown>(`/relations/tables/${id}`),
  reference: (endpoint: string, keyword?: string) =>
    get<unknown[]>(endpoint, { params: keyword ? { keyword } : undefined }),
}

export const semanticApi = {
  metric: (code: string) => get<SemanticMetric>(`/semantic/metrics/${code}`),
}

export const relationApi = {
  graph: (id: string, params?: Record<string, unknown>) =>
    get<RelationGraph>(`/relations/graph/${id}`, { params }),
  columnGraph: (id: string, params?: Record<string, unknown>) =>
    get<RelationGraph>(`/relations/columns/${id}`, { params }),
  tableFields: (id: string) => get<TableFieldLineage>(`/relations/fields/table/${id}`),
  impact: (id: string, params?: Record<string, unknown>) =>
    get<RelationGraph>(`/relations/impact/${id}`, { params }),
  path: (source: string, target: string, maxDepth = 8) =>
    get<any>('/relations/path', { params: { source, target, max_depth: maxDepth } }),
}

export const agentApi = {
  conversations: () => get<ServerAgentConversation[]>('/agent/conversations'),
  createConversation: (title: string, modelMode: AgentModelMode, contextAsset?: Record<string, unknown> | null) =>
    post<ServerAgentConversation>('/agent/conversations', { title, modelMode, contextAsset }),
  importConversations: (conversations: Array<Record<string, unknown>>) =>
    post<ServerAgentConversation[]>('/agent/conversations/import', { conversations }),
  editConversation: (id: string, data: { title?: string; pinned?: boolean }) =>
    http.patch<{ code: string; data: ServerAgentConversation }>(`/agent/conversations/${id}`, data).then(r => r.data.data),
  deleteConversation: (id: string) => remove<{ deleted: boolean }>(`/agent/conversations/${id}`),
  runStatus: (runId: string) => get<{ status: string; runId: string; modelMode: AgentModelMode }>(`/agent/runs/${runId}`),
  status: (modelMode: AgentModelMode = 'deepseek') =>
    get<AgentStatus>('/agent/status', { params: { modelMode } }),
  query: (question: string, sessionId?: string | null, modelMode: AgentModelMode = 'deepseek') =>
    post<AgentResult>('/agent/query', {
      question, sessionId: sessionId || undefined, modelMode,
      publicGatewayConsent: modelMode === 'free-test',
    }),
  stream: streamAgentTurn,
  cancel: (runId: string) => post<{ cancelled: boolean }>(`/agent/query/${runId}/cancel`),
}

export const authApi = {
  login: (username: string, password: string) => post<any>('/auth/login', { username, password }),
  me: () => get<any>('/auth/me'),
}

export const activityApi = {
  favorites: () => get<any[]>('/activity/favorites'),
  recent: () => get<any[]>('/activity/recent-views'),
  history: () => get<any[]>('/activity/search-history'),
  recordSearch: (keyword: string) => post('/activity/search-history', { keyword }),
  recordView: (assetId: string) => post('/activity/views', { assetType: 'TABLE', assetId }),
}
