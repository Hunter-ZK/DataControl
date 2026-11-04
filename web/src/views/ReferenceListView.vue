<template>
  <div class="dc-page"><div class="dc-container">
    <div class="reference-toolbar">
      <nav class="reference-tabs" aria-label="资产分类">
        <RouterLink v-for="tab in tabs" :key="tab.to" :to="tab.to" :class="{active:tab.kind===kind}">{{tab.label}}</RouterLink>
      </nav>
      <div class="dc-toolbar">
        <el-input v-model="keyword" clearable :placeholder="config.placeholder" @keyup.enter="load" />
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </div>

    <div class="reference-layout">
      <section class="dc-card reference-list">
        <div class="list-head"><b>{{filteredRows.length.toLocaleString()}} 条资产</b></div>
        <div ref="listEl" class="reference-rows">
          <button
            v-for="row in visibleRows"
            :key="keyOf(row)"
            type="button"
            class="reference-row"
            :class="{selected:selectedKey===keyOf(row)}"
            @click="select(row)"
          >
            <span class="row-title">{{titleOf(row)}}</span>
            <code class="dc-tech">{{codeOf(row)}}</code>
            <span class="row-description">{{descOf(row)}}</span>
          </button>
          <div v-if="!filteredRows.length" class="dc-empty">暂无匹配资产。</div>
        </div>
        <Pager v-model:page="page" :page-size="pageSize" :total="filteredRows.length" />
      </section>

      <section v-if="selectedData" class="dc-card reference-detail">
        <div class="detail-head">
          <div>
            <span class="dc-chip">{{config.badge}}</span>
            <h2>{{titleOf(selectedData)}}</h2>
            <code class="dc-tech">{{codeOf(selectedData)}}</code>
          </div>
          <span class="status">{{statusLabel(selectedData.status || selectedData.version)}}</span>
        </div>
        <div class="detail-body">
          <template v-if="kind==='code-tables'">
            <h3>码表说明</h3>
            <p>{{selectedData.description||'暂无说明。'}}</p>
            <div class="value-toolbar">
              <b>码值列表（{{filteredValues.length}}）</b>
              <el-input v-model="valueKeyword" clearable placeholder="搜索码值或名称" />
            </div>
            <div class="dc-table-wrap values-table">
              <table class="dc-table">
                <thead><tr><th>码值</th><th>名称</th><th>说明</th></tr></thead>
                <tbody>
                  <tr v-for="value in filteredValues" :key="value.value">
                    <td><code class="dc-tech">{{value.value}}</code></td><td>{{value.name}}</td><td>{{value.description||'—'}}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="!filteredValues.length" class="dc-empty">没有匹配的码值。</div>
            </div>
          </template>

          <template v-else-if="kind==='data-standards'">
            <h3>标准定义</h3>
            <p>{{selectedData.definition||'暂无业务定义。'}}</p>
            <div class="kv-grid">
              <div><span>标准编号</span><code class="dc-tech">{{selectedData.standardNo||'—'}}</code></div>
              <div><span>关联码表</span><RouterLink v-if="selectedData.codeTableNo" :to="`/code-tables/${selectedData.codeTableNo}`">{{selectedData.codeTableNo}}</RouterLink><b v-else>—</b></div>
              <div><span>资产标识</span><code class="dc-tech">{{selectedData.assetId||'—'}}</code></div>
            </div>
          </template>

          <template v-else-if="kind==='word-roots'">
            <h3>词根定义</h3>
            <p>{{descOf(selectedData)}}</p>
            <div class="kv-grid">
              <div><span>英文词根</span><code class="dc-tech">{{selectedData.root||'—'}}</code></div>
              <div><span>英文全称</span><b>{{selectedData.enFull||'—'}}</b></div>
              <div><span>中文名称</span><b>{{selectedData.cnName||'—'}}</b></div>
              <div><span>同义词</span><b>{{selectedData.synonyms||'—'}}</b></div>
            </div>
          </template>

          <template v-else-if="kind==='metrics'">
            <h3>指标定义与统计口径</h3>
            <p>{{descOf(selectedData)}}</p>
            <div class="kv-grid">
              <div><span>指标编码</span><code class="dc-tech">{{selectedData.metricCode||'—'}}</code></div>
              <div><span>聚合方式</span><b>{{selectedData.aggregation||'—'}}</b></div>
              <div><span>度量字段</span><code class="dc-tech">{{selectedData.measureColumn||'—'}}</code></div>
              <div><span>时间字段</span><code class="dc-tech">{{selectedData.timeField||'—'}}</code></div>
              <div><span>来源数据集</span><RouterLink v-if="selectedData.sourceDatasetId" :to="`/datasets/${selectedData.sourceDatasetId}`">{{selectedData.sourceDatasetId}}</RouterLink><b v-else>—</b></div>
              <div><span>时间可加性</span><b>{{selectedData.timeAdditivity||'—'}}</b></div>
            </div>
          </template>

          <template v-else>
            <h3>统计制度信息</h3>
            <p>{{descOf(selectedData)}}</p>
            <div class="kv-grid">
              <div><span>制度编码</span><code class="dc-tech">{{selectedData.code||'—'}}</code></div>
              <div><span>版本</span><b>{{selectedData.version||'—'}}</b></div>
              <div><span>发布机构</span><b>{{selectedData.issuer||'—'}}</b></div>
              <div><span>文号</span><b>{{selectedData.documentNo||'—'}}</b></div>
            </div>
          </template>
        </div>
      </section>
      <section v-else class="dc-card reference-detail dc-empty">选择左侧资产查看详情。</section>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import api, { assetApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
import { statusLabel } from '@/utils/labels'

const props = defineProps<{ kind: string }>()
const route = useRoute()
const router = useRouter()
const keyword = ref('')
const rows = ref<any[]>([])
const selectedData = ref<any | null>(null)
const selectedKey = ref('')
const valueKeyword = ref('')
const listEl = ref<HTMLElement | null>(null)
const pageSize = useFitPageSize(listEl, 66, 5)
const page = ref(1)

const configs: Record<string, any> = {
  'code-tables': { title: '标准码值', placeholder: '搜索码表编号或名称', badge: '码表' },
  'data-standards': { title: '数据标准', placeholder: '搜索标准编号或名称', badge: '数据标准' },
  'word-roots': { title: '词根索引', placeholder: '搜索词根、中文名或同义词', badge: '词根' },
  metrics: { title: '指标与制度', placeholder: '搜索指标名称或编码', badge: '指标' },
  'stat-systems': { title: '统计制度', placeholder: '搜索统计制度', badge: '统计制度' },
}
const config = computed(() => configs[props.kind] || configs.metrics)
const tabs = computed(() => {
  if (['code-tables', 'data-standards', 'word-roots'].includes(props.kind)) {
    return [
      { kind: 'data-standards', to: '/standards', label: '数据标准' },
      { kind: 'code-tables', to: '/code-tables', label: '码表' },
      { kind: 'word-roots', to: '/word-roots', label: '词根' },
    ]
  }
  return [
    { kind: 'metrics', to: '/metrics', label: '指标' },
    { kind: 'stat-systems', to: '/stat-systems', label: '统计制度' },
  ]
})
const filteredRows = computed(() => rows.value)
const visibleRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})
const filteredValues = computed(() => {
  const values = selectedData.value?.values || []
  const query = valueKeyword.value.trim().toLowerCase()
  return query ? values.filter((item: any) => `${item.value} ${item.name} ${item.description || ''}`.toLowerCase().includes(query)) : values
})

