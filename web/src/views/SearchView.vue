<template>
  <div class="dc-page">
    <div class="dc-container">
      <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
      <section class="search-head dc-card">
        <span class="dc-eyebrow">ASSET SEARCH</span>
        <h1 class="dc-title">资产检索</h1>
        <p class="dc-subtitle">从数据集、字段、指标与标准资产中快速定位目标。</p>
        <div class="search-box">
          <Search :size="19"/>
          <input v-model="q" @keydown.enter="runSearch" placeholder="搜索业务名称、表名、字段名、指标…" />
          <button @click="runSearch">搜索</button>
        </div>
        <div class="recent"><span>快捷：</span><button v-for="x in ['贷款余额','region_code','企业风险','监管报送']" :key="x" @click="quick(x)">{{x}}</button></div>
      </section>

      <div class="summary"><b>{{ summary }}</b><span>按综合相关度排序</span></div>
      <div class="search-layout">
        <aside class="facets dc-card">
          <div class="facet-title">结果范围</div>
          <button v-for="item in types" :key="item.key" :class="{active:type===item.key}" @click="type=item.key">
            <span>{{item.label}}</span><b>{{count(item.key)}}</b>
          </button>
          <div class="sep" />
          <div class="facet-title">快捷入口</div>
          <RouterLink to="/catalog">资产目录</RouterLink>
          <RouterLink to="/code-tables">标准码值</RouterLink>
          <RouterLink to="/word-roots">词根索引</RouterLink>
        </aside>

        <section class="results dc-card">
          <div v-if="loading" class="dc-empty">正在检索资产索引…</div>
          <div v-else-if="filtered.length===0" class="dc-empty">没有找到匹配资产，试试更短的业务词或技术名称。</div>
          <article v-for="item in filtered" :key="item.asset_id" class="result-card" @click="open(item)">
            <div class="result-main">
              <div class="kicker"><span class="dc-chip">{{label(item.asset_type)}}</span><span>统一资产索引</span></div>
              <h3 v-html="item.title_hl || item.title" />
              <code class="dc-tech">{{item.technical_name}}</code>
              <p v-html="item.body_hl || '点击查看资产定义、字段、口径及相关信息。'" />
            </div>
            <div class="score"><small>相关度</small><b>{{Number(item.score || 0).toFixed(2)}}</b><ArrowRight :size="18"/></div>
          </article>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const route=useRoute(); const router=useRouter(); const q=ref(String(route.query.q||'')); const type=ref('ALL'); const rows=ref<any[]>([]); const loading=ref(false)
const types=[{key:'ALL',label:'全部'},{key:'TABLE',label:'数据集'},{key:'COLUMN',label:'字段'},{key:'METRIC',label:'指标'},{key:'CODE_TABLE',label:'码表'}]
const filtered=computed(()=>type.value==='ALL'?rows.value:rows.value.filter(x=>x.asset_type===type.value))
const summary=computed(()=>q.value?`“${q.value}” · ${filtered.value.length} 条结果`:'请输入关键词开始检索')
function count(k:string){ return k==='ALL'?rows.value.length:rows.value.filter(x=>x.asset_type===k).length }
function label(v:string){ return ({TABLE:'数据集',COLUMN:'字段',METRIC:'指标',CODE_TABLE:'码表'} as Record<string,string>)[v]||v }
async function runSearch(){ const value=q.value.trim(); if(!value)return; loading.value=true; try{rows.value=await assetApi.search(value) as any[]; await activityApi.recordSearch(value); await router.replace({query:{...route.query,q:value}})}finally{loading.value=false} }
function quick(v:string){q.value=v;runSearch()}
function open(item:any){ if(item.asset_type==='TABLE') router.push(`/datasets/${item.asset_id}`); else if(item.asset_type==='CODE_TABLE') router.push('/code-tables'); else if(item.asset_type==='METRIC') router.push('/metrics') }
watch(()=>route.query.q,(v)=>{if(typeof v==='string'&&v!==q.value){q.value=v;runSearch()}})
onMounted(()=>{if(q.value)runSearch()})
</script>

<style scoped>
.search-head{padding:26px 28px}.search-box{margin-top:20px;height:54px;display:flex;align-items:center;gap:10px;padding:5px 5px 5px 16px;border:1px solid #cfe3ee;border-radius:13px;background:#fbfdff;color:#72a0b7}.search-box input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text)}.search-box button{height:42px;border:0;border-radius:9px;padding:0 22px;color:white;background:linear-gradient(135deg,var(--dc-primary),var(--dc-accent));cursor:pointer}.recent{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:11px;color:var(--dc-text-3);font-size:12px}.recent button{border:1px solid #dceaf2;background:#fff;border-radius:999px;padding:5px 10px;color:#4d809b;cursor:pointer}.summary{display:flex;gap:12px;align-items:center;margin:18px 2px 12px}.summary span{font-size:11px;color:var(--dc-text-3)}.search-layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:16px;align-items:start}.facets{padding:14px;position:sticky;top:86px;display:grid;gap:4px}.facet-title{padding:5px 8px 7px;font-size:11px;font-weight:700;color:#7b92a1}.facets button{border:0;background:transparent;padding:9px 10px;display:flex;justify-content:space-between;border-radius:8px;color:#5f798a;cursor:pointer}.facets button.active,.facets button:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.facets button b{font-size:11px}.facets a{padding:8px 10px;font-size:12px;color:#5f798a}.sep{height:1px;background:#edf3f6;margin:9px 4px}.results{min-width:0;padding:4px 20px 12px}.result-card{display:grid;grid-template-columns:minmax(0,1fr) 76px;gap:20px;padding:20px 4px;border-bottom:1px solid #edf2f5;cursor:pointer}.result-card:last-child{border-bottom:0}.result-main{min-width:0}.kicker{display:flex;align-items:center;gap:8px;font-size:10px;color:#8da0ac}.result-card h3{font-size:17px;margin:8px 0 5px;color:#234a60}.result-card code{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px}.result-card p{margin:9px 0 0;font-size:12px;line-height:1.65;color:#6f8493;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.result-card :deep(mark){background:#e2f6ff;color:#1f6686}.score{display:flex;flex-direction:column;align-items:flex-end;justify-content:center;color:#82a0af}.score small{font-size:9px}.score b{font-size:12px;color:#347d9d;margin:3px 0}@media(max-width:980px){.search-layout{grid-template-columns:1fr}.facets{position:static;display:flex;flex-wrap:wrap}.facet-title,.sep{display:none}.facets button,.facets a{width:auto}}@media(max-width:620px){.search-head{padding:21px 18px}.result-card{grid-template-columns:1fr}.score{display:none}.results{padding:3px 14px 10px}.summary{align-items:flex-start;flex-direction:column;gap:4px}}
</style>
