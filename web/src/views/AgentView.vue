<template>
  <div class="dc-page agent-screen">
    <div class="dc-container agent-page">
      <header class="agent-head">
        <div>
          <span class="dc-eyebrow">INTELLIGENT DATA Q&A</span>
          <h1>智能问数</h1>
          <p>面向数据查询与开发场景检索内部可信指标、资产和口径；存在业务分歧时先让你选择，再生成经过静态校验的 MaxCompute SQL。系统不执行生产 SQL，也不访问外部网络补全口径。</p>
        </div>
        <span class="service-status" :class="{ ready: status?.ready }"><i></i>{{ status?.ready ? '服务正常' : '服务未就绪' }}</span>
      </header>

      <section class="agent-workspace dc-card">
        <AgentConversationSidebar
          :groups="conversationGroups"
          :count="conversations.length"
          :active-id="activeConversationId"
          :loading="loading"
          v-model:search-query="searchQuery"
          @new="newSession"
          @select="selectConversation"
          @rename="renameConversation"
          @delete="deleteConversation"
          @toggle-pin="toggleConversationPin"
        />

        <section class="chat-shell">
          <div class="chat-model-bar">
            <span class="chat-model-label">对话模型</span>
            <div class="model-options" role="group" aria-label="选择当前对话模型">
              <button type="button" :class="{ selected: modelMode === 'deepseek' }" :disabled="loading" :aria-pressed="modelMode === 'deepseek'" @click="switchModel('deepseek')">DeepSeek 官方</button>
            </div>
            <span class="model-context">官方 DeepSeek · 可信 SQL 校验 · 不执行 SQL</span>
          </div>
          <div v-if="contextAsset" class="context-strip">
            <Database :size="17" />
            <div><span>当前数据资产</span><b>{{ contextAsset.bizName || contextAsset.tableName }}</b><code>{{ contextAsset.tableName }}</code></div>
            <button @click="clearContext"><X :size="15" />清除</button>
          </div>
          <div v-if="!status?.ready" class="runtime-warning"><TriangleAlert :size="18" /><span>{{ agentUnavailableReason }}</span></div>

          <div ref="messageBox" class="messages">
            <div v-if="messages.length === 0" class="welcome">
              <div class="welcome-icon"><Sparkles :size="26" /></div>
              <h2>想查什么数据？</h2>
              <p>我会先解析内部可信语义；如果一个问题对应多个统计口径，会直接给出选项让你确认。</p>
              <div class="prompt-grid">
                <button v-for="item in quickPrompts" :key="item" @click="usePrompt(item)">{{ item }}<ArrowUpRight :size="15" /></button>
              </div>
            </div>

            <AgentMessageView
              v-for="(item, index) in messages"
              :key="index"
              :message="item"
              @clarify="submitClarification(index, $event)"
            />

            <article v-if="loading" class="loading-answer">
              <div class="loading-label">
                <span class="agent-avatar"><LoaderCircle class="spin" :size="16" /></span>
                <b>{{ stopRequested ? '正在停止任务' : 'DataAgent 正在分析' }}</b>
                <button class="stop-turn" :disabled="stopRequested" @click="stopAgentTurn"><Square :size="12" />停止</button>
              </div>
              <p>{{ liveEvents.length ? '以下步骤来自真实 Agent3 工具调用，完成后将展示证据与最终答案。' : '已开始处理，等待 Agent3 返回实际工具步骤。' }}</p>
              <AgentTrace v-if="liveEvents.length" :events="liveEvents" />
            </article>
          </div>

          <div class="composer-wrap">
            <div class="composer" :class="{ disabled: !status?.ready }">
              <textarea
                ref="composer"
                v-model="question"
                rows="1"
                :disabled="!status?.ready || loading"
                placeholder="输入你的问题，例如：今年贷款增长怎么样？"
                @input="resizeComposer"
                @keydown.enter.exact.prevent="submit"
              />
              <button class="send" :disabled="!status?.ready || loading || !question.trim()" @click="submit"><Send :size="19" /></button>
            </div>
            <div class="composer-hint"><span>Enter 发送 · Shift+Enter 换行</span><span><ShieldCheck :size="14" />内部证据 · 静态校验 · 不执行生产 SQL</span></div>
          </div>
        </section>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Database, LoaderCircle, Send, ShieldCheck, Sparkles, Square, TriangleAlert, X } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, assetApi, type AgentActivity, type AgentModelMode, type AgentResult, type AgentStatus, type AgentStreamEvent, AgentTurnCancelledError } from '@/api/client'
