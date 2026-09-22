<template>
  <div class="dc-page agent-screen">
    <div class="dc-container agent-page">
      <header class="agent-head">
        <div>
          <span class="dc-eyebrow">INTELLIGENT DATA Q&A</span>
          <h1>智能问数</h1>
          <p>面向数据查询与开发场景检索指标、资产和口径，生成经过静态校验的 MaxCompute SQL。系统只生成和校验，不执行生产 SQL。</p>
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

            <AgentMessageView v-for="(item, index) in messages" :key="index" :message="item" />

            <article v-if="loading" class="loading-answer">
              <div class="loading-label"><span class="agent-avatar"><LoaderCircle class="spin" :size="16" /></span><b>DataAgent 正在分析</b></div>
              <p>正在处理当前问题。完成后会展示真实工具调用、数据证据、SQL 与校验结果。</p>
            </article>
          </div>

          <div class="composer-wrap">
            <div class="composer" :class="{ disabled: !status?.ready }">
              <textarea
                ref="composer"
                v-model="question"
                rows="1"
                :disabled="!status?.ready || loading"
                placeholder="输入你的问题，例如：本期各地区贷款余额是多少？"
                @input="resizeComposer"
                @keydown.enter.exact.prevent="submit"
              />
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
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Database, LoaderCircle, Send, ShieldCheck, Sparkles, TriangleAlert, X } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, assetApi, type AgentResult, type AgentStatus } from '@/api/client'
import AgentConversationSidebar from '@/components/agent/AgentConversationSidebar.vue'
import AgentMessageView from '@/components/agent/AgentMessage.vue'
import type { AgentConversation, AgentMessage, ContextAsset } from '@/components/agent/types'
import { useAgentConversations } from '@/composables/useAgentConversations'

const route = useRoute()
const router = useRouter()
const status = ref<AgentStatus | null>(null)
const question = ref('')
const loading = ref(false)
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
} = useAgentConversations()

const quickPrompts = [
  '本期各地区贷款余额是多少？',
  '本期各机构普惠贷款余额',
  '本期不良贷款余额怎么统计？',
  '帮我生成贷款快照表的 MaxCompute 查询 SQL',
  'region_code 是什么字段？',
  '贷款余额使用哪张数据表？',
]

async function refreshStatus() {
  try { status.value = await agentApi.status() } catch { status.value = null }
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
  sessionId.value = conversation.sessionId || null
  messages.value = [...conversation.messages]
  contextAsset.value = conversation.contextAsset ? { ...conversation.contextAsset } : null
  nextTick(() => { resizeComposer(); scrollBottom() })
}

async function selectConversation(conversation: AgentConversation) {
  if (loading.value) return
  if (route.query.asset || route.query.q) await router.replace({ name: 'agent' })
  const selected = activateConversation(conversation.id)
  if (selected) restoreConversation(selected)
}

async function renameConversation(conversation: AgentConversation) {
  try {
    const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', { inputValue: conversation.title, inputPlaceholder: '会话名称', confirmButtonText: '保存', cancelButtonText: '取消', inputValidator: (value) => !!String(value || '').trim() || '请输入会话名称' })
    rename(conversation.id, String(result.value || ''))
  } catch { /* user cancelled */ }
}

async function deleteConversation(conversation: AgentConversation) {
  try { await ElMessageBox.confirm(`删除“${conversation.title}”？删除后仅移除当前浏览器中的历史记录。`, '删除会话', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }) } catch { return }
  if (remove(conversation.id)) resetConversationState()
}

function toggleConversationPin(conversation: AgentConversation) { togglePin(conversation.id) }
function resetConversationState() { sessionId.value = null; messages.value = []; contextAsset.value = null; question.value = ''; nextTick(resizeComposer) }

async function newSession() {
  if (loading.value) return
  clearActive(); resetConversationState()
  if (route.query.asset || route.query.q) await router.replace({ name: 'agent' })
}

