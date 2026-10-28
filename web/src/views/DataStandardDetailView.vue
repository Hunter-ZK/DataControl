<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section v-if="data" class="standard-head dc-card"><div><span class="dc-chip">DATA STANDARD</span><h1>{{data.name}}</h1><code class="dc-tech">{{data.standardNo}}</code><p>{{data.definition||'暂无业务定义。'}}</p></div><span class="status">{{data.status}}</span></section>
    <div v-if="data" class="standard-grid"><section class="dc-card panel"><span class="dc-eyebrow">DEFINITION</span><h2>标准定义</h2><p>{{data.definition||'暂无业务定义。'}}</p><div class="info-grid"><div><span>标准编号</span><code class="dc-tech">{{data.standardNo}}</code></div><div><span>关联码表</span><RouterLink v-if="data.codeTableNo" :to="`/code-tables/${data.codeTableNo}`">{{data.codeTableNo}}</RouterLink><b v-else>—</b></div><div><span>稳定标识</span><code class="dc-tech">{{data.assetId}}</code></div><div><span>状态</span><b>{{data.status}}</b></div></div></section><aside class="dc-card panel"><span class="dc-eyebrow">GUIDANCE</span><h3>使用建议</h3><p>字段设计和开发命名时优先复用已发布标准；如有关联码表，应同步遵循对应码值范围。</p></aside></div>
    <div v-else-if="loading" class="dc-empty">正在加载数据标准…</div><div v-else class="dc-empty">未找到该数据标准。</div>
  </div></div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
const route=useRoute();const router=useRouter();const data=ref<any|null>(null);const loading=ref(true)
watch(()=>route.params.no,async(value)=>{const no=String(value);data.value=null;loading.value=true;try{const rows=await assetApi.reference('/data-standards',no) as any[];if(String(route.params.no)===no)data.value=rows.find(x=>x.standardNo===no)||null}finally{if(String(route.params.no)===no)loading.value=false}},{immediate:true})
</script>
<style scoped>
.standard-head{padding:25px 28px;display:flex;justify-content:space-between;align-items:center;gap:20px}.standard-head h1{font-size:28px;margin:10px 0 5px}.standard-head code{font-size:12px}.standard-head p{max-width:760px;color:var(--dc-text-2);font-size:12px;line-height:1.7}.status{padding:6px 10px;border-radius:999px;background:#edf8f3;color:#2f8b6c;font-size:11px;font-weight:700}.standard-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px}.panel{padding:22px}.panel h2,.panel h3{font-size:18px;margin:6px 0 12px}.panel>p{font-size:12px;line-height:1.75;color:var(--dc-text-2)}.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.info-grid>div{padding:14px;border:1px solid var(--dc-border);border-radius:10px}.info-grid span{display:block;font-size:10px;color:var(--dc-text-3);margin-bottom:5px}.info-grid a{color:var(--dc-primary-strong);font-size:12px}@media(max-width:800px){.standard-head{align-items:flex-start;flex-direction:column}.standard-grid{grid-template-columns:1fr}.info-grid{grid-template-columns:1fr}}

.standard-head{padding:29px;border-color:#c8dcf8;border-radius:15px;background:linear-gradient(110deg,#fff,#f3f8ff);box-shadow:var(--dc-shadow-md)}.standard-head h1{font-size:29px;color:#1b3d6b}.standard-head p,.panel>p{font-size:14px}.panel{padding:25px;border-color:#d3e2f7;border-radius:13px}.panel h2,.panel h3{font-size:19px;color:#24476f}.info-grid>div{background:#f7fbff;border-color:#d8e5f7}.info-grid span{font-size:13px}.info-grid a{font-size:14px}@media(max-width:620px){.standard-head{padding:20px}.standard-head h1{font-size:23px}}
</style>
