<template>
  <div class="dc-page agent-screen">
    <div class="dc-container agent-page">
      <header class="agent-head">
        <div>
          <span class="dc-eyebrow">INTELLIGENT DATA Q&A</span>
          <h1>智能问数</h1>
          <p>面向数据查询与开发场景检索指标、资产和口径，生成经过静态校验的 MaxCompute SQL。系统只生成和校验，不执行生产 SQL。</p>
        </div>
        <div class="head-actions">
          <span class="service-status" :class="{ ready: status?.ready }"><i></i>{{ status?.ready ? '服务正常' : '服务未就绪' }}</span>
        </div>
      </header>

      <section class="agent-workspace dc-card">
        <aside class="history-pane">
          <div class="history-head">
            <div>
              <span>对话记录</span>
              <b>{{ conversations.length }}</b>
            </div>
            <button class="history-new" :disabled="loading" @click="newSession"><Plus :size="16" />新会话</button>
          </div>

          <div class="history-scroll">
            <template v-if="conversationGroups.length">
              <section v-for="group in conversationGroups" :key="group.label" class="history-group">
                <div class="history-group-title">{{ group.label }}</div>
                <button
                  v-for="conversation in group.items"
                  :key="conversation.id"
                  class="history-item"
                  :class="{ active: conversation.id === activeConversationId }"
                  :disabled="loading"
                  @click="selectConversation(conversation)"
                >
                  <div class="history-item-main">
                    <MessageSquare :size="15" />
                    <span>{{ conversation.title }}</span>
                  </div>
                  <div class="history-item-actions" @click.stop>
                    <button title="重命名" @click="renameConversation(conversation)"><Pencil :size="13" /></button>
                    <button title="删除" @click="deleteConversation(conversation)"><Trash2 :size="13" /></button>
                  </div>
                </button>
              </section>
            </template>
            <div v-else class="history-empty">
              <MessageSquare :size="20" />
              <b>暂无历史对话</b>
              <span>发起第一次问数后，会自动保存在当前浏览器。</span>
            </div>
          </div>

          <div class="history-foot"><ShieldCheck :size="13" />对话保存在当前浏览器</div>
        </aside>

        <section class="chat-shell">
          <div v-if="contextAsset" class="context-strip">
            <Database :size="17" />
            <div><span>当前数据资产</span><b>{{ contextAsset.bizName || contextAsset.tableName }}</b><code>{{ contextAsset.tableName }}</code></div>
            <button @click="clearContext"><X :size="15" />清除</button>
          </div>
          <div v-if="!status?.ready" class="runtime-warning"><TriangleAlert :size="18" /><span>智能问数服务暂未就绪，请确认本地 Agent 服务已启动后重试。</span></div>

          <div ref="messageBox" class="messages">
            <div v-if="messages.length === 0" class="welcome">
              <div class="welcome-icon"><Sparkles :size="26" /></div>
              <h2>想查什么数据？</h2>
              <p>我会先检索可信事实，再确认指标、资产和统计口径；需要 SQL 时会给出静态校验结果。</p>
              <div class="prompt-grid">
                <button v-for="item in quickPrompts" :key="item" @click="usePrompt(item)">{{ item }}<ArrowUpRight :size="15" /></button>
              </div>
            </div>

            <article v-for="(item, index) in messages" :key="index" class="message" :class="item.role">
              <div v-if="item.role === 'user'" class="user-bubble">{{ item.text }}</div>
              <div v-else class="assistant-answer">
                <div class="answer-label"><span class="agent-avatar"><Sparkles :size="16" /></span><b>DataAgent</b></div>
                <div class="answer-summary">{{ item.summary || firstLine(item.text) }}</div>

                <div v-if="answerBlocks(item.text, item.summary).length" class="answer-body">
                  <template v-for="(block, blockIndex) in answerBlocks(item.text, item.summary)" :key="blockIndex">
                    <div v-if="block.type === 'key'" class="answer-key"><b>{{ block.label }}</b><span>{{ block.text }}</span></div>
                    <div v-else-if="block.type === 'bullet'" class="answer-bullet"><i></i><span>{{ block.text }}</span></div>
                    <p v-else>{{ block.text }}</p>
                  </template>
                </div>

                <section v-if="processSteps(item.events).length" class="analysis-trace">
                  <div class="trace-head">
                    <span class="trace-icon"><BrainCircuit :size="17" /></span>
                    <div><b>分析过程</b><span>基于实际工具调用生成的可审计执行记录，不展示模型隐藏思维。</span></div>
                  </div>
                  <div class="trace-flow">
                    <div v-for="(step, stepIndex) in processSteps(item.events)" :key="`${step.callId}-${stepIndex}`" class="trace-step" :class="step.status">
                      <span class="trace-index">{{ stepIndex + 1 }}</span>
                      <span>{{ step.label }}</span>
                      <CheckCircle2 v-if="step.status === 'done'" :size="14" />
                      <TriangleAlert v-else-if="step.status === 'error'" :size="14" />
                      <LoaderCircle v-else class="spin" :size="14" />
                    </div>
                  </div>
                </section>

                <div v-if="hasEvidence(item.evidence)" class="evidence-area">
                  <div v-if="item.evidence?.period" class="evidence-row"><span>统计期间</span><b>{{ item.evidence.period.label }}</b></div>
                  <div v-if="item.evidence?.metrics?.length" class="evidence-row"><span>使用指标</span><div class="chips"><span v-for="(metric, metricIndex) in item.evidence.metrics" :key="metric.code || metric.name || `metric-${metricIndex}`" class="evidence-chip metric"><BarChart3 :size="14" />{{ metric.name || metric.code }}</span></div></div>
                  <div v-if="item.evidence?.datasets?.length" class="evidence-row"><span>引用资产</span><div class="chips"><span v-for="(table, tableIndex) in item.evidence.datasets.slice(0, 4)" :key="table.tableName || table.name || `dataset-${tableIndex}`" class="evidence-chip"><Database :size="14" />{{ shortTable(table.tableName || table.name || '') }}</span></div></div>
                  <div v-if="item.evidence?.dimensions?.length" class="evidence-row"><span>分析维度</span><div class="chips"><span v-for="dimension in item.evidence.dimensions" :key="dimension" class="evidence-chip neutral">{{ dimensionName(dimension) }} <code>{{ dimension }}</code></span></div></div>
                  <div v-if="item.evidence?.caliber" class="caliber"><span>统计口径</span><p>{{ item.evidence.caliber }}</p></div>
                </div>

                <section v-if="item.sql" class="sql-card">
                  <div class="block-head">
                    <div class="sql-head-main">
                      <Code2 :size="16" />
                      <b>生成 SQL</b>
                      <span class="sql-type">{{ statementLabel(item.validation) }}</span>
                      <span class="sql-state" :class="validationTone(item)">{{ sqlStatusText(item) }}</span>
                      <span v-if="showRisk(item.validation)" class="risk-chip" :class="`risk-${item.validation?.risk_level}`">{{ riskLabel(item.validation) }}</span>
                    </div>
                    <button @click="copySql(displaySql(item))"><Copy :size="15" />复制</button>
                  </div>
                  <pre>{{ displaySql(item) }}</pre>
                </section>

                <section v-if="item.sql" class="validation-panel" :class="validationTone(item)">
                  <div class="validation-head">
                    <span class="validation-icon">
                      <CheckCircle2 v-if="validationState(item) === 'passed'" :size="19" />
                      <TriangleAlert v-else :size="19" />
                    </span>
                    <div>
                      <b>{{ validationTitle(item) }}</b>
                      <p>{{ validationDescription(item) }}</p>
                    </div>
                  </div>

                  <div class="validation-facts">
                    <div><span>方言</span><b>{{ item.validation?.dialect || 'MaxCompute' }}</b></div>
                    <div><span>语句类型</span><b>{{ statementLabel(item.validation) }}</b></div>
                    <div><span>风险等级</span><b>{{ riskLabel(item.validation) }}</b></div>
                    <div><span>执行状态</span><b>不会执行</b></div>
                  </div>

                  <div v-if="validationIssues(item.validation).length" class="issue-list">
                    <div v-for="issue in validationIssues(item.validation)" :key="`${issue.code}-${issue.message}`" class="issue-row" :class="`issue-${issue.severity}`">
                      <span class="issue-badge">{{ severityLabel(issue.severity) }}</span>
                      <div>
                        <b>{{ issue.message }}</b>
                        <p v-if="issue.suggestion">{{ issue.suggestion }}</p>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="validationState(item) === 'passed'" class="validation-empty"><CheckCircle2 :size="16" />静态校验未发现阻断项。</div>
                  <div v-else-if="validationState(item) === 'not_validated'" class="validation-empty pending"><TriangleAlert :size="16" />当前 SQL 尚未完成静态校验，不应显示为可信结果。</div>
                </section>
              </div>
            </article>

            <article v-if="loading" class="message assistant">
              <div class="assistant-answer loading-answer">
                <div class="answer-label"><span class="agent-avatar"><LoaderCircle class="spin" :size="16" /></span><b>DataAgent 正在分析</b></div>
                <p>正在理解问题并检索可信事实；如需 SQL，将继续完成生成与静态校验。</p>
                <div class="loading-steps"><span>理解问题</span><span>检索事实</span><span>组织答案</span></div>
              </div>
            </article>
          </div>

          <div class="composer-wrap">
            <div class="composer" :class="{ disabled: !status?.ready }">
              <textarea ref="composer" v-model="question" rows="1" :disabled="!status?.ready || loading" @input="resizeComposer" @keydown.enter.exact.prevent="submit" placeholder="输入你的问题，例如：本期各地区贷款余额是多少？" />
              <button class="send" :disabled="!status?.ready || loading || !question.trim()" @click="submit"><Send :size="19" /></button>
            </div>
            <div class="composer-hint"><span>Enter 发送 · Shift+Enter 换行</span><span><ShieldCheck :size="14" />静态校验 · 生产 SQL 不执行</span></div>
          </div>
        </section>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowUpRight,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Code2,
  Copy,
  Database,
  LoaderCircle,
  MessageSquare,
  Pencil,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  TriangleAlert,
  X,
} from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  agentApi,
  assetApi,
  type AgentActivity,
  type AgentEvidence,
  type AgentResult,
  type AgentStatus,
  type AgentValidation,
  type AgentValidationIssue,
  type AgentValidationState,
} from '@/api/client'

