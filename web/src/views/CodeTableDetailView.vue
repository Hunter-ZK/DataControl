<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section v-if="data" class="head dc-card"><div><span class="dc-chip">CODE TABLE</span><h1>{{data.name}}</h1><code class="dc-tech">{{data.codeTableNo}}</code><p>{{data.description||'暂无说明。'}}</p></div><div class="head-actions"><span class="status">{{data.status}}</span><AssetOperationBar kind="CODE_TABLE" :asset="data"/></div></section>
    <section v-if="data" class="dc-card values"><div class="value-head"><div><span class="dc-eyebrow">CODE VALUES</span><h2>码值列表</h2></div><el-input v-model="keyword" clearable placeholder="搜索码值或名称"/></div><div class="dc-table-wrap"><table class="dc-table"><thead><tr><th>码值</th><th>名称</th><th>说明</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.value"><td><code class="dc-tech">{{row.value}}</code></td><td>{{row.name}}</td><td>{{row.description||'—'}}</td></tr></tbody></table></div></section>
    <AssetReferencePanel v-if="data" kind="CODE_TABLE" :asset-id="data.assetId" title="引用该码表的字段"/>
    <div v-else class="dc-empty">正在加载码表详情…</div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import api from '@/api/client'
import AssetOperationBar from '@/components/AssetOperationBar.vue'
import AssetReferencePanel from '@/components/AssetReferencePanel.vue'
const route=useRoute();const router=useRouter();const data=ref<any|null>(null);const keyword=ref('')
const filtered=computed(()=>{const k=keyword.value.trim().toLowerCase();return !k?(data.value?.values||[]):(data.value?.values||[]).filter((x:any)=>`${x.value} ${x.name} ${x.description||''}`.toLowerCase().includes(k))})
watch(()=>route.params.no,async(value)=>{const no=String(value);data.value=null;keyword.value='';const result=await api.get(`/code-tables/${no}`);if(String(route.params.no)===no)data.value=result},{immediate:true})
</script>
<style scoped>
.head{padding:25px 28px;display:flex;justify-content:space-between;gap:20px;align-items:center}.head h1{font-size:28px;margin:10px 0 5px}.head code{font-size:12px}.head p{margin:8px 0 0;color:var(--dc-text-2);font-size:12px}.status{padding:6px 10px;border-radius:999px;background:#edf8f3;color:#2f8b6c;font-size:11px;font-weight:700}.values{padding:20px;margin-top:16px}.value-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}.value-head h2{font-size:18px;margin:5px 0 0}.value-head :deep(.el-input){width:260px}@media(max-width:620px){.head,.value-head{align-items:flex-start;flex-direction:column}.value-head :deep(.el-input){width:100%}}

.head{border-color:#c8ddf7;border-radius:15px;background:linear-gradient(110deg,#fff,#f2f8ff);box-shadow:var(--dc-shadow-md);padding:29px}.head h1{color:#1b3d6b;font-size:29px}.head code{font-size:13px}.head p{font-size:14px;line-height:1.8}.status{font-size:13px}.values{padding:25px;border-color:#d5e3f6;border-radius:14px}.value-head h2{font-size:21px;color:#234875}.value-head :deep(.el-input){width:315px}.dc-table th,.dc-table td{font-size:14px}@media(max-width:620px){.head{padding:19px}.head h1{font-size:23px}.value-head :deep(.el-input){width:100%}}

.head-actions,.reference-actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:10px;min-width:0}.reference-actions .status,.head-actions .status{white-space:nowrap}@media(max-width:760px){.head-actions,.reference-actions{width:100%;justify-content:flex-start}}
</style>
