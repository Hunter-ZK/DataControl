<template>
  <div class="dc-page compact-page">
    <div class="dc-container page-inner">
      <div class="search-toolbar">
        <div><span v-if="q">“{{q}}” · 共 {{total.toLocaleString()}} 条结果</span><span v-else>输入关键词开始检索</span></div>
        <span class="hint">在顶部搜索框可修改关键词 · Ctrl/⌘ K</span>
      </div>
      <section class="dc-card search-panel">
        <div class="facets" role="tablist" aria-label="资产类型">
          <button v-for="option in types" :key="option.key" role="tab"
            :aria-selected="type===option.key" :class="{active:type===option.key}"
            @click="selectType(option.key)">{{option.label}} <span>{{count(option.key)}}</span></button>
        </div>
        <div ref="resultContainer" class="results">
          <div v-if="!q" class="dc-empty">使用顶部搜索框或返回首页输入关键词。</div>
          <div v-else-if="loading" class="dc-empty">正在搜索…</div>
          <div v-else-if="!rows.length" class="dc-empty">没有找到匹配资产，请尝试更短的业务词或技术标识。</div>
          <RouterLink v-for="item in rows" v-else :key="item.asset_id" :to="target(item)" class="result">
            <div class="result-head">
              <span class="type">{{typeLabel(item.asset_type)}}</span>
              <b>{{item.title}}</b><code class="dc-tech">{{item.technical_name}}</code>
              <ArrowUpRight :size="15" class="arrow"/>
            </div>
            <p>{{item.excerpt||'点击查看资产定义与关联信息'}}</p>
          </RouterLink>
        </div>
        <Pager :page="page" :page-size="pageSize" :total="total" @update:page="page=$event"/>
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ArrowUpRight } from 'lucide-vue-next'
import { assetApi, activityApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
import { typeLabel } from '@/utils/labels'
const route=useRoute()
const q=ref(String(route.query.q||'')),type=ref('ALL'),rows=ref<any[]>([]),
  facets=ref<Record<string,number>>({}),total=ref(0),loading=ref(false),page=ref(1)
const types=[{key:'ALL',label:'全部'},{key:'TABLE',label:'数据集'},{key:'COLUMN',label:'字段'},
 {key:'METRIC',label:'指标'},{key:'CODE_TABLE',label:'码表'}]
const resultContainer=ref<HTMLElement|null>(null)
const pageSize=useFitPageSize(resultContainer,66,4)
function count(k:string){return k==='ALL'?Object.values(facets.value).reduce((a,b)=>a+b,0):facets.value[k]||0}
function selectType(k:string){type.value=k;page.value=1;load()}
function target(item:any){
  const value=encodeURIComponent(item.asset_type==='TABLE'||item.asset_type==='COLUMN'?item.asset_id:item.technical_name)
  if(item.asset_type==='TABLE')return '/datasets/'+value
  if(item.asset_type==='COLUMN')return '/fields/'+value
  if(item.asset_type==='METRIC')return '/metrics/'+value
  if(item.asset_type==='CODE_TABLE')return '/code-tables/'+value
  return '/search?q='+encodeURIComponent(q.value)
}
let seq=0
async function load(){
  const i=++seq;if(!q.value.trim()){rows.value=[];total.value=0;facets.value={};return}
  loading.value=true
  try{
    const result=await assetApi.searchPage({q:q.value,asset_type:type.value,offset:(page.value-1)*pageSize.value,limit:pageSize.value})
    if(i===seq){rows.value=result.items;total.value=result.total;facets.value=result.facets}
  }catch{if(i===seq){rows.value=[];total.value=0;facets.value={}}}
  finally{if(i===seq)loading.value=false}
}
watch(()=>route.query.q,(value)=>{const next=typeof value==='string'?value:'';if(next!==q.value){q.value=next;page.value=1;type.value='ALL';load();if(next)activityApi.recordSearch(next).catch(()=>{})}})
watch(page,load)
watch(pageSize,()=>{page.value=1;load()})
onMounted(()=>{load();if(q.value)activityApi.recordSearch(q.value).catch(()=>{})})
</script>
<style scoped>
.compact-page{height:100%;min-height:450px}.page-inner{height:100%;display:flex;flex-direction:column;min-height:0}
.search-toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:5px 0 14px}
.search-toolbar div{display:flex;gap:12px;align-items:center}.search-toolbar b{font-size:15px}.search-toolbar span,.hint{font-size:12px;color:var(--dc-text-2)}
.search-panel{display:flex;flex-direction:column;flex:1;min-height:0;padding:0 14px 4px}
.facets{display:flex;gap:5px;border-bottom:1px solid var(--dc-border);padding:6px 0;overflow-x:auto;flex:0 0 auto}
.facets button{border:0;background:transparent;white-space:nowrap;color:var(--dc-text-2);padding:9px 13px;font-size:13px;border-radius:5px}
.facets button.active{color:var(--dc-primary-strong);background:var(--dc-primary-soft);font-weight:700}
.facets span{margin-left:3px;font-size:12px}
.results{flex:1;min-height:0;overflow:auto}
.result{display:block;padding:11px 5px;border-bottom:1px solid #edf2f5;min-height:66px}
.result:hover{background:#f8fbfd}
.result-head{display:flex;align-items:center;gap:10px;min-width:0;font-size:13px}
.result-head b{max-width:35%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.result-head code{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px}
.type{flex:0 0 46px;color:var(--dc-primary-strong);font-size:12px}
.arrow{margin-left:auto;flex:0 0 auto;color:var(--dc-text-2)}
.result p{margin:5px 0 0 56px;color:var(--dc-text-2);font-size:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
@media(max-width:820px){.compact-page{height:auto}.page-inner{height:auto}.search-panel{min-height:470px}.hint{display:none}.result-head b{max-width:48%}.result-head code{display:none}}
</style>
