<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section v-if="data" class="head dc-card"><div><span class="dc-chip">CODE TABLE</span><h1>{{data.name}}</h1><code class="dc-tech">{{data.codeTableNo}}</code><p>{{data.description||'暂无说明。'}}</p></div><span class="status">{{data.status}}</span></section>
    <section v-if="data" class="dc-card values"><div class="value-head"><div><span class="dc-eyebrow">CODE VALUES</span><h2>码值列表</h2></div><el-input v-model="keyword" clearable placeholder="搜索码值或名称"/></div><div class="dc-table-wrap"><table class="dc-table"><thead><tr><th>码值</th><th>名称</th><th>说明</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.value"><td><code class="dc-tech">{{row.value}}</code></td><td>{{row.name}}</td><td>{{row.description||'—'}}</td></tr></tbody></table></div></section>
    <div v-else class="dc-empty">正在加载码表详情…</div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import api from '@/api/client'
const route=useRoute();const router=useRouter();const data=ref<any|null>(null);const keyword=ref('')
const filtered=computed(()=>{const k=keyword.value.trim().toLowerCase();return !k?(data.value?.values||[]):(data.value?.values||[]).filter((x:any)=>`${x.value} ${x.name} ${x.description||''}`.toLowerCase().includes(k))})
onMounted(async()=>{data.value=await api.get(`/code-tables/${String(route.params.no)}`)})
</script>
<style scoped>
.head{padding:25px 28px;display:flex;justify-content:space-between;gap:20px;align-items:center}.head h1{font-size:28px;margin:10px 0 5px}.head code{font-size:12px}.head p{margin:8px 0 0;color:var(--dc-text-2);font-size:12px}.status{padding:6px 10px;border-radius:999px;background:#edf8f3;color:#2f8b6c;font-size:11px;font-weight:700}.values{padding:20px;margin-top:16px}.value-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}.value-head h2{font-size:18px;margin:5px 0 0}.value-head :deep(.el-input){width:260px}@media(max-width:620px){.head,.value-head{align-items:flex-start;flex-direction:column}.value-head :deep(.el-input){width:100%}}
</style>
