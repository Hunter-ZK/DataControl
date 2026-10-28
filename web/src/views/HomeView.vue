<template>
  <div class="dc-page atlas-home">
    <div class="dc-container">
      <section class="atlas-hero">
        <div class="hero-lead">
          <span class="dc-eyebrow">DATA INTELLIGENCE WORKSPACE</span>
          <h1>找到数据，理解口径，开始分析。</h1>
          <p>从一个入口发现数据集、字段、指标与标准，让每次查询都有清晰的依据。</p>
        </div>
        <div class="hero-content">
          <div class="hero-search">
            <Search :size="20"/>
            <input v-model="keyword" @input="updateSuggestions" @keydown.enter.prevent="submitSearch"
              placeholder="搜索数据集、字段、指标，或描述你的问题…"
              aria-label="数据资产检索与 DataAgent 统一入口"/>
            <button class="search-primary" @click="submitSearch">检索资产 <ArrowRight :size="16"/></button>
          </div>
          <div class="search-mode">
            <button class="mode-active" @click="submitSearch"><Search :size="14"/>查找资产</button>
            <button @click="askAgent"><Sparkles :size="14"/>向 DataAgent 提问</button>
            <span>Enter 搜索</span>
          </div>
          <div v-if="suggestions.length && !assetResults.length" class="search-suggestions" aria-label="资产联想">
            <div class="suggest-title">相关资产 · 点击直接查看</div>
            <RouterLink v-for="item in suggestions" :key="item.assetType+item.assetId"
              :to="assetRoute(item)" class="suggest-item">
              <AssetIcon :type="item.assetType" :size="18"/><span><b>{{item.title}}</b><code>{{item.technicalName}}</code></span><ArrowUpRight :size="15"/>
            </RouterLink>
          </div>
          <section v-if="resultsVisible" class="home-search-results" aria-live="polite">
            <div class="result-heading"><b>资产检索结果</b><span>{{ resultKeyword }} · {{resultTotal}} 项</span>
              <RouterLink :to="{name:'search',query:{q:resultKeyword}}">完整检索 <ArrowUpRight :size="14"/></RouterLink>
            </div>
            <p v-if="loadingSearch" class="dc-empty">正在检索数据资产…</p>
            <div v-else-if="!assetResults.length" class="dc-empty">未找到匹配的资产，请调整关键词或向 DataAgent 提问。</div>
            <RouterLink v-for="item in assetResults" :key="item.assetType+item.assetId"
              :to="assetRoute(item)" class="result-card">
              <AssetIcon :type="item.assetType" :size="19"/>
              <span><b>{{item.title}}</b><code>{{item.technicalName}}</code><small>{{item.snippet}}</small></span>
              <ArrowUpRight :size="16"/>
            </RouterLink>
          </section>
          <div class="hot"><span>试试搜索</span><button v-for="x in hot" :key="x" @click="quick(x)">{{x}}</button></div>
        </div>
      </section>
      <div class="workspace-heading">
        <div><span class="dc-eyebrow">YOUR WORKSPACE</span><h2>继续你的工作</h2></div>
        <RouterLink to="/catalog">浏览资产目录 <ArrowUpRight :size="14"/></RouterLink>
      </div>
      <div class="workspace-grid">
        <section class="dc-card recent-panel">
          <div class="panel-head"><div><h3>最近访问的资产</h3><p>从上次的数据集继续查看字段和口径</p></div><RouterLink to="/search">查看全部 <ArrowUpRight :size="14"/></RouterLink></div>
          <div v-if="recent.length" class="asset-list">
            <RouterLink v-for="item in recent" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="recent-item">
              <AssetIcon type="TABLE" :size="19"/>
              <span><b>{{item.bizName}}</b><code>{{item.tableName}}</code></span>
              <span class="dc-chip">{{item.layerCode||'数据集'}}</span><ArrowRight :size="16"/>
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无浏览记录。使用上方搜索发现你的第一个资产。</div>
        </section>
        <div class="workspace-side">
          <section class="dc-card chat-panel">
            <div class="panel-head"><div><h3>最近问数会话</h3><p>继续上次的数据分析</p></div><RouterLink to="/agent">全部会话</RouterLink></div>
            <div v-if="recentChats.length" class="chat-list">
              <RouterLink v-for="chat in recentChats" :key="chat.id" :to="{name:'agent',query:{conversationId:chat.id}}" class="recent-chat"><Sparkles :size="15"/><span>{{chat.title}}</span><ArrowUpRight :size="14"/></RouterLink>
            </div>
            <RouterLink v-else class="start-agent" to="/agent"><Sparkles :size="17"/>开启第一次智能问数<ArrowRight :size="15"/></RouterLink>
          </section>
          <section class="dc-card overview-panel">
            <div class="panel-head"><div><h3>数据资产概览</h3><p>当前已收录的资产类型</p></div><RouterLink to="/overview">详情</RouterLink></div>
            <div class="mini-stats">
              <div><strong>{{format(overview.tableCount)}}</strong><span>数据集</span></div>
              <div><strong>{{format(overview.columnCount)}}</strong><span>字段</span></div>
              <div><strong>{{format(overview.metricCount)}}</strong><span>指标</span></div>
              <div><strong>{{format(overview.codeTableCount)}}</strong><span>码表</span></div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, ArrowUpRight, Search, Sparkles } from 'lucide-vue-next'
