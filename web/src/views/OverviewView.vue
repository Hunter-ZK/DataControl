<template>
  <div class="dc-page"><div class="dc-container">
    <section class="dc-page-head"><div><span class="dc-eyebrow">DATA OVERVIEW</span><h1 class="dc-title">数据资产概览</h1><p class="dc-subtitle">从资产规模、数仓分层和业务目录查看整体数据资产情况。</p></div></section>
    <section class="dc-grid-4"><article class="dc-card dc-stat"><small>数据集</small><strong>{{fmt(data.tableCount)}}</strong><span>已登记资产表</span></article><article class="dc-card dc-stat"><small>字段</small><strong>{{fmt(data.columnCount)}}</strong><span>字段级元数据</span></article><article class="dc-card dc-stat"><small>业务指标</small><strong>{{fmt(data.metricCount)}}</strong><span>已定义指标口径</span></article><article class="dc-card dc-stat"><small>标准码表</small><strong>{{fmt(data.codeTableCount)}}</strong><span>统一标准与码值</span></article></section>
    <div class="overview-grid">
      <section class="dc-card panel"><div class="panel-head"><div><span class="dc-eyebrow">BUSINESS CATALOG</span><h2>业务目录分布</h2></div><RouterLink to="/catalog">进入资产目录</RouterLink></div><div class="catalog-grid"><article v-for="c in data.topCatalogs||[]" :key="c.code"><div><b>{{c.name}}</b><code>{{c.code}}</code></div><strong>{{c.tableCount}}</strong></article></div></section>
      <section class="dc-card panel"><span class="dc-eyebrow">WAREHOUSE LAYERS</span><h2>数仓分层</h2><div class="layers"><div v-for="x in data.layers||[]" :key="x.layerCode"><span><b>{{x.layerCode}}</b><em>{{x.tableCount}} 个数据集</em></span><div class="bar"><i :style="{width:bar(x.tableCount)}"/></div></div></div></section>
    </div>
    <section class="dc-card standards"><span class="dc-eyebrow">REFERENCE ASSETS</span><h2>标准资产规模</h2><div class="reference-stats"><RouterLink to="/standards"><strong>{{fmt(data.standardCount)}}</strong><span>数据标准</span></RouterLink><RouterLink to="/word-roots"><strong>{{fmt(data.wordRootCount)}}</strong><span>词根</span></RouterLink><RouterLink to="/stat-systems"><strong>{{fmt(data.statSystemCount)}}</strong><span>统计制度</span></RouterLink></div></section>
  </div></div>
</template>
<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { assetApi } from '@/api/client'
const data=reactive<any>({tableCount:0,columnCount:0,metricCount:0,codeTableCount:0,standardCount:0,wordRootCount:0,statSystemCount:0,layers:[],topCatalogs:[]})
function fmt(v:number){return Number(v||0).toLocaleString()}
function bar(v:number){const max=Math.max(...(data.layers||[]).map((x:any)=>Number(x.tableCount||0)),1);return `${Math.max(8,Math.round(Number(v||0)/max*100))}%`}
onMounted(async()=>Object.assign(data,await assetApi.overview()))
</script>
<style scoped>
.overview-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,.8fr);gap:16px;margin-top:16px}.panel,.standards{padding:22px}.panel-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:16px}.panel h2,.standards h2{font-size:18px;margin:5px 0 0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.catalog-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.catalog-grid article{padding:15px;border:1px solid var(--dc-border);border-radius:11px;display:flex;justify-content:space-between;align-items:center}.catalog-grid article div{display:grid;gap:4px}.catalog-grid b{font-size:13px}.catalog-grid code{font-size:9px;color:var(--dc-text-3)}.catalog-grid strong{font-size:22px;color:#2c7294}.layers{margin-top:14px;display:grid;gap:14px}.layers span{display:flex;justify-content:space-between;align-items:center}.layers b{font-size:12px}.layers em{font-size:10px;color:var(--dc-text-3);font-style:normal}.bar{height:7px;background:#edf4f7;border-radius:999px;overflow:hidden;margin-top:7px}.bar i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#74c7dc,#49a3cd)}.standards{margin-top:16px}.reference-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}.reference-stats a{padding:16px;border:1px solid var(--dc-border);border-radius:11px;background:#fbfdff}.reference-stats strong{display:block;font-size:23px;color:#2b7091}.reference-stats span{font-size:11px;color:var(--dc-text-2)}@media(max-width:980px){.overview-grid{grid-template-columns:1fr}}@media(max-width:650px){.catalog-grid,.reference-stats{grid-template-columns:1fr}}
</style>
