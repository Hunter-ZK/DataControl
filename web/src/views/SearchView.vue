<template>
  <div class="dc-page search-v2">
    <div class="dc-container">
      <section class="search-hero dc-card">
        <div class="search-box-wrap">
          <div class="search-box">
            <Search :size="20" />
            <input
              v-model="q"
              placeholder="搜索数据集、字段、指标、标准…"
              @input="loadSuggestions"
              @focus="showSuggestions = true"
              @keydown.enter="runSearch(true)"
            />
            <button @click="runSearch(true)"><Search :size="16" />搜索</button>
          </div>
          <div v-if="showSuggestions && suggestions.length" class="suggestions dc-card">
            <button v-for="item in suggestions" :key="item.assetId" @mousedown.prevent="openSuggestion(item)">
              <span class="asset-chip">{{ label(item.assetType) }}</span>
              <div><b>{{ item.title }}</b><code>{{ item.technicalName }}</code></div>
              <ArrowRight :size="15" />
            </button>
          </div>
        </div>
        <div class="query-meta" v-if="q.trim()">
          <span>按 {{ terms.length }} 个词检索，结果需同时包含：</span>
          <b v-for="term in terms" :key="term">{{ term }}</b>
          <span>支持 2 字词；加引号可按整句匹配</span>
          <strong>共 {{ total }} 条</strong>
        </div>
        <div class="agent-intent" v-if="q.trim()">
          <div><Sparkles :size="17" /><span>看起来你在找和 <b>{{ q }}</b> 有关的数据。可以直接提问，系统会结合资产、指标与口径生成并校验 SQL。</span></div>
          <button @click="askAgent"><WandSparkles :size="15" />问：{{ agentQuestion }}</button>
        </div>
      </section>

      <div class="search-grid">
        <aside class="filter-panel dc-card">
          <div class="filter-head"><b>筛选</b><button @click="clearFilters">清除</button></div>
          <FilterGroup title="资产类型" :items="typeFacetItems" :selected="type" @select="selectType" />
          <FilterGroup title="数仓层级" :items="layerFacetItems" :selected="layer" @select="selectLayer" />
          <FilterGroup title="主题目录" :items="catalogFacetItems" :selected="catalog" @select="selectCatalog" />
          <FilterGroup title="状态" :items="statusFacetItems" :selected="status" @select="selectStatus" />
          <p class="facet-note">计数按“排除本组筛选”计算，选择一个类型后仍可看到其它类型的真实命中数。</p>
        </aside>

        <main class="search-main">
          <section v-if="bestRows.length" class="best-section">
            <div class="section-title"><span>最佳匹配</span><small>名称、技术名与业务定义综合排序</small></div>
            <div class="best-grid">
              <article v-for="item in bestRows" :key="item.assetId" class="best-card dc-card" @click="open(item)">
                <div class="best-tags"><span class="asset-chip">{{ label(item.assetType) }}</span><span v-if="item.layerCode" class="layer-chip" :data-layer="item.layerCode">{{ item.layerCode }}</span><span>{{ statusText(item.status) }}</span></div>
                <h2 v-html="safeMarkHtml(item.titleHighlight || item.title)" />
                <code v-html="safeMarkHtml(item.technicalNameHighlight || item.technicalName)" />
                <p v-html="safeMarkHtml(item.snippet || '点击查看资产定义、字段与治理信息。')" />
                <div class="best-actions"><button @click.stop="open(item)">查看详情</button><button v-if="item.assetType==='METRIC' || item.assetType==='TABLE'" class="primary" @click.stop="askAbout(item)"><Sparkles :size="14" />用此资产提问</button></div>
              </article>
            </div>
          </section>

          <section class="results dc-card">
            <div class="result-tabs">
              <button :class="{active:!type}" @click="selectType('')">全部 <b>{{ totalForAll }}</b></button>
              <button v-for="item in typeFacetItems.slice(0,4)" :key="item.key" :class="{active:type===item.key}" @click="selectType(item.key)">{{ item.label }} <b>{{ item.count }}</b></button>
              <span class="sort">排序：相关度</span>
            </div>

            <div v-if="loading" class="dc-empty">正在检索统一资产索引…</div>
            <div v-else-if="rows.length===0" class="dc-empty">没有找到匹配资产。可以尝试业务词、字段英文名或标准编号。</div>
            <article v-for="item in rows" :key="item.assetId" class="result-row" @click="open(item)">
              <div class="row-tags"><span class="asset-chip">{{ label(item.assetType) }}</span><span v-if="item.layerCode" class="layer-chip" :data-layer="item.layerCode">{{ item.layerCode }}</span><span v-if="item.catalogCode">{{ item.catalogCode }}</span></div>
              <div class="row-body">
                <div><h3 v-html="safeMarkHtml(item.titleHighlight || item.title)" /><code v-html="safeMarkHtml(item.technicalNameHighlight || item.technicalName)" /></div>
                <p v-html="safeMarkHtml(item.snippet || '点击查看资产详情。')" />
              </div>
              <ArrowRight :size="17" />
            </article>

            <footer v-if="total > 0" class="pagination">
              <span>第 {{ offset + 1 }}–{{ Math.min(offset + pageSize, total) }} 条，共 {{ total }} 条</span>
              <div>
                <button :disabled="currentPage===1" @click="goPage(currentPage-1)">上一页</button>
                <button v-for="page in visiblePages" :key="page" :class="{active:page===currentPage}" @click="goPage(page)">{{ page }}</button>
                <button :disabled="currentPage===totalPages" @click="goPage(currentPage+1)">下一页</button>
              </div>
            </footer>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Search, Sparkles, WandSparkles } from 'lucide-vue-next'
