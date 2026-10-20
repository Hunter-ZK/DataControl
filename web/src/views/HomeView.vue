<template>
  <div class="dc-page home-page">
    <div class="dc-container">
      <header class="home-head">
        <div>
          <h1>你好，今天想从数据里了解什么？</h1>
          <p>不用先知道表名。直接问 DataAgent，再进入具体数据集、字段或关系继续分析。</p>
        </div>
        <div class="asset-total">
          <strong>{{ format(overview.tableCount) }}</strong>
          <span>个在用数据集</span>
        </div>
      </header>

      <section class="top-grid">
        <div class="agent-card">
          <div class="agent-top">
            <span class="agent-brand"><Sparkles :size="16" /> DataAgent</span>
            <span class="agent-trust">内部资产 · 静态校验 · 不执行生产 SQL</span>
          </div>

          <div class="agent-copy">
            <h2>把业务问题直接交给我</h2>
            <p>我会基于数据集、字段、指标、标准和码表回答，也可以生成 SQL 或给出字段规范化命名建议。</p>
          </div>

          <div class="agent-composer">
            <textarea
              v-model="question"
              rows="2"
              placeholder="例如：哪些表可以分析企业贷款余额？"
              @keydown.enter.exact.prevent="askAgent"
            />
            <button :disabled="!question.trim()" @click="askAgent">
              <ArrowUpRight :size="19" />
            </button>
          </div>

          <div class="prompt-row">
            <button v-for="item in prompts" :key="item" @click="usePrompt(item)">{{ item }}</button>
          </div>

          <div class="capabilities">
            <span><Database :size="14" />数据资产问答</span>
            <span><Code2 :size="14" />Text2SQL</span>
            <span><FileText :size="14" />字段规范命名</span>
          </div>
        </div>

        <aside class="dc-card recent-panel">
          <div class="panel-head">
            <div>
              <h2>最近使用</h2>
              <p>继续上次的数据工作</p>
            </div>
            <RouterLink to="/profile">查看全部</RouterLink>
          </div>

          <div v-if="recent.length" class="recent-list">
            <RouterLink
              v-for="item in recent.slice(0, 4)"
              :key="item.assetId"
              :to="`/datasets/${item.assetId}`"
              class="recent-item"
            >
              <div>
                <span class="layer">{{ item.layerCode || 'TABLE' }}</span>
                <b>{{ item.bizName }}</b>
                <code>{{ item.tableName }}</code>
              </div>
              <ArrowRight :size="16" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty compact-empty">还没有最近浏览记录。</div>
        </aside>
      </section>

      <section class="bottom-grid">
        <div class="dc-card warehouse-panel">
          <div class="panel-head">
            <div>
              <h2>浏览数仓</h2>
              <p>不用搜索，先看数仓里有哪些业务数据</p>
            </div>
            <RouterLink to="/catalog">进入数据资产</RouterLink>
          </div>

          <div class="catalog-grid" v-if="overview.topCatalogs.length">
            <RouterLink
              v-for="item in overview.topCatalogs.slice(0, 6)"
              :key="item.code"
              :to="{ name: 'catalog', query: { catalog: item.code } }"
              class="catalog-card"
            >
              <div>
                <b>{{ item.name }}</b>
                <code>{{ item.code }}</code>
              </div>
              <strong>{{ format(item.tableCount) }}</strong>
              <span>数据集</span>
            </RouterLink>
          </div>
          <div v-else class="dc-empty compact-empty">正在整理业务目录。</div>
        </div>

        <aside class="dc-card overview-panel">
          <div class="panel-head">
            <div>
              <h2>资产概览</h2>
              <p>数仓资产规模</p>
            </div>
          </div>
          <div class="mini-stats">
            <div><strong>{{ format(overview.tableCount) }}</strong><span>数据集</span></div>
            <div><strong>{{ format(overview.columnCount) }}</strong><span>字段</span></div>
            <div><strong>{{ format(overview.metricCount) }}</strong><span>指标</span></div>
            <div><strong>{{ format(overview.codeTableCount) }}</strong><span>码表</span></div>
          </div>
          <RouterLink class="overview-link" to="/overview">查看数仓地图 <ArrowRight :size="15" /></RouterLink>
        </aside>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, ArrowUpRight, Code2, Database, FileText, Sparkles } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const router = useRouter()
const question = ref('')
const prompts = [
  '哪些表可以分析贷款余额？',
  '生成深圳分行 9 月贷款余额 SQL',
  '“客户风险等级”字段怎么规范命名？',
  '解释贷款余额的统计口径',
]

const overview = reactive({
  tableCount: 0,
  columnCount: 0,
  metricCount: 0,
  codeTableCount: 0,
  topCatalogs: [] as any[],
})
const recent = ref<any[]>([])

function askAgent() {
  const value = question.value.trim()
  if (!value) return
  router.push({ name: 'agent', query: { q: value } })
}

function usePrompt(value: string) {
  question.value = value
  askAgent()
}

function format(value: number) {
  return Number(value || 0).toLocaleString()
}

onMounted(async () => {
  try {
    Object.assign(overview, await assetApi.overview())
  } catch {}

  try {
    recent.value = await activityApi.recent() as any[]
  } catch {
    try {
      recent.value = (await assetApi.tables({ limit: 4 }) as any[]).slice(0, 4)
    } catch {}
  }
})
</script>

