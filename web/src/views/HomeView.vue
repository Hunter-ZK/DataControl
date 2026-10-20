<template>
  <div class="dc-page home-page">
    <div class="dc-container">
      <header class="home-head">
        <div>
          <p class="eyebrow">TUESDAY · DATA WORKSPACE</p>
          <h1>早上好，Hanna</h1>
          <p>直接把业务问题交给 DataAgent，或从数仓资产继续工作。</p>
        </div>
        <div class="agent-status">
          <span class="status-dot"></span>
          <span>{{ agentReady ? 'DataAgent 已就绪' : '演示模式' }}</span>
          <b>3 项智能能力</b>
        </div>
      </header>

      <section id="home-agent" class="agent-command-card dc-card">
        <div class="command-icon"><Sparkles :size="18" /></div>
        <div class="command-main">
          <label for="home-agent-input">问 DataAgent</label>
          <textarea
            id="home-agent-input"
            v-model="question"
            rows="1"
            placeholder="例如：哪些表可以分析企业贷款余额？"
            @keydown.enter.exact.prevent="runQuestion"
          />
          <div class="prompt-row">
            <button v-for="item in prompts" :key="item.label" @click="selectPrompt(item)">
              {{ item.label }}
            </button>
          </div>
        </div>
        <button class="command-send" :disabled="!question.trim()" @click="runQuestion">
          <ArrowUpRight :size="19" />
        </button>
      </section>

      <section class="workspace-grid">
        <article class="analysis-panel">
          <div class="analysis-head">
            <div>
              <span class="agent-chip"><Sparkles :size="14" /> DataAgent</span>
              <span class="demo-chip">演示数据</span>
            </div>
            <span class="analysis-meta">{{ currentScenario.meta }}</span>
          </div>

          <div v-if="activeScenario==='assets'" class="viz assets-viz">
            <div class="viz-copy">
              <span class="viz-kicker">DATASET RECOMMENDATION</span>
              <h2>贷款余额相关资产</h2>
              <p>根据指标口径、粒度和数据层级，优先推荐已汇总的 ADS 数据集。</p>
            </div>
            <svg class="network" viewBox="0 0 820 330" role="img" aria-label="贷款余额相关数据资产关系图">
              <defs>
                <linearGradient id="agentGlow" x1="0" x2="1">
                  <stop offset="0%" stop-color="#7c67f2"/>
                  <stop offset="100%" stop-color="#9c78ff"/>
                </linearGradient>
              </defs>
              <path d="M410 164 C330 110 245 84 170 82" class="edge" />
              <path d="M410 164 C332 210 248 245 166 248" class="edge" />
              <path d="M410 164 C500 117 586 92 662 92" class="edge" />
              <path d="M410 164 C504 207 594 233 678 236" class="edge" />
              <circle cx="410" cy="164" r="62" class="center-ring" />
              <circle cx="410" cy="164" r="45" fill="url(#agentGlow)" />
              <text x="410" y="158" text-anchor="middle" class="center-main">贷款余额</text>
              <text x="410" y="177" text-anchor="middle" class="center-sub">metric</text>

              <g class="node recommended">
                <rect x="78" y="50" width="180" height="64" rx="13"/>
                <text x="96" y="76" class="node-title">企业贷款月度汇总</text>
                <text x="96" y="98" class="node-sub">ADS · 推荐度 96</text>
              </g>
              <g class="node">
                <rect x="74" y="216" width="188" height="64" rx="13"/>
                <text x="92" y="242" class="node-title">贷款余额主题汇总</text>
                <text x="92" y="264" class="node-sub">DWS · 推荐度 82</text>
              </g>
              <g class="node">
                <rect x="570" y="60" width="182" height="64" rx="13"/>
                <text x="588" y="86" class="node-title">贷款合同明细</text>
                <text x="588" y="108" class="node-sub">DWD · 推荐度 68</text>
              </g>
              <g class="node">
                <rect x="584" y="204" width="180" height="64" rx="13"/>
                <text x="602" y="230" class="node-title">机构维度</text>
                <text x="602" y="252" class="node-sub">DIM · 关联维度</text>
              </g>

              <circle cx="322" cy="110" r="5" class="signal purple"/>
              <circle cx="520" cy="121" r="5" class="signal orange"/>
              <circle cx="523" cy="212" r="5" class="signal purple"/>
            </svg>
            <div class="viz-footer">
              <span><i class="legend-dot purple"></i> Agent 推荐</span>
              <span><i class="legend-dot orange"></i> 需确认口径</span>
              <strong>首选：企业贷款月度汇总</strong>
            </div>
          </div>

          <div v-else-if="activeScenario==='trend'" class="viz trend-viz">
            <div class="viz-copy">
              <span class="viz-kicker">TREND ANALYSIS</span>
              <h2>贷款余额走势</h2>
              <p>模拟 6 个月余额变化，用于预览最终分析结果的可视化呈现。</p>
            </div>
            <div class="trend-summary">
              <div><strong>146.8</strong><span>亿元 · 9 月</span></div>
              <div class="positive">+8.4% <span>较 4 月</span></div>
            </div>
            <svg class="trend-chart" viewBox="0 0 820 260" role="img" aria-label="贷款余额六个月趋势图">
              <line v-for="y in [50,100,150,200]" :key="y" x1="56" :y1="y" x2="770" :y2="y" class="grid-line"/>
              <polyline points="80,198 210,176 340,182 470,142 600,122 730,88" class="trend-line"/>
              <polygon points="80,198 210,176 340,182 470,142 600,122 730,88 730,220 80,220" class="trend-area"/>
              <g v-for="(point,index) in trendPoints" :key="point.month">
                <circle :cx="point.x" :cy="point.y" r="5" :class="['trend-point',{latest:index===trendPoints.length-1}]"/>
                <text :x="point.x" y="242" text-anchor="middle" class="axis-label">{{ point.month }}</text>
              </g>
            </svg>
            <div class="viz-footer">
              <span><i class="legend-dot purple"></i> 贷款余额</span>
              <span><i class="legend-dot orange"></i> 最新值</span>
              <strong>Agent 发现：8 月后增速明显抬升</strong>
            </div>
          </div>

          <div v-else-if="activeScenario==='naming'" class="viz naming-viz">
            <div class="viz-copy">
              <span class="viz-kicker">FIELD NAMING</span>
              <h2>字段规范化命名</h2>
              <p>把业务语义拆成标准词根，并优先复用已有字段命名。</p>
            </div>
            <div class="naming-flow">
              <div class="word-card"><span>客户</span><b>customer</b><code>cust</code></div>
              <ArrowRight :size="20" />
              <div class="word-card"><span>风险</span><b>risk</b><code>risk</code></div>
              <ArrowRight :size="20" />
              <div class="word-card"><span>等级</span><b>level</b><code>lvl</code></div>
              <ArrowRight :size="20" />
              <div class="word-card result"><span>推荐字段</span><b>cust_risk_lvl</b><code>命中现有规范</code></div>
            </div>
            <div class="naming-compare">
              <div><span>已有字段</span><b>cust_risk_lvl</b><em>推荐复用</em></div>
              <div><span>相似字段</span><b>customer_risk_level</b><em>不建议新增</em></div>
              <div><span>相似字段</span><b>risk_lvl</b><em>语义不完整</em></div>
            </div>
          </div>

          <div v-else class="viz sql-viz">
            <div class="viz-copy">
              <span class="viz-kicker">TEXT2SQL PLAN</span>
              <h2>深圳分行 9 月贷款余额</h2>
              <p>先把问题拆成指标、数据集和过滤条件，再生成可校验 SQL。</p>
            </div>
            <div class="sql-plan">
              <div><span>指标</span><b>贷款余额</b></div>
              <ArrowRight :size="18" />
              <div><span>数据集</span><b>ADS 企业贷款月度汇总</b></div>
              <ArrowRight :size="18" />
              <div><span>过滤</span><b>深圳分行 · 202609</b></div>
            </div>
            <div class="sql-code">
              <div class="sql-head"><span>MaxCompute SQL</span><span class="validation">✓ 静态校验通过</span></div>
              <pre>SELECT org_name, SUM(loan_balance) AS loan_balance