import { activityApi, assetApi, type SearchItem, type SearchSuggestion } from '@/api/client'

interface FacetItem { key: string; label: string; count: number }

const FilterGroup = defineComponent({
  props: { title: { type: String, required: true }, items: { type: Array as () => FacetItem[], required: true }, selected: { type: String, default: '' } },
  emits: ['select'],
  setup(props, { emit }) {
    return () => h('section', { class: 'filter-group' }, [
      h('h4', props.title),
      ...props.items.map((item) => h('button', { class: { checked: props.selected === item.key }, onClick: () => emit('select', item.key) }, [
        h('i'), h('span', item.label), h('b', String(item.count)),
      ])),
    ])
  },
})

const route = useRoute()
const router = useRouter()
const q = ref(String(route.query.q || '贷款 余额'))
const type = ref(String(route.query.type || ''))
const layer = ref(String(route.query.layer || ''))
const catalog = ref(String(route.query.catalog || ''))
const status = ref(String(route.query.status || ''))
const rows = ref<SearchItem[]>([])
const total = ref(0)
const offset = ref(Number(route.query.offset || 0))
const pageSize = 20
const loading = ref(false)
const suggestions = ref<SearchSuggestion[]>([])
const showSuggestions = ref(false)
const facets = ref({ assetTypes: {} as Record<string, number>, layers: {} as Record<string, number>, catalogs: {} as Record<string, number>, statuses: {} as Record<string, number> })
let suggestionSeq = 0