function keyOf(row: any) {
  if (props.kind === 'code-tables') return row.codeTableNo || row.assetId
  if (props.kind === 'data-standards') return row.standardNo || row.assetId
  if (props.kind === 'word-roots') return row.root || row.assetId
  if (props.kind === 'metrics') return row.metricCode || row.assetId
  if (props.kind === 'stat-systems') return row.code || row.assetId
  return row.assetId || row.code
}
function titleOf(row: any) {
  return row.name || row.cnName || row.metricName || row.codeTableName || row.standardName || row.root || '未命名资产'
}
function codeOf(row: any) {
  return row.codeTableNo || row.standardNo || row.root || row.metricCode || row.code || row.assetId || '—'
}
function descOf(row: any) {
  return row.description || row.definition || row.caliber || row.aliases || '暂无补充说明。'
}
async function loadDetail(row: any) {
  const key = String(keyOf(row))
  if (props.kind === 'code-tables') {
    selectedData.value = await api.get(`/code-tables/${encodeURIComponent(key)}`)
    return
  }
  const result = await assetApi.reference(`/${props.kind}`, key) as any[]
  selectedData.value = result.find((item: any) => String(keyOf(item)) === key) || row
}
async function select(row: any, updateRoute = true) {
  selectedKey.value = String(keyOf(row))
  valueKeyword.value = ''
  page.value = Math.floor(Math.max(0, rows.value.findIndex((item) => keyOf(item) === keyOf(row))) / pageSize.value) + 1
  if (updateRoute && route.query.selected !== selectedKey.value) {
    await router.replace({ query: { ...route.query, selected: selectedKey.value } })
  }
  try { await loadDetail(row) } catch { selectedData.value = row }
}
async function load() {
  page.value = 1
  rows.value = await assetApi.reference(`/${props.kind}`, keyword.value || undefined) as any[]
  const requested = String(route.query.selected || '')
  const matched = requested ? rows.value.find((item) => String(keyOf(item)) === requested) : null
  const row = matched || rows.value[0]
  if (row) await select(row, Boolean(requested && !matched))
  else { selectedKey.value = ''; selectedData.value = null }
}
watch(() => props.kind, load)
watch(() => route.query.selected, (value) => {
  if (!value || String(value) === selectedKey.value) return
  const row = rows.value.find((item) => String(keyOf(item)) === String(value))
  if (row) void select(row, false)
})
watch(pageSize, () => { page.value = 1 })
onMounted(load)
</script>