import AgentConversationSidebar from '@/components/agent/AgentConversationSidebar.vue'
import AgentMessageView from '@/components/agent/AgentMessage.vue'
import AgentTrace from '@/components/agent/AgentTrace.vue'
import type { AgentConversation, AgentMessage, ContextAsset } from '@/components/agent/types'
import { useAgentConversations } from '@/composables/useAgentConversations'

const route = useRoute()
const router = useRouter()
const status = ref<AgentStatus | null>(null)
const modelMode = ref<AgentModelMode>('deepseek')
let statusRequestSerial = 0
const agentUnavailableReason = computed(() => {
  if (!status.value) return '无法获取 Agent 状态：请确认 DataControl 后端已在 8000 端口启动。'
  return status.value.reason
    ? `Agent 暂不可用：${status.value.reason}`
    : 'Agent 暂不可用：请查看启动终端的 Gateway/MCP 状态和日志。'
})
const question = ref('')
const loading = ref(false)
const liveEvents = ref<AgentActivity[]>([])
const stopRequested = ref(false)
let activeRunId: string | null = null
let activeController: AbortController | null = null
const messages = ref<AgentMessage[]>([])
const messageBox = ref<HTMLElement | null>(null)
const composer = ref<HTMLTextAreaElement | null>(null)
const sessionId = ref<string | null>(null)
const contextAsset = ref<ContextAsset | null>(null)

const {
  conversations,
  activeConversationId,
  searchQuery,
  conversationGroups,
  load: loadConversations,
  restoreLast,
  create: createConversation,
  activate: activateConversation,
  clearActive,
  syncActive,
  rename,
  remove,
  togglePin,
  attachServerId,
  mergeServer,
} = useAgentConversations()

const quickPrompts = [
  '今年贷款增长怎么样？',
  '本期各地区贷款余额是多少？',
  '各地区不良贷款率是多少？',
  '贷款余额最高的前 10 个地区',
  '广东省人民币贷款余额怎么统计？',
  '贷款余额使用哪张数据表？',
]

async function refreshStatus() {
  const serial = ++statusRequestSerial
  const chosen = modelMode.value
  try {
    const state = await agentApi.status(chosen)
    if (serial === statusRequestSerial && chosen === modelMode.value) status.value = state
  } catch {
    if (serial === statusRequestSerial) status.value = null
  }
}

async function loadContext() {
  const asset = typeof route.query.asset === 'string' ? route.query.asset : ''
  if (!asset) { contextAsset.value = null; return }
  try {
    const row = await assetApi.table(asset)
    contextAsset.value = { assetId: String(row.assetId), tableName: String(row.tableName), bizName: row.bizName ? String(row.bizName) : null }
  } catch { contextAsset.value = null }
}

function restoreConversation(conversation: AgentConversation) {
  modelMode.value = 'deepseek'
  sessionId.value = conversation.modelMode === 'deepseek' ? conversation.sessionId || null : null
  messages.value = [...conversation.messages]
  contextAsset.value = conversation.contextAsset ? { ...conversation.contextAsset } : null
  nextTick(() => { resizeComposer(); scrollBottom() })
}

