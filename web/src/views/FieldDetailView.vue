<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="goBack"><ArrowLeft :size="16"/>返回</button>
    <section v-if="field" class="field-head dc-card"><div><span class="dc-chip">COLUMN</span><h1>{{field.cnName||field.columnName}}</h1><code class="dc-tech">{{field.columnName}}</code><p>所属数据集：<RouterLink :to="`/datasets/${field.datasetId}`">{{field.datasetId}}</RouterLink></p></div><div class="head-actions"><RouterLink class="dataset-link"  :to="{name:'dataset',params:{id:field.datasetId},query:{tab:'columns'}}">返回数据集字段列表 <ArrowRight :size="16"/></RouterLink><RouterLink class="lineage-link" :to="{name:'relations',query:{mode:'field',field:field.assetId}}"><GitFork :size="16"/>查看字段血缘</RouterLink></div></section>
    <div v-if="field" class="field-grid"><section class="dc-card info"><h2>字段定义</h2><p>{{field.bizDefinition||'暂无业务定义。'}}</p><div class="kv"><div><span>数据类型</span><b>{{field.dataType}}</b></div><div><span>字段序号</span><b>{{field.ordinalNo}}</b></div><div><span>单位</span><b>{{field.unit||'—'}}</b></div><div><span>稳定标识</span><code class="dc-tech">{{field.assetId}}</code></div></div><div class="lineage-callout"><GitFork :size="18"/><div><b>字段级血缘已接入</b><p>可查看该字段的上游来源、下游去向、转换表达式、任务名和关系证据。</p></div><RouterLink :to="{name:'relations',query:{mode:'field',field:field.assetId}}">打开图谱</RouterLink></div></section><aside class="dc-card side"><h3>标准关联</h3><div><span>数据标准</span><RouterLink v-if="field.standardNo" :to="{name:'standard',params:{no:field.standardNo}}">{{field.standardNo}}</RouterLink><b v-else>未关联</b></div><div><span>码表</span><RouterLink v-if="field.codeTableNo" :to="{name:'codeTable',params:{no:field.codeTableNo}}">{{field.codeTableNo}}</RouterLink><b v-else>未关联</b></div></aside></div>
    <div v-else-if="loadError" class="dc-empty" role="alert">{{ loadError }} <button class="retry-button" @click="loadField">重试</button></div>
     <div v-else class="dc-empty">正在加载字段详情…</div>
  </div></div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, GitFork } from 'lucide-vue-next'
import api from '@/api/client'
const route=useRoute();const router=useRouter();const field=ref<any|null>(null);const loadError=ref('')
function goBack(){
  const previous=window.history.state?.back
  if(typeof previous==='string'&&previous.startsWith('/')&&previous!==route.fullPath){router.back();return}
  if(field.value?.datasetId){router.push({name:'dataset',params:{id:field.value.datasetId},query:{tab:'columns'}});return}
  router.push({name:'catalog'})
}
async function loadField(){
  field.value=null;loadError.value=''
  try{field.value=await api.get(`/columns/${String(route.params.id)}`)}
  catch{loadError.value='字段详情加载失败，请检查服务或重试。'}
}
watch(()=>route.params.id,()=>{void loadField()},{immediate:true})
</script>
<style scoped>
.field-head{padding:25px 28px;display:flex;justify-content:space-between;gap:20px;align-items:center}.field-head h1{font-size:28px;margin:10px 0 5px}.field-head code{font-size:12px}.field-head p{font-size:11px;color:var(--dc-text-3);margin:7px 0 0}.field-head p a{color:var(--dc-primary-strong)}.head-actions{display:flex;gap:8px;flex-wrap:wrap}.dataset-link,.lineage-link{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dc-primary-strong);padding:9px 12px;border-radius:9px;background:var(--dc-primary-soft)}.lineage-link{background:#e7f5f2;color:#176c61}.field-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px}.info,.side{padding:22px}.info h2,.side h3{font-size:18px;margin:6px 0 12px}.info>p{font-size:13px;line-height:1.75;color:var(--dc-text-2)}.kv{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.kv div,.side div{padding:14px;border:1px solid var(--dc-border);border-radius:10px}.kv span,.side span{display:block;font-size:10px;color:var(--dc-text-3);margin-bottom:5px}.kv b,.kv code,.side b{font-size:12px}.side{display:grid;gap:10px;align-content:start}
.side a{font-size:12px;color:#5d47df;font-weight:750}
.retry-button{margin-left:8px;border:1px solid #d7d1ff;background:#f5f2ff;color:#5d47df;border-radius:8px;padding:7px 12px;cursor:pointer}.lineage-callout{margin-top:16px;padding:13px 14px;border:1px solid #cde5e0;border-radius:11px;background:#f2faf8;display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:center;color:#2d7167}.lineage-callout b{font-size:12px}.lineage-callout p{font-size:10px;color:#5f817b;margin:4px 0 0}.lineage-callout a{font-size:10px;color:#176c61;font-weight:700}@media(max-width:800px){.field-head{align-items:flex-start;flex-direction:column}.field-grid{grid-template-columns:1fr}.kv{grid-template-columns:1fr}.lineage-callout{grid-template-columns:auto 1fr}.lineage-callout a{grid-column:2}}
</style>
