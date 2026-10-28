<template>
  <div class="dc-page">
    <div class="dc-container">
      <section class="hero">
        <div class="hero-copy">
          <span class="dc-eyebrow">DATA ASSET DISCOVERY</span>
          <h1>从一个问题开始，找到可信数据</h1>
          <p>查找数据集、字段、指标和标准，或向 DataAgent 提问并生成经过静态校验的 SQL。</p>
          <div class="hero-search">
            <Search :size="20" />
            <input v-model="keyword" @input="updateSuggestions" @keydown.enter.prevent="submitSearch"
              placeholder="输入数据集、字段、指标或业务问题，例如：贷款余额" aria-label="数据资产检索与 DataAgent 统一入口"/>
            <button class="search-primary" @click="submitSearch">检索资产</button>
            <button class="ask-action" @click="askAgent"><Sparkles :size="16"/>问 DataAgent</button>
          </div>
          <div v-if="suggestions.length && !assetResults.length" class="search-suggestions">
            <div class="suggest-title">相关资产 · 选择后查看详情</div>
            <RouterLink v-for="item in suggestions" :key="item.assetType+item.assetId"
              :to="assetRoute(item)" class="suggest-item">
              <span>{{ item.title }}</span><code>{{ item.technicalName }}</code>
              <small>{{ item.assetType }}</small>
            </RouterLink>
          </div>
          <section v-if="resultsVisible" class="home-search-results" aria-live="polite">
            <div class="result-heading"><b>检索结果</b><span>{{ resultKeyword }} · {{ resultTotal }} 项</span>
              <RouterLink :to="{name:'search',query:{q:resultKeyword}}">完整检索</RouterLink>
            </div>
            <p v-if="loadingSearch">正在检索内部资产…</p>
            <div v-else-if="!assetResults.length" class="empty-result">未找到匹配资产，可以改用“问 DataAgent”进一步描述需求。</div>
            <RouterLink v-for="item in assetResults" :key="item.assetType+item.assetId"
              :to="assetRoute(item)" class="result-card">
              <span class="result-kind">{{ item.assetType }}</span>
              <span><b>{{ item.title }}</b><code>{{ item.technicalName }}</code><small>{{ item.snippet }}</small></span>
              <ArrowUpRight :size="17"/>
            </RouterLink>
          </section>
          <div class="hot"><span>热门搜索</span><button v-for="x in hot" :key="x" @click="quick(x)">{{ x }}</button></div>
        </div>
        <div class="hero-orbit" aria-hidden="true"><div class="orb orb-a"/><div class="orb orb-b"/><div class="grid-dot"/></div>
      </section>

      <section class="launch-grid">
        <RouterLink v-for="item in launchers" :key="item.to" :to="item.to" class="launch-card">
          <span class="launch-icon"><component :is="item.icon" :size="21" stroke-width="1.8" /></span>
          <div><b>{{ item.title }}</b><p>{{ item.desc }}</p></div>
          <ArrowUpRight :size="17" class="launch-arrow" />
        </RouterLink>
      </section>

      <section v-if="recentChats.length" class="recent-conversations dc-card">
        <div class="panel-head"><div><span class="dc-eyebrow">CONTINUE</span><h2>最近问数会话</h2></div>
          <RouterLink to="/agent">全部会话</RouterLink>
        </div>
        <div class="recent-chat-list">
          <RouterLink v-for="chat in recentChats" :key="chat.id" :to="{name:'agent',query:{conversationId:chat.id}}" class="recent-chat">
            <Sparkles :size="16"/><span>{{ chat.title }}</span><ArrowUpRight :size="14"/>
          </RouterLink>
        </div>
      </section>
      <section class="home-row">
        <div class="dc-card recent-panel">
          <div class="panel-head"><div><span class="dc-eyebrow">RECENT</span><h2>最近使用</h2></div><RouterLink to="/profile">查看全部</RouterLink></div>
          <div class="recent-grid" v-if="recent.length">
            <RouterLink v-for="item in recent" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="recent-item">
              <div><span class="dc-chip">{{ item.layerCode || 'TABLE' }}</span><b>{{ item.bizName }}</b><code>{{ item.tableName }}</code></div>
              <ArrowRight :size="17" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无最近浏览，先从资产目录或搜索开始。</div>
        </div>
        <div class="dc-card overview-panel">
          <span class="dc-eyebrow">AT A GLANCE</span><h2>资产概览</h2>
          <div class="mini-stats"><div><strong>{{ format(overview.tableCount) }}</strong><span>数据集</span></div><div><strong>{{ format(overview.columnCount) }}</strong><span>字段</span></div><div><strong>{{ format(overview.metricCount) }}</strong><span>指标</span></div><div><strong>{{ format(overview.codeTableCount) }}</strong><span>码表</span></div></div>
          <RouterLink class="overview-link" to="/overview">进入数据概览 <ArrowRight :size="16" /></RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, ArrowUpRight, BookOpenCheck, Boxes, Database, Hash, Search, Sparkles } from 'lucide-vue-next'