import { activityApi, assetApi, agentApi, type SearchItem, type SearchSuggestion, type ServerAgentConversation } from '@/api/client'
import AssetIcon from '@/components/AssetIcon.vue'

const router = useRouter(); const keyword = ref(''); const hot = ['贷款余额','企业风险','region_code','监管报送']
const overview = reactive({ tableCount: 0, columnCount: 0, metricCount: 0, codeTableCount: 0 })
const recent = ref<any[]>([])
const recentChats = ref<ServerAgentConversation[]>([])
const suggestions = ref<SearchSuggestion[]>([])
const assetResults = ref<SearchItem[]>([])
const resultsVisible = ref(false)
const loadingSearch = ref(false)
const resultTotal = ref(0)
const resultKeyword = ref('')
let suggestionEpoch = 0
function assetRoute(item: {assetType: string;assetId: string;technicalName: string}) {
  const code = item.technicalName || item.assetId
  switch (item.assetType) {
    case 'TABLE': return {name: 'dataset', params: {id:item.assetId}}
    case 'COLUMN': return {name: 'field', params: {id:item.assetId}}
    case 'METRIC': return {name:'metric',params:{code}}
    case 'CODE_TABLE': return {name:'codeTable',params:{no:code}}
    case 'STANDARD': return {name:'standard',params:{no:code}}
    case 'WORD_ROOT': return {name:'wordRoot',params:{root:code}}
    case 'STAT_SYSTEM': return {name:'statSystem',params:{code}}
    default: return {name:'search',query:{q:code}}
  }
}
async function updateSuggestions() {
  const key = keyword.value.trim()
  const request = ++suggestionEpoch
  assetResults.value=[]
  resultsVisible.value=false
  if (!key) {suggestions.value=[];return}
  try {
    const next = await assetApi.suggest(key, 6)
    if (request===suggestionEpoch) suggestions.value=next
  } catch {if (request===suggestionEpoch) suggestions.value=[]}
}
async function submitSearch() {
  const query=keyword.value.trim()
  if (!query) return
  ++suggestionEpoch
  suggestions.value=[]
  resultsVisible.value=true
  loadingSearch.value=true
  resultKeyword.value=query
  try {
    const result = await assetApi.search(query,{limit:8})
    if (query===resultKeyword.value) {
      assetResults.value=result.items
      resultTotal.value=result.total
    }
  } catch { assetResults.value=[]; resultTotal.value=0 }
  finally { loadingSearch.value=false }
}
function askAgent() {
  const q=keyword.value.trim()
  if (q) router.push({name:'agent',query:{q}})
  else router.push({name:'agent'})
}
function quick(value:string){ keyword.value=value; submitSearch() }
function format(v:number){ return Number(v||0).toLocaleString() }
onMounted(async()=>{
  try { Object.assign(overview, await assetApi.overview()) } catch {}
  if (localStorage.getItem('datacontrol_token')) {
    try { recentChats.value=(await agentApi.conversations()).slice(0, 4) } catch { /* optional */ }
  }
  try { recent.value = await activityApi.recent() as any[] } catch {
    try { recent.value = (await assetApi.tables({limit:4}) as any[]).slice(0,4) } catch {}
  }
})
</script>