FROM stat_prod.ads_corp_loan_month
WHERE stat_month = '202609'
  AND org_name = '深圳分行'
GROUP BY org_name;</pre>
            </div>
          </div>
        </article>

        <aside class="action-panel dc-card">
          <div class="action-head">
            <div>
              <span class="purple-dot"></span>
              <span>DataAgent 建议</span>
            </div>
            <small>{{ currentScenario.badge }}</small>
          </div>
          <h2>{{ currentScenario.title }}</h2>
          <p>{{ currentScenario.summary }}</p>

          <div class="action-list">
            <button v-for="(action,index) in currentScenario.actions" :key="action.label" @click="handleAction(action)">
              <span>{{ action.label }}</span>
              <small>{{ action.desc }}</small>
              <ArrowUpRight :size="15" />
            </button>
          </div>

          <div class="action-footer">
            <button class="primary-action" @click="handlePrimary">{{ currentScenario.primary }}</button>
            <RouterLink to="/agent">完整会话</RouterLink>
          </div>
        </aside>
      </section>

      <section class="insight-grid">
        <article class="dc-card warehouse-panel">
          <div class="panel-head">
            <div>
              <h2>数仓地图</h2>
              <p>直接浏览业务域，无需先知道表名</p>
            </div>
            <RouterLink to="/catalog">查看全部</RouterLink>
          </div>
          <div class="catalog-grid">
            <RouterLink
              v-for="item in catalogCards"
              :key="item.code"
              :to="{ name:'catalog', query:{ catalog:item.code } }"
              class="catalog-card"
            >
              <div class="catalog-top"><span>{{ item.name }}</span><strong>{{ item.count }}</strong></div>
              <div class="catalog-bar"><i :style="{ width: item.width + '%' }"></i></div>
              <small>{{ item.code }} · {{ item.count }} 个数据集</small>
            </RouterLink>
          </div>
        </article>

        <article class="dc-card recent-panel">
          <div class="panel-head">
            <div>
              <h2>最近工作</h2>
              <p>继续上次的数据分析</p>
            </div>
            <RouterLink to="/profile">查看全部</RouterLink>
          </div>
          <div class="recent-list">
            <RouterLink v-for="item in recentCards" :key="item.title" :to="item.to" class="recent-item">
              <span class="recent-icon" :class="item.kind"><component :is="item.icon" :size="15"/></span>
              <div><b>{{ item.title }}</b><small>{{ item.meta }}</small></div>
              <ArrowRight :size="15" />
            </RouterLink>
          </div>
        </article>

        <article class="dc-card health-panel">
          <div class="panel-head">
            <div>
              <h2>资产健康</h2>
              <p>演示数据</p>
            </div>
          </div>
          <div class="health-number"><strong>92%</strong><span>核心资产有完整口径</span></div>
          <div class="health-bar"><i class="good" style="width:68%"></i><i class="warn" style="width:18%"></i><i class="risk" style="width:6%"></i></div>
          <div class="health-legend"><span><i class="good"></i>完整 68%</span><span><i class="warn"></i>待完善 18%</span><span><i class="risk"></i>异常 6%</span></div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Database,
  FileText,
  Sparkles,
} from 'lucide-vue-next'
import { agentApi, assetApi, type AgentStatus } from '@/api/client'

