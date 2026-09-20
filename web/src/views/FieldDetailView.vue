<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section v-if="field" class="field-head dc-card"><div><span class="dc-chip">COLUMN</span><h1>{{field.cnName||field.columnName}}</h1><code class="dc-tech">{{field.columnName}}</code><p>所属数据集：<RouterLink :to="`/datasets/${field.datasetId}`">{{field.datasetId}}</RouterLink></p></div><RouterLink class="dataset-link" :to="`/datasets/${field.datasetId}`">查看所属数据集 <ArrowRight :size="16"/></RouterLink></section>
    <div v-if="field" class="field-grid"><section class="dc-card info"><span class="dc-eyebrow">FIELD DEFINITION</span><h2>字段定义</h2><p>{{field.bizDefinition||'暂无业务定义。'}}</p><div class="kv"><div><span>数据类型</span><b>{{field.dataType}}</b></div><div><span>字段序号</span><b>{{field.ordinalNo}}</b></div><div><span>单位</span><b>{{field.unit||'—'}}</b></div><div><span>稳定标识</span><code class="dc-tech">{{field.assetId}}</code></div></div></section><aside class="dc-card side"><span class="dc-eyebrow">STANDARD</span><h3>标准关联</h3><div><span>数据标准</span><b>{{field.standardNo||'未关联'}}</b></div><div><span>码表</span><b>{{field.codeTableNo||'未关联'}}</b></div></aside></div>
    <div v-else class="dc-empty">正在加载字段详情…</div>
  </div></div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight } from 'lucide-vue-next'
import api from '@/api/client'
const route=useRoute(); const router=useRouter(); const field=ref<any|null>(null)
onMounted(async()=>{field.value=await api.get(`/columns/${String(route.params.id)}`)})
</script>
<style scoped>
.field-head{padding:25px 28px;display:flex;justify-content:space-between;gap:20px;align-items:center}.field-head h1{font-size:28px;margin:10px 0 5px}.field-head code{font-size:12px}.field-head p{font-size:11px;color:var(--dc-text-3);margin:7px 0 0}.field-head p a{color:var(--dc-primary-strong)}.dataset-link{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dc-primary-strong);padding:9px 12px;border-radius:9px;background:var(--dc-primary-soft)}.field-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px}.info,.side{padding:22px}.info h2,.side h3{font-size:18px;margin:6px 0 12px}.info>p{font-size:13px;line-height:1.75;color:var(--dc-text-2)}.kv{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.kv div,.side div{padding:14px;border:1px solid var(--dc-border);border-radius:10px}.kv span,.side span{display:block;font-size:10px;color:var(--dc-text-3);margin-bottom:5px}.kv b,.kv code,.side b{font-size:12px}.side{display:grid;gap:10px;align-content:start}@media(max-width:800px){.field-head{align-items:flex-start;flex-direction:column}.field-grid{grid-template-columns:1fr}.kv{grid-template-columns:1fr}}
</style>
