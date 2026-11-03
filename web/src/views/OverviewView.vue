<template>
  <div class="dc-page"><div class="dc-container">
    <div class="overview-title"><b>数据资产概览</b><span>按资产类型、数仓层级和业务目录查看</span></div>
    <section class="stats">
      <RouterLink v-for="item in statItems" :key="item.label" :to="item.to" class="dc-card stat">
        <strong>{{fmt(data[item.key])}}</strong><span>{{item.label}}</span>
      </RouterLink>
    </section>
    <div class="charts">
      <section class="dc-card panel">
        <h2>业务目录分布</h2>
        <RouterLink v-for="item in data.topCatalogs||[]" :key="item.code" to="/catalog" class="catalog-row">
          <span>{{item.name}}</span><div class="bar"><i :style="{width:percent(item.tableCount, catalogMax)+'%'}"/></div>
          <b>{{fmt(item.tableCount)}}</b>
        </RouterLink>
      </section>
      <section class="dc-card panel">
        <h2>数仓分层</h2>
        <div v-for="item in data.layers||[]" :key="item.layerCode" class="layer-row">
          <LayerTag :layer="item.layerCode"/>
          <div class="bar"><i :style="{width:percent(item.tableCount,layerMax)+'%'}"/></div>
          <b>{{fmt(item.tableCount)}}</b>
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
const data=reactive<any>({tableCount:0,columnCount:0,metricCount:0,codeTableCount:0,
  standardCount:0,wordRootCount:0,statSystemCount:0,layers:[],topCatalogs:[]})
const statItems=[
 {key:'tableCount',label:'数据集',to:'/catalog'}, {key:'columnCount',label:'字段',to:'/catalog'},
 {key:'metricCount',label:'指标',to:'/metrics'}, {key:'codeTableCount',label:'码表',to:'/code-tables'},
 {key:'standardCount',label:'数据标准',to:'/standards'},
 {key:'wordRootCount',label:'词根',to:'/word-roots'},
 {key:'statSystemCount',label:'统计制度',to:'/stat-systems'}]
const catalogMax=computed(()=>Math.max(1,...data.topCatalogs.map((x:any)=>Number(x.tableCount||0))))
const layerMax=computed(()=>Math.max(1,...data.layers.map((x:any)=>Number(x.tableCount||0))))
function percent(n:number,max:number){return Math.max(2,Math.round(Number(n||0)/max*100))}
function fmt(n:number){return Number(n||0).toLocaleString()}
onMounted(async()=>{try{Object.assign(data,await assetApi.overview())}catch{}})
</script>
<style scoped>
.overview-title{display:flex;align-items:center;gap:14px;margin-bottom:14px}
.overview-title b{font-size:15px}.overview-title span{font-size:12px;color:var(--dc-text-2)}
.stats{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px}
.stat{padding:14px 10px;min-width:0;display:grid;gap:5px}.stat:hover{border-color:#aad2e5}
.stat strong{font-size:23px;font-variant-numeric:tabular-nums}.stat span{font-size:12px;color:var(--dc-text-2)}
.charts{display:grid;grid-template-columns:1.3fr 1fr;gap:12px;margin-top:14px}
.panel{padding:18px;min-width:0}.panel h2{font-size:15px;margin:0 0 16px}
.catalog-row,.layer-row{display:grid;grid-template-columns:minmax(90px,1fr) minmax(70px,2fr) 58px;align-items:center;gap:12px;min-height:42px;font-size:13px;border-bottom:1px solid #edf2f5}
.catalog-row:last-child,.layer-row:last-child{border:0}.catalog-row b,.layer-row b{font-weight:600;font-variant-numeric:tabular-nums;text-align:right}
.bar{height:8px;background:#edf3f6;border-radius:5px;overflow:hidden}
.bar i{height:100%;display:block;background:#5da5c9;border-radius:5px}
.layer-row{grid-template-columns:60px minmax(70px,1fr) 58px}
@media(max-width:1100px){.stats{grid-template-columns:repeat(4,1fr)}}
@media(max-width:820px){.charts{grid-template-columns:1fr}.stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:480px){.stats{grid-template-columns:repeat(2,1fr)}}
</style>