type ScenarioKey = 'assets' | 'trend' | 'naming' | 'sql'
type DemoAction = { label: string; desc: string; type: 'catalog' | 'metrics' | 'roots' | 'scenario'; value?: string }

const router = useRouter()
const route = useRoute()
const question = ref('哪些表可以分析企业贷款余额？')
const activeScenario = ref<ScenarioKey>('assets')
const agentStatus = ref<AgentStatus | null>(null)

const prompts = [
  { label: '哪些表可以分析贷款余额？', scenario: 'assets' as ScenarioKey },
  { label: '看贷款余额趋势', scenario: 'trend' as ScenarioKey },
  { label: '“客户风险等级”怎么命名？', scenario: 'naming' as ScenarioKey },
  { label: '生成深圳分行 9 月贷款余额 SQL', scenario: 'sql' as ScenarioKey },
]

const scenarios: Record<ScenarioKey, {
  meta: string
  badge: string
  title: string
  summary: string
  primary: string
  actions: DemoAction[]
}> = {
  assets: {
    meta: '资产推荐 · 4 个关联对象',
    badge: '推荐度 96',
    title: '优先使用 ADS 企业贷款月度汇总',
    summary: '该表已经按月份、机构与客户类型汇总，与你的“贷款余额”分析粒度最匹配，可以减少二次聚合和口径偏差。',
    primary: '查看推荐数据集',
    actions: [
      { label: '查看贷款余额指标口径', desc: '确认统计定义与时间口径', type: 'metrics' },
      { label: '对比 3 个候选数据集', desc: '查看粒度、字段与更新频率', type: 'catalog', value: '贷款' },
      { label: '继续生成查询 SQL', desc: '沿用当前推荐资产', type: 'scenario', value: 'sql' },
    ],
  },
  trend: {
    meta: '趋势分析 · 6 个月',
    badge: '+8.4%',
    title: '8 月后贷款余额增速明显抬升',
    summary: '演示数据中 9 月余额达到 146.8 亿元，较 4 月提升 8.4%。建议继续按机构、客户类型拆分，确认增长来自哪些业务分组。',
    primary: '查看指标详情',
    actions: [
      { label: '按机构拆分', desc: '定位贡献最大的机构', type: 'scenario', value: 'assets' },
      { label: '查看贷款余额口径', desc: '确认是否包含表外业务', type: 'metrics' },
      { label: '生成趋势查询 SQL', desc: '按月生成聚合 SQL', type: 'scenario', value: 'sql' },
    ],
  },
  naming: {
    meta: '字段规范 · 3 个词根',
    badge: '命中规范',
    title: '推荐直接复用 cust_risk_lvl',
    summary: '“客户 / 风险 / 等级”分别命中 cust / risk / lvl 词根，且仓内已经存在同名规范字段，因此不建议新增 customer_risk_level。',
    primary: '打开词根索引',
    actions: [
      { label: '查看 cust 词根', desc: 'customer 的标准缩写', type: 'roots' },
      { label: '查看 lvl 词根', desc: 'level 的标准缩写', type: 'roots' },
      { label: '查找已有同义字段', desc: '避免重复建设', type: 'catalog', value: 'risk' },
    ],
  },
  sql: {
    meta: 'Text2SQL · 静态校验',
    badge: '已校验',
    title: 'SQL 已绑定到推荐数据资产',
    summary: '查询使用 ADS 企业贷款月度汇总，并将“深圳分行”“2026 年 9 月”解析为机构与月份过滤条件。演示 SQL 不执行生产查询。',
    primary: '查看贷款数据资产',
    actions: [
      { label: '检查字段来源', desc: '查看 loan_balance 的字段血缘', type: 'catalog', value: 'loan_balance' },
      { label: '修改统计口径', desc: '重新选择指标定义', type: 'metrics' },
      { label: '查看完整会话', desc: '进入 Agent 会话与证据详情', type: 'scenario', value: 'assets' },
    ],
  },
}

