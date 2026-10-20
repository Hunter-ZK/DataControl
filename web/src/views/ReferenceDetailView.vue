<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section v-if="data" class="detail-head dc-card">
      <div><span class="dc-chip">{{config.badge}}</span><h1>{{titleOf(data)}}</h1><code class="dc-tech">{{codeOf(data)}}</code><p>{{descriptionOf(data)}}</p></div>
      <span class="status">{{data.status||data.version||'VALID'}}</span>
    </section>
    <div v-if="data" class="detail-grid">
      <section class="dc-card panel">
        <span class="dc-eyebrow">DEFINITION</span><h2>{{config.sectionTitle}}</h2><p>{{descriptionOf(data)}}</p>
        <div class="kv-grid">
          <template v-if="kind==='word-roots'">
            <div><span>英文词根</span><code class="dc-tech">{{data.root}}</code></div><div><span>英文全称</span><b>{{data.enFull||'—'}}</b></div><div><span>中文名称</span><b>{{data.cnName||'—'}}</b></div><div><span>同义词</span><b>{{data.synonyms||'—'}}</b></div>
          </template>
          <template v-else-if="kind==='metrics'">
            <div><span>指标编码</span><code class="dc-tech">{{data.metricCode}}</code></div><div><span>聚合方式</span><b>{{data.aggregation||'—'}}</b></div><div><span>度量字段</span><code class="dc-tech">{{data.measureColumn||'—'}}</code></div><div><span>时间字段</span><code class="dc-tech">{{data.timeField||'—'}}</code></div><div><span>来源数据集</span><RouterLink v-if="data.sourceDatasetId" :to="`/datasets/${data.sourceDatasetId}`">{{data.sourceDatasetId}}</RouterLink><b v-else>—</b></div><div><span>时间可加性</span><b>{{data.timeAdditivity||'—'}}</b></div>
          </template>
          <template v-else>
            <div><span>制度编码</span><code class="dc-tech">{{data.code}}</code></div><div><span>版本</span><b>{{data.version||'—'}}</b></div><div><span>发布机构</span><b>{{data.issuer||'—'}}</b></div><div><span>文号</span><b>{{data.documentNo||'—'}}</b></div>
          </template>
        </div>
      </section>
      <aside class="dc-card panel side"><span class="dc-eyebrow">IDENTITY</span><h3>资产身份</h3><div><span>稳定标识</span><code class="dc-tech">{{data.assetId||'—'}}</code></div><div><span>状态</span><b>{{data.status||'VALID'}}</b></div></aside>
    </div>
    <div v-else-if="loading" class="dc-empty">正在加载资产详情…</div><div v-else class="dc-empty">未找到该资产。</div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
const props=defineProps<{kind:string}>();const route=useRoute();const router=useRouter();const data=ref<any|null>(null);const loading=ref(true)
const configs:any={
  'word-roots':{badge:'WORD ROOT',sectionTitle:'词根定义'},
  metrics:{badge:'METRIC',sectionTitle:'指标定义与统计口径'},
  'stat-systems':{badge:'STAT SYSTEM',sectionTitle:'统计制度信息'},
}
const config=computed(()=>configs[props.kind]||configs.metrics)
function identifier(){return String(route.params.id||route.params.root||route.params.code||'')}
function titleOf(r:any){return r.name||r.cnName||r.metricName||r.root||r.code||'未命名资产'}
function codeOf(r:any){return r.metricCode||r.root||r.code||r.assetId||'—'}
function descriptionOf(r:any){return r.caliber||r.description||r.definition||r.aliases||'暂无补充说明。'}
async function load(){loading.value=true;try{const id=identifier();const rows=await assetApi.reference(`/${props.kind}`,id) as any[];data.value=rows.find((x:any)=>codeOf(x)===id)||rows[0]||null}finally{loading.value=false}}
watch(()=>[props.kind,route.fullPath],load)
onMounted(load)
</script>
<style scoped>
.detail-head{padding:25px 28px;display:flex;justify-content:space-between;align-items:center;gap:20px}.detail-head h1{font-size:28px;margin:10px 0 5px}.detail-head code{font-size:12px}.detail-head p{max-width:760px;color:var(--dc-text-2);font-size:12px;line-height:1.7}.status{padding:6px 10px;border-radius:999px;background:#edf8f3;color:#2f8b6c;font-size:11px;font-weight:700}.detail-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px}.panel{padding:22px}.panel h2,.panel h3{font-size:18px;margin:6px 0 12px}.panel>p{font-size:12px;line-height:1.75;color:var(--dc-text-2)}.kv-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.kv-grid>div,.side>div{padding:14px;border:1px solid var(--dc-border);border-radius:10px}.kv-grid span,.side span{display:block;font-size:10px;color:var(--dc-text-3);margin-bottom:5px}.kv-grid a{font-size:12px;color:var(--dc-primary-strong)}.side{display:grid;gap:10px;align-content:start}@media(max-width:800px){.detail-head{align-items:flex-start;flex-direction:column}.detail-grid{grid-template-columns:1fr}.kv-grid{grid-template-columns:1fr}}
</style>
