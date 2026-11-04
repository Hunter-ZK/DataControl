<template>
  <div class="dc-page"><div class="dc-container">
    <div class="catalog-toolbar">
      <div class="dc-toolbar">
        <el-input v-model="keyword" clearable placeholder="搜索数据集" @keyup.enter="load" />
        <el-select v-model="layerFilter" clearable placeholder="数仓层级">
          <el-option v-for="layer in layers" :key="layer" :label="layer" :value="layer" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="资产状态">
          <el-option label="在用" value="ONLINE" />
          <el-option label="已废弃" value="DEPRECATED" />
          <el-option label="已下线" value="OFFLINE" />
          <el-option label="全部状态" value="ALL" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>
    </div>
    <div class="catalog-layout">
      <aside class="dc-card catalog-side">
        <div class="side-title">业务目录</div>
        <button :class="{active:!selected}" @click="selected=''">全部资产</button>
        <button v-for="c in catalogs" :key="c.code" :class="{active:selected===c.code}" @click="selected=c.code">
          <span>{{c.name}}</span><small>{{c.code}}</small>
        </button>
      </aside>
      <section class="dc-card asset-list">
        <div class="list-head"><b>当前载入 {{filtered.length.toLocaleString()}} 个数据集</b><span>按业务目录和数仓层级筛选</span></div>
        <div ref="rowsEl" class="asset-rows">
          <RouterLink v-for="item in visibleRows" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="asset-row">
            <div class="asset-main">
              <div class="asset-title"><LayerTag :layer="item.layerCode" /><b>{{item.bizName}}</b></div>
              <code class="dc-tech">{{item.tableName}}</code>
            </div>
            <div class="asset-meta"><span>负责人 · {{item.techOwner||'未登记'}}</span><span>{{item.updateFreq||'—'}}</span><ArrowRight :size="17"/></div>
          </RouterLink>
          <div v-if="filtered.length===0" class="dc-empty">没有符合条件的数据集。</div>
        </div>
        <Pager v-model:page="page" :page-size="pageSize" :total="filtered.length" />
      </section>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'

const keyword = ref('')
const selected = ref('')
const layerFilter = ref('')
const statusFilter = ref('ONLINE')
const catalogs = ref<any[]>([])
const rows = ref<any[]>([])
const layers = ['ODS', 'DWD', 'DWS', 'ADS', 'DIM']
const rowsEl = ref<HTMLElement | null>(null)
const pageSize = useFitPageSize(rowsEl, 44, 5)
const page = ref(1)

const filtered = computed(() => rows.value.filter((row) => {
  const catalogMatch = !selected.value || row.catalogCode === selected.value
  const layerMatch = !layerFilter.value || row.layerCode === layerFilter.value
  const statusMatch = statusFilter.value === 'ALL' || row.status === statusFilter.value
  return catalogMatch && layerMatch && statusMatch
}))
const visibleRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

watch([selected, layerFilter, statusFilter, pageSize], () => { page.value = 1 })

async function load() {
  page.value = 1
  rows.value = await assetApi.tables({ limit: 200, keyword: keyword.value || undefined }) as any[]
}
onMounted(async () => {
  try { catalogs.value = await assetApi.catalogs() as any[] } catch {}
  await load()
})
</script>

<style scoped>
.catalog-toolbar{display:flex;justify-content:flex-end;margin-bottom:16px}.catalog-toolbar .dc-toolbar{gap:9px}.catalog-toolbar :deep(.el-input){width:250px}.catalog-toolbar :deep(.el-select){width:140px}.catalog-layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:16px;align-items:start}.catalog-side{padding:14px;position:sticky;top:86px;display:grid;gap:4px;max-height:calc(100vh - 150px);overflow:auto}.side-title{font-size:12px;color:#5B6B7A;font-weight:700;padding:6px 9px 8px}.catalog-side button{border:0;background:transparent;border-radius:9px;padding:10px;text-align:left;color:#587587;cursor:pointer;display:grid;gap:3px}.catalog-side button small{font-size:12px;color:#5B6B7A}.catalog-side button.active,.catalog-side button:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.asset-list{padding:4px 20px 8px;min-width:0}.list-head{height:48px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf2f5}.list-head span{font-size:12px;color:var(--dc-text-3)}.asset-rows{max-height:calc(100vh - 280px);min-height:260px;overflow:auto}.asset-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;padding:7px 3px;border-bottom:1px solid #edf2f5;align-items:center;min-height:44px}.asset-row:last-child{border-bottom:0}.asset-main{min-width:0;display:flex;align-items:center;gap:16px}.asset-title{display:flex;align-items:center;gap:8px;flex:0 0 220px;min-width:0}.asset-title b{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.asset-main code{display:block;font-size:12px;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:360px}.asset-meta{display:flex;align-items:center;gap:14px;color:#5B6B7A;font-size:12px}.asset-list :deep(.pager){border-top:1px solid #edf2f5}.catalog-side button small{font-size:12px}@media(max-width:980px){.catalog-layout{grid-template-columns:1fr}.catalog-side{position:static;display:flex;overflow:auto;max-height:none}.catalog-side .side-title{display:none}.catalog-side button{flex:0 0 auto;min-width:120px}}@media(max-width:820px){.asset-rows{max-height:none;min-height:0;overflow:visible}.catalog-toolbar{justify-content:stretch}.catalog-toolbar .dc-toolbar{width:100%;flex-wrap:wrap}.catalog-toolbar :deep(.el-input),.catalog-toolbar :deep(.el-select){flex:1;min-width:140px}}@media(max-width:700px){.asset-row{grid-template-columns:1fr;gap:6px}.asset-main{align-items:flex-start;flex-direction:column;gap:5px}.asset-title{flex:1 1 auto}.asset-main code{max-width:100%}.asset-meta{justify-content:space-between}.list-head{align-items:flex-start;flex-direction:column;height:auto;padding:14px 0;gap:5px}}
</style>