const currentScenario = computed(() => scenarios[activeScenario.value])
const agentReady = computed(() => agentStatus.value?.ready === true)

const trendPoints = [
  { month: '4月', x: 80, y: 198 },
  { month: '5月', x: 210, y: 176 },
  { month: '6月', x: 340, y: 182 },
  { month: '7月', x: 470, y: 142 },
  { month: '8月', x: 600, y: 122 },
  { month: '9月', x: 730, y: 88 },
]

const catalogCards = reactive([
  { name: '金融统计', code: 'FIN_STAT', count: 58, width: 92 },
  { name: '风险管理', code: 'RISK', count: 43, width: 72 },
  { name: '客户管理', code: 'CUSTOMER', count: 36, width: 60 },
  { name: '监管报送', code: 'REG_REPORT', count: 31, width: 52 },
  { name: '机构主题', code: 'ORG', count: 24, width: 40 },
  { name: '财务分析', code: 'FINANCE', count: 18, width: 31 },
])

const recentCards = [
  { title: '金融统计存款月报', meta: 'ADS · 18 分钟前', to: { name: 'catalog', query: { keyword: '存款' } }, icon: Database, kind: 'dataset' },
  { title: '贷款余额趋势分析', meta: 'DataAgent · 今天 09:42', to: { name: 'home', hash: '#home-agent' }, icon: Sparkles, kind: 'agent' },
  { title: '客户风险等级命名', meta: '词根规范 · 昨天', to: '/word-roots', icon: FileText, kind: 'standard' },
  { title: '资产分层概览', meta: '数据概览 · 昨天', to: '/overview', icon: BarChart3, kind: 'overview' },
]