async function selectConversation(conversation: AgentConversation) {
  if (loading.value) return
  if (route.query.asset || route.query.q) await router.replace({ name: 'agent' })
  const selected = activateConversation(conversation.id)
  if (selected) {
    restoreConversation(selected)
    await refreshStatus()
  }
}

async function renameConversation(conversation: AgentConversation) {
  try {
    const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', { inputValue: conversation.title, inputPlaceholder: '会话名称', confirmButtonText: '保存', cancelButtonText: '取消', inputValidator: (value) => !!String(value || '').trim() || '请输入会话名称' })
    const title = String(result.value || '')
    if (conversation.serverId) await agentApi.editConversation(conversation.serverId, { title })
    rename(conversation.id, title)
  } catch { /* cancelled or update failed, local state unchanged */ }
}

async function deleteConversation(conversation: AgentConversation) {
  try { await ElMessageBox.confirm(`删除“${conversation.title}”？删除后仅移除当前浏览器中的历史记录。`, '删除会话', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }) } catch { return }
  try {
    if (conversation.serverId) await agentApi.deleteConversation(conversation.serverId)
    if (remove(conversation.id)) resetConversationState()
  } catch { ElMessage.error('服务端删除未成功，原会话已保留。') }
}

async function toggleConversationPin(conversation: AgentConversation) {
  try {
    if (conversation.serverId) await agentApi.editConversation(conversation.serverId, { pinned: !conversation.pinned })
    togglePin(conversation.id)
  } catch { ElMessage.error('置顶操作未保存，原状态已保留。') }
}
function resetConversationState() { sessionId.value = null; messages.value = []; contextAsset.value = null; question.value = ''; nextTick(resizeComposer) }

async function newSession() {
  if (loading.value) return
  clearActive(); resetConversationState()
  if (route.query.asset || route.query.q) await router.replace({ name: 'agent' })
}

async function clearContext() {
  contextAsset.value = null
  syncActive(messages.value, sessionId.value, null, modelMode.value)
  await router.replace({ name: 'agent' })
}

function usePrompt(value: string) {
  question.value = value
  nextTick(() => { resizeComposer(); submit() })
}

async function scrollBottom() {
  await nextTick()
  if (messageBox.value) messageBox.value.scrollTo({ top: messageBox.value.scrollHeight, behavior: 'smooth' })
}

