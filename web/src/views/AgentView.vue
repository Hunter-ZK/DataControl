<template>
  <div class="dc-page agent-screen">
    <div class="dc-container agent-page">
      <header class="agent-head">
        <div>
          <span class="dc-eyebrow">✦ DATA INTELLIGENCE COPILOT</span>
          <h1>DataAgent <span>智能工作台</span></h1>
          <p>让数仓知识参与每一次问答：检索数据资产、解释指标口径、生成 SQL 与开发草案。</p>
        </div>
        <div class="agent-head-status"><span class="agent-version">INTELLIGENCE WORKSPACE</span>
          <span class="service-status" :class="{ ready: status?.ready }"><i></i>{{ status?.ready ? '服务正常' : '服务未就绪' }}</span>
        </div>
      </header>

      <section class="agent-workspace dc-card" :class="{ 'mobile-history-open': mobileHistoryOpen, 'inspector-visible': inspectorOpen, 'deliverables-visible': workspaceOpen }">
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
          <button class="mobile-history-trigger" @click="mobileHistoryOpen=!mobileHistoryOpen">
            <History :size="16"/> {{ mobileHistoryOpen ? '关闭历史' : '查看历史会话' }}
          </button>
          <div class="chat-model-bar">
            <div class="model-bar-brand"><span class="model-mark"><Sparkles :size="21"/></span><span>DataAgent</span></div>
            <span class="chat-model-label">模型</span>
            <div class="model-options" role="group" aria-label="选择当前对话模型">
              <button type="button" :class="{selected:modelMode==='deepseek'}" :disabled="loading" @click="chooseModel('deepseek')">DeepSeek 官方</button>
              <button type="button" :class="{selected:modelMode==='free-test'}" :disabled="loading" @click="chooseModel('free-test')"><FlaskConical :size="14"/>免费模型测试</button>
              <button type="button" :class="{selected:modelMode==='local-deepseek'}" :disabled="loading" @click="chooseModel('local-deepseek')"><Cpu :size="14"/>本地 DeepSeek</button>
            </div>
            <div class="tier-options" role="group" aria-label="选择任务类型">
              <button type="button" :class="{active:taskTier==='standard'}" :disabled="loading"
                @click="chooseTier('standard')">标准问数</button>
              <button type="button" :class="{active:taskTier==='multi'}" :disabled="loading"
                @click="chooseTier('multi')">多步任务</button>
              <button v-if="modelMode==='local-deepseek'" type="button" :class="{active:taskTier==='quick'}" :disabled="loading"
                @click="chooseTier('quick')"><Zap :size="14"/>极速回答</button>
            </div>
            <div v-if="modelMode==='local-deepseek' && taskTier==='quick'" class="quick-token-config">
              <label for="quick-tokens">最长输出</label>
              <select id="quick-tokens" v-model.number="quickMaxTokens" :disabled="loading" aria-label="极速模式最长输出 Token">
                <option :value="128">128 tokens · 最快</option>
                <option :value="256">256 tokens · 推荐</option>
                <option :value="512">512 tokens · 详细</option>
              </select>
            </div>
            <button class="deliverables-toggle" :class="{active:workspaceOpen}" @click="toggleWorkspace">
              <PanelsTopLeft :size="19"/> {{workspaceOpen?'收起成果':'成果工作区'}} <span v-if="deliverableCount">{{deliverableCount}}</span>
            </button>
            <button class="inspector-toggle" :class="{active:inspectorOpen}" @click="toggleInspector">
              <PanelRight :size="18"/>{{ inspectorOpen ? '收起工作面板' : '展开工作面板' }}
            </button>
          </div>
          <div class="agent-mode-strip">
            <span class="mode-indicator"><span class="mode-pulse" :class="{idle:status?.ready&&!loading,offline:!status?.ready}"></span>{{loading?'正在处理任务':status?.ready?'已就绪':'服务未就绪'}}</span>
            <span><Cpu :size="15"/>{{modelMode==='local-deepseek'?'本地 DeepSeek · llama.cpp':modelMode==='free-test'?'免费模型测试': 'DeepSeek 官方'}}</span>
            <span><Workflow :size="15"/>{{taskTier==='quick'?'极速回答 · 单次推理':taskTier==='multi'?'多步任务':'标准问数'}}</span>
            <span class="mode-safe"><ShieldCheck :size="15"/>{{taskTier==='quick'?'仅生成文本 · 不访问工具与 SQL':'仅生成和校验 · 不执行 SQL'}}</span>
          </div>
          <div v-if="modelMode==='free-test'" class="runtime-warning"><TriangleAlert :size="18"/><span>免费模型使用第三方公共网关，可能记录问题及工具信息。仅测试模拟数据；不得输入真实业务、内部 SQL、账号或个人信息。</span></div>
          <div v-if="modelMode==='local-deepseek' && taskTier!=='quick'" class="runtime-warning"><Cpu :size="18"/><span>调用本机 llama.cpp（127.0.0.1:9931）。7B CPU 推理可能较慢；完整任务仍使用 MCP 与静态 SQL 校验，不执行生产 SQL。</span></div>
          <div v-if="modelMode==='local-deepseek' && taskTier==='quick'" class="runtime-warning"><Zap :size="18"/><span>极速模式：仅参考本次问题，单次调用本地模型并尝试关闭深度思考；不读取历史对话、不查询元数据、不调用 Agent 工具或校验 SQL。可信问数请切换标准模式。</span></div>
          <div v-if="contextAsset" class="context-strip">
            <Database :size="17" />
            <div><span>当前数据资产</span><b>{{ contextAsset.bizName || contextAsset.tableName }}</b><code>{{ contextAsset.tableName }}</code></div>
            <button @click="clearContext"><X :size="15" />清除</button>
          </div>
          <div v-if="!status?.ready" class="runtime-warning"><TriangleAlert :size="18" /><span>{{ agentUnavailableReason }}</span></div>

          <div ref="messageBox" class="messages">
            <div v-if="messages.length === 0" class="welcome">
              <div class="welcome-constellation" aria-hidden="true">
                <span class="constellation-orbit orbit-first"></span><span class="constellation-orbit orbit-second"></span>
                <span class="constellation-dot dot-a"></span><span class="constellation-dot dot-b"></span>
                <span class="constellation-dot dot-c"></span>
              </div>
              <div class="welcome-icon"><Sparkles :size="36" /></div>
              <span class="welcome-label">YOUR DATA COPILOT</span>
              <h2>今天，想探索什么数据？</h2>
              <p>从一个问题开始，DataAgent 将结合现有元数据与业务口径，为你提供有依据的回答和经过静态校验的 SQL。</p>
              <div class="welcome-capabilities" aria-label="DataAgent 支持的工作">
                <span><Database :size="16"/>发现可信资产</span>
                <span><ChartNoAxesCombined :size="16"/>理解业务口径</span>
                <span><Code2 :size="16"/>生成 SQL 草案</span>
                <span><ShieldCheck :size="16"/>静态校验</span>
              </div>
              <div class="prompt-heading"><span>从这些任务开始</span><small>选择后可修改问题</small></div>
              <div class="prompt-grid">
                <button v-for="(item,index) in quickPrompts" :key="item" @click="usePrompt(item)">
                  <span class="prompt-icon"><component :is="[Database, ChartNoAxesCombined, Code2, ShieldCheck][index%4]" :size="24"/></span>
                  <span>{{ item }}</span><ArrowUpRight :size="17" />
                </button>
              </div>
              <p class="welcome-note"><ShieldCheck :size="16"/>{{taskTier==='quick'?'极速模式仅回答一般问题，不查询元数据或验证 SQL':'只生成与校验 SQL，不执行生产查询'}}</p>
            </div>

            <AgentMessageView
              v-for="(item, index) in messages"
              :key="index"
              :message="item"
              :tier="taskTier==='quick'?'standard':taskTier"
              @clarify="submitClarification(index, $event)"
            />
            <div v-if="latestAnswer && !loading && (latestAnswer.sql || latestAnswer.evidence || latestAnswer.events?.length)" class="result-shortcuts">
              <button class="result-workspace-entry" @click="openWorkspace"><PanelsTopLeft :size="17"/>打开独立成果工作区 <ArrowUpRight :size="15"/></button>
              <span><PanelsTopLeft :size="17"/> 结果工作区</span>
              <button v-if="latestAnswer.sql" @click="openInspector('sql')"><Code2 :size="16"/>查看生成的 SQL <ArrowUpRight :size="14"/></button>
              <button v-if="latestAnswer.evidence" @click="openInspector('evidence')"><Database :size="16"/>查看数据依据 <ArrowUpRight :size="14"/></button>
              <button v-if="latestAnswer.events?.length" @click="openInspector('steps')"><Workflow :size="16"/>查看任务步骤 <ArrowUpRight :size="14"/></button>
            </div>
            <div v-if="latestAnswer && !loading" class="answer-quick-actions">
              <button @click="copyLatestAnswer"><Copy :size="14"/>复制回答</button>
              <button @click="regenerateLatest"><RotateCcw :size="14"/>重新生成</button>
              <button @click="recordFeedback('useful')"><ThumbsUp :size="14"/>有用</button>
              <button @click="recordFeedback('incorrect')"><ThumbsDown :size="14"/>有误</button>
            </div>
            <div v-if="latestAnswer && !loading && suggestedPrompts.length" class="followup-prompts">
              <span>继续探索</span>
              <button v-for="suggestion in suggestedPrompts" :key="suggestion" @click="question=suggestion;nextTick(resizeComposer)">
                {{ suggestion }}
              </button>
            </div>

            <article v-if="loading" class="loading-answer">
              <div class="loading-label">
                <span class="agent-avatar"><LoaderCircle class="spin" :size="16" /></span>
                <b>{{ stopRequested ? '正在停止任务' : 'DataAgent 正在分析' }}</b>
                <button class="stop-turn" :disabled="stopRequested" @click="stopAgentTurn"><Square :size="12" />停止</button>
              </div>
              <p v-if="taskTier==='quick'">本地 CPU 模型单次生成中{{liveElapsedMs>0?'，已运行 '+Math.floor(liveElapsedMs/1000)+' 秒':''}}；不调用 MCP 工具。服务器每 10 秒发送一次保活信号。</p>
              <template v-else>
                <p>{{ liveEvents.length ? '以下步骤来自真实 Agent3 工具调用，完成后将展示证据与最终答案。' : '已开始处理，等待 Agent3 返回实际工具步骤。' }}</p>
                <AgentTaskJourney :events="liveEvents" :tier="taskTier" :running="true"/>
              </template>
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
              <button class="send" :disabled="!status?.ready || loading || !question.trim()" @click="submit" title="发送问题" aria-label="发送问题"><ArrowUp :size="22" /></button>
            </div>
            <div class="composer-hint"><span>Enter 发送 · Shift+Enter 换行</span><span><ShieldCheck :size="16" />资产依据 · SQL 静态校验 · 不执行查询</span></div>
          </div>
        </section>
        <AgentDeliverableWorkspace v-if="workspaceOpen" :messages="messages" :tier="taskTier==='quick'?'standard':taskTier" :running="loading" @close="workspaceOpen=false"/>
        <aside v-if="inspectorOpen" class="agent-inspector" aria-label="依据与 SQL 检查器">
          <header><div><b>工作面板</b><small>证据、SQL 和工具活动</small></div><button @click="inspectorOpen=false" title="收起面板" aria-label="收起面板"><X :size="17"/></button></header>
          <nav class="inspector-tabs" aria-label="检查器页面">
            <button :class="{active:inspectorTab==='evidence'}" @click="inspectorTab='evidence'">数据依据</button>
            <button :class="{active:inspectorTab==='sql'}" @click="inspectorTab='sql'">SQL 校验</button>
            <button :class="{active:inspectorTab==='steps'}" @click="inspectorTab='steps'">执行步骤</button>
          </nav>
          <div class="inspector-content">
            <template v-if="inspectorTab==='evidence'">
              <AgentEvidence v-if="latestAnswer?.evidence" :evidence="latestAnswer.evidence"/>
              <p v-else class="inspector-empty">尚无可信资产证据。提问后会显示相关指标和数据资产。</p>
            </template>
            <template v-if="inspectorTab==='sql'">
              <template v-if="latestAnswer?.sql">
                <AgentSqlCard :message="latestAnswer"/>
                <AgentValidationPanel :message="latestAnswer"/>
              </template>
              <p v-else class="inspector-empty">本轮尚无生成的 SQL。</p>
            </template>
            <template v-if="inspectorTab==='steps'">
              <AgentTaskJourney v-if="loading" :events="liveEvents" :tier="taskTier==='quick'?'standard':taskTier" :running="true"/>
              <AgentTaskJourney v-else-if="latestAnswer?.events?.length" :events="latestAnswer.events" :tier="taskTier==='quick'?'standard':taskTier" :running="false"/>
              <AgentTrace v-if="loading && liveEvents.length" :events="liveEvents"/>
              <AgentTrace v-else-if="latestAnswer?.events?.length" :events="latestAnswer.events"/>
              <p v-else class="inspector-empty">真实工具调用会在这里逐步显示，不展示模型隐藏推理。</p>
            </template>
          </div>
        </aside>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUp, ArrowUpRight, ChartNoAxesCombined, Code2, Copy, Cpu, Database, FlaskConical, History, LoaderCircle, PanelRight, PanelsTopLeft, RotateCcw, ShieldCheck, Sparkles, Square, ThumbsDown, ThumbsUp, TriangleAlert, Workflow, X, Zap } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, assetApi, type AgentActivity, type AgentModelMode, type AgentResult, type AgentStatus, type AgentStreamEvent, AgentTurnCancelledError, AgentStreamFailureError } from '@/api/client'
