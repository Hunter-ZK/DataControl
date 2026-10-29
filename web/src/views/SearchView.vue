<template>
  <div class="dc-page atlas-search"><div class="dc-container">
    <header class="search-heading"><div><span class="dc-eyebrow">UNIFIED ASSET SEARCH</span><h1 class="dc-title">全局资产检索</h1>
      <p class="dc-subtitle">找表、找字段、查指标、查标准。搜索结果按资产类型分组，一眼看清来源与层级。</p></div>
      <RouterLink to="/catalog" class="catalog-switch"><FolderTree :size="19"/> 按业务目录浏览 <ArrowRight :size="16"/></RouterLink>
    </header>
    <section class="search-hero">
      <div class="search-box-wrap">
        <div class="search-box"><Search :size="23"/><input v-model="q" placeholder="输入中文业务名称、技术名或字段名称…"
          @input="loadSuggestions" @focus="showSuggestions=true" @keydown.enter.prevent="runSearch(true)" aria-label="全局资产搜索"/>
          <button @click="runSearch(true)">搜索资产 <ArrowRight :size="18"/></button>
        </div>
        <div v-if="showSuggestions&&suggestions.length" class="suggestions">
          <button v-for="item in suggestions" :key="item.assetType+item.assetId" @mousedown.prevent="openSuggestion(item)">
            <AssetIcon :type="item.assetType" :size="21"/><span><b>{{item.title}}</b><code>{{item.technicalName}}</code></span><ArrowRight :size="17"/>
          </button>
        </div>
      </div>
      <div class="search-actions"><div v-if="q.trim()" class="query-meta"><span>关键词</span>
        <b v-for="term in terms" :key="term">{{term}}</b><span v-if="total">匹配 {{total}} 项</span>
      </div><div v-else class="query-meta"><span>支持按业务词、字段技术名、标准编码检索</span></div>
      <button @click="askAgent"><Sparkles :size="17"/>让 DataAgent 解释相关资产 <ArrowRight :size="16"/></button></div>
    </section>
    <section v-if="q.trim() && typeHighlights.length" class="type-highlights" aria-label="按资产类型查看">
      <button v-for="item in typeHighlights" :key="item.key" @click="selectType(item.key)" :class="{active:type===item.key}">
        <AssetIcon :type="item.key" :size="25"/><span><b>{{item.count}}</b><small>{{item.label}}</small></span><ArrowRight :size="16"/>
      </button>
    </section>
    <button class="mobile-filter-toggle" @click="filtersOpen=!filtersOpen"><Filter :size="19"/>筛选范围 <span>{{filtersOpen?'收起':'展开'}}</span></button>
    <div class="search-grid">
      <aside class="filter-panel dc-card" :class="{'mobile-open':filtersOpen}">
        <div class="filter-head"><b><Filter :size="19"/>筛选数据资产</b><button @click="clearFilters">清除</button></div>
        <div class="filter-section">
          <div class="filter-title"><FolderTree :size="17"/>业务目录层级</div>
          <button class="all-catalog" :class="{active:!catalog}" @click="selectCatalog('')">全部目录</button>
          <div v-if="catalogTree.length" class="facet-tree">
            <el-tree :data="catalogTree" node-key="code" :props="{label:'name',children:'children'}"
              default-expand-all :expand-on-click-node="false" @node-click="chooseCatalogNode">
              <template #default="{data}"><span class="facet-node" :class="{selected:catalog===data.code}">
                <FolderTree :size="15"/><span>{{data.name}}</span>
              </span></template>
            </el-tree>
          </div>
          <div v-else class="facet-empty">目录未加载，仍可按其他条件检索。</div>
          <p v-if="catalog" class="selected-catalog">已选择：{{catalogName}}</p>
        </div>
        <FilterGroup title="资产类型" :items="typeFacetItems" :selected="type" @select="selectType"/>
        <FilterGroup title="数仓层级" :items="layerFacetItems" :selected="layer" @select="selectLayer"/>
        <FilterGroup title="状态" :items="statusFacetItems" :selected="status" @select="selectStatus"/>
        <p class="facet-note">目录层级由系统中的真实父子关系生成。筛选仅约束当前目录，不自动合并下级目录结果。</p>
      </aside>
      <main class="search-main">
        <div class="results-head"><div><span class="dc-eyebrow">SEARCH RESULTS</span><h2>搜索结果 <em>{{total}}</em></h2></div>
          <div class="results-tools"><span>查看方式</span>
            <div class="density-switch" role="group" aria-label="结果展示密度">
              <button :class="{active:!compactResults}" :aria-pressed="!compactResults" @click="compactResults=false">详细</button>
              <button :class="{active:compactResults}" :aria-pressed="compactResults" @click="compactResults=true">精简</button>
            </div>
            <button class="clear-chip" v-if="type||layer||catalog||status" @click="clearFilters">清除筛选</button>
          </div>
        </div>
        <div v-if="type||layer||catalog||status" class="active-chips">
          <button v-if="type" @click="selectType(type)">{{label(type)}} ×</button>
          <button v-if="layer" @click="selectLayer(layer)">{{layer}} ×</button>
          <button v-if="catalog" @click="selectCatalog(catalog)">{{catalogName}} ×</button>
          <button v-if="status" @click="selectStatus(status)">{{statusText(status)}} ×</button>
        </div>
        <div v-if="!q.trim()" class="search-empty-state dc-card"><Search :size="39"/><h3>输入关键词，开始发现数据</h3><p>统一搜索数据集、字段、指标、码表、数据标准与统计制度。</p></div>
        <div v-else-if="loading" class="search-empty-state dc-card"><Search :size="33"/><h3>正在检索统一资产索引…</h3></div>
        <div v-else-if="!rows.length" class="search-empty-state dc-card"><Database :size="37"/><h3>没有找到符合条件的资产</h3><p>尝试更换关键词、清除目录筛选，或向 DataAgent 描述你的需求。</p></div>
        <template v-else>
          <section v-for="group in groupedRows" :key="group.assetType" class="result-group dc-card" :data-asset-type="group.assetType">
            <header class="result-group-head">
              <AssetIcon :type="group.assetType" :size="25"/>
              <div><h3>{{label(group.assetType)}}</h3><p>本页 {{group.items.length}} 条相关资产</p></div>
              <button v-if="type!==group.assetType" @click="selectType(group.assetType)">只看{{label(group.assetType)}} <ChevronRight :size="17"/></button>
            </header>
            <div class="group-items" :class="{ 'density-compact': compactResults }">
              <article v-for="item in group.items" :key="item.assetType+item.assetId"
                class="result-asset" role="link" tabindex="0" @click="open(item)" @keydown.enter="open(item)">
                <div class="asset-heading-block"><div class="asset-headline"><h4 v-html="safeMarkHtml(item.titleHighlight||item.title)"/>
                  <span v-if="item.layerCode" class="layer-tag" :data-layer="item.layerCode">{{item.layerCode}}</span>
                  <span v-if="item.status" class="status-tag">{{statusText(item.status)}}</span>
                </div>
                <code class="asset-tech" v-html="safeMarkHtml(item.technicalNameHighlight||item.technicalName)"/></div>
                <div class="asset-definition" v-if="!compactResults">
                  <span class="asset-definition-label">资产说明</span>
                  <p v-html="safeMarkHtml(item.snippet||'打开资产详情查看业务定义与关联信息。')"/>
                </div>
                <div class="asset-footer"><span v-if="item.catalogCode"><FolderTree :size="14"/>{{item.catalogCode}}</span>
                  <AssetQuickPreview :item="item" @open="open"/>
                  <button v-if="item.assetType==='TABLE'||item.assetType==='METRIC'" @click.stop="askAbout(item)"><WandSparkles :size="14"/>用此资产提问</button>
                  <span class="detail-link">查看详情 <ArrowRight :size="15"/></span>
                </div>
              </article>
            </div>
          </section>
          <footer v-if="total>pageSize" class="pagination">
            <span>第 {{offset+1}}–{{Math.min(offset+pageSize,total)}} 条，共 {{total}} 条</span>
            <div><button :disabled="currentPage===1" @click="goPage(currentPage-1)">上一页</button>
              <button v-for="p in visiblePages" :key="p" :class="{active:p===currentPage}" @click="goPage(p)">{{p}}</button>
              <button :disabled="currentPage===totalPages" @click="goPage(currentPage+1)">下一页</button></div>
          </footer>
        </template>
      </main>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, ChevronRight, Database, Filter, FolderTree, Search, Sparkles, WandSparkles } from 'lucide-vue-next'
