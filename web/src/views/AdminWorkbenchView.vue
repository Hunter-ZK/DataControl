<template>
  <div class="admin-page">
    <header class="page-heading">
      <div>
        <div class="eyebrow"><Settings2 :size="14" /> DEVELOPER CONTROL PLANE</div>
        <h1>管理员工作台</h1>
        <p>集中检查 Agent 实际运行轨迹、运行时规则和元数据覆盖情况。</p>
      </div>
      <div class="heading-status" :class="{ enabled: config?.captureEnabled }">
        <span class="status-dot" />
        {{ config?.captureEnabled ? '详细 Trace 采集中' : '详细 Trace 未启用' }}
      </div>
    </header>

    <nav class="workbench-tabs" aria-label="管理员工作台模块">
      <button :class="{ active: tab === 'runs' }" @click="tab = 'runs'"><Activity :size="16" /> Agent 运行调试 <span>{{ runs.length }}</span></button>
      <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'"><ShieldCheck :size="16" /> Prompt 与规则中心</button>
      <button :class="{ active: tab === 'metadata' }" @click="tab = 'metadata'"><Database :size="16" /> 元数据管理</button>
    </nav>

    <div v-if="pageError" class="error-banner"><AlertTriangle :size="17" />{{ pageError }}</div>

    <section v-if="tab === 'runs'" class="tab-panel">
      <div class="section-heading">
        <div><h2>运行记录</h2><p>展示真实服务端任务。选择一轮运行，查看捕获到的原始事件与结果；运行中的任务每 2.5 秒自动刷新。</p></div>
        <button class="secondary-button" :disabled="runsLoading" @click="loadRuns"><RefreshCw :size="15" />刷新</button>
      </div>
      <div class="filter-bar">
        <input v-model="keyword" placeholder="搜索问题或会话名称" @keydown.enter="loadRuns" />
        <select v-model="statusFilter" @change="loadRuns">
          <option value="all">全部状态</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="timeout">超时</option>
          <option value="interrupted">中断</option>
          <option value="running">运行中</option>
          <option value="cancelled">已取消</option>
        </select>
        <button class="primary-button" :disabled="runsLoading" @click="loadRuns"><Search :size="15" />查询</button>
      </div>

      <div class="run-layout">
        <div class="run-list panel-card">
          <div class="list-head"><b>运行列表</b><span>{{ runs.length }} 条</span></div>
          <div v-if="runsLoading" class="empty-state">正在读取真实运行记录…</div>
          <div v-else-if="!runs.length" class="empty-state">没有符合条件的运行记录。</div>
          <button v-for="run in runs" :key="run.runId" class="run-row" :class="{ selected: selectedRunId === run.runId }" @click="selectRun(run.runId)">
            <div class="run-row-top"><span class="run-status" :class="statusClass(run.status)">{{ statusLabel(run.status) }}</span><time>{{ formatDate(run.createdAt) }}</time></div>
            <b>{{ run.displayQuestion || run.conversationTitle || '未命名任务' }}</b>
            <div class="run-row-meta"><span>{{ run.modelMode }} · {{ run.taskTier }}</span><span>{{ run.toolCallCount }} 次工具</span><span>{{ run.durationMs == null ? '—' : (run.durationMs / 1000).toFixed(1) + 's' }}</span></div>
            <div class="run-row-bottom"><code>{{ run.runId }}</code><span :class="{ 'trace-present': run.debugCaptureAvailable }">{{ run.debugCaptureAvailable ? run.debugEventCount + ' 条 Trace' : '无详细 Trace' }}</span></div>
          </button>
        </div>

        <div class="run-detail panel-card">
          <div v-if="detailLoading" class="empty-state">正在加载本轮 Trace…</div>
          <div v-else-if="!detail" class="empty-state detail-empty"><Activity :size="30" /><b>选择一轮运行</b><span>查看实际输入、模型/工具事件、输出与异常。</span></div>
          <template v-else>
            <div class="detail-heading">
              <div><div class="eyebrow">RUN DETAIL</div><h3>{{ detail.run.displayQuestion || 'Agent 运行详情' }}</h3><p>{{ detail.run.runId }}</p></div>
              <button class="secondary-button" @click="copyText(pretty(detail))"><Copy :size="14" />复制详情</button>
            </div>
            <div class="run-metrics">
              <div><small>运行状态</small><b>{{ statusLabel(detail.run.status) }}</b></div>
              <div><small>总耗时</small><b>{{ detail.run.durationMs == null ? '—' : (detail.run.durationMs / 1000).toFixed(2) + ' s' }}</b></div>
              <div><small>详细事件</small><b>{{ detail.debugEvents.length }}</b></div>
              <div><small>模式</small><b>{{ detail.run.modelMode }} / {{ detail.run.taskTier }}</b></div>
            </div>
            <details class="payload-block">
              <summary><FileText :size="15" />用户原始问题与实际发送给 Harness 的输入</summary>
              <div class="payload-label">界面展示问题</div><pre>{{ detail.run.displayQuestion }}</pre>
              <div class="payload-label">发送给 dsh 的文本</div><pre>{{ detail.run.promptSentToHarness }}</pre>
            </details>
            <div v-if="detail.run.error" class="error-banner"><AlertTriangle :size="16" />{{ detail.run.error }}</div>
            <div class="trace-heading"><h4>完整事件时间线</h4><span>按服务端捕获顺序排列</span></div>
            <div v-if="!detail.debugCaptureAvailable" class="notice-banner"><Info :size="16" /><div><b>本轮没有详细 Trace</b><p>可能是旧运行、调试采集未启用，或运行期间没有产生可捕获事件。历史摘要无法反向还原工具参数和完整返回值。</p></div></div>
            <div v-else class="trace-list">
              <details v-for="(event, index) in detail.debugEvents" :key="event.sequence" class="trace-event" :open="index === 0">
                <summary>
                  <span class="event-index">{{ String(event.sequence).padStart(2, '0') }}</span>
                  <span class="event-name">{{ event.eventType }}</span>
                  <span class="event-source">{{ event.source || 'gateway' }}</span>
                  <time>{{ formatDate(event.createdAt) }}</time>
                  <ChevronDown :size="15" />
                </summary>
                <pre>{{ pretty(event.payload) }}</pre>
              </details>
            </div>
            <details class="payload-block">
              <summary><CheckCircle2 :size="15" />最终结果对象</summary>
              <pre>{{ pretty(detail.run.result) }}</pre>
            </details>
            <details class="payload-block">
              <summary><Wrench :size="15" />历史工具调用摘要（不含原始参数）</summary>
              <pre>{{ pretty(detail.toolEvents) }}</pre>
            </details>
            <div v-if="detail.limitations.length" class="limitations"><b>本轮可观测性边界</b><ul><li v-for="item in detail.limitations" :key="item">{{ item }}</li></ul></div>
          </template>
        </div>
      </div>
    </section>

    <section v-else-if="tab === 'rules'" class="tab-panel">
      <div class="section-heading">
        <div><h2>Prompt 与规则中心</h2><p>查看当前请求对应的源配置、实际 Profile 文件、工具白名单和 Guard 规则。文件哈希可用于核对配置是否一致。</p></div>
        <button class="secondary-button" :disabled="configLoading" @click="loadConfig"><RefreshCw :size="15" />重新读取</button>
      </div>
      <div class="config-controls">
        <label>模型模式<select v-model="modelMode" @change="loadConfig"><option value="deepseek">DeepSeek 官方</option><option value="local-deepseek">本地 DeepSeek · llama.cpp</option><option value="free-test">公共免费模型测试</option></select></label>
        <label>任务类型<select v-model="taskTier" @change="loadConfig"><option value="standard">标准任务</option><option value="multi">多步任务</option><option v-if="modelMode==='local-deepseek'" value="quick">极速回答（无工具）</option></select></label>
      </div>
      <div v-if="configLoading" class="empty-state">正在读取 Gateway 实际配置…</div>
      <template v-else-if="config">
        <div class="config-summary">
          <div><small>实际 Profile</small><b>{{ config.profile }}</b><span>{{ config.profileDir }}</span></div>
          <div><small>模型</small><b>{{ config.provider }}</b><span>{{ config.model }}</span></div>
          <div><small>运行超时</small><b>{{ config.timeoutSeconds }} 秒</b><span>DEEPSEEK_API_KEY：{{ config.apiKeyPresent ? '已配置（值不展示）' : '未配置' }}</span></div>
          <div><small>安全边界</small><b>{{ config.sqlExecutionEnabled ? 'SQL 执行开启' : '不执行生产 SQL' }}</b><span>{{ config.hiddenReasoningCaptured ? '推理字段已捕获' : '隐藏思维链不采集' }}</span></div>
        </div>
        <div class="notice-banner"><Info :size="16" /><div><b>先区分规则的作用层级</b><p>Prompt 是给模型的行为指引；tool-catalog 限制可用 MCP 工具；Guard 与服务端校验属于代码执行约束。标记“运行候选”的文件是 Gateway 按当前模式识别的生效候选；请同时核对实际 Profile 内容和 SHA-256，不能只凭源文件推断运行时一定加载成功。</p></div></div>
        <div class="config-layout">
          <div class="file-list panel-card">
            <div class="list-head"><b>配置与规则文件</b><span>{{ config.files.length }} 个</span></div>
            <button v-for="file in config.files" :key="file.id" class="file-row" :class="{ selected: selectedFileId === file.id }" @click="selectedFileId = file.id">
              <span class="file-icon"><ShieldCheck v-if="file.kind.includes('guard')" :size="16" /><BookOpen v-else-if="file.kind === 'skill'" :size="16" /><FileText v-else :size="16" /></span>
              <span class="file-copy"><b>{{ file.label }}</b><small>{{ file.path }}</small><code>{{ file.sha256 ? file.sha256.slice(0, 16) + '…' : '文件不存在' }}</code></span>
              <span v-if="file.activeForRequest" class="active-file">运行候选</span>
            </button>
          </div>
          <div class="file-detail panel-card">
            <template v-if="selectedFile">
              <div class="detail-heading"><div><h3>{{ selectedFile.label }}</h3><p>{{ selectedFile.path }} · {{ selectedFile.bytes }} bytes</p></div><button class="secondary-button" @click="copyText(selectedFile.content)"><Copy :size="14" />复制内容</button></div>
              <div class="file-tags"><span>{{ ruleLayer(selectedFile) }}</span><span>{{ selectedFile.kind }}</span><span :class="{ 'trace-present': selectedFile.activeForRequest }">{{ selectedFile.activeForRequest ? '标记为运行候选' : '参考/未选中配置' }}</span><span v-if="selectedFile.truncated">内容已截断</span></div>
              <pre class="source-code">{{ selectedFile.content || '文件不存在或没有内容。' }}</pre>
              <div class="hash-line">SHA-256：{{ selectedFile.sha256 || '不可用' }}</div>
            </template>
            <div v-else class="empty-state">选择左侧文件查看内容。</div>
          </div>
        </div>
        <div class="limitations"><b>可观测性说明</b><ul><li v-for="item in config.limitations" :key="item">{{ item }}</li></ul></div>
      </template>
    </section>

    <section v-else class="tab-panel">
      <div class="section-heading"><div><h2>元数据管理</h2><p>使用真实元数据统计和完整性指标，统一进入现有的数据集、字段与语义资产模块。</p></div><button class="secondary-button" :disabled="metadataLoading" @click="loadMetadata"><RefreshCw :size="15" />刷新统计</button></div>
      <div v-if="metadataLoading" class="empty-state">正在读取元数据统计…</div>
      <template v-else-if="metadata">
        <div class="metadata-grid">
          <RouterLink v-for="item in metadataCards" :key="item.key" :to="item.to" class="metadata-card">
            <span class="metadata-icon"><component :is="item.icon" :size="18" /></span><span class="metadata-count">{{ metadata.counts[item.key] ?? 0 }}</span><b>{{ item.label }}</b><small>{{ item.description }}</small><span class="open-link">进入管理 <ArrowUpRight :size="14" /></span>
          </RouterLink>
        </div>
        <div class="quality-panel panel-card">
          <div class="section-heading"><div><h3>元数据完整性检查</h3><p>以下数字由当前数据库直接统计，不是模型推断。</p></div></div>
          <div class="quality-grid">
            <div v-for="item in qualityCards" :key="item.key" class="quality-item"><span>{{ item.label }}</span><b :class="{ issue: (metadata.quality[item.key] || 0) > 0 }">{{ metadata.quality[item.key] ?? 0 }}</b><small>{{ item.description }}</small></div>
          </div>
        </div>
        <div class="notice-banner"><Info :size="16" /><div><b>关于元数据编辑</b><p>当前仓库已具备数据集、字段、指标、标准码值、数据标准、词根和统计制度的检索/详情接口，但没有覆盖这些实体的统一写入 API。本页不会伪造编辑能力。下一步应按实体定义可编辑字段、校验规则、变更留痕和导入回滚，再接入真正的维护表单。</p></div></div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Activity, AlertTriangle, ArrowUpRight, BookOpen, Boxes, CheckCircle2, ChevronDown,
  Copy, Database, FileText, Info, Layers3, RefreshCw, Search, Settings2, ShieldCheck,
  Table2, Tags, Wrench,
} from 'lucide-vue-next'
import { adminApi, type AdminAgentConfig, type AdminAgentRun, type AdminAgentRunDetail, type AdminAgentConfigFile, type AdminMetadataOverview, type AgentModelMode } from '@/api/client'