import AgentConversationSidebar from '@/components/agent/AgentConversationSidebar.vue'
import AgentMessageView from '@/components/agent/AgentMessage.vue'
import AgentTrace from '@/components/agent/AgentTrace.vue'
import AgentTaskJourney from '@/components/agent/AgentTaskJourney.vue'
import AgentEvidence from '@/components/agent/AgentEvidence.vue'
import AgentSqlCard from '@/components/agent/AgentSqlCard.vue'
import AgentValidationPanel from '@/components/agent/AgentValidationPanel.vue'
import AgentDeliverableWorkspace from '@/components/agent/AgentDeliverableWorkspace.vue'
import type { AgentConversation, AgentMessage, ContextAsset } from '@/components/agent/types'
import { useAgentConversations } from '@/composables/useAgentConversations'

const route = useRoute()
const router = useRouter()
const status = ref<AgentStatus | null>(null)
const modelMode = ref<AgentModelMode>('deepseek')
async function chooseModel(value: AgentModelMode) {
  if (loading.value || modelMode.value === value) return
  if (messages.value.length) {
    ElMessage.warning('请新建会话后切换模型，避免不同模型混用上下文。')
    return
  }
  if (value === 'free-test' && contextAsset.value) {
    ElMessage.warning('已绑定资产的会话不能切换到公共网关测试模式。请使用纯模拟问题。')
    return
  }
  if (value === 'free-test') {
    try {
      await ElMessageBox.confirm(
        '免费模型通过外部公共网关处理请求，可能记录提示词和工具结果。请仅使用公开模拟数据，不要输入内部元数据、业务 SQL 或个人信息。开启此会话的免费测试模式？',
        '使用免费模型',
        { confirmButtonText: '使用免费模型', cancelButtonText: '取消', type: 'warning' },
      )
    } catch { return }
  }
  modelMode.value = value
  taskTier.value = 'standard'
  await refreshStatus()
}
const taskTier = ref<'standard' | 'multi' | 'quick'>('standard')
const savedQuickTokenChoice = Number(localStorage.getItem('datacontrol_local_quick_tokens_v1'))
const quickMaxTokens = ref<128 | 256 | 512>(
  savedQuickTokenChoice === 128 || savedQuickTokenChoice === 512 ? savedQuickTokenChoice : 256,
)
watch(quickMaxTokens, value => localStorage.setItem('datacontrol_local_quick_tokens_v1', String(value)))
function chooseTier(value: 'standard' | 'multi' | 'quick') {
  if (value === 'quick' && modelMode.value !== 'local-deepseek') return
  if (value === 'quick' && contextAsset.value) {
    ElMessage.warning('极速回答不查询绑定资产，请先清除资产上下文或使用标准问数。')
    return
  }
  if (loading.value) return
  if (messages.value.length && taskTier.value !== value) {
    ElMessage.warning('当前对话的任务类型已固定，请先新建会话后切换。')
    return
  }
  taskTier.value = value
  refreshStatus()
}
let statusRequestSerial = 0
const agentUnavailableReason = computed(() => {
  if (!status.value) return '无法获取 Agent 状态：请确认 DataControl 后端已在 8000 端口启动。'
  return status.value.reason
    ? `Agent 暂不可用：${status.value.reason}`
    : 'Agent 暂不可用：请查看启动终端的 Gateway/MCP 状态和日志。'
})
const mobileHistoryOpen = ref(false)
const inspectorOpen = ref(false)
const workspaceOpen = ref(false)
const deliverableCount = computed(() => messages.value.filter(x=>x.role==='assistant' && (x.text||x.sql)).length)
function toggleInspector(){
  if(!inspectorOpen.value)workspaceOpen.value=false
  inspectorOpen.value=!inspectorOpen.value
}
function toggleWorkspace(){
  if(!workspaceOpen.value)inspectorOpen.value=false
  workspaceOpen.value=!workspaceOpen.value
}
function openWorkspace(){workspaceOpen.value=true;inspectorOpen.value=false}
const inspectorTab = ref<'evidence' | 'sql' | 'steps'>('evidence')
function openInspector(tab: 'evidence' | 'sql' | 'steps') {
  inspectorTab.value = tab
  workspaceOpen.value = false
  inspectorOpen.value = true
}
const question = ref('')
const loading = ref(false)
const liveEvents = ref<AgentActivity[]>([])
const stopRequested = ref(false)
const liveElapsedMs = ref(0)
let activeRunId: string | null = null
let activeController: AbortController | null = null
const messages = ref<AgentMessage[]>([])
const latestAnswer = computed<AgentMessage | null>(
  () => [...messages.value].reverse().find(m => m.role === 'assistant') || null,
)
const suggestedPrompts = computed(() => {
  const dims = latestAnswer.value?.evidence?.dimensions || []
  if (!latestAnswer.value?.sql) return []
  const prompts = ['解释这个 SQL 的统计口径']
  if (dims.includes('region_code')) prompts.push('仅查看广东省的结果')
  if (dims.includes('org_code')) prompts.push('改为按机构统计')
  return prompts.slice(0, 3)
})
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
  hasUnscopedLegacy,
  adoptUnscopedLegacy,
  declineUnscopedLegacy,
} = useAgentConversations()

