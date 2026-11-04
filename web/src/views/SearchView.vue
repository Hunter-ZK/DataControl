<template>
  <div class="dc-page">
    <div class="dc-container">
      <div class="search-summary">
        <b>{{ summary }}</b>

      </div>
      <section class="dc-card search-panel">
        <div class="facets" role="tablist" aria-label="资产类型">
          <button v-for="item in types" :key="item.key" type="button" role="tab" :aria-selected="type===item.key" :class="{active:type===item.key}" @click="selectType(item.key)">
            <span>{{item.label}}</span><b>{{count(item.key)}}</b>
          </button>
        </div>
        <div ref="resultsEl" class="results">
          <div v-if="loading" class="dc-empty">正在检索资产索引…</div>
          <div v-else-if="!q" class="dc-empty">使用首页搜索框或顶部全局搜索输入关键词。</div>
          <div v-else-if="filtered.length===0" class="dc-empty">没有找到匹配资产，试试更短的业务词或技术名称。</div>
          <article v-for="item in visibleRows" :key="item.asset_id" class="result-card" @click="open(item)">
            <div class="result-main">
              <div class="result-heading">
                <span class="dc-chip">{{assetTypeLabel(item.asset_type)}}</span>
                <h3 v-html="item.title_hl || item.title" />
                <code class="dc-tech">{{item.technical_name}}</code>
              </div>
              <p v-html="item.body_hl || '点击查看资产定义、字段、口径及相关信息。'" />
            </div>
            <div class="score"><small>相关度</small><b>{{Number(item.score || 0).toFixed(2)}}</b><ArrowRight :size="18"/></div>
          </article>
        </div>
        <div class="result-pager"><Pager v-model:page="page" :page-size="pageSize" :total="filtered.length" /></div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
import { assetTypeLabel } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const q = ref(String(route.query.q || ''))
const type = ref('ALL')
const rows = ref<any[]>([])
const loading = ref(false)
const resultsEl = ref<HTMLElement | null>(null)
const pageSize = useFitPageSize(resultsEl, 64, 5)
const page = ref(1)
const types = [
  { key: 'ALL', label: '全部' },
  { key: 'TABLE', label: '数据集' },
  { key: 'COLUMN', label: '字段' },
  { key: 'METRIC', label: '指标' },
  { key: 'CODE_TABLE', label: '码表' },
]
const filtered = computed(() => type.value === 'ALL' ? rows.value : rows.value.filter((row) => row.asset_type === type.value))
const visibleRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})
const summary = computed(() => q.value ? `“${q.value}” · 当前返回 ${filtered.value.length.toLocaleString()} 条` : '请输入关键词开始检索')

function count(key: string) {
  return key === 'ALL' ? rows.value.length : rows.value.filter((row) => row.asset_type === key).length
}
function selectType(key: string) {
  type.value = key
  page.value = 1
}
async function runSearch() {
  const value = q.value.trim()
  if (!value) return
  loading.value = true
  page.value = 1
  try {
    rows.value = await assetApi.search(value, 100) as any[]
    await activityApi.recordSearch(value)
    if (route.query.q !== value) await router.replace({ query: { ...route.query, q: value } })
  } finally {
    loading.value = false
  }
}
function open(item: any) {
  if (item.asset_type === 'TABLE') router.push(`/datasets/${item.asset_id}`)
  else if (item.asset_type === 'COLUMN') router.push(`/fields/${item.asset_id}`)
  else if (item.asset_type === 'CODE_TABLE') router.push(`/code-tables/${item.technical_name}`)
  else if (item.asset_type === 'METRIC') router.push(`/metrics/${item.technical_name}`)
}
watch(() => route.query.q, (value) => {
  if (typeof value === 'string' && value !== q.value) {
    q.value = value
    runSearch()
  }
})
watch(pageSize, () => { page.value = 1 })
onMounted(() => { if (q.value) runSearch() })
</script>

<style scoped>
.search-summary{display:flex;align-items:center;gap:12px;margin:0 2px 14px;min-height:32px}.search-summary b{font-size:15px;color:var(--dc-text)}.search-summary span{font-size:12px;color:var(--dc-text-3)}.search-panel{padding:4px 20px 10px;min-width:0}.facets{display:flex;align-items:center;gap:6px;overflow-x:auto;padding:8px 0 12px;border-bottom:1px solid #edf2f5}.facets button{display:flex;align-items:center;gap:7px;flex:0 0 auto;padding:8px 12px;border:1px solid transparent;border-radius:9px;background:transparent;color:#5f798a;font-size:12px;cursor:pointer}.facets button b{font-size:12px;color:var(--dc-text-3)}.facets button.active,.facets button:hover{background:var(--dc-primary-soft);border-color:#d9edf6;color:var(--dc-primary-strong)}.results{max-height:calc(100vh - 350px);min-height:280px;overflow:auto}.result-card{display:grid;grid-template-columns:minmax(0,1fr) 76px;gap:20px;padding:9px 4px;border-bottom:1px solid #edf2f5;cursor:pointer;min-height:64px;align-items:center}.result-card:last-child{border-bottom:0}.result-main{min-width:0}.result-heading{display:flex;align-items:center;gap:9px;min-width:0}.result-card h3{font-size:14px;margin:0;color:#234a60;min-width:0;max-width:44%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.result-card code{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;flex:1;min-width:0}.result-card p{margin:5px 0 0;font-size:12px;line-height:1.35;color:#5B6B7A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.result-card :deep(mark){background:#e2f6ff;color:#1f6686}.score{display:flex;flex-direction:column;align-items:flex-end;justify-content:center;color:#5B6B7A}.score small{font-size:12px}.score b{font-size:12px;color:#347d9d;margin:3px 0}.result-pager{border-top:1px solid #edf2f5}.result-pager :deep(.pager){padding-top:8px}@media(max-width:980px){.facets{flex-wrap:nowrap}}@media(max-width:820px){.results{max-height:none;min-height:0;overflow:visible}}@media(max-width:620px){.result-card{grid-template-columns:1fr}.score{display:none}.search-panel{padding:3px 14px 8px}.search-summary{align-items:flex-start;flex-direction:column;gap:3px}}
</style>