type Tab = 'runs' | 'rules' | 'metadata'
const tab = ref<Tab>('runs')
const pageError = ref('')
const runs = ref<AdminAgentRun[]>([])
const runsLoading = ref(false)
const statusFilter = ref('all')
const keyword = ref('')
const selectedRunId = ref('')
const detail = ref<AdminAgentRunDetail | null>(null)
const detailLoading = ref(false)
const config = ref<AdminAgentConfig | null>(null)
const configLoading = ref(false)
const modelMode = ref<AgentModelMode>('deepseek')
const taskTier = ref<'standard' | 'multi' | 'quick'>('standard')
const selectedFileId = ref('')
const metadata = ref<AdminMetadataOverview | null>(null)
const metadataLoading = ref(false)

const selectedFile = computed<AdminAgentConfigFile | undefined>(() =>
  config.value?.files.find(file => file.id === selectedFileId.value)
)
const metadataCards = [
  { key: 'datasets', label: '数据集', description: '数据集与表结构', to: '/catalog', icon: Database },
  { key: 'columns', label: '字段', description: '字段定义与类型', to: '/search?type=COLUMN', icon: Table2 },
  { key: 'metrics', label: '业务指标', description: '指标语义、时间与维度', to: '/metrics', icon: Activity },
  { key: 'codeTables', label: '标准码表', description: '码表及码值', to: '/code-tables', icon: Tags },
  { key: 'standards', label: '数据标准', description: '标准定义与关联码表', to: '/standards', icon: BookOpen },
  { key: 'wordRoots', label: '词根索引', description: '字段命名词根', to: '/word-roots', icon: Boxes },
  { key: 'statSystems', label: '统计制度', description: '制度与报表口径', to: '/stat-systems', icon: Layers3 },
]
const qualityCards = [
  { key: 'datasetsMissingDefinition', label: '数据集缺少业务定义', description: '空值或未填写' },
  { key: 'columnsMissingChineseName', label: '字段缺少中文名', description: '空值或未填写' },
  { key: 'columnsMissingDefinition', label: '字段缺少业务定义', description: '空值或未填写' },
  { key: 'metricsMissingDefinition', label: '指标缺少业务定义', description: '空值或未填写' },
  { key: 'metricsMissingMeasureColumn', label: '指标缺少度量字段', description: '空值或未填写' },
]
function ruleLayer(file: AdminAgentConfigFile) {
  if (['guard-policy', 'guard-integration', 'guard-runtime', 'hard-policy'].includes(file.kind)) return '代码级硬约束'
  if (file.kind === 'tool-catalog') return '工具可用范围'
  if (file.kind === 'profile-source' || file.kind === 'active-runtime') return 'Prompt / Profile 指引与配置'
  if (file.kind === 'skill') return 'Skill 任务指引'
  if (file.kind === 'plugin-lock') return '插件加载约束'
  return '参考配置'
}
function statusLabel(status: string) {
  return ({ queued: '排队中', running: '运行中', cancel_requested: '取消中', completed: '已完成', failed: '失败', timeout: '超时', interrupted: '中断', cancelled: '已取消' } as Record<string, string>)[status] || status
}
function statusClass(status: string) {
  return ['completed'].includes(status) ? 'success' : ['failed', 'timeout', 'interrupted'].includes(status) ? 'danger' : ['running', 'queued', 'cancel_requested'].includes(status) ? 'running' : 'neutral'
}
function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
function pretty(value: unknown) {
  try { return JSON.stringify(value, null, 2) ?? 'null' } catch { return String(value) }
}
async function copyText(value: string) {
  try { await navigator.clipboard.writeText(value); pageError.value = '' }
  catch { pageError.value = '复制失败，请手动选择文本。' }
}
async function loadRuns() {
  runsLoading.value = true
  pageError.value = ''
  try {
    runs.value = await adminApi.runs({ limit: 100, status: statusFilter.value, keyword: keyword.value.trim() || undefined })
    if (selectedRunId.value && !runs.value.some(run => run.runId === selectedRunId.value)) {
      selectedRunId.value = ''
      detail.value = null
    }
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : '读取 Agent 运行记录失败。'
  } finally { runsLoading.value = false }
}
async function selectRun(id: string) {
  selectedRunId.value = id
  detailLoading.value = true
  detail.value = null
  pageError.value = ''
  try { detail.value = await adminApi.run(id) }
  catch (error) { pageError.value = error instanceof Error ? error.message : '读取本轮 Trace 失败。' }
  finally { detailLoading.value = false }
}
async function loadConfig() {
  configLoading.value = true
  pageError.value = ''
  try {
    config.value = await adminApi.config(modelMode.value, taskTier.value)
    const preferred = config.value.files.find(file => file.kind === 'active-runtime' && file.exists)
      || config.value.files.find(file => file.activeForRequest && file.exists)
      || config.value.files.find(file => file.exists)
    selectedFileId.value = preferred?.id || ''
  } catch (error) { pageError.value = error instanceof Error ? error.message : '读取实际运行配置失败。' }
  finally { configLoading.value = false }
}
async function loadMetadata() {
  metadataLoading.value = true
  pageError.value = ''
  try { metadata.value = await adminApi.metadataOverview() }
  catch (error) { pageError.value = error instanceof Error ? error.message : '读取元数据统计失败。' }
  finally { metadataLoading.value = false }
}
let refreshTimer: number | undefined
onMounted(() => {
  void loadRuns()
  void loadConfig()
  void loadMetadata()
  refreshTimer = window.setInterval(() => {
    if (tab.value !== 'runs') return
    if (!runsLoading.value) void loadRuns()
    if (selectedRunId.value && detail.value
      && ['queued', 'running', 'cancel_requested'].includes(detail.value.run.status)
      && !detailLoading.value) {
      void selectRun(selectedRunId.value)
    }
  }, 2500)
})
onBeforeUnmount(() => {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
})
</script>