function resizeComposer() {
  const element = composer.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 160)}px`
}

function assistantMessage(result: AgentResult): AgentMessage {
  return {
    role: 'assistant',
    text: result.answer || '分析完成。',
    summary: result.summary,
    sql: result.sql,
    validation: result.validation,
    validationState: result.validationState,
    events: result.events,
    evidence: result.evidence,
    clarification: result.clarification,
    clarificationResolved: false,
    clarificationSelection: [],
  }
}

function reportAgentDevtools(result: AgentResult) {
  if (!import.meta.env.DEV) return
  const steps = (result.events || []).filter((item) => item.type === 'tool_call' || item.type === 'tool_result')
  console.groupCollapsed(`[DataAgent] 本轮完成 · ${steps.filter((item) => item.type === 'tool_call').length} 次 Agent3 工具调用`)
  for (const item of steps) {
    // Show only trusted tool identifiers and status; never print question, SQL or tool input.
    console.info(item.type === 'tool_call' ? 'TOOL_START' : 'TOOL_END', item.tool, item.type === 'tool_result' ? item.status : '')
  }
  console.info('SQL:', result.sql ? 'generated' : 'none', 'Validation:', result.validationState || 'n/a')
  console.groupEnd()
}

function onAgentStreamEvent(update: AgentStreamEvent) {
  if (update.type !== 'activity') return
  if (update.event.type !== 'tool_call' && update.event.type !== 'tool_result') return
  liveEvents.value = [...liveEvents.value, update.event].slice(-40)
  scrollBottom()
}

async function stopAgentTurn() {
  if (!loading.value || !activeRunId || stopRequested.value) return
  stopRequested.value = true
  const runId = activeRunId
  // The server endpoint cancels the actual Harness child; AbortController only
  // closes this browser's stream and must not be mistaken for a server-side stop.
  try {
    const outcome = await agentApi.cancel(runId)
    if (!outcome.cancelled) {
      stopRequested.value = false
      ElMessage.warning('服务端未确认取消，正在等待任务最终状态；请勿将其视为已停止。')
      return
    }
    // Do not abort the stream here: only a terminal 'cancelled' event confirms stop.
  } catch {
    stopRequested.value = false
    ElMessage.warning('停止请求失败，仍在等待服务端结果；请检查 Agent 日志。')
  }
}

async function runAgentTurn(displayText: string, prompt: string, createTitle?: string) {
  if (!status.value?.ready || loading.value) return
  if (!localStorage.getItem('datacontrol_token')) {
    await router.push({ name: 'login', query: { redirect: '/agent' } })
    return
  }
  const existing = conversations.value.find(c => c.id === activeConversationId.value)
  if (existing?.modelMode === 'free-test') {
    ElMessage.warning('旧免费测试会话只可查看，请创建新的官方模型会话。')
    return
  }
  const selectedMode: AgentModelMode = 'deepseek'
  if (!activeConversationId.value) createConversation(createTitle || displayText, contextAsset.value, selectedMode)
  messages.value.push({ role: 'user', text: displayText })
  syncActive(messages.value, sessionId.value, contextAsset.value, selectedMode)
  loading.value = true
  if (activeConversationId.value) {
    const active = conversations.value.find((c) => c.id === activeConversationId.value)
    if (active && !active.serverId) {
      try {
        const saved = await agentApi.createConversation(active.title, selectedMode, active.contextAsset || null)
        attachServerId(active.id, saved.id)
      } catch {
        loading.value = false
        ElMessage.error('无法创建服务端会话，已阻止本轮请求，请检查登录状态和服务。')
        messages.value.pop()
        syncActive(messages.value, null, contextAsset.value, 'deepseek')
        return
      }
    }
  }
  stopRequested.value = false
  liveEvents.value = []
  activeRunId = crypto.randomUUID()
  activeController = new AbortController()
  await scrollBottom()
  try {
    const serverId = conversations.value.find((c) => c.id === activeConversationId.value)?.serverId || null
    const result = await agentApi.stream(prompt, sessionId.value, activeRunId, onAgentStreamEvent, activeController.signal, selectedMode, serverId, displayText)
    reportAgentDevtools(result)
    if (result.sessionId) sessionId.value = result.sessionId
    messages.value.push(assistantMessage(result))
    syncActive(messages.value, sessionId.value, contextAsset.value, modelMode.value)
    await scrollBottom()
  } catch (error) {
    if (error instanceof AgentTurnCancelledError) {
      // A partially written dsh session must not be silently resumed.
      sessionId.value = null
      messages.value.push({ role: 'assistant', text: '本轮任务已停止，未生成可采信的最终结果。Agent 会话上下文已重置，请重新发起需要的查询。' })
      syncActive(messages.value, sessionId.value, contextAsset.value, modelMode.value)
    } else {
      console.error('DataAgent query failed', error)
      // The dsh session may already contain an incomplete model turn.
      // Do not resume it after a broken stream or unknown server outcome.
      sessionId.value = null
      messages.value.push({ role: 'assistant', text: '本轮请求未完成，服务端最终状态暂时无法确认。为避免沿用不完整上下文，已重置模型会话。' })
      ElMessage.error('智能问数本次未完成，请检查 Agent 服务与运行日志。')
      await refreshStatus()
      syncActive(messages.value, sessionId.value, contextAsset.value, modelMode.value)
    }
  } finally {
    loading.value = false
    stopRequested.value = false
    liveEvents.value = []
    activeRunId = null
    activeController = null
    await scrollBottom()
  }
}

async function submit() {
  const userQuestion = question.value.trim()
  if (!userQuestion || !status.value?.ready || loading.value) return
  question.value = ''
  resizeComposer()
  const prompt = contextAsset.value
    ? `当前问题针对 DataControl 数据资产：${contextAsset.value.bizName || contextAsset.value.tableName}（asset_id=${contextAsset.value.assetId}，table=${contextAsset.value.tableName}）。请优先通过 Agent3 MCP 读取该资产及关联内部事实后回答，不要凭空猜测，不使用外部网络。\n用户问题：${userQuestion}`
    : userQuestion
  await runAgentTurn(userQuestion, prompt, userQuestion)
}

async function submitClarification(
  messageIndex: number,
  payload: { values: string[]; labels: string[]; custom?: string },
) {
  if (loading.value || !status.value?.ready) return
  const message = messages.value[messageIndex]
  if (!message || message.role !== 'assistant' || !message.clarification || message.clarificationResolved) return

  message.clarificationResolved = true
  message.clarificationSelection = [...payload.values]
  syncActive(messages.value, sessionId.value, contextAsset.value, modelMode.value)

  const displayText = payload.custom
    ? `补充口径：${payload.custom}`
    : `选择口径：${payload.labels.join('、')}`
  const technicalChoice = payload.custom
    ? `用户对上一轮澄清补充了业务口径：“${payload.custom}”。请仅使用 DataControl 内部可信证据继续原问题；证据仍不足时继续结构化澄清，不要访问外部网络。`
    : `用户已选择上一轮结构化澄清选项：${payload.labels.map((label, index) => `${label}（metric_id=${payload.values[index]}）`).join('；')}。请把所选 value 作为受治理指标 ID，继续上一问题的规划、生成和校验；不要再次要求用户重述原问题，也不要访问外部网络。`
  await runAgentTurn(displayText, technicalChoice)
}

async function refreshServerHistory() {
  if (!localStorage.getItem('datacontrol_token')) return
  try {
    const remote = await agentApi.conversations()
    mergeServer(remote as unknown as AgentConversation[])
    const unlinked = conversations.value.filter((c) => !c.serverId && c.messages.length > 0)
    if (unlinked.length) {
      try {
        await ElMessageBox.confirm(
          `发现 ${unlinked.length} 条仅保存在本浏览器的历史会话。是否导入当前登录账号？不导入也不会删除。`,
          '导入本地会话',
          { confirmButtonText: '确认导入', cancelButtonText: '保留本地', type: 'info' },
        )
        const imported = await agentApi.importConversations(unlinked.map((c) => ({
          title: c.title, modelMode: c.modelMode, pinned: c.pinned,
          sessionId: null, messages: c.messages, contextAsset: c.contextAsset,
        })))
        for (let i = 0; i < imported.length; i++) attachServerId(unlinked[i].id, imported[i].id)
        mergeServer(imported as unknown as AgentConversation[])
      } catch { /* User declined, or import failed: keep all local history. */ }
    }
    const active = conversations.value.find((c) => c.id === activeConversationId.value)
    if (active) restoreConversation(active)
  } catch { ElMessage.warning('暂时无法同步服务端历史，本地会话仍可使用。') }
}

onMounted(async () => {
  loadConversations()
  const initialQuestion = typeof route.query.q === 'string' ? route.query.q.trim() : ''
  if (!localStorage.getItem('datacontrol_token')) {
    await router.replace({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  const hasRouteAsset = typeof route.query.asset === 'string' && !!route.query.asset
  if (hasRouteAsset || initialQuestion) {
    clearActive(); resetConversationState()
    modelMode.value = 'deepseek'
    if (hasRouteAsset) await loadContext()
    if (initialQuestion) question.value = initialQuestion
  } else {
    const restored = restoreLast()
    if (restored) restoreConversation(restored)
  }
  await refreshStatus()
  await refreshServerHistory()
  resizeComposer()
})
</script>

<style scoped>
.agent-screen { height: calc(100dvh - var(--dc-topbar)); min-height: 700px; padding: 18px 0; background: linear-gradient(180deg,#e2f1f9 0,#eef6fa 38%,#f4f8fb 100%); overflow: hidden; }
.agent-page { height: 100%; display: flex; flex-direction: column; max-width: 1420px; }
.agent-head { flex: none; display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; padding: 0 4px 16px; }
.agent-head h1 { font-size: 38px; letter-spacing: -.035em; margin: 5px 0 7px; color: #0f3b53; }
.agent-head p { font-size: 15px; line-height: 1.7; margin: 0; color: #3c6277; max-width: 900px; }
.service-status { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px; background: #ffeab7; border: 1px solid #d49e35; font-size: 13px; font-weight: 750; color: #70480a; }
.service-status i { width: 9px; height: 9px; border-radius: 50%; background: #bd7410; }
.service-status.ready { background: #d8efe4; border-color: #61aa84; color: #126546; }
.service-status.ready i { background: #1c805a; }
.agent-workspace { flex: 1; min-height: 0; display: grid; grid-template-columns: 268px minmax(0,1fr); overflow: hidden; border-color: #a9c9d8; box-shadow: 0 20px 52px rgba(27,78,106,.15); background: #fff; }
.chat-shell { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; background: rgba(255,255,255,.99); }
.chat-model-bar { flex: none; display: flex; align-items: center; gap: 12px; padding: 11px 20px; background: #f7fbfd; border-bottom: 1px solid #d8e7ef; }
.chat-model-label { color: #547184; font-weight: 700; font-size: 12px; white-space: nowrap; }
.model-options { display: inline-flex; align-items: center; gap: 3px; border: 1px solid #d0e1eb; background: #eaf3f8; border-radius: 10px; padding: 3px; }
.model-options button { display: inline-flex; gap: 6px; align-items: center; padding: 8px 12px; border: 1px solid transparent; border-radius: 8px; background: transparent; color: #567587; font-size: 12px; font-weight: 650; white-space: nowrap; cursor: pointer; }
.model-options button.selected { background: #fff; border-color: #c3dce9; color: #12618b; box-shadow: 0 1px 6px rgba(30,90,120,.09); }
.model-options button:hover:not(:disabled):not(.selected) { color: #17688f; background: #dcecf4; }
.model-options button:disabled { opacity: .55; cursor: not-allowed; }
.model-context { margin-left: auto; color: #738d9e; font-size: 12px; text-align: right; }
.context-strip { flex: none; display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 12px; align-items: center; padding: 12px 20px; background: #d9edf6; border-bottom: 1px solid #aacddb; color: #245b75; }
.context-strip > div { display: flex; align-items: baseline; gap: 9px; min-width: 0; }
.context-strip span { font-size: 13px; color: #4f788d; }
.context-strip b { font-size: 14px; }
.context-strip code { font-size: 12px; color: #577b8d; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.context-strip button { display: flex; align-items: center; gap: 4px; border: 0; background: transparent; color: #326d87; font-size: 13px; cursor: pointer; }
.runtime-warning { flex: none; display: flex; gap: 9px; align-items: center; padding: 11px 20px; background: #ffe9ad; border-bottom: 1px solid #d6a33a; color: #6f4a0b; font-size: 14px; font-weight: 650; }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 30px clamp(24px,4.5vw,64px); scrollbar-gutter: stable; }
.welcome { max-width: 800px; margin: 5vh auto 0; text-align: center; }
.welcome-icon { width: 56px; height: 56px; border-radius: 17px; display: grid; place-items: center; margin: 0 auto 15px; color: #0b6c98; background: linear-gradient(145deg,#c3e6f5,#e8f5fb); border: 1px solid #8fc4d8; box-shadow: 0 9px 24px rgba(30,116,155,.13); }
.welcome h2 { font-size: 29px; margin: 0; color: #103c53; }
.welcome p { font-size: 15px; line-height: 1.7; color: #4b6f82; margin: 9px 0 24px; }
.prompt-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 11px; }
.prompt-grid button { min-height: 52px; display: flex; justify-content: space-between; align-items: center; text-align: left; gap: 12px; padding: 13px 15px; border: 1px solid #b8d3df; border-radius: 12px; background: #f7fbfd; color: #285970; font-size: 14px; font-weight: 600; cursor: pointer; }
.prompt-grid button:hover { border-color: #579fbd; background: #e2f1f7; color: #0d638d; }
.loading-answer { max-width: 980px; margin: 0 0 28px; }
.loading-label { display: flex; align-items: center; gap: 9px; color: #174f69; font-size: 14px; }
.agent-avatar { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: #c8e6f2; color: #0b6a94; }
.loading-answer p { font-size: 14px; color: #4d7183; margin: 8px 0 0 39px; }
.composer-wrap { flex: none; padding: 13px 20px 14px; border-top: 1px solid #c1d8e3; background: #f6fbfd; box-shadow: 0 -8px 22px rgba(48,91,115,.05); }
.composer { display: flex; align-items: flex-end; gap: 9px; max-width: 1040px; margin: 0 auto; border: 1.5px solid #79b2c9; background: #fff; border-radius: 14px; padding: 10px 10px 10px 15px; box-shadow: 0 6px 22px rgba(41,102,134,.09); }
.composer:focus-within { border-color: #2685ad; box-shadow: 0 0 0 3px rgba(48,151,195,.14); }
.composer.disabled { background: #f1f5f6; }
.composer textarea { flex: 1; border: 0; outline: 0; resize: none; min-height: 28px; max-height: 160px; overflow-y: auto; padding: 4px 2px; background: transparent; color: #1e4a60; font-size: 15px; line-height: 1.6; }
.composer textarea::placeholder { color: #7893a1; }
.send { width: 40px; height: 40px; flex: none; border: 0; border-radius: 10px; display: grid; place-items: center; background: #1178a5; color: #fff; cursor: pointer; }
.send:hover { background: #0b668f; }
.send:disabled { opacity: .38; cursor: not-allowed; }
.composer-hint { max-width: 1040px; margin: 7px auto 0; display: flex; justify-content: space-between; color: #668493; font-size: 12px; }
.composer-hint span:last-child { display: flex; align-items: center; gap: 4px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media(max-width:980px){.agent-workspace{grid-template-columns:220px minmax(0,1fr)}}
@media(max-width:760px){.chat-model-bar{padding:9px 12px;gap:7px;flex-wrap:wrap}.model-context{display:none}.model-options button{padding:7px 9px}.agent-screen{min-height:640px;padding:12px 0}.agent-head{align-items:flex-start;flex-direction:column;gap:10px;padding-bottom:12px}.agent-head h1{font-size:31px}.agent-workspace{grid-template-columns:1fr}.agent-workspace :deep(.history-pane){display:none}.messages{padding:21px 15px}.prompt-grid{grid-template-columns:1fr}.composer-wrap{padding:10px 12px 11px}.composer-hint span:first-child{display:none}.composer-hint{justify-content:flex-end}}
</style>

<style scoped>
.stop-turn { margin-left: auto; display: inline-flex; align-items: center; gap: 5px; padding: 6px 11px; border: 1px solid #b8cdd9; border-radius: 8px; background: #fff; color: #516b7a; cursor: pointer; font-size: 12px; font-weight: 650; }
.stop-turn:hover:not(:disabled) { border-color: #d78b8b; color: #a64a4a; background: #fff6f6; }
.stop-turn:disabled { cursor: wait; opacity: .6; }
</style>