function inferScenario(value: string): ScenarioKey {
  const normalized = value.toLowerCase()
  if (normalized.includes('命名') || normalized.includes('字段') && normalized.includes('规范')) return 'naming'
  if (normalized.includes('sql') || normalized.includes('查询')) return 'sql'
  if (normalized.includes('趋势') || normalized.includes('增长') || normalized.includes('走势')) return 'trend'
  return 'assets'
}

function runQuestion() {
  const value = question.value.trim()
  if (!value) return
  activeScenario.value = inferScenario(value)
}

function selectPrompt(item: { label: string; scenario: ScenarioKey }) {
  question.value = item.label
  activeScenario.value = item.scenario
}

function handleAction(action: DemoAction) {
  if (action.type === 'scenario' && action.value) {
    activeScenario.value = action.value as ScenarioKey
    const prompt = prompts.find((item) => item.scenario === activeScenario.value)
    if (prompt) question.value = prompt.label
    return
  }
  if (action.type === 'metrics') {
    router.push('/metrics')
    return
  }
  if (action.type === 'roots') {
    router.push('/word-roots')
    return
  }
  router.push({ name: 'catalog', query: action.value ? { keyword: action.value } : undefined })
}

function handlePrimary() {
  if (activeScenario.value === 'naming') {
    router.push('/word-roots')
    return
  }
  if (activeScenario.value === 'trend') {
    router.push('/metrics')
    return
  }
  router.push({ name: 'catalog', query: { keyword: activeScenario.value === 'sql' ? '贷款' : '贷款余额' } })
}

async function hydrateCatalogs() {
  try {
    const data = await assetApi.overview() as any
    const incoming = Array.isArray(data?.topCatalogs) ? data.topCatalogs : []
    incoming.slice(0, 6).forEach((item: any, index: number) => {
      if (!catalogCards[index]) return
      catalogCards[index].name = String(item.name || catalogCards[index].name)
      catalogCards[index].code = String(item.code || catalogCards[index].code)
      catalogCards[index].count = Number(item.tableCount || item.count || catalogCards[index].count)
      catalogCards[index].width = Math.max(22, Math.min(100, catalogCards[index].count / 60 * 100))
    })
  } catch {}
}

onMounted(async () => {
  try { agentStatus.value = await agentApi.status() } catch { agentStatus.value = null }
  await hydrateCatalogs()
  if (route.hash === '#home-agent') {
    await nextTick()
    document.querySelector<HTMLTextAreaElement>('#home-agent-input')?.focus()
  }
})
</script>