async function clearContext() {
  contextAsset.value = null
  syncActive(messages.value, sessionId.value, null)
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

async function submit() {
  const userQuestion = question.value.trim()
  if (!userQuestion || !status.value?.ready || loading.value) return
  if (!activeConversationId.value) createConversation(userQuestion, contextAsset.value)
  messages.value.push({ role: 'user', text: userQuestion })
  syncActive(messages.value, sessionId.value, contextAsset.value)
  question.value = ''; resizeComposer(); loading.value = true; await scrollBottom()

  const prompt = contextAsset.value
    ? `当前问题针对 DataControl 数据资产：${contextAsset.value.bizName || contextAsset.value.tableName}（asset_id=${contextAsset.value.assetId}，table=${contextAsset.value.tableName}）。请优先通过 Agent3 MCP 读取该资产及关联事实后回答，不要凭空猜测。\n用户问题：${userQuestion}`
    : userQuestion
  try {
    const result: AgentResult = await agentApi.query(prompt, sessionId.value)
    if (result.sessionId) sessionId.value = result.sessionId
    messages.value.push({ role: 'assistant', text: result.answer || '分析完成。', summary: result.summary, sql: result.sql, validation: result.validation, validationState: result.validationState, events: result.events, evidence: result.evidence })
    syncActive(messages.value, sessionId.value, contextAsset.value)
    await scrollBottom()
  } catch (error) {
    console.error('DataAgent query failed', error)
    ElMessage.error('智能问数本次未完成，请确认 Agent 服务状态后重试。')
    await refreshStatus()
    syncActive(messages.value, sessionId.value, contextAsset.value)
  } finally { loading.value = false; await scrollBottom() }
}

onMounted(async () => {
  loadConversations()
  await refreshStatus()
  const initialQuestion = typeof route.query.q === 'string' ? route.query.q.trim() : ''
  const hasRouteAsset = typeof route.query.asset === 'string' && !!route.query.asset
  if (hasRouteAsset || initialQuestion) {
    clearActive(); resetConversationState()
    if (hasRouteAsset) await loadContext()
    if (initialQuestion) question.value = initialQuestion
  } else {
    const restored = restoreLast()
    if (restored) restoreConversation(restored)
  }
  resizeComposer()
})
</script>

<style scoped>
.agent-screen { height: calc(100dvh - var(--dc-topbar)); min-height: 700px; padding: 18px 0; background: linear-gradient(180deg,#e2f1f9 0,#eef6fa 38%,#f4f8fb 100%); overflow: hidden; }
.agent-page { height: 100%; display: flex; flex-direction: column; max-width: 1420px; }
.agent-head { flex: none; display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; padding: 0 4px 16px; }
.agent-head h1 { font-size: 38px; letter-spacing: -.035em; margin: 5px 0 7px; color: #0f3b53; }
.agent-head p { font-size: 15px; line-height: 1.7; margin: 0; color: #3c6277; max-width: 820px; }
.service-status { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px; background: #ffeab7; border: 1px solid #d49e35; font-size: 13px; font-weight: 750; color: #70480a; }
.service-status i { width: 9px; height: 9px; border-radius: 50%; background: #bd7410; }
.service-status.ready { background: #d8efe4; border-color: #61aa84; color: #126546; }
.service-status.ready i { background: #1c805a; }
.agent-workspace { flex: 1; min-height: 0; display: grid; grid-template-columns: 268px minmax(0,1fr); overflow: hidden; border-color: #a9c9d8; box-shadow: 0 20px 52px rgba(27,78,106,.15); background: #fff; }
.chat-shell { min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; background: rgba(255,255,255,.99); }
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
@media(max-width:760px){.agent-screen{min-height:640px;padding:12px 0}.agent-head{align-items:flex-start;flex-direction:column;gap:10px;padding-bottom:12px}.agent-head h1{font-size:31px}.agent-workspace{grid-template-columns:1fr}.agent-workspace :deep(.history-pane){display:none}.messages{padding:21px 15px}.prompt-grid{grid-template-columns:1fr}.composer-wrap{padding:10px 12px 11px}.composer-hint span:first-child{display:none}.composer-hint{justify-content:flex-end}}
</style>
