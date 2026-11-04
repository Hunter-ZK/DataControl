<template>
  <aside class="ref-side dc-card" ref="side" aria-label="相关资产导航">
    <div class="ref-side-head"><b>{{title}}</b><span>{{filtered.length}} 项</span></div>
    <el-input v-model="keyword" size="small" clearable placeholder="查找编号或名称" aria-label="筛选当前资产目录"/>
    <div class="ref-side-list">
      <RouterLink v-for="row in pageRows" :key="codeOf(row)" :to="target(row)" class="ref-side-item"
        :class="{selected:codeOf(row)===selected}"><b>{{nameOf(row)}}</b><code>{{codeOf(row)}}</code></RouterLink>
      <div v-if="!filtered.length" class="dc-empty">{{loading?'正在加载…':'没有匹配的资产'}}</div>
    </div>
    <footer v-if="filtered.length>pageSize" class="ref-side-pager">
      <button :disabled="page===1" @click="page--">上一页</button><span>{{page}} / {{pageCount}}</span>
      <button :disabled="page>=pageCount" @click="page++">下一页</button>
    </footer>
  </aside>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import api, { assetApi } from '@/api/client'
import { useFitPageSize } from '@/composables/useFitPageSize'
const props=defineProps<{kind:string;selected:string}>()
type Row=Record<string,any>
const rows=ref<Row[]>([]),keyword=ref(''),loading=ref(false),page=ref(1)
const side=ref<HTMLElement|null>(null)
const pageSize=useFitPageSize(side,{rowHeight:48,reserved:135,min:5,max:14})
const title=computed(()=>({'code-tables':'码表','data-standards':'数据标准','word-roots':'词根','metrics':'指标','stat-systems':'统计制度'} as Record<string,string>)[props.kind]||'资产目录')
function codeOf(r:Row){return String(r.codeTableNo||r.standardNo||r.metricCode||r.root||r.code||'')}
function nameOf(r:Row){return String(r.name||r.cnName||r.metricName||r.root||codeOf(r))}
function target(r:Row){const path=({'code-tables':'/code-tables','data-standards':'/standards','word-roots':'/word-roots','metrics':'/metrics','stat-systems':'/stat-systems'} as Record<string,string>)[props.kind]||'/search';return path+'/'+encodeURIComponent(codeOf(r))}
const filtered=computed(()=>{const q=keyword.value.trim().toLowerCase();return q?rows.value.filter(r=>(nameOf(r)+' '+codeOf(r)).toLowerCase().includes(q)):rows.value})
const pageCount=computed(()=>Math.max(1,Math.ceil(filtered.value.length/pageSize.value)))
const pageRows=computed(()=>filtered.value.slice((page.value-1)*pageSize.value,page.value*pageSize.value))
let seq=0
async function load(){
  const id=++seq;loading.value=true;rows.value=[]
  try{
    const result=props.kind==='code-tables'
      ? await api.get<Row[]>('/code-tables',{params:{limit:500}})
      : await assetApi.reference('/'+props.kind) as Row[]
    if(id!==seq)return
    rows.value=result
    if(props.selected && !result.some(r=>codeOf(r)===props.selected)){
      const extra=await assetApi.reference('/'+props.kind,props.selected) as Row[]
      if(id===seq){const match=extra.find(r=>codeOf(r)===props.selected);if(match)rows.value=[match,...rows.value]}
    }
  }catch{if(id===seq)rows.value=[]}
  finally{if(id===seq)loading.value=false}
}
watch(()=>props.kind,()=>{keyword.value='';page.value=1;load()},{immediate:true})
watch([()=>props.selected,filtered,pageSize],()=>{const idx=filtered.value.findIndex(r=>codeOf(r)===props.selected);if(idx>=0)page.value=Math.floor(idx/pageSize.value)+1})
watch(keyword,()=>{page.value=1})
</script>
<style scoped>
.ref-side{height:100%;min-height:0;display:flex;flex-direction:column;padding:10px;overflow:hidden}
.ref-side-head{display:flex;align-items:center;justify-content:space-between;padding:6px 7px 10px}.ref-side-head b{font-size:14px}.ref-side-head span{font-size:12px;color:var(--dc-text-2)}
.ref-side-list{flex:1;min-height:0;overflow-y:auto;margin-top:10px}.ref-side-item{display:grid;gap:2px;padding:9px 11px;border-radius:7px;margin-bottom:3px;border:1px solid transparent}
.ref-side-item b{font-size:13px;line-height:1.35;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.ref-side-item code{font:12px var(--dc-mono);color:#5b6b7a;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.ref-side-item:hover{background:#f2f7ff}.ref-side-item.selected{background:#edf4ff;border-color:#bcd4fb;color:#2563eb}
.ref-side-pager{height:36px;display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--dc-text-2);border-top:1px solid var(--dc-border)}.ref-side-pager button{border:0;background:transparent;color:#2563eb;cursor:pointer}.ref-side-pager button:disabled{opacity:.35;cursor:default}
@media(max-width:820px){.ref-side{height:280px;margin-bottom:12px}}
</style>