<style scoped>
.atlas-home{min-height:100%;padding-top:36px}
.atlas-hero{padding:36px 42px 27px;background:linear-gradient(128deg,#fff 16%,#f4f8ff 100%);border:1px solid #dfebfa;border-radius:16px;box-shadow:0 12px 36px rgba(26,76,142,.035)}
.hero-lead h1{margin:8px 0 6px;font-size:31px;line-height:1.35;letter-spacing:-.025em;font-weight:770;color:#172c4d}
.hero-lead p{margin:0;color:var(--dc-text-2);font-size:14px}
.hero-content{max-width:890px;margin-top:24px}
.hero-search{display:flex;align-items:center;gap:13px;padding:7px 8px 7px 16px;min-height:58px;border:1px solid #bfcff0;border-radius:11px;background:#fff;box-shadow:0 7px 22px rgba(40,92,164,.075);color:var(--dc-primary)}
.hero-search:focus-within{border-color:#6297f1;box-shadow:0 0 0 3px rgba(37,99,235,.08)}
.hero-search input{flex:1;min-width:0;border:0;background:transparent;outline:0;color:var(--dc-text);font-size:14px}
.hero-search input::placeholder{color:#91a0b5}
.search-primary{display:inline-flex;align-items:center;gap:9px;border:0;border-radius:8px;background:var(--dc-primary);height:42px;padding:0 20px;color:#fff;font-weight:700;cursor:pointer}
.search-primary:hover{background:var(--dc-primary-strong)}
.search-mode{display:flex;align-items:center;gap:5px;margin:10px 0 0}
.search-mode button{display:inline-flex;align-items:center;gap:6px;padding:6px 11px;border:0;border-radius:7px;background:transparent;color:#7386a1;font-size:12px;cursor:pointer}
.search-mode .mode-active{color:var(--dc-primary);background:#e8f0ff;font-weight:700}
.search-mode>span{margin-left:auto;color:#a4afbf;font-size:12px}
.hot{display:flex;align-items:center;gap:7px;margin-top:15px;flex-wrap:wrap}
.hot span{font-size:12px;color:#8898ad;margin-right:3px}
.hot button{border:1px solid #e0e8f5;border-radius:7px;background:#fff;padding:5px 11px;font-size:12px;color:#627892;cursor:pointer}
.hot button:hover{color:var(--dc-primary);border-color:#aac8f8}
.search-suggestions,.home-search-results{background:#fff;border:1px solid var(--dc-border);border-radius:10px;padding:13px 15px;margin-top:9px;box-shadow:var(--dc-shadow-sm)}
.suggest-title{color:#7e91ac;font-size:12px;padding-bottom:7px}
.suggest-item,.result-card{display:flex;align-items:center;gap:13px;min-height:58px;padding:8px 5px;border-top:1px solid #f0f3f9}
.suggest-item:first-of-type{border-top:0}
.suggest-item:hover,.result-card:hover{background:#f7faff}
.suggest-item span,.result-card span{display:grid;gap:3px;flex:1;min-width:0}
.suggest-item b,.result-card b{font-size:13px;font-weight:680}
.suggest-item code,.result-card code{font:12px var(--dc-mono);color:#788ba3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.result-card small{font-size:12px;color:var(--dc-text-2)}
.result-heading{display:flex;align-items:center;gap:10px;padding-bottom:7px}
.result-heading span{font-size:12px;color:var(--dc-text-3)}
.result-heading a{margin-left:auto;color:var(--dc-primary);display:flex;align-items:center;gap:4px;font-size:12px}
.workspace-heading{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:30px 0 13px}
.workspace-heading h2{font-size:19px;margin:4px 0 0;font-weight:740}
.workspace-heading>a{display:flex;align-items:center;gap:4px;font-size:12px;color:var(--dc-primary);font-weight:630}
.workspace-grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(300px,1fr);align-items:start;gap:16px}
.workspace-side{display:grid;gap:16px;min-width:0}
.recent-panel,.chat-panel,.overview-panel{padding:20px 22px;min-width:0}
.panel-head{display:flex;align-items:start;justify-content:space-between;gap:10px;margin-bottom:14px}
.panel-head h3{font-size:15px;margin:0 0 2px;font-weight:730}
.panel-head p{margin:0;color:var(--dc-text-3);font-size:12px}
.panel-head a{font-size:12px;color:var(--dc-primary);display:flex;align-items:center;gap:4px;white-space:nowrap}
.recent-item{display:flex;align-items:center;gap:13px;min-height:69px;padding:11px 0;border-top:1px solid #f0f3f8}
.recent-item:hover{background:#fafcff}
.recent-item>span:nth-child(2){display:grid;gap:3px;flex:1;min-width:0}
.recent-item b{font-size:13px;font-weight:680;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recent-item code{font:12px var(--dc-mono);color:#8192a8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recent-item>.dc-chip{flex:none}
.chat-list{display:grid;gap:3px}
.recent-chat{display:flex;align-items:center;gap:10px;padding:10px 3px;border-top:1px solid #f0f3f8;color:#58708c;font-size:13px}
.recent-chat span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.recent-chat:hover{color:var(--dc-primary)}
.start-agent{display:flex;align-items:center;gap:9px;color:var(--dc-primary);font-size:13px;padding:10px 0}
.mini-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
.mini-stats div{display:grid;justify-items:start;gap:2px;padding:10px 0}
.mini-stats strong{font-size:21px;font-weight:760;color:var(--dc-text);font-variant-numeric:tabular-nums}
.mini-stats span{font-size:12px;color:var(--dc-text-3)}
@media(max-width:1180px){.workspace-grid{grid-template-columns:1fr}.mini-stats{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:720px){.atlas-home{padding-top:18px}.atlas-hero{padding:25px 19px 21px}.hero-lead h1{font-size:25px}.hero-search{flex-wrap:wrap}.search-primary{flex:0 0 auto}.mini-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.hero-search input{flex-basis:calc(100% - 40px)}.search-primary{width:100%;justify-content:center}.search-mode>span{display:none}.recent-item>.dc-chip{display:none}.recent-panel,.chat-panel,.overview-panel{padding:16px}}
</style>
