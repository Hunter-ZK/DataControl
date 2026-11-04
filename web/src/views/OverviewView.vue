<template>
  <div class="dc-page"><div class="dc-container">
    <section class="dc-grid-7">
      <RouterLink v-for="item in statItems" :key="item.label" :to="item.to" class="dc-card dc-stat">
        <small>{{item.label}}</small><strong>{{fmt(data[item.key])}}</strong>
      </RouterLink>
    </section>
    <div class="overview-grid">
      <section class="dc-card panel">
        <div class="panel-head"><h2>业务目录分布</h2><RouterLink to="/catalog">进入资产目录</RouterLink></div>
        <div class="catalog-grid">
          <article v-for="c in topCatalogs" :key="c.code"><div><b>{{c.name}}</b><code>{{c.code}}</code></div><strong>{{c.tableCount}}</strong></article>
        </div>
      </section>
      <section class="dc-card panel">
        <h2>数仓分层</h2>
        <div class="layers">
          <div v-for="x in data.layers||[]" :key="x.layerCode">
            <span><LayerTag :layer="x.layerCode" /><em>{{x.tableCount}} 个数据集</em></span>
            <div class="bar"><i :style="{width:bar(x.tableCount)}"/></div>
          </div>
        </div>
      </section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { assetApi } from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'

const data = reactive<any>({ tableCount: 0, columnCount: 0, metricCount: 0, codeTableCount: 0, standardCount: 0, wordRootCount: 0, statSystemCount: 0, layers: [], topCatalogs: [] })
const statItems = [
  { key: 'tableCount', label: '数据集', to: '/catalog' },
  { key: 'columnCount', label: '字段', to: '/catalog' },
  { key: 'metricCount', label: '指标', to: '/metrics' },
  { key: 'codeTableCount', label: '码表', to: '/code-tables' },
  { key: 'standardCount', label: '数据标准', to: '/standards' },
  { key: 'wordRootCount', label: '词根', to: '/word-roots' },
  { key: 'statSystemCount', label: '统计制度', to: '/stat-systems' },
]
const topCatalogs = computed(() => (data.topCatalogs || []).slice(0, 8))
function fmt(value: number) { return Number(value || 0).toLocaleString() }
function bar(value: number) {
  const max = Math.max(...(data.layers || []).map((item: any) => Number(item.tableCount || 0)), 1)
  return `${Math.max(8, Math.round(Number(value || 0) / max * 100))}%`
}
onMounted(async () => Object.assign(data, await assetApi.overview()))
</script>
<style scoped>
.dc-grid-7{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:12px}.dc-stat{padding:16px 14px;min-width:0}.dc-stat small{color:var(--dc-text-2);font-size:12px}.dc-stat strong{display:block;font-size:25px;margin:8px 0 2px;color:#245d7c;font-variant-numeric:tabular-nums}.overview-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,.8fr);gap:16px;margin-top:16px}.panel{padding:22px}.panel-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:16px}.panel h2{font-size:18px;margin:5px 0 0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.catalog-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.catalog-grid article{padding:15px;border:1px solid var(--dc-border);border-radius:11px;display:flex;justify-content:space-between;align-items:center}.catalog-grid article div{display:grid;gap:4px}.catalog-grid b{font-size:13px}.catalog-grid code{font-size:11px;color:var(--dc-text-2)}.catalog-grid strong{font-size:22px;color:#2c7294;font-variant-numeric:tabular-nums}.layers{margin-top:14px;display:grid;gap:14px}.layers span{display:flex;justify-content:space-between;align-items:center}.layers em{font-size:12px;color:var(--dc-text-2);font-style:normal}.bar{height:7px;background:#edf4f7;border-radius:999px;overflow:hidden;margin-top:7px}.bar i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#74c7dc,#49a3cd)}@media(max-width:1200px){.dc-grid-7{grid-template-columns:repeat(4,minmax(0,1fr))}}@media(max-width:980px){.overview-grid{grid-template-columns:1fr}}@media(max-width:650px){.dc-grid-7{grid-template-columns:repeat(2,minmax(0,1fr))}.catalog-grid{grid-template-columns:1fr}}
</style>