type Message = {
  role: 'user' | 'assistant'
  text: string
  summary?: string | null
  sql?: string | null
  validation?: AgentValidation | null
  validationState?: AgentValidationState
  events?: AgentActivity[]
  evidence?: AgentEvidence
}

type ContextAsset = { assetId: string; tableName: string; bizName?: string | null }
type Conversation = {
  id: string
  title: string
  sessionId: string | null
  createdAt: number
  updatedAt: number
  messages: Message[]
  contextAsset?: ContextAsset | null
}
type AnswerBlock = { type: 'paragraph' | 'bullet' | 'key'; text: string; label?: string }
type ProcessStep = { callId: string; label: string; status: 'done' | 'error' | 'running' }

const STORAGE_KEY = 'datacontrol_agent_conversations_v1'
const ACTIVE_KEY = 'datacontrol_agent_active_conversation_v1'
const MAX_CONVERSATIONS = 40
const MAX_MESSAGES_PER_CONVERSATION = 80

const route = useRoute()
const router = useRouter()
const status = ref<AgentStatus | null>(null)
const question = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const messageBox = ref<HTMLElement | null>(null)
const composer = ref<HTMLTextAreaElement | null>(null)
const sessionId = ref<string | null>(null)
const contextAsset = ref<ContextAsset | null>(null)
const conversations = ref<Conversation[]>([])
const activeConversationId = ref<string | null>(null)