const typeLabels: Record<string,string> = { COLUMN:'字段', METRIC:'指标', TABLE:'数据集', STANDARD:'数据标准', CODE_TABLE:'码表', WORD_ROOT:'词根', STAT_SYSTEM:'统计制度' }
const statusLabels: Record<string,string> = { ONLINE:'在用', EFFECTIVE:'有效', OFFLINE:'已废弃', DISABLED:'停用' }
const terms = computed(() => q.value.trim().split(/\s+/).filter(Boolean))
const agentQuestion = computed(() => `本期${q.value.trim()}怎么统计`)
const currentPage = computed(() => Math.floor(offset.value / pageSize) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, Math.min(currentPage.value - 2, totalPages.value - 4))
  for (let p = start; p <= Math.min(totalPages.value, start + 4); p += 1) pages.push(p)
  return pages
})
const typeFacetItems = computed<FacetItem[]>(() => Object.entries(facets.value.assetTypes).sort((a,b)=>Number(b[1])-Number(a[1])).map(([key,count])=>({key,label:label(key),count:Number(count)})))
const layerFacetItems = computed<FacetItem[]>(() => Object.entries(facets.value.layers).sort((a,b)=>Number(b[1])-Number(a[1])).map(([key,count])=>({key,label:key,count:Number(count)})))
const catalogFacetItems = computed<FacetItem[]>(() => Object.entries(facets.value.catalogs).sort((a,b)=>Number(b[1])-Number(a[1])).slice(0,8).map(([key,count])=>({key,label:key,count:Number(count)})))
const statusFacetItems = computed<FacetItem[]>(() => Object.entries(facets.value.statuses).sort((a,b)=>Number(b[1])-Number(a[1])).map(([key,count])=>({key,label:statusText(key),count:Number(count)})))
const totalForAll = computed(() => Object.values(facets.value.assetTypes).reduce((sum,count)=>sum+Number(count),0) || total.value)
const bestRows = computed(() => {
  const preferred = ['METRIC','TABLE','COLUMN','STANDARD']
  return [...rows.value].sort((a,b)=>preferred.indexOf(a.assetType)-preferred.indexOf(b.assetType) || a.score-b.score).slice(0,2)
})