const quickPrompts = computed(() => taskTier.value === 'quick' ? [
  '解释 ODS、DWD、DWS 的区别',
  '帮我把这段需求表述得更简洁',
  '简要说明数仓开发的主要流程',
  'SQL 中 GROUP BY 有什么作用？',
  '给我几个规范的字段命名建议',
  '如何写好业务需求说明？',
] : [
  '今年贷款增长怎么样？',
  '本期各地区贷款余额是多少？',
  '各地区不良贷款率是多少？',
  '贷款余额最高的前 10 个地区',
  '广东省人民币贷款余额怎么统计？',
  '贷款余额使用哪张数据表？',
])

async function refreshStatus() {
  const serial = ++statusRequestSerial
  const chosen = modelMode.value
  const selectedTier = taskTier.value
  try {
    const state = await agentApi.status(chosen, selectedTier)
    if (serial === statusRequestSerial && chosen === modelMode.value
        && selectedTier === taskTier.value) status.value = state
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
  taskTier.value = conversation.taskTier === 'multi' ? 'multi' : conversation.taskTier === 'quick' ? 'quick' : 'standard'
  modelMode.value = conversation.modelMode
  sessionId.value = null
  messages.value = [...conversation.messages]
  contextAsset.value = conversation.contextAsset ? { ...conversation.contextAsset } : null
  nextTick(() => { resizeComposer(); scrollBottom() })
}

async function selectConversation(conversation: AgentConversation) {
  if (loading.value) return
  mobileHistoryOpen.value = false
  workspaceOpen.value=false
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
function resetConversationState() { sessionId.value = null; messages.value = []; contextAsset.value = null; question.value = ''; workspaceOpen.value = false; inspectorOpen.value=false; nextTick(resizeComposer) }

async function newSession() {
  if (loading.value) return
  mobileHistoryOpen.value = false
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
    durationMs: result.durationMs,
    toolCallCount: result.toolCallCount,
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
  if (update.type === 'heartbeat') {
    if (Number.isFinite(update.elapsedMs) && update.elapsedMs >= 0) {
      liveElapsedMs.value = Math.max(liveElapsedMs.value, update.elapsedMs)
    }
    return
  }
  if (update.type !== 'activity') return
  if (update.event.type !== 'tool_call' && update.event.type !== 'tool_result') return
  liveEvents.value = [...liveEvents.value, update.event].slice(-40)
  scrollBottom()
}

async function copyLatestAnswer() {
  if (!latestAnswer.value) return
  try { await navigator.clipboard.writeText(latestAnswer.value.text); ElMessage.success('已复制回答') }
  catch { ElMessage.warning('复制失败，请手动选择内容。') }
}
function recordFeedback(value: 'useful' | 'incorrect') {
  ElMessage.info(value === 'useful' ? '已记录本地有用标记' : '已记录本地有误标记')
  const user = JSON.parse(localStorage.getItem('datacontrol_user') || '{}') as { id?: number }
  if (!user.id) return
  const key = `datacontrol_agent_feedback_v1_user_${user.id}`
  const saved = JSON.parse(localStorage.getItem(key) || '{}') as Record<string, string>
  saved[activeConversationId.value || 'unknown'] = value
  localStorage.setItem(key, JSON.stringify(saved))
}
async function regenerateLatest() {
  if (loading.value) return
  const prior = [...messages.value].reverse().find(m => m.role === 'user')
  if (prior) await runAgentTurn('重新生成：' + prior.text, prior.text)
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
  const selectedMode = modelMode.value
  if (existing && existing.modelMode !== selectedMode) {
    ElMessage.warning('会话模型不一致，请新建会话。')
    return
  }
  if (selectedMode === 'free-test' && contextAsset.value) {
    ElMessage.error('公共测试模式不允许绑定业务资产。')
    return
  }
  if (!activeConversationId.value) {
    createConversation(createTitle || displayText, contextAsset.value, selectedMode, taskTier.value)
  }
  messages.value.push({ role: 'user', text: displayText })
  syncActive(messages.value, sessionId.value, contextAsset.value, selectedMode)
  loading.value = true
  if (activeConversationId.value) {
    const active = conversations.value.find((c) => c.id === activeConversationId.value)
    if (active && !active.serverId) {
      try {
        const saved = await agentApi.createConversation(active.title, selectedMode,
          active.contextAsset || null, active.taskTier || 'standard')
        attachServerId(active.id, saved.id)
      } catch {
        loading.value = false
        ElMessage.error('无法创建服务端会话，已阻止本轮请求，请检查登录状态和服务。')
        messages.value.pop()
        syncActive(messages.value, null, contextAsset.value, selectedMode)
        return
      }
    }
  }
  stopRequested.value = false
  liveEvents.value = []
  liveElapsedMs.value = 0
  activeRunId = crypto.randomUUID()
  activeController = new AbortController()
  await scrollBottom()
  try {
    const serverId = conversations.value.find((c) => c.id === activeConversationId.value)?.serverId || null
    const result = await agentApi.stream(prompt, sessionId.value, activeRunId,
      onAgentStreamEvent, activeController.signal, selectedMode, serverId, displayText,
      taskTier.value, selectedMode==='free-test', quickMaxTokens.value)
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
      // Never reuse an interrupted or failed Harness session.
      sessionId.value = null
      let explanation: string
      if (error instanceof AgentStreamFailureError) {
        explanation = `本轮运行失败 [${error.code}]：${error.message}`
      } else {
        let serverStatus: string | null = null
        if (activeRunId) {
          try { serverStatus = (await agentApi.runStatus(activeRunId)).status }
          catch { /* The status endpoint may also be unavailable. */ }
        }
        explanation = serverStatus === 'completed'
          ? '浏览器结果连接中断，但服务端记录显示任务已完成。请刷新当前会话查看结果，不要重复提交。'
          : serverStatus === 'failed' || serverStatus === 'timeout'
            ? `本轮在服务端的实际状态为 ${serverStatus}；请在管理员工作台查看对应 Run 的错误信息。`
            : 'Agent 连接中断，尚未确认服务端最终结果；请在管理员工作台查看该运行记录。'
      }
      messages.value.push({ role: 'assistant', text: explanation })
      ElMessage.error('本轮请求未成功，请查看聊天中的具体原因。')
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
          taskTier: c.taskTier || 'standard',
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
  const initialQuestion = typeof route.query.q === 'string' ? route.query.q.trim() : ''
  if (!localStorage.getItem('datacontrol_token')
    || !localStorage.getItem('datacontrol_user')) {
    await router.replace({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  loadConversations()
  if (hasUnscopedLegacy()) {
    try {
      await ElMessageBox.confirm(
        '发现旧版本未标记所属账号的浏览器会话。为避免账号间混用，默认不会展示。确认这些记录属于当前登录账号后，是否导入当前账号？',
        '旧版历史归属确认',
        { confirmButtonText: '导入到当前账号', cancelButtonText: '暂不导入', type: 'warning' },
      )
      const count = adoptUnscopedLegacy()
      if (count) ElMessage.success(`已将 ${count} 条旧会话迁入当前账号的本地历史`)
    } catch { declineUnscopedLegacy() }
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
  const requestedId = typeof route.query.conversationId === 'string' ? route.query.conversationId : null
  if (requestedId) {
    const matching = conversations.value.find(c => c.serverId === requestedId || c.id === requestedId)
    if (matching) {
      const selected = activateConversation(matching.id)
      if (selected) restoreConversation(selected)
    }
  }
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
.agent-workspace { flex: 1; min-height: 0; display: grid; grid-template-columns: 240px minmax(0,1fr) 300px; overflow: hidden; border-color: #a9c9d8; box-shadow: 0 20px 52px rgba(27,78,106,.15); background: #fff; }
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
@media(max-width:1180px){.agent-workspace{grid-template-columns:220px minmax(0,1fr)}.agent-inspector{display:none}}
@media(max-width:760px){.chat-model-bar{padding:9px 12px;gap:7px;flex-wrap:wrap}.model-context{display:none}.model-options button{padding:7px 9px}.agent-screen{min-height:640px;padding:12px 0}.agent-head{align-items:flex-start;flex-direction:column;gap:10px;padding-bottom:12px}.agent-head h1{font-size:31px}.agent-workspace{grid-template-columns:1fr}.agent-workspace :deep(.history-pane){display:none}.messages{padding:21px 15px}.prompt-grid{grid-template-columns:1fr}.composer-wrap{padding:10px 12px 11px}.composer-hint span:first-child{display:none}.composer-hint{justify-content:flex-end}}
.mode-pulse.offline{animation:none;background:#c48f49;box-shadow:0 0 0 3px #fbf0dd}

/* Dual-mode long-task deliverable workspace, mutually exclusive with inspector. */
.deliverables-toggle{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid #abc9f2;background:linear-gradient(110deg,#eaf3ff,#fff);color:#285fd1;border-radius:9px;font-size:13px;font-weight:770;cursor:pointer;white-space:nowrap}
.deliverables-toggle:hover,.deliverables-toggle.active{border-color:#6da5ed;background:#dbeaff;box-shadow:0 3px 10px #2b62b526}
.deliverables-toggle span{background:#2d6fde;color:white;border-radius:999px;font-size:11px;padding:2px 7px}
.agent-workspace.deliverables-visible{grid-template-columns:222px minmax(330px,.82fr) minmax(440px,1.18fr)!important}
.agent-workspace.deliverables-visible .chat-shell{min-width:0}
.result-shortcuts .result-workspace-entry{border-color:#2d6ad9;background:linear-gradient(100deg,#326fe5,#5395ef);color:white;font-weight:800}
.result-shortcuts .result-workspace-entry:hover{background:#1e58c8}
@media(max-width:1450px){.agent-workspace.deliverables-visible{grid-template-columns:205px minmax(250px,.75fr) minmax(390px,1.25fr)!important}}
@media(max-width:1180px){.agent-workspace.deliverables-visible{grid-template-columns:205px minmax(0,1fr)!important;position:relative}
.agent-workspace.deliverables-visible .deliverable-workspace{position:absolute;right:0;top:0;bottom:0;width:min(720px,85vw);z-index:28;box-shadow:-15px 0 44px #224a8740}}
@media(max-width:760px){.deliverables-toggle{font-size:12px;padding:8px}.agent-workspace.deliverables-visible{grid-template-columns:1fr!important}
.agent-workspace.deliverables-visible .deliverable-workspace{width:100%;left:0;right:0}.result-shortcuts .result-workspace-entry{width:100%;justify-content:center}}
</style>

<style scoped>
 .mobile-history-trigger {display:none;border:0;border-bottom:1px solid var(--dc-border);padding:10px 14px;background:var(--dc-primary-soft);color:var(--dc-primary);font-size:13px;align-items:center;gap:7px;cursor:pointer;}
 @media(max-width:760px) {
  .mobile-history-trigger{display:flex;}
  .agent-workspace{position:relative;}
  .agent-workspace.mobile-history-open :deep(.history-pane){display:flex;position:absolute;top:0;bottom:0;left:0;width:min(320px,88vw);z-index:20;background:#fff;box-shadow:0 10px 32px rgba(28,60,85,.22);}
 }
 .tier-options{display:inline-flex;gap:3px;padding:3px;border:1px solid var(--dc-border);border-radius:9px;background:var(--dc-surface-soft);}
 .tier-options button{border:0;border-radius:6px;padding:7px 10px;color:var(--dc-text-2);background:transparent;font-size:12px;cursor:pointer;}
 .tier-options button.active{background:#fff;color:var(--dc-agent);font-weight:750;box-shadow:0 1px 5px rgba(18,90,112,.1);}
 .tier-options button:disabled{opacity:.5;cursor:not-allowed;}
 .fixed-model {display:inline-flex;align-items:center;padding:8px 12px;background:#fff;border:1px solid var(--dc-border);border-radius:8px;color:var(--dc-primary);font-size:12px;font-weight:700;}
 .inspector-toggle {border:0;background:transparent;color:var(--dc-primary);font-size:12px;display:inline-flex;align-items:center;gap:5px;cursor:pointer;}
 .agent-inspector {min-height:0;display:flex;flex-direction:column;overflow:hidden;border-left:1px solid var(--dc-border);background:#fbfdfe;}
 .agent-inspector header {display:grid;gap:4px;padding:18px 15px 10px;}
 .agent-inspector header b {font-size:15px;}
 .agent-inspector header small {color:var(--dc-text-2);font-size:12px;}
 .inspector-tabs {display:flex;gap:2px;padding:7px;border-bottom:1px solid var(--dc-border);}
 .inspector-tabs button {flex:1;border:0;padding:8px 4px;border-radius:7px;background:transparent;color:var(--dc-text-2);font-size:12px;cursor:pointer;}
 .inspector-tabs button.active {background:var(--dc-primary-soft);color:var(--dc-primary);font-weight:700;}
 .inspector-content {flex:1;overflow-y:auto;padding:12px;}
 .inspector-empty{color:var(--dc-text-2);font-size:13px;line-height:1.7;}
 .answer-quick-actions,.followup-prompts{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin:0 0 14px;}
 .answer-quick-actions button,.followup-prompts button{border:1px solid var(--dc-border);border-radius:8px;background:white;padding:7px 10px;color:var(--dc-text-2);cursor:pointer;display:inline-flex;align-items:center;gap:5px;font-size:12px;}
 .followup-prompts>span{font-size:12px;color:var(--dc-text-3);}
 .stop-turn { margin-left: auto; display: inline-flex; align-items: center; gap: 5px; padding: 6px 11px; border: 1px solid #b8cdd9; border-radius: 8px; background: #fff; color: #516b7a; cursor: pointer; font-size: 12px; font-weight: 650; }
.stop-turn:hover:not(:disabled) { border-color: #d78b8b; color: #a64a4a; background: #fff6f6; }
.stop-turn:disabled { cursor: wait; opacity: .6; }

/* B3: quiet IDE-like Agent workspace, with task state first and visual clutter last */
.agent-screen{background:var(--dc-bg);min-height:680px;padding:14px 0;overflow:hidden}
.agent-page{max-width:1510px}
.agent-head{padding:0 3px 13px;align-items:center;gap:16px}
.agent-head h1{font-size:24px;font-weight:750;color:var(--dc-text);margin:3px 0 4px;letter-spacing:-.02em}
.agent-head p{font-size:12px;color:var(--dc-text-2);line-height:1.6;max-width:880px}
.service-status{background:#fff5e8;border:1px solid #f0dbb5;color:#99600c;padding:7px 11px;font-size:12px;font-weight:680}
.service-status.ready{background:#ebf8f2;border-color:#d1ebdf;color:#087e66}
.agent-workspace{grid-template-columns:216px minmax(0,1fr) 292px;border:1px solid var(--dc-border);border-radius:12px;box-shadow:var(--dc-shadow-sm)}
.chat-shell{background:#fff}
.chat-model-bar{padding:10px 15px;gap:8px;background:#fff;border-bottom:1px solid var(--dc-border);flex-wrap:wrap}
.chat-model-label{font-size:12px;color:var(--dc-text-3)}
.model-options,.tier-options{border-color:#e1e9f5;background:#f6f9fd;border-radius:8px}
.model-options button{padding:7px 9px;color:#607692;font-size:12px;border-radius:6px}
.model-options button.selected,.tier-options button.active{background:#fff;border-color:#d8e4f7;color:var(--dc-primary);box-shadow:0 1px 4px rgba(27,73,143,.05)}
.model-context{color:var(--dc-text-3);font-size:12px}
.inspector-toggle{color:var(--dc-primary);font-size:12px}
.context-strip{background:#f2f7ff;border-color:#dfeafc;color:#335b96;padding:9px 15px}
.context-strip span,.context-strip code{color:#7289a9}
.runtime-warning{background:#fff9ed;border-color:#f0dfbf;color:#8b661e;padding:9px 15px;font-size:12px;font-weight:550}
.messages{padding:25px clamp(18px,3vw,46px)}
.welcome{margin:7vh auto 0;max-width:680px}
.welcome-icon{background:#edf4ff;color:var(--dc-primary);border:1px solid #dce8fc;box-shadow:none;border-radius:15px}
.welcome h2{font-size:24px;color:var(--dc-text)}
.welcome p{font-size:13px;color:var(--dc-text-2)}
.prompt-grid button{min-height:55px;background:#fff;border:1px solid var(--dc-border);color:#435b7a;font-size:13px;font-weight:570;border-radius:9px}
.prompt-grid button:hover{background:#f7faff;border-color:#bfd4fa;color:var(--dc-primary)}
.loading-label{color:var(--dc-text);font-size:13px}
.agent-avatar{background:#eaf2ff;color:var(--dc-primary)}
.loading-answer p{font-size:12px;color:var(--dc-text-3)}
.composer-wrap{background:#fff;border-top:1px solid var(--dc-border);padding:13px 17px 14px;box-shadow:none}
.composer{border:1px solid #bdcfec;box-shadow:none;border-radius:11px}
.composer:focus-within{border-color:#6295ec;box-shadow:0 0 0 3px rgba(37,99,235,.09)}
.composer textarea{font-size:14px;color:var(--dc-text)}
.send{background:var(--dc-primary);border-radius:8px}
.send:hover{background:var(--dc-primary-strong)}
.composer-hint{font-size:12px;color:var(--dc-text-3)}
.agent-inspector{background:#fbfcff;border-color:var(--dc-border)}
.agent-inspector header{padding:15px 14px 9px}
.inspector-tabs button.active{background:#eaf2ff;color:var(--dc-primary)}
.answer-quick-actions button:hover,.followup-prompts button:hover{border-color:#bcd3f8;color:var(--dc-primary);background:#f8fbff}
@media(max-width:1200px){.agent-workspace{grid-template-columns:205px minmax(0,1fr)}}
@media(max-width:760px){.agent-screen{height:calc(100dvh - var(--dc-topbar));min-height:640px}.agent-head p{display:none}.agent-head h1{font-size:21px}.chat-model-bar{gap:6px;padding:8px}.model-context{display:none}.messages{padding:20px 12px}.agent-workspace{grid-template-columns:1fr}}


/* Atlas Agent: AI-native conversation, more expressive but evidence-first */
.agent-screen{background:radial-gradient(ellipse at 60% 0,#e2efff,transparent 47%),var(--dc-bg);height:calc(100dvh - var(--dc-topbar));min-height:680px;padding:15px 0 17px}
.agent-page{width:min(calc(100% - 30px),1540px);max-width:1540px}
.agent-head{align-items:center;padding-bottom:13px}
.agent-head .dc-eyebrow{font-size:12px;letter-spacing:.105em}
.agent-head h1{font-size:27px;letter-spacing:-.03em;font-weight:790;color:#1a3969;margin:2px 0}
.agent-head h1 span{color:#396ed1}
.agent-head p{font-size:13px;max-width:900px;color:#5e7596}
.service-status{border-radius:9px;padding:8px 12px}
.agent-workspace{grid-template-columns:248px minmax(0,1fr)!important;border-radius:16px;border-color:#bed3ee;box-shadow:0 16px 39px rgba(34,82,155,.13)}
.agent-workspace.inspector-visible{grid-template-columns:248px minmax(0,1fr) 334px!important}
.chat-shell{min-width:0;background:#fff}
.chat-model-bar{display:flex;flex-wrap:wrap;align-items:center;gap:9px;padding:12px 19px;background:linear-gradient(100deg,#f8fbff,#fff);border-bottom:1px solid #dae6f7}
.model-bar-brand{display:flex;align-items:center;gap:8px;margin-right:6px;color:#2b63d1;font-size:16px;font-weight:790;white-space:nowrap}
.model-bar-brand svg{color:#3774eb}
.chat-model-label{font-size:12px;color:#8698b1}
.model-options,.tier-options{background:#ecf3ff;border:1px solid #cbdcf4;border-radius:10px;padding:4px;gap:2px}
.model-options button,.tier-options button{font-size:13px;font-weight:650;padding:8px 11px;border-radius:7px}
.model-options button.selected,.tier-options button.active{background:#fff;border-color:#c4d6f3;color:#286be4;box-shadow:0 3px 9px rgba(33,87,167,.11)}
.inspector-toggle{margin-left:auto;display:flex;align-items:center;gap:8px;padding:9px 12px;border:1px solid #d0def4;background:#fff;border-radius:9px;color:#4772b1;font-size:13px;font-weight:730}
.inspector-toggle:hover,.inspector-toggle.active{background:#eaf2ff;color:#215fcf}
.messages{background:radial-gradient(ellipse 600px 430px at 52% 0,#f5f9ff 0%,#fff 80%);padding:25px clamp(22px,3vw,48px)}
.welcome{max-width:785px;margin:4vh auto 0;text-align:center}
.welcome-icon{width:77px;height:77px;border-radius:24px;background:linear-gradient(145deg,#2b66e7,#59a0ff);color:#fff;border:1px solid #8abbff;box-shadow:0 16px 35px rgba(39,104,213,.25),inset 0 1px rgba(255,255,255,.3);margin:0 auto 17px}
.welcome-label{display:block;letter-spacing:.14em;color:#5182d2;font-size:12px;font-weight:800;margin-bottom:8px}
.welcome h2{font-size:32px;letter-spacing:-.025em;color:#193a69;font-weight:800}
.welcome>p{font-size:15px;line-height:1.85;color:#6b81a2;max-width:630px;margin:11px auto 25px}
.prompt-heading{display:flex;justify-content:space-between;align-items:center;text-align:left;margin:14px 1px 11px;color:#36567e;font-size:15px;font-weight:770}
.prompt-heading small{font-size:12px;color:#9badc3;font-weight:550}
.prompt-grid{gap:13px}
.prompt-grid button{min-height:95px;display:flex;align-items:center;gap:13px;text-align:left;padding:18px;border-radius:13px;background:linear-gradient(145deg,#fff,#f7faff);border:1px solid #ccdff7;box-shadow:0 6px 17px rgba(45,91,158,.065);color:#304f76;font-size:14px;font-weight:660;transition:transform .17s,box-shadow .17s}
.prompt-grid button:hover{transform:translateY(-2px);border-color:#91b8f4;background:#eef6ff;box-shadow:0 12px 29px rgba(38,100,183,.14)}
.prompt-grid button>span:nth-child(2){flex:1}
.prompt-icon{display:grid;place-items:center;width:47px;height:47px;flex:none;border-radius:13px;background:#e6f0ff;color:#3477e2}
.prompt-grid button:nth-child(2) .prompt-icon{background:#efeaff;color:#7d65d2}
.prompt-grid button:nth-child(3) .prompt-icon{background:#e3f7ff;color:#1486b7}
.prompt-grid button:nth-child(4) .prompt-icon{background:#e4f7ef;color:#0e8c6a}
.welcome>p.welcome-note{margin:22px auto 0;display:flex;align-items:center;justify-content:center;gap:8px;font-size:12px;color:#8ba0ba}
.runtime-warning{font-size:13px}
.messages .loading-answer{background:#fff;border:1px solid #d3e2f6;box-shadow:0 9px 24px rgba(40,89,162,.06);padding:18px 20px;border-radius:14px}
.loading-answer p{margin-left:40px;font-size:13px}
.agent-avatar{background:#e7f0ff;color:#2769d7}
.composer-wrap{padding:14px 23px 16px;border-top:1px solid #dce7f8;background:#fff}
.composer{border:1.5px solid #b5ccef;border-radius:14px;padding:10px 10px 10px 17px;background:#fff;box-shadow:0 5px 19px rgba(36,88,163,.08)}
.composer:focus-within{border-color:#5590ef;box-shadow:0 0 0 4px rgba(37,99,235,.08),0 9px 25px rgba(36,88,163,.1)}
.composer textarea{font-size:15px;color:#213e68;padding:6px 4px;line-height:1.6}
.composer textarea::placeholder{color:#99aac3}
.send{width:44px;height:44px;border-radius:10px;background:linear-gradient(125deg,#2a66eb,#4c8cf3);box-shadow:0 6px 17px rgba(43,103,219,.19)}
.send:hover{background:#1c5bda}
.composer-hint{font-size:12px;margin-top:8px;color:#90a2b9}
.agent-inspector{background:#f9fbff;border-left:1px solid #d4e2f6}
.agent-inspector header{display:flex;align-items:center;justify-content:space-between;padding:17px 17px 13px;gap:10px;border-bottom:1px solid #e5edf8}
.agent-inspector header>div{display:grid;gap:3px}
.agent-inspector header b{font-size:17px;color:#24436c}
.agent-inspector header small{font-size:12px;color:#8ba0ba}
.agent-inspector header button{border:0;border-radius:7px;display:grid;place-items:center;width:29px;height:29px;background:#eaf2ff;color:#477aca;cursor:pointer}
.inspector-tabs{padding:9px 10px;border-bottom:1px solid #dce6f5}
.inspector-tabs button{font-size:13px;font-weight:630}
.inspector-tabs button.active{background:#e6f0ff;color:#2769d8}
.inspector-content{padding:15px}
.answer-quick-actions button,.followup-prompts button{font-size:13px;padding:9px 12px}
@media(max-width:1250px){.agent-workspace{grid-template-columns:220px minmax(0,1fr)!important}.agent-workspace.inspector-visible{grid-template-columns:220px minmax(0,1fr)!important}.agent-inspector{display:flex!important;position:absolute;right:0;top:0;bottom:0;width:min(355px,90vw);z-index:25;box-shadow:-12px 0 32px rgba(15,53,113,.19)}.agent-workspace{position:relative}}
@media(max-width:760px){.agent-screen{padding:8px 0 10px;min-height:600px}.agent-page{width:calc(100% - 16px)}.agent-head{padding:0 5px 10px}.agent-head h1{font-size:21px}.agent-head p{display:none}.agent-workspace{grid-template-columns:1fr!important}.agent-workspace.inspector-visible{grid-template-columns:1fr!important}.chat-model-bar{padding:9px;gap:7px}.model-bar-brand{font-size:14px}.model-bar-brand svg{width:17px}.model-options button,.tier-options button{padding:7px 9px;font-size:12px}.chat-model-label{display:none}.inspector-toggle{margin-left:0}.welcome{margin:3vh auto 0}.welcome h2{font-size:24px}.welcome>p{font-size:13px}.welcome-icon{width:60px;height:60px}.prompt-grid{grid-template-columns:1fr 1fr;gap:8px}.prompt-grid button{min-height:88px;padding:12px;flex-direction:column;align-items:flex-start;font-size:12px;gap:7px}.prompt-icon{width:35px;height:35px}.composer-wrap{padding:9px}.composer textarea{font-size:14px}.messages{padding:18px 13px}}


/* Atlas 2.1 — premium AI workspace without fabricated progress */

.agent-screen{background:radial-gradient(ellipse 820px 550px at 89% -10%,rgba(109,169,255,.20),transparent 76%),linear-gradient(165deg,#edf4ff,#f2f6ff 60%,#edf5ff)}
.agent-head{position:relative}
.agent-head .dc-eyebrow{color:#4b7fd2}
.agent-head h1{font-size:30px}
.agent-head-status{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.agent-version{font-size:11px;letter-spacing:.1em;color:#7694c4;font-weight:790;border:1px solid #c8dcfa;background:#f7faff;padding:8px 11px;border-radius:9px}
.agent-workspace{border:1px solid #aecaef;box-shadow:0 19px 55px rgba(27,71,143,.18),0 2px 12px rgba(30,96,198,.07)}
.chat-model-bar{background:linear-gradient(110deg,#f0f6ff,#fff);border-bottom:1px solid #cfe0f5}
.model-mark{display:grid;place-items:center;width:35px;height:35px;border-radius:11px;background:linear-gradient(135deg,#2e6ce4,#7ca9ff);color:white;box-shadow:0 5px 16px #2659d62c}
.model-bar-brand svg{color:#fff}
.agent-mode-strip{display:flex;align-items:center;gap:17px;flex-wrap:wrap;padding:9px 22px;background:linear-gradient(93deg,#f8fbff,#eef5ff);border-bottom:1px solid #e1eaf7;min-height:39px}
.agent-mode-strip>span{display:inline-flex;align-items:center;gap:6px;color:#738aab;font-size:12px;font-weight:650}
.agent-mode-strip .mode-indicator{color:#376ec1;font-weight:760}
.mode-pulse{width:8px;height:8px;display:inline-block;border-radius:50%;background:#347ee5;box-shadow:0 0 0 4px #dae9ff;animation:mode-breathe 1.6s ease-in-out infinite}
.mode-pulse.idle{animation:none;background:#2eaa87;box-shadow:0 0 0 3px #e2f4ed}
.agent-mode-strip .mode-safe{margin-left:auto;color:#37836f}
@keyframes mode-breathe{0%,100%{opacity:1;box-shadow:0 0 0 3px #d9e8ff}50%{opacity:.6;box-shadow:0 0 0 6px #e4efff}}
.welcome{position:relative;isolation:isolate;max-width:820px;margin:clamp(10px,3vh,34px) auto 0;padding:12px 0 18px}
.welcome:before{content:'';position:absolute;z-index:-1;left:10%;right:10%;top:-18px;height:220px;background:radial-gradient(ellipse at 50% 48%,rgba(74,134,230,.17),transparent 75%);pointer-events:none}
.welcome-constellation{position:absolute;z-index:-1;pointer-events:none;width:300px;height:180px;top:-10px;left:calc(50% - 150px)}
.constellation-orbit{position:absolute;border:1px dashed rgba(56,123,227,.18);border-radius:50%;inset:3px 12px}
.orbit-second{inset:18px 51px;border-style:solid;border-color:rgba(75,142,232,.15)}
.constellation-dot{position:absolute;width:9px;height:9px;border:2px solid #f6faff;border-radius:50%;background:#68a7ed;box-shadow:0 0 0 5px #dceaff}
.dot-a{left:14px;top:74px}.dot-b{right:25px;top:31px}.dot-c{right:58px;bottom:12px;background:#8c83e9}
.welcome-icon{position:relative;z-index:1;width:85px;height:85px;border-radius:27px;background:linear-gradient(135deg,#205bd7 0%,#4a85f4 57%,#80c7fd 100%);box-shadow:0 16px 40px #2d6bd54a,inset 0 1px 3px #ffffff91;transform:rotate(-3deg)}
.welcome-icon svg{transform:rotate(3deg)}
.welcome-label{color:#477bd2}
.welcome h2{color:#183967;font-size:33px}
.welcome-capabilities{display:flex;align-items:center;justify-content:center;gap:9px;flex-wrap:wrap;margin:0 auto 25px}
.welcome-capabilities span{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:690;color:#3568ae;border:1px solid #c8dcf8;background:linear-gradient(115deg,#fff,#f0f6ff);padding:9px 12px;border-radius:999px;box-shadow:0 4px 12px #3168aa0e}
.welcome-capabilities svg{color:#3a7ce2}
.prompt-heading{padding-top:9px;border-top:1px solid #deebfa}
.prompt-grid button{border:1px solid #c7daf5;box-shadow:0 7px 23px rgba(33,93,180,.095);position:relative;overflow:hidden}
.prompt-grid button:before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#4a85ea,#9fcaff);opacity:.7}
.prompt-grid button:nth-child(2):before{background:linear-gradient(90deg,#8162dc,#c3a8ff)}
.prompt-grid button:nth-child(3):before{background:linear-gradient(90deg,#25abc8,#a2e7f6)}
.prompt-grid button:nth-child(4):before{background:linear-gradient(90deg,#35a792,#a4efd4)}
.result-shortcuts{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:14px 0 13px;padding:12px 13px;border:1px solid #cbdff8;border-radius:12px;background:linear-gradient(95deg,#f0f6ff,#fff);box-shadow:0 5px 15px #3465b513}
.result-shortcuts>span{display:flex;align-items:center;gap:7px;color:#335d9c;font-size:13px;font-weight:790;margin-right:auto}
.result-shortcuts button{display:flex;align-items:center;gap:6px;border:1px solid #ccdef6;border-radius:8px;background:#fff;color:#2e6cce;padding:9px 10px;font-size:12px;font-weight:700;cursor:pointer}
.result-shortcuts button:hover{background:#e7f1ff;border-color:#8cb7f2}
.agent-inspector{background:linear-gradient(150deg,#f8fbff,#eef5ff)}
.agent-inspector header{background:#edf5ff}
.agent-inspector .inspector-content{padding:16px}
.composer-wrap{background:linear-gradient(180deg,#fff,#f9fbff)}
.composer{border-color:#9cbef0;box-shadow:0 7px 25px #2b6bd31b}
@media(max-width:900px){.agent-head-status{display:none}.agent-mode-strip{gap:10px;padding:8px 12px}.agent-mode-strip .mode-safe{margin-left:0}}
@media(max-width:760px){.agent-head h1{font-size:22px}.agent-mode-strip{gap:8px}.agent-mode-strip>span{font-size:11px}.agent-mode-strip .mode-safe{width:100%}.welcome-capabilities{gap:5px;margin-bottom:14px}.welcome-capabilities span{font-size:11px;padding:7px 9px}.welcome-constellation{transform:scale(.7)}.welcome h2{font-size:24px}.result-shortcuts{padding:9px}.result-shortcuts>span{width:100%}.result-shortcuts button{font-size:11px}}
@media(prefers-reduced-motion:reduce){.mode-pulse{animation:none}.prompt-grid button{transition:none}}

</style>

<style scoped>
.quick-token-config{display:flex;align-items:center;gap:7px;color:#607692;font-size:12px;font-weight:650}
.quick-token-config select{max-width:160px;min-height:34px;padding:5px 8px;border:1px solid #cbdcf4;border-radius:8px;background:#f9fbff;color:#375477;font-size:12px}
.quick-token-config select:focus-visible{outline:2px solid #6ca0f1;outline-offset:2px}
@media(max-width:760px){.quick-token-config{width:100%;justify-content:flex-start}}
</style>