import { activityApi, assetApi, agentApi, type SearchItem, type SearchSuggestion, type ServerAgentConversation } from '@/api/client'

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
const launchers = [
  { to:'/catalog', title:'资产目录', desc:'按业务主题浏览数据集与字段', icon:Database },
  { to:'/code-tables', title:'标准码值', desc:'查询标准码表、数据标准与引用', icon:Boxes },
  { to:'/word-roots', title:'词根索引', desc:'查看字段命名词根与规范用法', icon:Hash },
  { to:'/metrics', title:'指标与制度', desc:'查询指标口径与制度依据', icon:BookOpenCheck },
  { to:'/search?mode=ai', title:'智能问数', desc:'自然语言提问并生成可信 SQL', icon:Sparkles },
]
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
.hero{position:relative;min-height:340px;overflow:hidden;border:1px solid #d9ebf4;border-radius:26px;background:linear-gradient(135deg,#eef9fd 0%,#fbfdff 58%,#edf8fc 100%);padding:54px 58px;box-shadow:var(--dc-shadow-md)}.hero-copy{position:relative;z-index:2;max-width:820px}.hero h1{font-size:42px;line-height:1.16;letter-spacing:-.04em;margin:12px 0 10px}.hero p{font-size:15px;color:var(--dc-text-2);margin:0}.hero-search{margin-top:30px;height:60px;display:flex;align-items:center;gap:10px;padding:6px 6px 6px 17px;background:#fff;border:1px solid #cfe4ef;border-radius:15px;box-shadow:0 18px 42px rgba(50,120,157,.12);color:#6b9db6}.hero-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text);font-size:15px}.hero-search button{height:48px;padding:0 27px;border:0;border-radius:11px;background:linear-gradient(135deg,#51add2,#72c8db);color:#fff;font-weight:700;cursor:pointer}.hot{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:12px;font-size:12px;color:#89a0af}.hot button{border:0;background:transparent;color:#4e8eab;cursor:pointer;padding:3px 5px}.hero-orbit{position:absolute;right:0;top:0;width:36%;height:100%}.orb{position:absolute;border-radius:50%;filter:blur(2px)}.orb-a{width:220px;height:220px;right:40px;top:34px;background:radial-gradient(circle at 35% 35%,rgba(123,207,226,.38),rgba(109,171,213,.04) 68%)}.orb-b{width:120px;height:120px;right:160px;bottom:22px;background:radial-gradient(circle,rgba(80,167,209,.22),transparent 70%)}.grid-dot{position:absolute;inset:0;background-image:radial-gradient(rgba(69,143,180,.15) 1px,transparent 1px);background-size:18px 18px;mask-image:linear-gradient(to left,#000,transparent)}.launch-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px;margin-top:20px}.launch-card{position:relative;min-height:116px;padding:18px 17px;display:flex;align-items:flex-start;gap:12px;border:1px solid var(--dc-border);border-radius:15px;background:#fff;box-shadow:0 8px 24px rgba(44,109,142,.04);transition:.18s}.launch-card:hover{transform:translateY(-2px);border-color:#bfdde9;box-shadow:0 14px 32px rgba(44,109,142,.08)}.launch-icon{flex:0 0 42px;height:42px;border-radius:12px;display:grid;place-items:center;background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.launch-card b{font-size:14px}.launch-card p{margin:7px 0 0;font-size:11px;line-height:1.55;color:var(--dc-text-2)}.launch-arrow{position:absolute;right:13px;top:13px;color:#9aafbc}.home-row{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(300px,.8fr);gap:18px;margin-top:22px}.recent-panel,.overview-panel{padding:22px}.panel-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}.panel-head h2,.overview-panel h2{font-size:18px;margin:5px 0 0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.recent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.recent-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px;border:1px solid #e7eff4;border-radius:11px}.recent-item div{min-width:0;display:grid;gap:5px}.recent-item b{font-size:13px}.recent-item code{font-size:10px;color:#718b9a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.mini-stats div{padding:13px;border-radius:11px;background:#f7fbfd;border:1px solid #e5f0f5}.mini-stats strong{display:block;font-size:22px;color:#276b8e}.mini-stats span{font-size:11px;color:#8297a5}.overview-link{margin-top:14px;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dc-primary-strong)}@media(max-width:1200px){.launch-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.home-row{grid-template-columns:1fr}}@media(max-width:760px){.hero{padding:34px 24px;min-height:auto}.hero h1{font-size:32px}.hero-orbit{opacity:.45;width:45%}.launch-grid{grid-template-columns:1fr 1fr}.recent-grid{grid-template-columns:1fr}}@media(max-width:520px){.hero-search{height:54px}.hero-search button{height:42px;padding:0 16px}.launch-grid{grid-template-columns:1fr}}
 .hero-search { flex-wrap:wrap;height:auto;min-height:60px; }
 .hero-search input { min-width: min(100%,210px); flex: 1 1 280px; }
 .hero-search .ask-action { display:inline-flex;align-items:center;gap:5px;background:var(--dc-agent);color:white; }
 .search-suggestions,.home-search-results { margin-top:12px;max-width:820px;padding:12px;border:1px solid var(--dc-border);border-radius:13px;background:white;box-shadow:var(--dc-shadow-sm); }
 .suggest-title {font-size:12px;color:var(--dc-text-2);margin-bottom:7px;}
 .suggest-item {display:flex;gap:12px;align-items:center;padding:9px 10px;border-radius:8px;color:var(--dc-text);text-decoration:none;}
 .suggest-item:hover,.result-card:hover{background:var(--dc-primary-soft);}
 .suggest-item code,.result-card code{font-size:12px;color:var(--dc-text-2);}
 .suggest-item small {margin-left:auto;font-size:12px;color:var(--dc-text-3);}
 .result-heading {display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:13px;}
 .result-heading span{color:var(--dc-text-2);}
 .result-heading a{margin-left:auto;color:var(--dc-primary);}
 .result-card{display:flex;align-items:center;gap:12px;padding:12px 8px;text-decoration:none;color:var(--dc-text);border-top:1px solid var(--dc-border);}
 .result-card>span:nth-child(2){display:grid;gap:4px;flex:1;min-width:0;}
 .result-card small{color:var(--dc-text-2);font-size:12px;}
 .result-kind{font-size:12px;color:var(--dc-primary);width:80px;}
 .recent-conversations {margin:16px 0;padding:18px;}
 .recent-chat-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;}
 .recent-chat{display:flex;gap:9px;align-items:center;padding:11px;border:1px solid var(--dc-border);border-radius:9px;color:var(--dc-text);font-size:13px;}
 .recent-chat span{flex:1;}
 @media(max-width:650px){.hero-search{align-items:stretch;}.hero-search .ask-action,.hero-search .search-primary{min-height:40px;}.result-card small{display:none}}
</style>