<style scoped>
.home-page{min-height:calc(100vh - var(--dc-topbar));padding:26px 0 48px;background:#f3f4f6}
.home-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:18px}
.eyebrow{margin:0 0 8px;font-size:9px;letter-spacing:.16em;color:#969ca5;font-weight:800}
.home-head h1{margin:0;font-size:33px;letter-spacing:-.04em;color:#141920}
.home-head>div>p:last-child{margin:7px 0 0;font-size:12px;color:#6d747d}
.agent-status{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:999px;background:#fff;border:1px solid #e3e5e8;font-size:9px;color:#707781}
.agent-status .status-dot{width:7px;height:7px;border-radius:50%;background:var(--dc-ai);box-shadow:0 0 0 4px var(--dc-ai-glow)}
.agent-status b{font-weight:700;color:#242a33}

.agent-command-card{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:start;padding:16px 18px;margin-bottom:16px;border-color:#dedfe4;box-shadow:none}
.command-icon{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;background:var(--dc-ai-soft);color:var(--dc-ai-strong)}
.command-main{min-width:0}
.command-main label{display:block;font-size:10px;font-weight:800;color:#343a44;margin-bottom:3px}
.command-main textarea{width:100%;min-height:30px;max-height:90px;border:0;outline:0;resize:none;background:transparent;font-size:14px;color:#171c24;line-height:1.5}
.command-main textarea::placeholder{color:#9ca2aa}
.prompt-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}
.prompt-row button{border:1px solid #e1e2e5;background:#f7f7f7;border-radius:999px;padding:5px 8px;color:#737a84;font-size:9px;cursor:pointer}
.prompt-row button:hover{border-color:#cfc8ff;color:var(--dc-ai-strong);background:#f4f1ff}
.command-send{width:38px;height:38px;border:0;border-radius:10px;background:#111823;color:#fff;display:grid;place-items:center;cursor:pointer}
.command-send:disabled{opacity:.35;cursor:not-allowed}

.workspace-grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(300px,.65fr);gap:16px}
.analysis-panel{min-height:520px;padding:22px;border-radius:15px;background:#08111e;color:#fff;box-shadow:0 18px 44px rgba(8,17,30,.16);overflow:hidden}
.analysis-head{display:flex;align-items:center;justify-content:space-between;gap:14px}
.analysis-head>div{display:flex;align-items:center;gap:8px}
.agent-chip,.demo-chip{display:inline-flex;align-items:center;gap:6px;border-radius:999px;font-size:9px;font-weight:800}
.agent-chip{padding:6px 9px;background:#2a204f;color:#cbbdff}
.demo-chip{padding:5px 8px;background:#151f2d;color:#8591a2;border:1px solid #2a3544}
.analysis-meta{font-size:9px;color:#7e8998}

.viz{height:100%;display:flex;flex-direction:column}
.viz-copy{max-width:690px;margin-top:24px}
.viz-kicker{font-size:8px;letter-spacing:.15em;color:#657082;font-weight:800}
.viz-copy h2{margin:7px 0 5px;font-size:27px;letter-spacing:-.03em}
.viz-copy p{margin:0;color:#9da7b5;font-size:11px;line-height:1.6}

.network{width:100%;height:310px;margin-top:2px}
.edge{fill:none;stroke:#3e4b5c;stroke-width:2}
.center-ring{fill:none;stroke:#3c2e68;stroke-width:2;stroke-dasharray:4 6}
.center-main{fill:#fff;font-size:13px;font-weight:800}
.center-sub{fill:#d6ccff;font-size:8px}
.node rect{fill:#141e2b;stroke:#2b3747;stroke-width:1}
.node.recommended rect{fill:#151d2c;stroke:#7c67f2;stroke-width:1.5}
.node-title{fill:#edf1f7;font-size:11px;font-weight:700}
.node-sub{fill:#7e8998;font-size:8px}
.signal{stroke:#0b111b;stroke-width:3}
.signal.purple{fill:#7c67f2}
.signal.orange{fill:#f09a4f}

.viz-footer{margin-top:auto;padding-top:12px;border-top:1px solid #1e2a38;display:flex;align-items:center;gap:16px;color:#778394;font-size:9px}
.viz-footer strong{margin-left:auto;color:#d8dee7;font-weight:700}
.legend-dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
.legend-dot.purple{background:#7c67f2}.legend-dot.orange{background:#f09a4f}

.trend-summary{display:flex;align-items:flex-end;gap:26px;margin-top:28px}
.trend-summary strong{font-size:34px;letter-spacing:-.04em}
.trend-summary span{display:block;margin-top:3px;color:#7e8998;font-size:9px}
.trend-summary .positive{font-size:15px;color:#bdb2ff;font-weight:800}
.trend-chart{width:100%;height:250px;margin-top:0}
.grid-line{stroke:#202b38;stroke-width:1}
.trend-line{fill:none;stroke:#8f7bf8;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.trend-area{fill:rgba(124,103,242,.08)}
.trend-point{fill:#08111e;stroke:#8f7bf8;stroke-width:3}
.trend-point.latest{stroke:#f09a4f;fill:#f09a4f}
.axis-label{fill:#697587;font-size:9px}

.naming-flow{display:grid;grid-template-columns:1fr auto 1fr auto 1fr auto 1.35fr;gap:10px;align-items:center;margin-top:58px}
.word-card{min-height:112px;padding:16px;border-radius:12px;background:#131d2a;border:1px solid #2a3544;display:flex;flex-direction:column;justify-content:center}
.word-card span{font-size:9px;color:#7d8999}.word-card b{margin-top:8px;font-size:14px}.word-card code{margin-top:6px;color:#a8b2bf;font-size:10px}
.word-card.result{background:#241d46;border-color:#7c67f2;box-shadow:0 0 0 1px rgba(124,103,242,.16)}
.word-card.result b{color:#d5ccff}
.naming-compare{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:28px}
.naming-compare div{padding:12px;border-radius:10px;background:#101925;border:1px solid #222e3c}
.naming-compare span,.naming-compare em{display:block;font-size:8px;color:#6f7b8b;font-style:normal}
.naming-compare b{display:block;margin:6px 0;font-size:11px}.naming-compare em{color:#a99bff}

.sql-plan{display:grid;grid-template-columns:1fr auto 1.5fr auto 1.2fr;gap:10px;align-items:center;margin-top:42px}
.sql-plan div{min-height:78px;padding:14px;border-radius:11px;background:#131d2a;border:1px solid #2a3544}
.sql-plan span{display:block;font-size:8px;color:#798596}.sql-plan b{display:block;margin-top:8px;font-size:11px}
.sql-code{margin-top:22px;border-radius:12px;overflow:hidden;border:1px solid #2b3645;background:#0d1622}
.sql-head{display:flex;justify-content:space-between;gap:12px;padding:10px 13px;border-bottom:1px solid #26313e;font-size:9px;color:#8a95a3}
.validation{color:#b8aaff}
.sql-code pre{margin:0;padding:16px;color:#cdd5df;font-size:10px;line-height:1.65;overflow:auto}

.action-panel{padding:21px;border-color:#e1e3e6;box-shadow:0 8px 24px rgba(17,25,39,.04);display:flex;flex-direction:column}
.action-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.action-head>div{display:flex;align-items:center;gap:7px;font-size:9px;color:#6b727d;font-weight:800}
.purple-dot{width:7px;height:7px;border-radius:50%;background:var(--dc-ai)}
.action-head small{padding:4px 7px;border-radius:999px;background:var(--dc-ai-soft);color:var(--dc-ai-strong);font-size:8px;font-weight:800}
.action-panel h2{margin:24px 0 8px;font-size:21px;letter-spacing:-.03em;color:#171c24}
.action-panel>p{margin:0;color:#6f7680;font-size:11px;line-height:1.65}
.action-list{display:grid;margin-top:24px;border-top:1px solid #ebedef}
.action-list button{position:relative;display:grid;gap:4px;padding:14px 22px 14px 0;border:0;border-bottom:1px solid #ebedef;background:transparent;text-align:left;cursor:pointer}
.action-list button span{font-size:11px;font-weight:700;color:#222831}
.action-list button small{font-size:9px;color:#8a9199}
.action-list button svg{position:absolute;right:0;top:16px;color:#8c939d}
.action-footer{margin-top:auto;padding-top:22px;display:flex;align-items:center;gap:12px}
.primary-action{border:0;border-radius:9px;background:#111823;color:#fff;padding:10px 14px;font-size:10px;font-weight:800;cursor:pointer}
.action-footer a{font-size:9px;color:#747b84}

.insight-grid{display:grid;grid-template-columns:1.45fr .85fr .7fr;gap:16px;margin-top:16px}
.warehouse-panel,.recent-panel,.health-panel{padding:19px;border-color:#e1e3e6;box-shadow:0 8px 24px rgba(17,25,39,.035)}
.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px}
.panel-head h2{margin:0;font-size:16px;color:#171c24}.panel-head p{margin:4px 0 0;font-size:9px;color:#8b929b}.panel-head a{font-size:9px;color:#666e78}
.catalog-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.catalog-card{padding:12px;border-radius:10px;border:1px solid #e8e9eb;background:#fafaf9}
.catalog-top{display:flex;justify-content:space-between;gap:10px;align-items:baseline}.catalog-top span{font-size:10px;font-weight:700;color:#242a33}.catalog-top strong{font-size:14px;color:#1b2028}
.catalog-bar{height:4px;border-radius:999px;background:#eceef0;margin:10px 0 7px;overflow:hidden}.catalog-bar i{display:block;height:100%;border-radius:inherit;background:#1a2230}
.catalog-card small{font-size:8px;color:#989ea5}

.recent-list{display:grid}.recent-item{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;padding:11px 0;border-top:1px solid #eceef0}.recent-item:first-child{border-top:0}
.recent-icon{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:#f1f2f3;color:#656d77}.recent-icon.agent{background:var(--dc-ai-soft);color:var(--dc-ai-strong)}
.recent-item b{display:block;font-size:10px;color:#232932}.recent-item small{display:block;margin-top:3px;font-size:8px;color:#949aa2}

.health-number{display:flex;align-items:flex-end;gap:8px;margin-top:26px}.health-number strong{font-size:34px;letter-spacing:-.04em;color:#171c24}.health-number span{padding-bottom:5px;font-size:9px;color:#8a9199}
.health-bar{display:flex;height:7px;border-radius:999px;overflow:hidden;background:#eceef0;margin-top:18px}.health-bar i.good{background:#2f8f69}.health-bar i.warn{background:#d7923f}.health-bar i.risk{background:#d35b62}
.health-legend{display:flex;flex-wrap:wrap;gap:9px;margin-top:10px;font-size:8px;color:#8b929a}.health-legend i{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px}.health-legend i.good{background:#2f8f69}.health-legend i.warn{background:#d7923f}.health-legend i.risk{background:#d35b62}

@media(max-width:1180px){.workspace-grid{grid-template-columns:1fr}.analysis-panel{min-height:500px}.insight-grid{grid-template-columns:1fr 1fr}.health-panel{grid-column:1/-1}}
@media(max-width:760px){
  .home-head{align-items:flex-start;flex-direction:column}.agent-status{display:none}
  .agent-command-card{grid-template-columns:auto minmax(0,1fr)}.command-send{grid-column:2;justify-self:end}
  .analysis-panel{padding:17px;min-height:auto}.network{height:260px}.viz-footer{align-items:flex-start;flex-direction:column}.viz-footer strong{margin-left:0}
  .naming-flow,.sql-plan{grid-template-columns:1fr}.naming-flow>svg,.sql-plan>svg{transform:rotate(90deg);justify-self:center}.naming-compare{grid-template-columns:1fr}
  .insight-grid{grid-template-columns:1fr}.health-panel{grid-column:auto}
}
</style>