import AssetIcon from '@/components/AssetIcon.vue'
import AssetQuickPreview from '@/components/AssetQuickPreview.vue'
import { buildCatalogTree, flattenCatalogs, type CatalogEntry, type CatalogNode } from '@/utils/catalogTree'
import { activityApi, assetApi, type SearchItem, type SearchSuggestion } from '@/api/client'

interface FacetItem { key: string; label: string; count: number }

const filtersOpen = ref(false)
const compactResults = ref(false)
const catalogEntries=ref<CatalogEntry[]>([])
const catalogTree=computed(()=>buildCatalogTree(catalogEntries.value))
const catalogName=computed(()=>flattenCatalogs(catalogTree.value).find(x=>x.code===catalog.value)?.name||catalog.value)
const groupOrder=['TABLE','COLUMN','METRIC','CODE_TABLE','STANDARD','WORD_ROOT','STAT_SYSTEM']
const groupedRows=computed(()=>groupOrder.map(assetType=>({assetType,items:rows.value.filter(row=>row.assetType===assetType)})).filter(group=>group.items.length))
const typeHighlights=computed(()=>groupOrder.map(key=>({key,label:typeLabels[key],count:Number(facets.value.assetTypes[key]||0)})).filter(x=>x.count>0))
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
const q = ref(String(route.query.q || ''))
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
const statusFacetItems = computed<FacetItem[]>(() => Object.entries(facets.value.statuses).sort((a,b)=>Number(b[1])-Number(a[1])).map(([key,count])=>({key,label:statusText(key),count:Number(count)})))
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
function chooseCatalogNode(node:CatalogNode){ selectCatalog(node.code) }
function selectStatus(value: string) { status.value = status.value === value ? '' : value; runSearch(true) }
function clearFilters() { type.value=''; layer.value=''; catalog.value=''; status.value=''; runSearch(true) }
function goPage(page: number) { const next = Math.min(Math.max(1,page), totalPages.value); offset.value=(next-1)*pageSize; runSearch(false); window.scrollTo({top:0,behavior:'smooth'}) }
function target(item: { assetType:string; assetId:string; technicalName:string }) { if(item.assetType==='TABLE')return `/datasets/${item.assetId}`; if(item.assetType==='COLUMN')return `/fields/${item.assetId}`; if(item.assetType==='CODE_TABLE')return `/code-tables/${item.technicalName}`; if(item.assetType==='STANDARD')return `/standards/${item.technicalName}`; if(item.assetType==='WORD_ROOT')return `/word-roots/${item.technicalName}`; if(item.assetType==='METRIC')return `/metrics/${item.technicalName}`; if(item.assetType==='STAT_SYSTEM')return `/stat-systems/${item.technicalName}`; return '' }
function open(item: SearchItem) { const to=target(item); if(to) router.push(to) }
function openSuggestion(item: SearchSuggestion) { showSuggestions.value=false; const to=target(item); if(to) router.push(to) }
function askAgent() { router.push({ name:'agent', query:{ q:`请根据 DataControl 中可信的指标、数据集和统计口径回答：${agentQuestion.value}。如需 SQL，请生成并静态校验 MaxCompute SQL。` } }) }
function askAbout(item: SearchItem) { router.push({ name:'agent', query:{ ...(item.assetType==='TABLE'?{asset:item.assetId}:{}), q:`请基于“${item.title}”（${item.technicalName}）回答我的数据问题，并优先使用该资产的可信口径。` } }) }
watch(() => route.query.q, (value) => { if (typeof value === 'string' && value !== q.value) { q.value=value; runSearch(true) } })
onMounted(async() => {try{catalogEntries.value=await assetApi.catalogs() as CatalogEntry[]}catch{catalogEntries.value=[]};if(q.value)runSearch(false)})
</script>
<style scoped>
.atlas-search{min-height:100%}
.search-heading{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-bottom:20px}
.catalog-switch{display:flex;align-items:center;gap:9px;color:#2b66cf;background:#fff;border:1px solid #c6dbf8;border-radius:10px;padding:12px 16px;font-size:14px;font-weight:730;box-shadow:var(--dc-shadow-sm);white-space:nowrap}
.catalog-switch:hover{background:#ecf4ff}
.search-hero{position:relative;padding:23px 27px;border-radius:17px;border:1px solid #cbdffa;background:linear-gradient(130deg,#fff,#f2f7ff 70%,#e6f1ff);box-shadow:0 12px 29px rgba(39,86,155,.09)}
.search-hero:after{content:'';position:absolute;right:32px;top:8px;width:170px;height:90px;pointer-events:none;background:radial-gradient(circle,#c8e0ff85,transparent 70%)}
.search-box-wrap{position:relative;z-index:2}
.search-box{height:60px;display:flex;align-items:center;gap:13px;border:1.5px solid #a8c7f1;background:white;padding:7px 8px 7px 17px;border-radius:11px;color:#387be5;box-shadow:0 5px 18px rgba(36,96,177,.07)}
.search-box:focus-within{border-color:#4d8df1;box-shadow:0 0 0 4px rgba(37,99,235,.09)}
.search-box input{flex:1;min-width:0;outline:0;border:0;background:transparent;font-size:15px;color:#253e63}
.search-box>button{height:44px;display:flex;align-items:center;gap:9px;background:linear-gradient(105deg,#2363eb,#4f8ef4);color:white;border:0;border-radius:9px;padding:0 20px;font-size:14px;font-weight:730;cursor:pointer}
.suggestions{position:absolute;left:0;right:0;top:65px;z-index:30;padding:9px;background:#fff;border:1px solid #bed4f2;border-radius:11px;box-shadow:0 15px 39px #1f529b23}
.suggestions button{width:100%;display:flex;align-items:center;gap:13px;padding:12px;border:0;border-radius:8px;background:white;cursor:pointer;text-align:left}
.suggestions button:hover{background:#f1f7ff}
.suggestions button span:nth-child(2){flex:1;min-width:0;display:grid;gap:3px}
.suggestions b{font-size:14px;color:#243b5d}
.suggestions code{font:12px var(--dc-mono);color:#7286a3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.search-actions{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 3px 0;position:relative;z-index:1}
.query-meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;color:#6e84a2;font-size:13px}
.query-meta b{background:#e4efff;border:1px solid #cbdffa;color:#2a66cd;border-radius:8px;padding:5px 9px;font-size:13px}
.search-actions>button{border:0;display:flex;align-items:center;gap:8px;background:#e4efff;border-radius:8px;padding:9px 13px;color:#285fc6;font-weight:700;font-size:13px;cursor:pointer}
.search-actions>button:hover{background:#d7e7ff}
.type-highlights{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:12px;margin-top:17px}
.type-highlights button{display:flex;align-items:center;gap:11px;text-align:left;min-height:90px;padding:15px 13px;border:1px solid #cbdff7;background:linear-gradient(145deg,#fff,#f7fbff);border-radius:13px;box-shadow:0 6px 17px rgba(39,91,163,.075);cursor:pointer}
.type-highlights button:hover,.type-highlights button.active{border-color:#86b4f5;background:#eef5ff;box-shadow:0 10px 24px rgba(33,91,177,.14)}
.type-highlights button span:nth-child(2){display:grid;flex:1;gap:2px}
.type-highlights b{font-size:23px;color:#1b4589;font-weight:800;font-variant-numeric:tabular-nums}
.type-highlights small{font-size:13px;color:#6580a3}
.type-highlights button>svg:last-child{color:#91aacd;flex:none}
.search-grid{display:grid;grid-template-columns:276px minmax(0,1fr);gap:18px;align-items:start;margin-top:19px}
.filter-panel{padding:19px 17px;position:sticky;top:83px;max-height:calc(100dvh - 100px);overflow:auto;background:linear-gradient(145deg,#fff,#fafcff)}
.filter-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding-bottom:15px}
.filter-head b{display:flex;align-items:center;gap:10px;font-size:16px;color:#1d3e70}
.filter-head button,.clear-chip{border:0;background:transparent;color:#3475dd;font-size:13px;cursor:pointer}
.filter-section,.filter-panel :deep(.filter-group){padding:14px 0;border-top:1px solid #e1eafa}
.filter-title{display:flex;align-items:center;gap:7px;color:#34547c;font-size:14px;font-weight:720;margin-bottom:10px}
.all-catalog{padding:9px 10px;color:#5d7494;border:0;background:transparent;border-radius:7px;cursor:pointer;text-align:left;width:100%;font-size:13px}
.all-catalog.active,.all-catalog:hover{background:#e8f2ff;color:#2265cf}
.facet-tree{max-height:290px;overflow:auto}
.facet-tree :deep(.el-tree){background:transparent;--el-tree-node-hover-bg-color:#edf5ff}
.facet-tree :deep(.el-tree-node__content){height:37px;border-radius:7px}
.facet-node{min-width:0;display:flex;align-items:center;gap:6px;font-size:13px;color:#577398}
.facet-node span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.facet-node.selected{color:#1b61d5;font-weight:800}
.selected-catalog{margin:9px 0 0;color:#2c66ca;font-size:12px}
.facet-empty,.facet-note{color:#899ab0;font-size:12px;line-height:1.7}
.filter-panel :deep(.filter-group h4){font-size:14px;color:#35557d;font-weight:710;margin:0 0 7px}
.filter-panel :deep(.filter-group button){display:grid;grid-template-columns:17px 1fr auto;align-items:center;gap:9px;text-align:left;width:100%;border:0;padding:10px 7px;background:transparent;border-radius:7px;cursor:pointer;color:#536e90;font-size:13px}
.filter-panel :deep(.filter-group button:hover){background:#f1f7ff}
.filter-panel :deep(.filter-group button i){width:15px;height:15px;border:1px solid #aac1df;background:white;border-radius:4px}
.filter-panel :deep(.filter-group button.checked i){background:#3778ec;border-color:#3778ec;box-shadow:inset 0 0 0 3px #fff}
.filter-panel :deep(.filter-group button b){font-size:12px;color:#889cb5}
.search-main{min-width:0}
.results-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:6px 0 14px}
.results-head h2{font-size:22px;color:#1b3559;margin:5px 0 0}
.results-head em{font-style:normal;color:#326ee5;font-size:14px;margin-left:7px;background:#e3efff;border-radius:9px;padding:4px 9px}
.active-chips{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.active-chips button{border:1px solid #bdd4fa;background:#e8f2ff;color:#2865d1;padding:6px 10px;font-size:13px;border-radius:7px;cursor:pointer}
.result-group{margin-bottom:16px;overflow:hidden;border-color:#cddff5;box-shadow:0 9px 24px rgba(38,86,159,.09)}
.result-group-head{display:flex;align-items:center;gap:13px;padding:18px 20px;background:linear-gradient(100deg,#f2f7ff,#fff);border-bottom:1px solid #dce8f8;position:relative}
.result-group-head:before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:#3479ec}
.result-group-head div{flex:1;display:grid;gap:3px}
.result-group-head h3{margin:0;font-size:18px;color:#24446e}
.result-group-head p{margin:0;font-size:12px;color:#8a9db6}
.result-group-head button{display:flex;align-items:center;gap:3px;background:transparent;border:0;color:#2d6dda;font-size:13px;cursor:pointer}
.group-items{display:grid;gap:0;padding:0 19px}
.result-asset{padding:18px 4px;border-bottom:1px solid #e8eff9;cursor:pointer;transition:background .12s}
.result-asset:last-child{border-bottom:0}
.result-asset:hover{background:#f9fbff}
.asset-headline{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.asset-headline h4{font-size:16px;margin:0;color:#1c3b63;font-weight:750}
.layer-tag{padding:3px 9px;border-radius:7px;background:#eaf3ff;color:#2766d2;font-size:12px;font-weight:750}
.layer-tag[data-layer="DWD"]{color:#05836f;background:#e0f7f1}
.layer-tag[data-layer="ADS"]{color:#93631d;background:#fff1db}
.status-tag{font-size:12px;color:#7891af}
.result-asset>code{display:block;margin:6px 0;font:13px var(--dc-mono);color:#687f9e;overflow-wrap:anywhere}
.result-asset>p{margin:6px 0 13px;font-size:14px;color:#5f7695;line-height:1.75}
.asset-footer{display:flex;align-items:center;gap:10px;color:#8b9db4;font-size:12px}
.asset-footer>span:first-child{display:inline-flex;align-items:center;gap:5px}
.asset-footer button{margin-left:auto;border:1px solid #d4e4fb;border-radius:7px;padding:6px 9px;color:#2868d4;background:#f4f8ff;display:flex;align-items:center;gap:5px;font-size:12px;cursor:pointer}
.asset-footer .detail-link{margin-left:auto;color:#2e6cd8;display:inline-flex;align-items:center;gap:5px}
.result-asset :deep(mark){background:#fff0b8;color:#314e76;border-radius:3px}
.search-empty-state{padding:65px 20px;text-align:center;display:grid;justify-items:center;gap:12px;color:#5787cb}
.search-empty-state h3{color:#2b4466;margin:0;font-size:18px}
.search-empty-state p{color:#7489a5;font-size:14px;margin:0}
.pagination{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:18px;color:#7c90aa;font-size:13px}
.pagination>div{display:flex;gap:5px}
.pagination button{border:1px solid #c6d9f2;background:white;padding:7px 11px;border-radius:7px;cursor:pointer;color:#46688d}
.pagination button.active{background:#e8f2ff;color:#2765d1;border-color:#a9c8f8}
.pagination button:disabled{opacity:.4;cursor:default}
.mobile-filter-toggle{display:none}
@media(max-width:1020px){.search-grid{grid-template-columns:1fr}.filter-panel{position:static;max-height:none}.search-heading{align-items:flex-start}.type-highlights{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:680px){.search-heading{display:grid}.catalog-switch{justify-self:start}.search-hero{padding:16px}.search-box{height:auto;min-height:55px;flex-wrap:wrap}.search-box input{flex-basis:calc(100% - 45px);font-size:14px}.search-box>button{width:100%;justify-content:center}.search-actions{flex-direction:column;align-items:flex-start}.type-highlights{grid-template-columns:repeat(2,minmax(0,1fr))}.mobile-filter-toggle{display:flex;align-items:center;gap:8px;width:100%;margin:15px 0 0;padding:12px;background:white;border:1px solid #cbdcf4;border-radius:9px;color:#2667d6;font-weight:730}.mobile-filter-toggle span{margin-left:auto}.filter-panel:not(.mobile-open){display:none}.filter-panel.mobile-open{display:block}.result-group-head{padding:14px}.result-group-head h3{font-size:16px}.group-items{padding:0 13px}.result-asset>p{font-size:13px}.result-asset>code{font-size:12px}.pagination{flex-direction:column;align-items:flex-start}}

/* Atlas 2.1 — enhanced intra-panel readability */

.results-head{align-items:center}
.results-tools{display:flex;align-items:center;gap:10px;color:#8298b5;font-size:12px;flex-wrap:wrap}
.density-switch{display:inline-flex;align-items:center;padding:3px;background:#eaf2fd;border:1px solid #d2e2f7;border-radius:9px;gap:2px}
.density-switch button{background:transparent;color:#607b9f;border:0;padding:6px 11px;font-size:12px;font-weight:680;border-radius:6px;cursor:pointer}
.density-switch button.active{background:#fff;color:#2469d9;box-shadow:0 2px 8px #2c64b51b}
.result-group{border:1px solid #c0d7f4;box-shadow:0 11px 29px #3268a218}
.result-group-head{background:linear-gradient(105deg,#eaf3ff,#f8fbff);border-bottom:1px solid #bdd5f4;padding:18px 22px}
.result-group-head:before{width:5px}
.result-group[data-asset-type="METRIC"] .result-group-head:before{background:#8d78de}
.result-group[data-asset-type="COLUMN"] .result-group-head:before{background:#16a3ba}
.result-group[data-asset-type="CODE_TABLE"] .result-group-head:before{background:#17a889}
.result-group[data-asset-type="STANDARD"] .result-group-head:before{background:#d59d3a}
.result-group[data-asset-type="WORD_ROOT"] .result-group-head:before{background:#8a69d4}
.group-items{gap:11px;padding:14px 15px 17px;background:linear-gradient(150deg,#f4f8ff,#edf5ff)}
.result-asset{padding:0;border:1px solid #d7e5f7;border-radius:11px;background:#fff;overflow:hidden;box-shadow:0 3px 10px #244f8a0a;transition:transform .16s,box-shadow .16s,border-color .16s}
.result-asset:nth-child(even){background:#f8fbff;border-color:#c9ddf5}
.result-asset:last-child{border-bottom:1px solid #d7e5f7}
.result-asset:hover{background:#fff;border-color:#8fb8ed;box-shadow:0 8px 23px #2c65a21f;transform:translateY(-1px)}
.result-asset:focus-visible{outline:3px solid #72a4fa;outline-offset:2px}
.asset-heading-block{padding:16px 18px 12px;display:grid;gap:8px}
.asset-headline h4{font-size:16px}
.asset-tech{display:block;margin:0!important;padding:8px 11px;border:1px solid #dce9f8;background:#f1f6ff;border-radius:7px;color:#43688c!important;line-height:1.5}
.asset-definition{margin:0 16px 13px;padding:12px 14px;display:grid;grid-template-columns:68px minmax(0,1fr);gap:10px;background:linear-gradient(90deg,#f2f8ff,#fcfdff);border:1px solid #e0eafa;border-radius:8px}
.asset-definition-label{font-size:12px;font-weight:730;color:#3d77c8;padding-top:2px}
.asset-definition p{font-size:13px;line-height:1.7;color:#5f7798;margin:0;overflow-wrap:anywhere}
.asset-footer{padding:10px 17px;border-top:1px solid #e5edf8;background:#f7faff;min-height:41px}
.result-asset:nth-child(even) .asset-footer{background:#f0f6ff}
.asset-footer button{background:#fff;border-color:#cadcf6}
.asset-footer button:hover{border-color:#79a9ec;background:#eaf2ff}
.group-items.density-compact{gap:6px}
.density-compact .asset-heading-block{padding:11px 15px 8px;gap:4px}
.density-compact .asset-tech{background:transparent;border:0;padding:0}
.density-compact .asset-footer{padding:6px 15px;min-height:35px}
@media(max-width:680px){.results-head{align-items:start;gap:10px;flex-direction:column}.results-tools{justify-content:space-between;width:100%}.group-items{padding:9px;gap:9px}.asset-heading-block{padding:13px}.asset-definition{margin:0 11px 9px;grid-template-columns:1fr;gap:3px;padding:9px 11px}.asset-footer{flex-wrap:wrap;padding:9px 11px}}

.asset-footer :deep(.preview-control){display:flex;align-items:center;margin-left:auto}
.asset-footer button:not(.preview-trigger){margin-left:0}
@media(max-width:680px){.asset-footer :deep(.preview-control){margin-left:0}.asset-footer .detail-link{margin-left:auto}}
</style>