function label(value: string) { return typeLabels[value] || value }
function statusText(value?: string | null) { return value ? (statusLabels[value] || value) : '—' }
function escapeHtml(value: string) { return value.replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'} as Record<string,string>)[ch]) }
function safeMarkHtml(value: string) { return value.split(/(<\/?mark>)/gi).map(part => /^<\/?mark>$/i.test(part) ? part : escapeHtml(part)).join('') }

async function runSearch(reset = false) {
  const value = q.value.trim()
  if (!value) return
  if (reset) offset.value = 0
  loading.value = true
  showSuggestions.value = false
  try {
    const result = await assetApi.search(value, {
      asset_type: type.value ? [type.value] : undefined,
      layer: layer.value || undefined,
      catalog: catalog.value || undefined,
      status: status.value || undefined,
      offset: offset.value,
      limit: pageSize,
    })
    rows.value = result.items
    total.value = result.total
    facets.value = result.facets
    await activityApi.recordSearch(value)
    await router.replace({ query: { q: value, ...(type.value?{type:type.value}:{}), ...(layer.value?{layer:layer.value}:{}), ...(catalog.value?{catalog:catalog.value}:{}), ...(status.value?{status:status.value}:{}), ...(offset.value?{offset:String(offset.value)}:{}) } })
  } finally { loading.value = false }
}

async function loadSuggestions() {
  const value = q.value.trim(); const seq = ++suggestionSeq
  if (!value) { suggestions.value = []; return }
  try { const data = await assetApi.suggest(value, 8); if (seq === suggestionSeq) suggestions.value = data } catch { if (seq === suggestionSeq) suggestions.value = [] }
}
function selectType(value: string) { type.value = type.value === value ? '' : value; runSearch(true) }
function selectLayer(value: string) { layer.value = layer.value === value ? '' : value; runSearch(true) }
function selectCatalog(value: string) { catalog.value = catalog.value === value ? '' : value; runSearch(true) }
function selectStatus(value: string) { status.value = status.value === value ? '' : value; runSearch(true) }
function clearFilters() { type.value=''; layer.value=''; catalog.value=''; status.value=''; runSearch(true) }
function goPage(page: number) { const next = Math.min(Math.max(1,page), totalPages.value); offset.value=(next-1)*pageSize; runSearch(false); window.scrollTo({top:0,behavior:'smooth'}) }
function target(item: { assetType:string; assetId:string; technicalName:string }) { if(item.assetType==='TABLE')return `/datasets/${item.assetId}`; if(item.assetType==='COLUMN')return `/fields/${item.assetId}`; if(item.assetType==='CODE_TABLE')return `/code-tables/${item.technicalName}`; if(item.assetType==='STANDARD')return `/standards/${item.technicalName}`; if(item.assetType==='WORD_ROOT')return `/word-roots/${item.technicalName}`; if(item.assetType==='METRIC')return `/metrics/${item.technicalName}`; if(item.assetType==='STAT_SYSTEM')return `/stat-systems/${item.technicalName}`; return '' }
function open(item: SearchItem) { const to=target(item); if(to) router.push(to) }
function openSuggestion(item: SearchSuggestion) { showSuggestions.value=false; const to=target(item); if(to) router.push(to) }
function askAgent() { router.push({ name:'agent', query:{ q:`请根据 DataControl 中可信的指标、数据集和统计口径回答：${agentQuestion.value}。如需 SQL，请生成并静态校验 MaxCompute SQL。` } }) }
function askAbout(item: SearchItem) { router.push({ name:'agent', query:{ ...(item.assetType==='TABLE'?{asset:item.assetId}:{}), q:`请基于“${item.title}”（${item.technicalName}）回答我的数据问题，并优先使用该资产的可信口径。` } }) }
watch(() => route.query.q, (value) => { if (typeof value === 'string' && value !== q.value) { q.value=value; runSearch(true) } })
onMounted(() => { if (q.value) runSearch(false) })
</script>

<style scoped>
.search-v2{background:#eef6fa;min-height:100%}.search-hero{padding:18px 20px 14px}.search-box-wrap{position:relative}.search-box{height:52px;display:flex;align-items:center;gap:10px;border:1.5px solid #5eabc9;border-radius:10px;background:#fff;padding:4px 5px 4px 14px;color:#2e7897;box-shadow:0 3px 10px rgba(34,108,142,.06)}.search-box input{flex:1;border:0;outline:0;background:transparent;font-size:15px;color:#173f54}.search-box>button{height:40px;border:0;border-radius:8px;background:#177da7;color:#fff;padding:0 17px;display:flex;align-items:center;gap:6px;font-weight:700;cursor:pointer}.suggestions{position:absolute;left:0;right:0;top:58px;z-index:40;padding:7px;box-shadow:0 18px 42px rgba(38,94,126,.15)}.suggestions button{width:100%;border:0;background:#fff;display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:10px;text-align:left;padding:10px;border-radius:8px;cursor:pointer}.suggestions button:hover{background:#eef8fc}.suggestions div{min-width:0;display:grid;gap:3px}.suggestions b{font-size:13px}.suggestions code{font-size:11px;color:#55778a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.query-meta{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin:9px 2px 0;font-size:11px;color:#607b8a}.query-meta b{padding:3px 8px;border-radius:999px;background:#dff1f8;color:#1f6f91}.query-meta strong{margin-left:auto;color:#355c70}.agent-intent{margin-top:10px;padding:10px 12px;border:1px solid #cce7df;background:#effaf6;border-radius:9px;display:flex;align-items:center;justify-content:space-between;gap:16px;color:#2f6959;font-size:12px}.agent-intent>div{display:flex;align-items:center;gap:8px}.agent-intent button{border:0;border-radius:8px;background:#137da5;color:#fff;padding:8px 12px;display:flex;gap:6px;align-items:center;cursor:pointer;font-size:11px}.search-grid{display:grid;grid-template-columns:220px minmax(0,1fr);gap:14px;margin-top:14px;align-items:start}.filter-panel{padding:14px 14px 16px;position:sticky;top:78px}.filter-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.filter-head b{font-size:13px}.filter-head button{border:0;background:transparent;color:#177da7;font-size:11px;cursor:pointer}.filter-panel :deep(.filter-group){padding:10px 0;border-top:1px solid #e6eef2}.filter-panel :deep(.filter-group h4){font-size:10px;color:#6c8493;margin:0 0 5px}.filter-panel :deep(.filter-group button){width:100%;border:0;background:transparent;display:grid;grid-template-columns:14px 1fr auto;align-items:center;gap:7px;padding:5px 2px;color:#4c6a7a;text-align:left;cursor:pointer;font-size:11px}.filter-panel :deep(.filter-group button i){width:11px;height:11px;border:1px solid #a8c1cd;border-radius:2px;background:#fff}.filter-panel :deep(.filter-group button.checked i){background:#1b83aa;border-color:#1b83aa;box-shadow:inset 0 0 0 2px #fff}.filter-panel :deep(.filter-group button b){font-size:10px;color:#6c8796}.facet-note{font-size:9px;line-height:1.55;color:#8498a4;margin:10px 0 0}.search-main{min-width:0}.section-title{display:flex;align-items:center;gap:10px;margin:2px 2px 8px}.section-title span{font-size:12px;font-weight:750;color:#34596c}.section-title small{font-size:10px;color:#8397a3}.best-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.best-card{padding:16px;cursor:pointer;border-color:#d1e3ec}.best-tags,.row-tags{display:flex;align-items:center;gap:6px;color:#718895;font-size:9px}.asset-chip{display:inline-flex;padding:3px 7px;border-radius:999px;background:#e3f3f8;color:#176f91;font-size:9px;font-weight:750}.layer-chip{padding:3px 6px;border-radius:5px;background:#edf3f6;color:#476575;font-weight:800}.layer-chip[data-layer="ODS"]{background:#eeeafd;color:#4f3fa8}.layer-chip[data-layer="DWD"]{background:#e2f4f1;color:#0d6f68}.layer-chip[data-layer="DWS"]{background:#e3f1f8;color:#126b93}.layer-chip[data-layer="ADS"]{background:#fff3da;color:#83570a}.layer-chip[data-layer="DIM"]{background:#edf1f4;color:#44596a}.best-card h2{font-size:16px;margin:9px 0 5px;color:#214c62}.best-card code{font-size:10px;color:#547687}.best-card p{font-size:11px;color:#607987;line-height:1.6;min-height:34px}.best-actions{display:flex;gap:7px;margin-top:12px}.best-actions button{border:1px solid #c7dbe4;background:#fff;color:#476e82;border-radius:7px;padding:7px 9px;font-size:10px;cursor:pointer}.best-actions button.primary{background:#177da7;border-color:#177da7;color:#fff;display:flex;align-items:center;gap:4px}.results{margin-top:12px;overflow:hidden}.result-tabs{height:47px;display:flex;align-items:center;border-bottom:1px solid #e1eaef;padding:0 10px;gap:2px}.result-tabs button{height:100%;border:0;border-bottom:2px solid transparent;background:transparent;padding:0 10px;color:#5f7785;font-size:10px;cursor:pointer}.result-tabs button.active{color:#15789f;border-bottom-color:#15789f;font-weight:800}.result-tabs b{font-size:9px}.sort{margin-left:auto;font-size:9px;color:#8094a0;padding-right:8px}.result-row{display:grid;grid-template-columns:130px minmax(0,1fr) auto;gap:10px;align-items:center;padding:13px 16px;border-bottom:1px solid #edf2f5;cursor:pointer}.result-row:hover{background:#f7fbfd}.row-body{min-width:0;display:grid;gap:6px}.row-body>div{display:flex;align-items:baseline;gap:8px;min-width:0}.row-body h3{font-size:13px;color:#234e63;margin:0}.row-body code{font-size:9px;color:#6d8795;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.row-body p{margin:0;font-size:10px;color:#647d8b;line-height:1.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.results :deep(mark),.best-section :deep(mark){background:#fff0a8;color:#284f61}.pagination{display:flex;align-items:center;justify-content:space-between;padding:12px 15px;font-size:10px;color:#718794}.pagination>div{display:flex;gap:5px}.pagination button{min-width:29px;height:27px;border:1px solid #d1e0e7;border-radius:6px;background:#fff;color:#537184;font-size:10px;cursor:pointer}.pagination button.active{border-color:#2c8db4;color:#16749a;background:#edf8fc}.pagination button:disabled{opacity:.4;cursor:not-allowed}@media(max-width:980px){.search-grid{grid-template-columns:1fr}.filter-panel{position:static}.best-grid{grid-template-columns:1fr}.agent-intent{align-items:flex-start;flex-direction:column}.result-row{grid-template-columns:1fr auto}.row-tags{grid-column:1/-1}}@media(max-width:620px){.search-box>button{padding:0 11px}.query-meta strong{margin-left:0}.filter-panel{display:none}.result-tabs button:nth-of-type(n+4){display:none}.row-body>div{display:grid}.pagination{align-items:flex-start;flex-direction:column;gap:8px}}
</style>