<style scoped>
.admin-page{max-width:1600px;margin:0 auto;padding:26px 28px 44px;color:var(--dc-text);display:grid;gap:20px}
.page-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}
.eyebrow{display:flex;align-items:center;gap:7px;font-size:10px;letter-spacing:.13em;font-weight:800;color:#3471c9}
.page-heading h1{font-size:26px;letter-spacing:-.035em;margin:8px 0 6px;color:#1e3b65}
.page-heading p,.section-heading p{margin:0;color:var(--dc-text-3);font-size:13px;line-height:1.6}
.heading-status{display:inline-flex;align-items:center;gap:8px;padding:9px 12px;border-radius:10px;background:#fff6e8;border:1px solid #f1dfc2;color:#9b6a1c;font-size:12px;font-weight:700;white-space:nowrap}
.heading-status.enabled{background:#eef9f3;border-color:#cbe9d8;color:#18734d}
.status-dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.workbench-tabs{display:flex;gap:6px;padding:5px;border:1px solid var(--dc-border);background:#f5f8fd;border-radius:12px;width:max-content;max-width:100%;flex-wrap:wrap}
.workbench-tabs button{display:flex;align-items:center;gap:8px;border:0;background:transparent;border-radius:9px;padding:10px 13px;color:#647895;font-size:13px;font-weight:650;cursor:pointer}
.workbench-tabs button.active{background:white;color:#245fbd;box-shadow:0 2px 8px #254e8810}
.workbench-tabs button span{font-size:11px;background:#e9f1ff;border-radius:99px;padding:2px 6px}
.tab-panel{display:grid;gap:15px;min-width:0}
.section-heading{display:flex;justify-content:space-between;align-items:center;gap:16px}
.section-heading h2{margin:0 0 5px;font-size:19px;color:#203d66}
.section-heading h3{margin:0 0 5px;font-size:16px;color:#203d66}
.primary-button,.secondary-button{display:inline-flex;align-items:center;justify-content:center;gap:7px;padding:9px 12px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.primary-button{border:1px solid #2c6bd0;background:#2e70d8;color:white}
.secondary-button{border:1px solid #d8e3f3;background:#fff;color:#4c668c}
.primary-button:disabled,.secondary-button:disabled{opacity:.55;cursor:wait}
.filter-bar,.config-controls{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
.filter-bar input,.filter-bar select,.config-controls select{height:38px;border:1px solid #d8e4f4;border-radius:9px;padding:0 11px;background:white;color:#385274;font:inherit;font-size:12px}
.filter-bar input{min-width:240px;flex:1}
.config-controls label{display:flex;align-items:center;gap:8px;color:#647895;font-size:12px}
.run-layout{display:grid;grid-template-columns:minmax(290px,365px) minmax(0,1fr);gap:14px;align-items:start}
.panel-card{border:1px solid #d9e5f6;background:white;border-radius:13px;box-shadow:0 6px 20px #234f8907;min-width:0}
.run-list{overflow:hidden}
.list-head{display:flex;justify-content:space-between;align-items:center;padding:14px 15px;border-bottom:1px solid #e7eef9;font-size:13px;color:#28476f}
.list-head span{font-size:11px;color:#8294af}
.run-row{display:grid;gap:9px;width:100%;text-align:left;padding:13px 14px;border:0;border-bottom:1px solid #edf2fa;background:#fff;color:#334f75;cursor:pointer}
.run-row:last-child{border-bottom:0}
.run-row:hover{background:#f8fbff}
.run-row.selected{background:#edf5ff;box-shadow:inset 3px 0 #3477df}
.run-row-top,.run-row-meta,.run-row-bottom{display:flex;align-items:center;justify-content:space-between;gap:7px;flex-wrap:wrap}
.run-row-top time,.run-row-meta,.run-row-bottom{font-size:10px;color:#8395ae}
.run-row>b{font-size:12px;line-height:1.55;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.run-row-meta{justify-content:flex-start;gap:10px}
.run-row-bottom code{font-size:9px;overflow-wrap:anywhere}
.run-row-bottom span{color:#9aa8ba}
.run-row-bottom span.trace-present{color:#16815c}
.run-status{border-radius:6px;padding:3px 7px;font-size:10px;font-weight:750;background:#edf1f7;color:#667993}
.run-status.success{background:#e9f8f0;color:#16815c}
.run-status.danger{background:#fff0f0;color:#b84646}
.run-status.running{background:#eaf2ff;color:#286bd0}
.run-detail{padding:18px;display:grid;gap:14px}
.detail-empty{min-height:250px}
.empty-state{padding:34px 16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:#8295af;text-align:center;font-size:12px}
.detail-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.detail-heading h3{margin:6px 0;font-size:16px;line-height:1.55;color:#1d3c68;overflow-wrap:anywhere}
.detail-heading p{margin:0;color:#8395ae;font-size:10px;overflow-wrap:anywhere}
.run-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.run-metrics>div{display:grid;gap:6px;padding:11px;border-radius:9px;background:#f6f9fe;border:1px solid #e5edf9;min-width:0}
.run-metrics small,.config-summary small{color:#8294ad;font-size:10px}
.run-metrics b{font-size:12px;color:#294c7a;overflow-wrap:anywhere}
.payload-block{border:1px solid #e0e9f6;border-radius:9px;overflow:hidden}
.payload-block>summary{display:flex;align-items:center;gap:8px;padding:11px 12px;background:#f8faff;color:#41628e;font-size:12px;font-weight:700;cursor:pointer;list-style:none}
.payload-block>summary::-webkit-details-marker{display:none}
.payload-label{padding:10px 12px 0;color:#7187a6;font-size:10px;font-weight:750}
pre{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;font:11px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace;color:#324d70}
.payload-block pre{margin:0;padding:11px 12px;max-height:320px;overflow:auto;background:#fbfcff}
.trace-heading{display:flex;align-items:baseline;gap:9px}
.trace-heading h4{margin:0;font-size:14px;color:#25466f}
.trace-heading span{font-size:10px;color:#8798af}
.trace-list{display:grid;gap:7px}
.trace-event{border:1px solid #dfe8f6;border-radius:9px;overflow:hidden}
.trace-event>summary{display:flex;align-items:center;gap:9px;padding:10px;background:#f8faff;cursor:pointer;list-style:none}
.trace-event>summary::-webkit-details-marker{display:none}
.trace-event>summary>svg:last-child{margin-left:auto;color:#8194af;flex:none}
.event-index{display:grid;place-items:center;width:24px;height:24px;background:#e6efff;color:#286bd0;border-radius:7px;font-size:10px;font-weight:800;flex:none}
.event-name{font-size:12px;color:#294d7a;font-weight:750;overflow-wrap:anywhere}
.event-source{font-size:10px;color:#8496af;background:#eef2f8;padding:3px 6px;border-radius:5px}
.trace-event time{font-size:10px;color:#8496af;margin-left:auto;white-space:nowrap}
.trace-event pre{margin:0;padding:13px;background:#111f36;color:#e0e9f8;max-height:500px;overflow:auto}
.notice-banner,.error-banner{display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:10px;font-size:12px;line-height:1.6}
.notice-banner{background:#f0f6ff;border:1px solid #d8e6fc;color:#42648f}
.notice-banner>svg{flex:none;margin-top:1px}
.notice-banner p{margin:4px 0 0;color:#6c83a3}
.error-banner{background:#fff1f1;border:1px solid #f2d3d3;color:#a94343}
.error-banner svg{flex:none;margin-top:1px}
.config-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.config-summary>div{display:grid;gap:6px;padding:14px;border:1px solid #dce7f6;border-radius:11px;background:linear-gradient(145deg,#fff,#f7faff);min-width:0}
.config-summary b{font-size:13px;color:#274c7b;overflow-wrap:anywhere}
.config-summary span{font-size:10px;color:#8194af;overflow-wrap:anywhere}
.config-layout{display:grid;grid-template-columns:minmax(280px,380px) minmax(0,1fr);gap:14px;align-items:start}
.file-list{overflow:hidden}
.file-row{display:flex;align-items:flex-start;gap:9px;width:100%;padding:12px;border:0;border-bottom:1px solid #edf2fa;background:white;text-align:left;cursor:pointer}
.file-row:hover{background:#f8fbff}
.file-row.selected{background:#edf5ff;box-shadow:inset 3px 0 #3477df}
.file-icon{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;background:#eaf2ff;color:#3473d1;flex:none}
.file-copy{display:grid;gap:4px;min-width:0;flex:1}
.file-copy b{font-size:11px;color:#294c78;line-height:1.5}
.file-copy small{font-size:9px;color:#8495ac;overflow-wrap:anywhere}
.file-copy code{font-size:9px;color:#7a8fae}
.active-file{font-size:9px;color:#187b59;background:#e8f8f0;padding:4px 6px;border-radius:5px;white-space:nowrap}
.file-detail{padding:15px;display:grid;gap:11px}
.file-tags{display:flex;gap:6px;flex-wrap:wrap}
.file-tags span{font-size:10px;padding:4px 7px;border-radius:6px;background:#f0f4fa;color:#7185a3}
.file-tags span.trace-present{background:#e9f8f0;color:#187b59}
.source-code{margin:0;padding:14px;border-radius:9px;background:#111f36;color:#e0e9f8;max-height:660px;overflow:auto;font-size:11px}
.hash-line{font-size:10px;color:#8295af;overflow-wrap:anywhere}
.limitations{padding:12px 14px;border:1px solid #e0e9f6;border-radius:9px;background:#fafcff;color:#607796;font-size:11px;line-height:1.7}
.limitations b{color:#3d5d87}
.limitations ul{margin:6px 0 0;padding-left:18px}
.metadata-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.metadata-card{display:grid;gap:7px;min-width:0;padding:16px;border:1px solid #dbe7f7;border-radius:12px;background:#fff;color:#2e4f7b;box-shadow:0 6px 20px #234f8907;transition:.15s ease}
.metadata-card:hover{border-color:#9dbff0;transform:translateY(-1px);box-shadow:0 10px 25px #234f8912}
.metadata-icon{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:#eaf2ff;color:#3473d1}
.metadata-count{font-size:25px;font-weight:800;letter-spacing:-.03em;color:#234b82}
.metadata-card b{font-size:13px}
.metadata-card small{font-size:11px;color:#8395ad}
.open-link{display:flex;align-items:center;gap:5px;margin-top:5px;color:#2d70d2;font-size:11px;font-weight:750}
.quality-panel{padding:16px;display:grid;gap:14px}
.quality-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}
.quality-item{display:grid;gap:7px;padding:12px;border-radius:9px;background:#f7faff;border:1px solid #e4ecf8;min-width:0}
.quality-item span{font-size:11px;color:#5b7395;line-height:1.5}
.quality-item b{font-size:22px;color:#1a835b}
.quality-item b.issue{color:#bd6c2b}
.quality-item small{font-size:10px;color:#8798af}
@media(max-width:1100px){.run-layout,.config-layout{grid-template-columns:1fr}.run-list{max-height:430px;overflow:auto}.metadata-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.quality-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:700px){.admin-page{padding:17px 12px 30px;gap:14px}.page-heading{flex-direction:column}.page-heading h1{font-size:22px}.workbench-tabs{width:100%}.workbench-tabs button{flex:1;justify-content:center;padding:9px 7px;font-size:11px}.section-heading{align-items:flex-start}.filter-bar input{min-width:100%;flex-basis:100%}.run-metrics,.config-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.metadata-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.quality-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.run-detail{padding:12px}.detail-heading{flex-direction:column}.trace-event>summary{flex-wrap:wrap}.trace-event time{margin-left:0}.file-detail{padding:11px}}
</style>