const quickPrompts = [
  '本期各地区贷款余额是多少？',
  '本期各机构普惠贷款余额',
  '本期不良贷款余额怎么统计？',
  '帮我生成贷款快照表的 MaxCompute 查询 SQL',
  'region_code 是什么字段？',
  '贷款余额使用哪张数据表？',
]

const conversationGroups = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const weekAgo = today - 6 * 24 * 60 * 60 * 1000
  const groups = [
    { label: '今天', items: [] as Conversation[] },
    { label: '近 7 天', items: [] as Conversation[] },
    { label: '更早', items: [] as Conversation[] },
  ]
  for (const conversation of [...conversations.value].sort((a, b) => b.updatedAt - a.updatedAt)) {
    if (conversation.updatedAt >= today) groups[0].items.push(conversation)
    else if (conversation.updatedAt >= weekAgo) groups[1].items.push(conversation)
    else groups[2].items.push(conversation)
  }
  return groups.filter((group) => group.items.length)
})

function conversationId() {
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function conversationTitle(value: string) {
  const normalized = value.replace(/\s+/g, ' ').trim()
  return normalized.length > 28 ? `${normalized.slice(0, 28)}…` : normalized || '新会话'
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    conversations.value = Array.isArray(parsed)
      ? parsed
          .filter((item): item is Conversation => !!item && typeof item.id === 'string' && Array.isArray(item.messages))
          .slice(0, MAX_CONVERSATIONS)
      : []
  } catch {
    conversations.value = []
  }
}

function persistConversations() {
  const snapshot = [...conversations.value]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_CONVERSATIONS)
    .map((conversation) => ({
      ...conversation,
      messages: conversation.messages.slice(-MAX_MESSAGES_PER_CONVERSATION),
    }))
  conversations.value = snapshot
  localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  if (activeConversationId.value) localStorage.setItem(ACTIVE_KEY, activeConversationId.value)
  else localStorage.removeItem(ACTIVE_KEY)
}

function restoreConversation(conversation: Conversation) {
  activeConversationId.value = conversation.id
  sessionId.value = conversation.sessionId || null
  messages.value = [...conversation.messages]
  contextAsset.value = conversation.contextAsset ? { ...conversation.contextAsset } : null
  localStorage.setItem(ACTIVE_KEY, conversation.id)
  nextTick(() => {
    resizeComposer()
    scrollBottom()
  })
}

function restoreLastConversation() {
  const activeId = localStorage.getItem(ACTIVE_KEY)
  const conversation = conversations.value.find((item) => item.id === activeId)
  if (conversation) restoreConversation(conversation)
}

function ensureConversation(firstQuestion: string) {
  if (activeConversationId.value) return
  const now = Date.now()
  const conversation: Conversation = {
    id: conversationId(),
    title: conversationTitle(firstQuestion),
    sessionId: null,
    createdAt: now,
    updatedAt: now,
    messages: [],
    contextAsset: contextAsset.value ? { ...contextAsset.value } : null,
  }
  conversations.value.unshift(conversation)
  activeConversationId.value = conversation.id
}

function syncActiveConversation() {
  if (!activeConversationId.value) return
  const conversation = conversations.value.find((item) => item.id === activeConversationId.value)
  if (!conversation) return
  conversation.sessionId = sessionId.value
  conversation.updatedAt = Date.now()
  conversation.messages = [...messages.value]
  conversation.contextAsset = contextAsset.value ? { ...contextAsset.value } : null
  persistConversations()
}

async function selectConversation(conversation: Conversation) {
  if (loading.value) return
  if (route.query.asset) await router.replace({ name: 'agent' })
  restoreConversation(conversation)
}

async function renameConversation(conversation: Conversation) {
  try {
    const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
      inputValue: conversation.title,
      inputPlaceholder: '会话名称',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (value) => !!String(value || '').trim() || '请输入会话名称',
    })
    conversation.title = String(result.value || '').trim()
    conversation.updatedAt = Date.now()
    persistConversations()
  } catch {
    // User cancelled.
  }
}

