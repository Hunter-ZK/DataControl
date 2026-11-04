<template>
  <div class="dc-page"><div class="dc-container">
    <section class="dc-page-head"><div><h1 class="dc-title">{{config.title}}</h1><p class="dc-subtitle">{{config.desc}}</p></div><div class="dc-toolbar">
    <el-input v-model="keyword" clearable :placeholder="config.placeholder" @keyup.enter="load"/>
    <el-button type="primary" @click="load">查询</el-button>
  </div></section>
    <div class="reference-tabs"><RouterLink v-for="tab in tabs" :key="tab.to" :to="tab.to" :class="{active:tab.kind===kind}">{{tab.label}}</RouterLink></div>
    <section class="dc-card ref-panel"><div class="ref-head"><b>已加载 {{rows.length}} 条资产</b><span>{{config.note}}</span></div><div v-if="rows.length" class="ref-grid"><component :is="target(row)?RouterLink:'article'" v-for="row in pageRows" :key="keyOf(row)" :to="target(row)||undefined" class="ref-card"><div class="ref-kicker"><span>{{statusOf(row)}}</span></div><h3>{{titleOf(row)}}</h3><code class="dc-tech">{{codeOf(row)}}</code><p>{{descOf(row)}}</p><div class="ref-meta" v-if="kind==='metrics'"><span>聚合：{{row.aggregation||'—'}}</span><span>来源：{{row.sourceDatasetId||'—'}}</span></div><div class="ref-meta" v-else-if="kind==='stat-systems'"><span>{{row.issuer||'—'}}</span><span>{{row.documentNo||'—'}}</span></div><div class="ref-meta" v-else-if="kind==='word-roots'"><span>{{row.enFull||'—'}}</span><span>{{row.synonyms||'—'}}</span></div><ArrowUpRight v-if="target(row)" class="ref-arrow" :size="16"/></component></div><div v-else class="dc-empty">暂无匹配资产。</div><Pager v-model:page="page" :page-size="pageSize" :total="rows.length"/></section>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowUpRight } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
import { statusLabel } from '@/utils/labels'
const props=defineProps<{kind:string}>(); const keyword=ref(''); const rows=ref<any[]>([]);const page=ref(1);const pageSize=8
const pageRows=computed(()=>rows.value.slice((page.value-1)*pageSize,page.value*pageSize))
const tabs=computed(()=>['code-tables','data-standards','word-roots'].includes(props.kind)?[
  {kind:'data-standards',label:'数据标准',to:'/standards'},
  {kind:'code-tables',label:'码表',to:'/code-tables'},
  {kind:'word-roots',label:'词根',to:'/word-roots'},
]:[
  {kind:'metrics',label:'指标',to:'/metrics'},
  {kind:'stat-systems',label:'统计制度',to:'/stat-systems'},
])
const configs:any={
  'code-tables':{title:'标准码值',desc:'集中查询业务码表、码值标准及其说明。',placeholder:'搜索码表编号或名称',note:'统一编码与业务取值'},
  'data-standards':{title:'数据标准',desc:'查询字段级数据标准、业务定义和关联码表。',placeholder:'搜索标准编号或名称',note:'统一定义与口径'},
  'word-roots':{title:'词根索引',desc:'查询字段命名词根、英文全称和规范用法。',placeholder:'搜索词根、中文名或同义词',note:'字段命名规范入口'},
  metrics:{title:'指标与制度',desc:'查询指标定义、统计口径、聚合方式与来源数据集。',placeholder:'搜索指标名称或编码',note:'确定性业务口径'},
  'stat-systems':{title:'统计制度',desc:'查询统计制度、版本、发布机构和文号信息。',placeholder:'搜索统计制度',note:'制度依据与版本信息'},
}
const config=computed(()=>configs[props.kind]||configs.metrics)
async function load(){
  page.value=1
  const query=keyword.value.trim()
  const result=await assetApi.reference(`/${props.kind}`,props.kind==='stat-systems'?undefined:(query||undefined)) as any[]
  rows.value=props.kind==='stat-systems'&&query?result.filter(x=>`${x.code} ${x.name} ${x.issuer||''} ${x.version||''}`.toLowerCase().includes(query.toLowerCase())):result
}
function keyOf(r:any){return r.assetId||r.codeTableNo||r.standardNo||r.root||r.metricCode||r.code}
function titleOf(r:any){return r.name||r.cnName||r.metricName||r.codeTableName||r.standardName||r.root||'未命名资产'}
function codeOf(r:any){return r.codeTableNo||r.standardNo||r.root||r.metricCode||r.code||r.assetId||'—'}
function statusOf(r:any){return statusLabel(r.status)}
function descOf(r:any){return r.description||r.definition||r.caliber||r.aliases||'暂无补充说明。'}
function target(r:any){if(props.kind==='code-tables')return `/code-tables/${r.codeTableNo}`;if(props.kind==='data-standards')return `/standards/${r.standardNo}`;if(props.kind==='word-roots')return `/word-roots/${r.root}`;if(props.kind==='metrics')return `/metrics/${r.metricCode}`;if(props.kind==='stat-systems')return `/stat-systems/${r.code}`;return ''}
watch(()=>props.kind,load)
onMounted(load)
</script>
<style scoped>
.dc-toolbar :deep(.el-input){width:280px}.ref-panel{padding:6px 20px 20px}.ref-head{height:54px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #edf2f5}.ref-head span{font-size:12px;color:var(--dc-text-3)}.ref-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding-top:16px}.ref-card{position:relative;padding:18px;border:1px solid var(--dc-border);border-radius:13px;background:#fff;transition:.18s}.ref-card:hover{border-color:#bdddea;box-shadow:0 12px 28px rgba(52,120,155,.07);transform:translateY(-1px)}.ref-kicker{display:flex;justify-content:space-between;align-items:center;color:#8ba0ae;font-size:12px}.ref-card h3{font-size:15px;margin:11px 0 6px}.ref-card code{font-size:12px}.ref-card p{margin:10px 0 0;font-size:12px;line-height:1.65;color:var(--dc-text-2)}.ref-meta{margin-top:13px;padding-top:11px;border-top:1px solid #edf3f6;display:flex;justify-content:space-between;gap:10px;color:#8ba0ad;font-size:12px}.ref-arrow{position:absolute;right:15px;bottom:15px;color:#9ab0bc}@media(max-width:800px){.ref-grid{grid-template-columns:1fr}.dc-toolbar :deep(.el-input){width:100%}}@media(max-width:560px){.ref-panel{padding:6px 14px 14px}.ref-head{align-items:flex-start;flex-direction:column;height:auto;padding:14px 0;gap:5px}}
.reference-tabs{display:flex;align-items:center;gap:6px;margin:0 0 12px;flex-wrap:wrap}.reference-tabs a{padding:8px 13px;border:1px solid var(--dc-border);border-radius:9px;background:#fff;color:var(--dc-text-2);font-size:13px}.reference-tabs a.active,.reference-tabs a:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong);border-color:#c9e5f1}
</style>