<style scoped>
.home-page{padding-top:24px;background:#f3f4f6;min-height:calc(100vh - var(--dc-topbar))}
.home-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:18px;padding:0 2px}
.home-head h1{font-size:30px;letter-spacing:-.035em;margin:0;color:#111820}
.home-head p{margin:7px 0 0;color:#6c737c;font-size:13px}
.asset-total{display:flex;align-items:baseline;gap:7px;color:#737a84}
.asset-total strong{font-size:24px;color:#111820}
.asset-total span{font-size:11px}

.top-grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(320px,.7fr);gap:16px}
.agent-card{min-height:350px;padding:26px 28px;border-radius:14px;background:#08121f;color:#fff;box-shadow:0 18px 42px rgba(8,18,31,.15);display:flex;flex-direction:column}
.agent-top{display:flex;align-items:center;justify-content:space-between;gap:16px}
.agent-brand{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:750}
.agent-trust{font-size:10px;color:#8f9bac}
.agent-copy{max-width:760px;margin-top:32px}
.agent-copy h2{font-size:28px;letter-spacing:-.03em;margin:0}
.agent-copy p{max-width:700px;margin:9px 0 0;color:#aab4c1;font-size:13px;line-height:1.65}

.agent-composer{margin-top:26px;display:grid;grid-template-columns:minmax(0,1fr) 46px;gap:9px;padding:8px 8px 8px 14px;background:#fff;border-radius:11px}
.agent-composer textarea{border:0;outline:0;resize:none;min-height:46px;max-height:110px;padding:7px 4px;background:transparent;color:#171c24;font-size:14px;line-height:1.55}
.agent-composer textarea::placeholder{color:#9299a2}
.agent-composer button{align-self:end;width:44px;height:44px;border:0;border-radius:9px;background:#111927;color:#fff;display:grid;place-items:center;cursor:pointer}
.agent-composer button:disabled{opacity:.35;cursor:not-allowed}

.prompt-row{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}
.prompt-row button{border:1px solid #2a3545;border-radius:999px;background:#111c2b;color:#b8c1cc;padding:7px 10px;font-size:10px;cursor:pointer}
.prompt-row button:hover{border-color:#596579;color:#fff}
.capabilities{display:flex;flex-wrap:wrap;gap:18px;margin-top:auto;padding-top:22px;color:#8793a3;font-size:10px}
.capabilities span{display:flex;align-items:center;gap:6px}

.recent-panel,.warehouse-panel,.overview-panel{padding:20px;border-color:#e0e3e6;box-shadow:0 8px 24px rgba(17,25,39,.04)}
.panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px}
.panel-head h2{font-size:17px;margin:0;color:#171c24}
.panel-head p{font-size:10px;color:#8a9098;margin:4px 0 0}
.panel-head a{font-size:10px;color:#505864}

.recent-list{display:grid}
.recent-item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 2px;border-top:1px solid #eceef0}
.recent-item:first-child{border-top:0}
.recent-item>div{min-width:0;display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:4px 8px}
.recent-item .layer{grid-row:1 / span 2;align-self:start;padding:3px 6px;border-radius:5px;background:#eef0f3;color:#535c68;font-size:8px;font-weight:800}
.recent-item b{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.recent-item code{font-size:9px;color:#8b929b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.compact-empty{padding:30px 12px}

.bottom-grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(320px,.7fr);gap:16px;margin-top:16px}
.catalog-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}
.catalog-card{position:relative;min-height:104px;padding:15px;border:1px solid #e6e8ea;border-radius:10px;background:#fafaf9;display:grid;grid-template-columns:minmax(0,1fr) auto;align-content:space-between;gap:6px 12px;transition:.15s ease}
.catalog-card:hover{border-color:#cdd1d6;background:#fff;transform:translateY(-1px)}
.catalog-card div{min-width:0}
.catalog-card b{display:block;font-size:12px;color:#1c222b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.catalog-card code{display:block;margin-top:5px;font-size:8px;color:#969ca4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.catalog-card strong{font-size:22px;color:#161b23}
.catalog-card>span{grid-column:2;font-size:9px;color:#969ca4}

.mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.mini-stats div{padding:14px;border-radius:9px;background:#f7f7f5;border:1px solid #e7e8ea}
.mini-stats strong{display:block;font-size:22px;color:#171c24}
.mini-stats span{font-size:9px;color:#9298a0}
.overview-link{margin-top:15px;display:flex;align-items:center;gap:6px;font-size:10px;color:#4e5661}

@media(max-width:1180px){
  .top-grid,.bottom-grid{grid-template-columns:1fr}
  .catalog-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:760px){
  .home-head{align-items:flex-start;flex-direction:column}
  .asset-total{display:none}
  .home-head h1{font-size:26px}
  .agent-card{padding:22px;min-height:330px}
  .agent-top{align-items:flex-start;flex-direction:column}
  .agent-trust{display:none}
  .agent-copy{margin-top:22px}
  .agent-copy h2{font-size:24px}
  .catalog-grid{grid-template-columns:1fr 1fr}
}
@media(max-width:520px){
  .catalog-grid{grid-template-columns:1fr}
  .capabilities{gap:10px}
}
</style>