async function deleteConversation(conversation: Conversation) {
  try {
    await ElMessageBox.confirm(`删除“${conversation.title}”？删除后仅移除当前浏览器中的历史记录。`, '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  conversations.value = conversations.value.filter((item) => item.id !== conversation.id)
  if (activeConversationId.value === conversation.id) {
    activeConversationId.value = null
    sessionId.value = null
    messages.value = []
    contextAsset.value = null
  }
  persistConversations()
}

async function refreshStatus() {
  try {
    status.value = await agentApi.status()
  } catch {
    status.value = null
  }
}

async function loadContext() {
  const asset = typeof route.query.asset === 'string' ? route.query.asset : ''
  if (!asset) {
    contextAsset.value = null
    return
  }
  try {
    const row = await assetApi.table(asset)
    contextAsset.value = {
      assetId: String(row.assetId),
      tableName: String(row.tableName),
      bizName: row.bizName ? String(row.bizName) : null,
    }
  } catch {
    contextAsset.value = null
  }
}

async function clearContext() {
  contextAsset.value = null
  syncActiveConversation()
  await router.replace({ name: 'agent' })
}

async function newSession() {
  if (loading.value) return
  activeConversationId.value = null
  sessionId.value = null
  messages.value = []
  question.value = ''
  contextAsset.value = null
  localStorage.removeItem(ACTIVE_KEY)
  if (route.query.asset) await router.replace({ name: 'agent' })
  nextTick(resizeComposer)
}

function usePrompt(value: string) {
  question.value = value
  nextTick(() => {
    resizeComposer()
    submit()
  })
}

async function scrollBottom() {
  await nextTick()
  if (messageBox.value) {
    messageBox.value.scrollTo({ top: messageBox.value.scrollHeight, behavior: 'smooth' })
  }
}

function resizeComposer() {
  const element = composer.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 160)}px`
}

function firstLine(text: string) {
  return text.split(/\n+/).find(Boolean) || '分析完成'
}

function answerBlocks(text: string, summary?: string | null): AnswerBlock[] {
  const first = (summary || firstLine(text)).trim()
  return text
    .split(/\n{2,}|\n/)
    .map((value) => value.trim())
    .filter((value) => value && value !== first)
    .slice(0, 14)
    .map((value) => {
      if (value.startsWith('• ')) return { type: 'bullet', text: value.slice(2).trim() }
      const key = value.match(/^(结论|结果|口径|说明|建议|注意|数据来源|计算逻辑)[：:]\s*(.+)$/)
      if (key) return { type: 'key', label: key[1], text: key[2] }
      return { type: 'paragraph', text: value }
    })
}

function processSteps(events?: AgentActivity[]): ProcessStep[] {
  if (!events?.length) return []
  const results = new Map<string, AgentActivity>()
  for (const event of events) {
    if (event.type === 'tool_result' && event.callId) results.set(event.callId, event)
  }
  return events
    .filter((event) => event.type === 'tool_call' && event.callId)
    .slice(-10)
    .map((event) => {
      const result = event.callId ? results.get(event.callId) : undefined
      return {
        callId: event.callId || '',
        label: activityText(event),
        status: result ? (result.status === 'error' ? 'error' : 'done') : 'running',
      }
    })
}

function hasEvidence(evidence?: AgentEvidence) {
  return !!(
    evidence?.metrics?.length ||
    evidence?.datasets?.length ||
    evidence?.dimensions?.length ||
    evidence?.period ||
    evidence?.caliber
  )
}

function shortTable(value: string) {
  return value.includes('.') ? value.split('.').pop() || value : value
}

function dimensionName(value: string) {
  return (
    {
      region_code: '地区',
      org_code: '机构',
      customer_type: '客户类型',
      loan_type: '贷款类型',
      currency_cd: '币种',
      product_code: '产品',
    } as Record<string, string>
  )[value] || '维度'
}

function validationState(item: Message): AgentValidationState {
  if (item.validationState) return item.validationState
  if (!item.sql) return 'not_applicable'
  if (!item.validation) return 'not_validated'
  return item.validation.valid ? 'passed' : 'failed'
}

function validationIssues(validation?: AgentValidation | null): AgentValidationIssue[] {
  return validation?.issues || []
}

function hasAdvisory(validation?: AgentValidation | null) {
  return validationIssues(validation).some((issue) => issue.blocking === false || issue.severity !== 'error')
}

function validationTone(item: Message) {
  const state = validationState(item)
  if (state === 'failed') return 'danger'
  if (state === 'not_validated' || state === 'unknown') return 'pending'
  if (state === 'passed' && hasAdvisory(item.validation)) return 'warning'
  return 'success'
}

function sqlStatusText(item: Message) {
  const state = validationState(item)
  if (state === 'failed') return '校验未通过 · 仅生成'
  if (state === 'not_validated') return '尚未校验 · 仅生成'
  if (state === 'unknown') return '校验状态未知 · 仅生成'
  if (state === 'passed' && hasAdvisory(item.validation)) return '校验通过 · 有提示 · 仅生成'
  return '静态校验通过 · 仅生成'
}

function validationTitle(item: Message) {
  const state = validationState(item)
  if (state === 'failed') return 'SQL 静态校验未通过'
  if (state === 'not_validated') return 'SQL 尚未完成静态校验'
  if (state === 'unknown') return 'SQL 校验状态未知'
  if (hasAdvisory(item.validation)) return 'SQL 静态校验通过，但存在提示项'
  return 'SQL 静态校验通过'
}

function validationDescription(item: Message) {
  const state = validationState(item)
  if (state === 'failed') return '存在阻断项，当前 SQL 不应作为可信结果直接使用。'
  if (state === 'not_validated') return '仅展示生成结果，不继承其他 SQL 的校验状态。'
  if (state === 'unknown') return '校验结果缺少可判定状态，请重新执行校验。'
  if (hasAdvisory(item.validation)) return '未发现阻断项，但仍需关注下方风险或规范提示。'
  return '未发现阻断项；DataControl 仍不会执行该 SQL。'
}

function statementLabel(validation?: AgentValidation | null) {
  return validation?.statement_type || {
    query: 'QUERY',
    dml: 'DML',
    ddl: 'DDL',
    access_control: 'ACCESS',
    unknown: 'SQL',
  }[validation?.operation || 'unknown']
}

function riskLabel(validation?: AgentValidation | null) {
  return {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '高危操作',
  }[validation?.risk_level || 'low']
}

function showRisk(validation?: AgentValidation | null) {
  return !!validation?.risk_level && validation.risk_level !== 'low'
}

function severityLabel(severity: AgentValidationIssue['severity']) {
  return { error: '阻断', warning: '提示', info: '说明' }[severity]
}

function activityText(event: AgentActivity) {
  const labels: Record<string, string> = {
    resolve_metric: '解析指标',
    get_schema: '读取表结构',
    search_tables: '检索数据资产',
    get_semantic_model: '读取指标口径',
    compile_query: '生成可信 SQL',
    validate_sql: '静态校验 SQL',
    explain_sql: '解析 SQL',
    search_verified_sql: '检索可信 SQL',
  }
  return labels[event.tool || ''] || event.tool || 'Agent3 工具'
}

function displaySql(item: Message) {
  return item.validation?.normalized_sql?.trim() || item.sql || ''
}

async function copySql(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('SQL 已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

async function submit() {
  const userQuestion = question.value.trim()
  if (!userQuestion || !status.value?.ready || loading.value) return

  ensureConversation(userQuestion)
  messages.value.push({ role: 'user', text: userQuestion })
  syncActiveConversation()
  question.value = ''
  resizeComposer()
  loading.value = true
  await scrollBottom()

  const prompt = contextAsset.value
    ? `当前问题针对 DataControl 数据资产：${contextAsset.value.bizName || contextAsset.value.tableName}（asset_id=${contextAsset.value.assetId}，table=${contextAsset.value.tableName}）。请优先通过 Agent3 MCP 读取该资产及关联事实后回答，不要凭空猜测。\n用户问题：${userQuestion}`
    : userQuestion

  try {
    const result: AgentResult = await agentApi.query(prompt, sessionId.value)
    if (result.sessionId) sessionId.value = result.sessionId
    messages.value.push({
      role: 'assistant',
      text: result.answer || '分析完成。',
      summary: result.summary,
      sql: result.sql,
      validation: result.validation,
      validationState: result.validationState,
      events: result.events,
      evidence: result.evidence,
    })
    syncActiveConversation()
    await scrollBottom()
  } catch (error) {
    console.error('DataAgent query failed', error)
    ElMessage.error('智能问数本次未完成，请确认 Agent 服务状态后重试。')
    await refreshStatus()
    syncActiveConversation()
  } finally {
    loading.value = false
    await scrollBottom()
  }
}

onMounted(async () => {
  loadConversations()
  await refreshStatus()
  const hasRouteAsset = typeof route.query.asset === 'string' && !!route.query.asset
  if (hasRouteAsset) {
    activeConversationId.value = null
    sessionId.value = null
    messages.value = []
    await loadContext()
  } else {
    restoreLastConversation()
  }
  resizeComposer()
})
</script>

<style scoped>
.agent-screen {
  height: calc(100dvh - var(--dc-topbar));
  min-height: 700px;
  padding: 18px 0;
  background: linear-gradient(180deg, #e6f3fa 0, #f1f7fb 36%, #f5f8fb 100%);
  overflow: hidden;
}
.agent-page { height: 100%; display: flex; flex-direction: column; max-width: 1420px; }
.agent-head { flex: none; display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; padding: 0 4px 16px; }
.agent-head h1 { font-size: 38px; letter-spacing: -.035em; margin: 5px 0 7px; color: #103d56; }
.agent-head p { font-size: 15px; line-height: 1.7; margin: 0; color: #416579; max-width: 820px; }
.head-actions { display: flex; align-items: center; gap: 10px; }
.service-status { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px; background: #fff0cf; border: 1px solid #ddb25d; font-size: 13px; font-weight: 750; color: #77510c; }
.service-status i { width: 9px; height: 9px; border-radius: 50%; background: #c9851d; }
.service-status.ready { background: #dff3e9; border-color: #77b996; color: #176b4c; }
.service-status.ready i { background: #238b64; }
.agent-workspace { flex: 1; min-height: 0; display: grid; grid-template-columns: 256px minmax(0,1fr); overflow: hidden; border-color: #bcd6e4; box-shadow: 0 20px 52px rgba(27,78,106,.14); background: #fff; }
.history-pane { min-width: 0; display: flex; flex-direction: column; background: #eaf4f9; border-right: 1px solid #bfd6e2; }
.history-head { padding: 16px 14px 13px; border-bottom: 1px solid #c9dde7; }
.history-head > div { display: flex; align-items: center; justify-content: space-between; color: #3b657b; font-size: 13px; margin-bottom: 10px; }
.history-head > div b { min-width: 24px; text-align: center; padding: 2px 6px; border-radius: 999px; background: #c9e2ee; color: #195e80; font-size: 11px; }
.history-new { width: 100%; display: flex; align-items: center; justify-content: center; gap: 7px; border: 1px solid #1b78a5; background: #1b78a5; color: #fff; border-radius: 10px; padding: 10px 12px; font-size: 14px; font-weight: 750; cursor: pointer; box-shadow: 0 6px 15px rgba(27,120,165,.16); }
.history-new:hover { background: #13698f; }
.history-new:disabled { opacity: .5; cursor: not-allowed; }
.history-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 12px 9px; }
.history-group + .history-group { margin-top: 15px; }
.history-group-title { padding: 0 8px 6px; color: #658396; font-size: 11px; font-weight: 800; letter-spacing: .04em; }
.history-item { position: relative; width: 100%; border: 1px solid transparent; background: transparent; color: #315d73; border-radius: 10px; padding: 9px 8px; margin-bottom: 3px; cursor: pointer; text-align: left; }
.history-item:hover { background: #dcecf4; border-color: #c1dce9; }
.history-item.active { background: #cce6f2; border-color: #8fbfd5; color: #125d80; box-shadow: inset 3px 0 0 #1b78a5; }
.history-item-main { display: flex; align-items: center; gap: 8px; min-width: 0; }
.history-item-main > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 650; }
.history-item-actions { position: absolute; right: 5px; top: 50%; transform: translateY(-50%); display: none; align-items: center; gap: 2px; padding-left: 18px; background: linear-gradient(90deg, transparent, #dcecf4 28%); }
.history-item.active .history-item-actions { background: linear-gradient(90deg, transparent, #cce6f2 28%); }
.history-item:hover .history-item-actions,.history-item.active:hover .history-item-actions { display: flex; }
.history-item-actions button { width: 27px; height: 27px; display: grid; place-items: center; border: 0; border-radius: 7px; background: rgba(255,255,255,.78); color: #53778a; cursor: pointer; }
.history-item-actions button:hover { color: #125d80; background: #fff; }
.history-empty { margin: 30px 12px; padding: 18px 12px; display: grid; justify-items: center; gap: 7px; text-align: center; color: #7693a2; border: 1px dashed #bdd4df; border-radius: 12px; background: rgba(255,255,255,.45); }
.history-empty b { font-size: 13px; color: #4a7185; }
.history-empty span { font-size: 11px; line-height: 1.55; }
.history-foot { flex: none; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 11px 8px; border-top: 1px solid #c9dde7; color: #6d8998; font-size: 11px; }
.chat-shell { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; background: rgba(255,255,255,.99); }
.context-strip { flex: none; display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 12px; align-items: center; padding: 12px 20px; background: #dff0f8; border-bottom: 1px solid #bad7e5; color: #275e78; }
.context-strip > div { display: flex; align-items: baseline; gap: 9px; min-width: 0; }
.context-strip span { font-size: 13px; color: #567d91; }
.context-strip b { font-size: 14px; }
.context-strip code { font-size: 12px; color: #607f90; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.context-strip button { display: flex; align-items: center; gap: 4px; border: 0; background: transparent; color: #3e7188; font-size: 13px; cursor: pointer; }
.runtime-warning { flex: none; display: flex; gap: 9px; align-items: center; padding: 11px 20px; background: #ffedbf; border-bottom: 1px solid #e1b34e; color: #75510d; font-size: 14px; font-weight: 650; }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 30px clamp(24px,4.5vw,64px); scrollbar-gutter: stable; }
.welcome { max-width: 800px; margin: 5vh auto 0; text-align: center; }
.welcome-icon { width: 56px; height: 56px; border-radius: 17px; display: grid; place-items: center; margin: 0 auto 15px; color: #0d709d; background: linear-gradient(145deg,#cbeaf7,#e9f6fc); border: 1px solid #9fcede; box-shadow: 0 9px 24px rgba(30,116,155,.12); }
.welcome h2 { font-size: 29px; margin: 0; color: #123f56; }
.welcome p { font-size: 15px; line-height: 1.7; color: #527385; margin: 9px 0 24px; }
.prompt-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 11px; }
.prompt-grid button { min-height: 52px; display: flex; justify-content: space-between; align-items: center; text-align: left; gap: 12px; padding: 13px 15px; border: 1px solid #c6dce7; border-radius: 12px; background: #f8fcfe; color: #2d5c72; font-size: 14px; font-weight: 600; cursor: pointer; }
.prompt-grid button:hover { border-color: #6faccc; background: #e5f3f9; color: #0f668e; }
.message { margin: 0 0 28px; }
.message.user { display: flex; justify-content: flex-end; }
.user-bubble { max-width: 74%; padding: 12px 16px; border-radius: 16px 16px 4px 16px; background: #176f9a; color: #fff; font-size: 15px; line-height: 1.68; box-shadow: 0 8px 22px rgba(20,105,147,.18); }
.assistant-answer { max-width: 960px; }
.answer-label { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; color: #1d526b; font-size: 14px; }
.agent-avatar { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: #cfeaf5; color: #0d6e98; }
.answer-summary { padding-left: 12px; border-left: 4px solid #2588b4; font-size: 18px; line-height: 1.72; font-weight: 750; color: #173f52; }
.answer-body { margin-top: 10px; display: grid; gap: 8px; }
.answer-body p { margin: 0; font-size: 15px; line-height: 1.78; color: #3d6275; }
.answer-bullet { display: grid; grid-template-columns: 8px minmax(0,1fr); gap: 9px; align-items: start; padding: 2px 0 2px 4px; font-size: 15px; line-height: 1.72; color: #3d6275; }
.answer-bullet i { width: 6px; height: 6px; margin-top: 10px; border-radius: 50%; background: #2c8ab3; }
.answer-key { display: grid; grid-template-columns: auto minmax(0,1fr); gap: 10px; align-items: start; padding: 10px 12px; border-radius: 10px; background: #eaf4f9; border-left: 4px solid #3b8faf; font-size: 14px; line-height: 1.65; color: #355e72; }
.answer-key b { color: #155f80; white-space: nowrap; }
.analysis-trace { margin-top: 16px; padding: 14px 15px; border: 1px solid #a9cadb; border-radius: 12px; background: #edf6fa; }
.trace-head { display: flex; gap: 10px; align-items: flex-start; }
.trace-icon { width: 32px; height: 32px; border-radius: 9px; display: grid; place-items: center; flex: none; background: #c9e7f3; color: #176f98; }
.trace-head > div { display: grid; gap: 2px; }
.trace-head b { font-size: 14px; color: #244f65; }
.trace-head span { font-size: 11px; line-height: 1.45; color: #718c9b; }
.trace-flow { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 11px; }
.trace-step { display: inline-flex; align-items: center; gap: 6px; padding: 7px 9px; border: 1px solid #bdd8e4; border-radius: 9px; background: #fff; color: #446c80; font-size: 12px; font-weight: 650; }
.trace-step.done { border-color: #8ec8ad; background: #e9f6ef; color: #266f53; }
.trace-step.error { border-color: #dc9696; background: #fdeaea; color: #9a3f3f; }
.trace-index { width: 18px; height: 18px; display: grid; place-items: center; border-radius: 50%; background: rgba(44,128,164,.12); font-size: 10px; font-weight: 800; }
.evidence-area { margin-top: 15px; padding: 14px 16px; background: #eaf4f9; border: 1px solid #b8d4e1; border-left: 4px solid #2c84aa; border-radius: 12px; display: grid; gap: 11px; }
.evidence-row { display: grid; grid-template-columns: 82px minmax(0,1fr); gap: 10px; align-items: flex-start; }
.evidence-row > span,.caliber > span { font-size: 13px; font-weight: 800; color: #607f90; padding-top: 4px; }
.evidence-row > b { font-size: 14px; color: #244f63; padding-top: 3px; }
.chips { display: flex; flex-wrap: wrap; gap: 7px; }
.evidence-chip { display: inline-flex; align-items: center; gap: 5px; border-radius: 8px; padding: 7px 9px; background: #d6ebf5; color: #175e7d; font-size: 13px; font-weight: 700; }
.evidence-chip.metric { background: #dff2e9; color: #1f6d50; }
.evidence-chip.neutral { background: #fff; border: 1px solid #c8dce6; color: #456a7d; font-weight: 650; }
.evidence-chip code { font-size: 11px; color: #678695; }
.caliber { display: grid; grid-template-columns: 82px minmax(0,1fr); gap: 10px; border-top: 1px solid #c9dee8; padding-top: 10px; }
.caliber p { margin: 0; font-size: 14px; line-height: 1.7; color: #3c6477; }
.sql-card { margin-top: 16px; border: 1px solid #86aec1; border-radius: 12px; overflow: hidden; background: #0b2737; box-shadow: 0 8px 22px rgba(15,59,82,.08); }
.block-head { min-height: 48px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: #e3eff5; border-bottom: 1px solid #b9d0dc; color: #315d72; }
.sql-head-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.block-head b { font-size: 14px; color: #234f65; }
.block-head button { display: flex; align-items: center; gap: 5px; border: 1px solid #b7cfdc; background: #fff; border-radius: 8px; padding: 6px 9px; color: #3c687c; font-size: 12px; cursor: pointer; }
.sql-type,.sql-state,.risk-chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; }
.sql-type { color: #365967; background: #cbdce5; }
.sql-state.success { color: #146643; background: #cfeadf; border: 1px solid #8cc7aa; }
.sql-state.warning { color: #79510b; background: #ffe6a8; border: 1px solid #e0b551; }
.sql-state.pending { color: #4f5f68; background: #dfe5e8; border: 1px solid #aab8bf; }
.sql-state.danger { color: #8e3030; background: #f9cccc; border: 1px solid #d98282; }
.risk-chip.risk-medium { color: #6d520d; background: #f4df9b; }
.risk-chip.risk-high { color: #874710; background: #f8cfaa; }
.risk-chip.risk-critical { color: #8e2e2e; background: #f5bcbc; }
.sql-card pre { margin: 0; padding: 18px 20px; color: #e1eef4; font-size: 14px; line-height: 1.75; overflow: auto; white-space: pre; tab-size: 2; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
.validation-panel { margin-top: 11px; padding: 15px 16px; border: 2px solid #b5cbd5; border-radius: 12px; background: #f5f8fa; }
.validation-panel.success { border-color: #77b997; background: #e7f5ee; }
.validation-panel.warning { border-color: #ddb14f; background: #fff1c9; }
.validation-panel.pending { border-color: #aeb9bf; background: #edf1f3; }
.validation-panel.danger { border-color: #d97d7d; background: #fde8e8; }
.validation-head { display: flex; gap: 11px; align-items: flex-start; }
.validation-icon { width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center; flex: none; background: #cfe9dc; color: #1f7a57; }
.warning .validation-icon { background: #ffe2a0; color: #936114; }
.pending .validation-icon { background: #d9e0e4; color: #5f6f78; }
.danger .validation-icon { background: #f4c2c2; color: #a03939; }
.validation-head b { font-size: 15px; color: #244e61; }
.validation-head p { margin: 4px 0 0; font-size: 13px; line-height: 1.6; color: #557383; }
.validation-facts { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 9px; margin-top: 13px; }
.validation-facts > div { min-width: 0; padding: 10px 11px; border-radius: 9px; background: rgba(255,255,255,.78); border: 1px solid rgba(145,174,188,.62); }
.validation-facts span { display: block; font-size: 11px; color: #6d8795; margin-bottom: 4px; }
.validation-facts b { display: block; font-size: 13px; color: #2e596e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.issue-list { display: grid; gap: 9px; margin-top: 11px; }
.issue-row { display: grid; grid-template-columns: auto minmax(0,1fr); gap: 10px; align-items: flex-start; padding: 11px; border-radius: 9px; background: #fff; border: 1px solid #cfdde4; }
.issue-row.issue-error { border-color: #d98686; background: #fff4f4; }
.issue-row.issue-warning { border-color: #dcb45c; background: #fff9e7; }
.issue-badge { border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; background: #dfe7eb; color: #556c78; }
.issue-error .issue-badge { background: #f5c7c7; color: #923636; }
.issue-warning .issue-badge { background: #ffe0a0; color: #80550f; }
.issue-row b { font-size: 13px; line-height: 1.55; color: #36596a; }
.issue-row p { margin: 4px 0 0; font-size: 12px; line-height: 1.55; color: #677f8b; }
.validation-empty { margin-top: 11px; display: flex; gap: 7px; align-items: center; color: #2f7259; font-size: 13px; font-weight: 650; }
.validation-empty.pending { color: #695c41; }
.loading-answer p { font-size: 14px; color: #567586; margin: 5px 0 10px; }
.loading-steps { display: flex; gap: 7px; flex-wrap: wrap; }
.loading-steps span { padding: 6px 9px; border-radius: 999px; background: #e4f1f7; color: #3b6f87; font-size: 12px; font-weight: 650; }
.composer-wrap { flex: none; padding: 13px 20px 14px; border-top: 1px solid #cbdce5; background: #f7fbfd; box-shadow: 0 -8px 22px rgba(48,91,115,.05); }
.composer { display: flex; align-items: flex-end; gap: 9px; max-width: 1040px; margin: 0 auto; border: 1.5px solid #8ebfd3; background: #fff; border-radius: 14px; padding: 10px 10px 10px 15px; box-shadow: 0 6px 22px rgba(41,102,134,.08); }
.composer:focus-within { border-color: #338eb5; box-shadow: 0 0 0 3px rgba(48,151,195,.13); }
.composer.disabled { background: #f2f5f6; }
.composer textarea { flex: 1; border: 0; outline: 0; resize: none; min-height: 28px; max-height: 160px; overflow-y: auto; padding: 4px 2px; background: transparent; color: #214b60; font-size: 15px; line-height: 1.6; }
.composer textarea::placeholder { color: #829aa7; }
.send { width: 40px; height: 40px; flex: none; border: 0; border-radius: 10px; display: grid; place-items: center; background: #1479a5; color: #fff; cursor: pointer; }
.send:hover { background: #0d6b92; }
.send:disabled { opacity: .38; cursor: not-allowed; }
.composer-hint { max-width: 1040px; margin: 7px auto 0; display: flex; justify-content: space-between; color: #718b99; font-size: 12px; }
.composer-hint span:last-child { display: flex; align-items: center; gap: 4px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media(max-width: 980px) {
  .agent-workspace { grid-template-columns: 210px minmax(0,1fr); }
  .history-pane { font-size: 12px; }
  .validation-facts { grid-template-columns: repeat(2,minmax(0,1fr)); }
}
@media(max-width: 760px) {
  .agent-screen { min-height: 640px; padding: 12px 0; }
  .agent-head { align-items: flex-start; flex-direction: column; gap: 10px; padding-bottom: 12px; }
  .agent-head h1 { font-size: 31px; }
  .agent-workspace { grid-template-columns: 1fr; }
  .history-pane { display: none; }
  .messages { padding: 21px 15px; }
  .prompt-grid { grid-template-columns: 1fr; }
  .user-bubble { max-width: 90%; }
  .composer-wrap { padding: 10px 12px 11px; }
  .composer-hint span:first-child { display: none; }
  .composer-hint { justify-content: flex-end; }
  .evidence-row,.caliber { grid-template-columns: 1fr; gap: 4px; }
  .validation-facts { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .answer-key { grid-template-columns: 1fr; gap: 3px; }
}
</style>