<style scoped>
.reference-toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px}.reference-tabs{display:flex;gap:5px;align-items:center;padding:4px;border:1px solid var(--dc-border);border-radius:11px;background:#f8fbfd}.reference-tabs a{padding:8px 13px;border-radius:8px;color:var(--dc-text-2);font-size:12px;white-space:nowrap}.reference-tabs a.active,.reference-tabs a:hover{background:#fff;color:var(--dc-primary-strong);box-shadow:0 3px 10px rgba(49,117,151,.07)}.reference-toolbar :deep(.el-input){width:260px}.reference-layout{display:grid;grid-template-columns:360px minmax(0,1fr);gap:16px;align-items:stretch}.reference-list{padding:4px 16px 8px;min-width:0}.list-head{height:48px;display:flex;align-items:center;border-bottom:1px solid #edf2f5;font-size:13px}.reference-rows{max-height:calc(100vh - 350px);min-height:280px;overflow:auto}.reference-row{width:100%;display:grid;gap:5px;padding:12px 10px;border:0;border-bottom:1px solid #edf2f5;border-radius:0;background:#fff;text-align:left;cursor:pointer}.reference-row:hover{background:#f8fcfe}.reference-row.selected{background:#eef8fc;box-shadow:inset 3px 0 #4ba8d1}.row-title{font-size:13px;font-weight:700;color:var(--dc-text)}.reference-row code{font-size:11px}.row-description{font-size:12px;color:var(--dc-text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.reference-list :deep(.pager){border-top:1px solid #edf2f5}.reference-detail{padding:22px;min-width:0;min-height:340px}.detail-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding-bottom:16px;border-bottom:1px solid #edf2f5}.detail-head h2{font-size:21px;margin:9px 0 5px}.detail-head code{font-size:12px}.status{padding:5px 9px;border-radius:999px;background:#edf8f3;color:#2f8b6c;font-size:11px;font-weight:700;white-space:nowrap}.detail-body{padding-top:18px}.detail-body h3{font-size:16px;margin:0 0 9px}.detail-body>p{font-size:13px;line-height:1.75;color:var(--dc-text-2);margin:0 0 16px}.kv-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:16px}.kv-grid>div{padding:13px;border:1px solid var(--dc-border);border-radius:10px;min-width:0}.kv-grid span{display:block;font-size:12px;color:var(--dc-text-2);margin-bottom:5px}.kv-grid b,.kv-grid code,.kv-grid a{font-size:12px;overflow-wrap:anywhere}.kv-grid a{color:var(--dc-primary-strong)}.value-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:18px 0 10px}.value-toolbar b{font-size:13px}.value-toolbar :deep(.el-input){width:240px}.values-table{max-height:calc(100vh - 470px);min-height:160px;overflow:auto}@media(max-width:1000px){.reference-layout{grid-template-columns:300px minmax(0,1fr)}}@media(max-width:820px){.reference-toolbar{align-items:stretch;flex-direction:column}.reference-toolbar .dc-toolbar{width:100%}.reference-toolbar :deep(.el-input){width:100%}.reference-layout{grid-template-columns:1fr}.reference-rows{max-height:none;min-height:0;overflow:visible}.reference-detail{min-height:0}}@media(max-width:560px){.reference-tabs{overflow:auto}.reference-tabs a{padding:8px 10px}.kv-grid{grid-template-columns:1fr}.value-toolbar{align-items:stretch;flex-direction:column}.value-toolbar :deep(.el-input){width:100%}.reference-detail{padding:17px}}
</style>
