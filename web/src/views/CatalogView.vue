<template>
  <div class="dc-page catalog-page">
    <div class="dc-container">
      <section class="dc-page-head">
        <div>
          <h1 class="dc-title">数据资产</h1>
          <p class="dc-subtitle">按业务主题浏览数据集，展开即可预览字段结构，不必先记住表名。</p>
        </div>
        <div class="dc-toolbar">
          <el-input v-model="keyword" clearable placeholder="搜索数据集名称或表名" @keyup.enter="search" @clear="search" />
          <el-button type="primary" @click="search">查询</el-button>
        </div>
      </section>

      <div class="catalog-layout">
        <aside class="dc-card catalog-side">
          <h2 class="side-title">业务主题</h2>
          <button type="button" :class="{ active: !selected }" @click="chooseCatalog('')">
            <span>全部数据集</span><small>查看所有业务主题</small>
          </button>
          <button v-for="catalog in catalogs" :key="catalog.code" type="button"
            :class="{ active: selected === catalog.code }" @click="chooseCatalog(catalog.code)">
            <span>{{ catalog.name }}</span><small>{{ catalog.code }}</small>
          </button>
          <p v-if="catalogsError" class="side-error">{{ catalogsError }}</p>
        </aside>

        <section class="dc-card asset-list">
          <div class="list-head">
            <div>
              <b>{{ total }} 个数据集</b>
              <span v-if="selected"> · {{ catalogs.find(c => c.code === selected)?.name || selected }}</span>
              <span v-if="keyword.trim()"> · “{{ keyword.trim() }}”</span>
            </div>
            <span v-if="total">第 {{ startRow }}–{{ endRow }} 条</span>
          </div>

          <div v-if="loading" class="dc-empty" role="status">正在加载数据集…</div>
          <div v-else-if="loadError" class="dc-empty error-state" role="alert">
            <p>{{ loadError }}</p><button type="button" @click="load">重试</button>
          </div>
          <div v-else-if="!rows.length" class="dc-empty">
            <p>没有符合条件的数据集。</p><button type="button" @click="clearFilters">清除筛选条件</button>
          </div>

          <template v-else>
            <article v-for="item in rows" :key="item.assetId" class="asset-block">
              <div class="asset-row">
                <div class="asset-main">
                  <div class="asset-title">
                    <span class="layer-chip" :data-layer="item.layerCode">{{ item.layerCode }}</span>
                    <RouterLink :to="{ name:'dataset', params:{ id:item.assetId } }">{{ item.bizName || item.tableName }}</RouterLink>
                  </div>
                  <code class="dc-tech">{{ item.tableName }}</code>
                  <p>{{ item.catalogCode }} · {{ item.workspaceCode || '未标注工作空间' }} · {{ item.status === 'ONLINE' ? '在用' : item.status }}</p>
                </div>
                <div class="asset-meta">
                  <span>{{ item.techOwner || '负责人未登记' }}</span>
                  <span>{{ item.updateFreq || '频率未知' }}</span>
                  <button type="button" class="preview-button" :aria-expanded="previewId === item.assetId"
                    :aria-controls="'fields-' + item.assetId" @click="togglePreview(item.assetId)">
                    {{ previewId === item.assetId ? '收起字段' : '预览字段' }}
                    <ChevronDown :size="15" :class="{ turned: previewId === item.assetId }" />
                  </button>
                  <RouterLink :to="{ name:'dataset', params:{ id:item.assetId } }" class="open-detail">查看详情 <ArrowRight :size="14" /></RouterLink>
                </div>
              </div>

              <div v-if="previewId === item.assetId" :id="'fields-' + item.assetId" class="field-preview">
                <div class="field-preview-head">
                  <div><b>字段结构预览</b><span>展示字段定义与类型，不代表真实数据行</span></div>
                  <RouterLink :to="{ name:'dataset', params:{id:item.assetId}, query:{tab:'columns'} }">查看全部字段 <ArrowRight :size="14" /></RouterLink>
                </div>
                <p v-if="previewLoading" class="preview-info">正在读取字段信息…</p>
                <p v-else-if="previewError" class="preview-info preview-error">{{ previewError }}</p>
                <p v-else-if="!previewRows.length" class="preview-info">该数据集暂未登记字段。</p>
                <div v-else class="preview-table-wrap">
                  <table class="preview-table">
                    <thead><tr><th>字段英文名</th><th>中文名称</th><th>数据类型</th><th>定义</th></tr></thead>
                    <tbody>
                      <tr v-for="field in previewRows" :key="field.assetId || field.columnName">
                        <td><RouterLink v-if="field.assetId" :to="{name:'field',params:{id:field.assetId}}">{{ field.columnName }}</RouterLink><code v-else>{{ field.columnName }}</code></td>
                        <td>{{ field.cnName || '—' }}</td>
                        <td><code>{{ field.dataType || '—' }}</code></td>
                        <td>{{ field.bizDefinition || '未登记' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </article>

            <footer v-if="totalPages > 1" class="pagination">
              <button type="button" :disabled="page === 1" @click="go(page - 1)">上一页</button>
              <button v-for="number in visiblePages" :key="number" type="button"
                :class="{ active: number === page }" :aria-current="number === page ? 'page' : undefined"
                @click="go(number)">{{ number }}</button>
              <button type="button" :disabled="page === totalPages" @click="go(page + 1)">下一页</button>
            </footer>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, ChevronDown } from 'lucide-vue-next'
import { assetApi, type DatasetBrief } from '@/api/client'

type CatalogItem = { code: string; name: string }
type FieldPreview = { assetId?: string; columnName: string; cnName?: string; dataType?: string; bizDefinition?: string }

const route = useRoute()
const router = useRouter()
const keyword = ref('')
const selected = ref('')
const catalogs = ref<CatalogItem[]>([])
const catalogsError = ref('')
const rows = ref<DatasetBrief[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const loadError = ref('')
const previewId = ref<string | null>(null)
const previewRows = ref<FieldPreview[]>([])
const previewLoading = ref(false)
const previewError = ref('')
let requestSequence = 0
let previewSequence = 0

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const startRow = computed(() => total.value ? (page.value - 1) * pageSize + 1 : 0)
const endRow = computed(() => Math.min(page.value * pageSize, total.value))
const visiblePages = computed(() => {
  const result: number[] = []
  const start = Math.max(1, Math.min(page.value - 2, totalPages.value - 4))
  for (let number = start; number <= Math.min(totalPages.value, start + 4); number += 1) result.push(number)
  return result
})

function navigate(nextKeyword: string, nextCatalog: string, nextPage = 1) {
  const query: Record<string, string> = {}
  if (nextKeyword.trim()) query.keyword = nextKeyword.trim()
  if (nextCatalog) query.catalog = nextCatalog
  if (nextPage > 1) query.page = String(nextPage)
  router.push({ name: 'catalog', query })
}
function search() { navigate(keyword.value, selected.value) }
function chooseCatalog(code: string) { navigate(keyword.value, code) }
function go(value: number) { navigate(keyword.value, selected.value, Math.max(1, Math.min(value, totalPages.value))); window.scrollTo({ top: 0, behavior: 'smooth' }) }
function clearFilters() { navigate('', '') }

async function load() {
  const current = ++requestSequence
  loading.value = true
  loadError.value = ''
  previewId.value = null
  previewRows.value = []
  try {
    const data = await assetApi.tablePage({
      offset: (page.value - 1) * pageSize, limit: pageSize,
      keyword: keyword.value.trim() || undefined, catalog: selected.value || undefined,
      status: 'ONLINE',
    })
    if (current !== requestSequence) return
    rows.value = data.items
    total.value = data.total
    if (page.value > totalPages.value) {
      navigate(keyword.value, selected.value, totalPages.value)
    }
  } catch {
    if (current !== requestSequence) return
    rows.value = []
    total.value = 0
    loadError.value = '数据集加载失败，请确认后端服务正常后重试。'
  } finally {
    if (current === requestSequence) loading.value = false
  }
}

async function togglePreview(id: string) {
  if (previewId.value === id) { previewId.value = null; return }
  previewId.value = id
  const current = ++previewSequence
  previewRows.value = []
  previewError.value = ''
  previewLoading.value = true
  try {
    const fields = await assetApi.columns({ dataset_id: id, limit: 8 }) as FieldPreview[]
    if (current === previewSequence && previewId.value === id) previewRows.value = fields
  } catch {
    if (current === previewSequence && previewId.value === id) previewError.value = '字段加载失败，请稍后重试。'
  } finally {
    if (current === previewSequence) previewLoading.value = false
  }
}

watch(
  () => [route.query.keyword, route.query.catalog, route.query.page],
  () => {
    keyword.value = typeof route.query.keyword === 'string' ? route.query.keyword : ''
    selected.value = typeof route.query.catalog === 'string' ? route.query.catalog : ''
    const rawPage = Number(route.query.page || 1)
    page.value = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1
    void load()
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    catalogs.value = await assetApi.catalogs() as CatalogItem[]
  } catch {
    catalogsError.value = '业务主题暂不可用，可直接使用上方关键词检索。'
  }
})
</script>

<style scoped>
.catalog-page{background:var(--dc-bg);min-height:100%}
.dc-toolbar :deep(.el-input){width:285px}
.catalog-layout{display:grid;grid-template-columns:230px minmax(0,1fr);gap:16px;align-items:start}
.catalog-side{padding:14px;position:sticky;top:90px;display:grid;gap:4px}
.side-title{font-size:13px;color:#343c47;font-weight:800;margin:0;padding:8px 10px}
.catalog-side button{border:0;background:transparent;border-radius:9px;padding:11px;text-align:left;color:#48515e;cursor:pointer;display:grid;gap:3px;font-size:12px}
.catalog-side button small{font-size:10px;color:#8a929b}
.catalog-side button.active,.catalog-side button.active:hover{background:#111823;color:#fff}
.catalog-side button.active small{color:#c7ccd4}
.catalog-side button:hover{background:#f1f2f4;color:#1f252e}
.side-error{font-size:11px;color:#b25735;margin:6px 8px}
.asset-list{padding:0 22px 12px;min-width:0}
.list-head{min-height:55px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid #e6e8eb}
.list-head b{font-size:13px}.list-head span{font-size:11px;color:#707985}
.asset-block{border-bottom:1px solid #e9ebef}
.asset-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:15px;padding:17px 2px;align-items:center}
.asset-main{min-width:0}
.asset-title{display:flex;align-items:center;gap:9px}
.asset-title a{font-size:14px;font-weight:750;color:#202733}.asset-title a:hover{color:#6555ca;text-decoration:underline}
.asset-main code{display:block;font-size:11px;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.asset-main p{font-size:11px;color:#79828c;margin:6px 0 0}
.asset-meta{display:flex;align-items:center;gap:12px;color:#78818d;font-size:11px;flex-wrap:wrap;justify-content:flex-end}
.preview-button,.open-detail{display:inline-flex;align-items:center;gap:5px;border-radius:8px;padding:7px 9px;font-size:11px;font-weight:700;white-space:nowrap}
.preview-button{border:1px solid #dcd8f9;background:#f4f1ff;color:#6250cb;cursor:pointer}
.preview-button .turned{transform:rotate(180deg)}
.open-detail{border:1px solid #dfe3e8;color:#374150}
.layer-chip{padding:4px 7px;border-radius:5px;background:#edf1f4;color:#485a6e;font-size:10px;font-weight:800}
.layer-chip[data-layer="ODS"]{background:#eeeafd;color:#4f3fa8}
.layer-chip[data-layer="DWD"]{background:#e2f4f1;color:#0d6f68}
.layer-chip[data-layer="DWS"]{background:#e3f1f8;color:#126b93}
.layer-chip[data-layer="ADS"]{background:#fff3da;color:#83570a}
.layer-chip[data-layer="DIM"]{background:#edf1f4;color:#44596a}
.field-preview{padding:16px 17px 18px;border:1px solid #e7e4f8;border-radius:11px;background:#fbfaff;margin:0 0 14px}
.field-preview-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:12px}
.field-preview-head>div{display:grid;gap:4px}
.field-preview-head b{font-size:13px}.field-preview-head span{font-size:11px;color:#727987}
.field-preview-head>a{font-size:11px;color:#5d47df;display:flex;align-items:center;gap:5px}
.preview-info{font-size:12px;color:#737987;margin:12px}
.preview-error{color:#bc5b48}
.preview-table-wrap{overflow-x:auto}
.preview-table{border-collapse:collapse;min-width:680px;width:100%;font-size:11px;text-align:left}
.preview-table th{background:#f1effa;color:#505665;font-weight:700;padding:10px 12px}
.preview-table td{padding:10px 12px;border-top:1px solid #e8e8ef;color:#37414f}
.preview-table td a{color:#5d47df;font-weight:650}
.error-state button,.dc-empty button{border:1px solid #d3caff;background:#f5f2ff;border-radius:8px;padding:8px 12px;color:#5d47df;margin-top:9px;cursor:pointer}
.pagination{display:flex;justify-content:flex-end;gap:6px;padding:15px 0 3px}
.pagination button{min-width:34px;height:32px;border:1px solid #dce0e5;border-radius:7px;background:#fff;color:#4b5665;font-size:11px;cursor:pointer}
.pagination button.active{border-color:#111823;background:#111823;color:#fff}
.pagination button:disabled{opacity:.4;cursor:not-allowed}
@media(max-width:1100px){.asset-row{grid-template-columns:1fr}.asset-meta{justify-content:flex-start}}
@media(max-width:980px){.catalog-layout{grid-template-columns:1fr}.catalog-side{position:static;display:flex;flex-wrap:wrap}.catalog-side button{flex:0 0 auto}.catalog-side .side-title{width:100%}}
@media(max-width:700px){.dc-toolbar :deep(.el-input){width:100%}.list-head{align-items:flex-start;flex-direction:column;padding:12px 0;gap:4px}.field-preview-head{align-items:flex-start;flex-direction:column}}
</style>
