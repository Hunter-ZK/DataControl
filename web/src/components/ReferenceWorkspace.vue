<template>
  <div class="dc-page compact-page"><div class="dc-container page-inner">
    <div class="work-toolbar">
      <nav class="segments" aria-label="标准资产分类">
        <RouterLink v-for="option in options" :key="option.kind" :to="option.path"
          :class="{active:kind===option.kind}">{{option.title}}</RouterLink>
      </nav>
      <el-input v-model="keyword" clearable :placeholder="'搜索'+config.title+'名称或编码'" @keyup.enter="load"/>
      <el-button @click="load">查询</el-button>
    </div>
    <div class="work-layout">
      <section class="dc-card side">
        <div class="pane-title"><b>{{config.title}}</b><span>已加载 {{rows.length}} 条</span></div>
        <div ref="listContainer" class="list">
          <button v-for="item in pagedRows" :key="keyOf(item)" :class="{selected:currentKey===keyOf(item)}"
            @click="select(item)">
            <b>{{titleOf(item)}}</b>
            <span>{{keyOf(item)}}</span>
          </button>
          <div v-if="!pagedRows.length && !loading" class="dc-empty">暂无匹配资产。</div>
          <div v-if="loading" class="dc-empty">正在加载…</div>
        </div>
        <Pager v-model:page="page" :page-size="pageSize" :total="rows.length"/>
      </section>
      <section class="dc-card detail">
        <div v-if="detailLoading" class="dc-empty">正在加载详情…</div>
        <div v-else-if="!current" class="dc-empty">从左侧选择一条资产查看定义与关联信息。</div>
        <template v-else>
          <div class="detail-heading">
            <div><small>{{config.title}}</small><h1>{{titleOf(current)}}</h1>
              <code class="dc-tech">{{keyOf(current)}}</code></div>
            <span class="status">{{statusLabel(current.status)}}</span>
          </div>
          <div class="detail-body">
            <div class="description" v-if="descriptionOf(current)">
              <h2>业务定义</h2><p>{{descriptionOf(current)}}</p>
            </div>
            <div class="details">
              <template v-if="kind==='code-tables'">
                <div><span>码表编号</span><code class="dc-tech">{{current.codeTableNo}}</code></div>
                <div><span>版本</span><b>{{current.version||'—'}}</b></div>
              </template>
              <template v-else-if="kind==='data-standards'">
                <div><span>标准编号</span><code class="dc-tech">{{current.standardNo}}</code></div>
                <div><span>关联码表</span><RouterLink v-if="current.codeTableNo" :to="'/code-tables/'+current.codeTableNo">{{current.codeTableNo}}</RouterLink><b v-else>—</b></div>
              </template>
              <template v-else-if="kind==='word-roots'">
                <div><span>英文词根</span><code class="dc-tech">{{current.root}}</code></div>
                <div><span>英文全称</span><b>{{current.enFull||'—'}}</b></div>
                <div><span>中文名称</span><b>{{current.cnName||'—'}}</b></div>
                <div><span>同义词</span><b>{{current.synonyms||'—'}}</b></div>
              </template>
              <template v-else-if="kind==='metrics'">
                <div><span>指标编码</span><code class="dc-tech">{{current.metricCode}}</code></div>
                <div><span>聚合方式</span><b>{{current.aggregation||'—'}}</b></div>
                <div><span>度量字段</span><code class="dc-tech">{{current.measureColumn||'—'}}</code></div>
                <div><span>时间字段</span><code class="dc-tech">{{current.timeField||'—'}}</code></div>
                <div><span>时间可加性</span><b>{{current.timeAdditivity||'—'}}</b></div>
                <div><span>来源数据集</span><RouterLink v-if="current.sourceDatasetId" :to="'/datasets/'+current.sourceDatasetId">{{current.sourceDatasetId}}</RouterLink><b v-else>—</b></div>
              </template>
              <template v-else>
                <div><span>制度编码</span><code class="dc-tech">{{current.code}}</code></div>
                <div><span>版本</span><b>{{current.version||'—'}}</b></div>
                <div><span>发布机构</span><b>{{current.issuer||'—'}}</b></div>
                <div><span>文号</span><b>{{current.documentNo||'—'}}</b></div>
              </template>
            </div>
            <section v-if="kind==='code-tables'" class="values">
              <div class="values-head"><h2>码值列表 <small>{{current.values?.length||0}} 条</small></h2><el-input v-model="valueKeyword" clearable placeholder="筛选码值或名称"/></div>
              <div class="dc-table-wrap"><table class="dc-table"><thead><tr><th>码值</th><th>名称</th><th>说明</th></tr></thead>
                <tbody><tr v-for="item in pagedValues" :key="item.value"><td><code class="dc-tech">{{item.value}}</code></td><td>{{item.name}}</td><td>{{item.description||'—'}}</td></tr></tbody></table></div>
              <Pager v-model:page="valuePage" :page-size="8" :total="filteredValues.length"/>
            </section>
          </div>
        </template>
      </section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { assetApi } from '@/api/client'
import api from '@/api/client'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
import { statusLabel } from '@/utils/labels'
const props=defineProps<{kind:string;selectedKey?:string}>()
const route=useRoute(),router=useRouter()
const configs:Record<string,{title:string;path:string}>={
 'data-standards':{title:'数据标准',path:'/standards'},'code-tables':{title:'码表',path:'/code-tables'},
 'word-roots':{title:'词根',path:'/word-roots'},metrics:{title:'指标',path:'/metrics'},
 'stat-systems':{title:'统计制度',path:'/stat-systems'},
}
const config=computed(()=>configs[props.kind]||configs.metrics)
const options=computed(()=>['data-standards','code-tables','word-roots'].includes(props.kind)
 ? ['data-standards','code-tables','word-roots'].map(kind=>({kind,...configs[kind]}))
 : ['metrics','stat-systems'].map(kind=>({kind,...configs[kind]})))
const keyword=ref(''),rows=ref<any[]>([]),current=ref<any|null>(null),loading=ref(false),detailLoading=ref(false)
const currentKey=ref(''),page=ref(1),valueKeyword=ref(''),valuePage=ref(1)
const listContainer=ref<HTMLElement|null>(null),pageSize=useFitPageSize(listContainer,50,5)
const pagedRows=computed(()=>rows.value.slice((page.value-1)*pageSize.value,page.value*pageSize.value))
const filteredValues=computed(()=>{
 const k=valueKeyword.value.trim().toLowerCase()
 return (current.value?.values||[]).filter((x:any)=>!k || (String(x.value)+' '+x.name+' '+(x.description||'')).toLowerCase().includes(k))
})
const pagedValues=computed(()=>filteredValues.value.slice((valuePage.value-1)*8,valuePage.value*8))
function keyOf(item:any){return String(item.codeTableNo||item.standardNo||item.root||item.metricCode||item.code||item.assetId||'')}
function titleOf(item:any){return item.name||item.cnName||item.root||'未命名资产'}
function descriptionOf(item:any){return item.definition||item.caliber||item.description||item.aliases||''}
let listingSeq=0,detailSeq=0
async function fetchDetail(key:string){
 const i=++detailSeq
 if(!key){current.value=null;return}
 detailLoading.value=true;valueKeyword.value='';valuePage.value=1
 try{
   let row=rows.value.find(x=>keyOf(x)===key)
   if(props.kind==='code-tables')row=await api.get('/code-tables/'+encodeURIComponent(key))
   else if(!row){
     const data=await assetApi.reference('/'+props.kind,key) as any[]
     row=data.find(x=>keyOf(x)===key)
   }
   if(i===detailSeq)current.value=row||null
 }catch{if(i===detailSeq)current.value=null}
 finally{if(i===detailSeq)detailLoading.value=false}
}
function select(item:any){
 const key=keyOf(item);currentKey.value=key
 const isDetail=Boolean(props.selectedKey)
 if(isDetail){
   router.push(config.value.path+'/'+encodeURIComponent(key))
 }else{
   router.replace({path:config.value.path,query:{...route.query,selected:key}})
 }
 fetchDetail(key)
}
async function load(){
 const i=++listingSeq;loading.value=true
 try{
   const endpoint='/'+props.kind
   const list=props.kind==='code-tables'
    ? await api.get<any[]>('/code-tables',{params:{keyword:keyword.value||undefined,limit:500}})
    : await assetApi.reference(endpoint,keyword.value||undefined) as any[]
   if(i===listingSeq){
     rows.value=list;page.value=1
     const key=props.selectedKey||String(route.query.selected||'')||keyOf(list[0]||{})
     currentKey.value=key
     if(key){
       const position=rows.value.findIndex(x=>keyOf(x)===key)
       if(position>=0)page.value=Math.floor(position/pageSize.value)+1
     }
     await fetchDetail(key)
   }
 }catch{if(i===listingSeq){rows.value=[];current.value=null}}
 finally{if(i===listingSeq)loading.value=false}
}
watch(()=>[props.kind,props.selectedKey,route.query.selected],()=>{
 const key=props.selectedKey||String(route.query.selected||'')
 if(key && key!==currentKey.value){currentKey.value=key;fetchDetail(key)}
})
watch(valueKeyword,()=>valuePage.value=1)
watch(pageSize,()=>{
 const idx=rows.value.findIndex(x=>keyOf(x)===currentKey.value)
 if(idx>=0)page.value=Math.floor(idx/pageSize.value)+1
})
watch(()=>props.kind,()=>{keyword.value='';load()})
onMounted(load)
</script>
<style scoped>
.compact-page{height:100%;min-height:490px}.page-inner{height:100%;display:flex;flex-direction:column;min-height:0}
.work-toolbar{display:flex;align-items:center;gap:10px;margin-bottom:12px;min-height:39px}
.segments{display:flex;gap:3px;background:#edf4f8;border-radius:7px;padding:3px;margin-right:auto}
.segments a{border-radius:5px;padding:8px 13px;color:var(--dc-text-2);font-size:13px;white-space:nowrap}
.segments a.active{background:#fff;color:var(--dc-primary-strong);font-weight:700;box-shadow:var(--dc-shadow-sm)}
.work-toolbar :deep(.el-input){width:220px}
.work-layout{display:grid;grid-template-columns:minmax(250px,340px) minmax(0,1fr);gap:12px;flex:1;min-height:0}
.side,.detail{min-height:0;min-width:0}
.side{padding:12px;display:flex;flex-direction:column}.pane-title{display:flex;justify-content:space-between;align-items:center;gap:10px;border-bottom:1px solid var(--dc-border);padding:6px 2px 12px}
.pane-title b{font-size:14px}.pane-title span{font-size:12px;color:var(--dc-text-2)}
.list{flex:1;min-height:0;overflow:auto;padding:6px 0}
.list button{width:100%;border:0;background:transparent;border-radius:5px;display:grid;gap:3px;text-align:left;min-height:50px;padding:9px 11px}
.list button b{font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.list button span{font-size:12px;color:var(--dc-text-2);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.list button:hover,.list button.selected{background:var(--dc-primary-soft)}.list button.selected b{color:var(--dc-primary-strong)}
.detail{padding:18px 20px;overflow:auto}
.detail-heading{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid var(--dc-border);padding-bottom:15px;gap:15px}
.detail-heading small{color:var(--dc-text-2);font-size:12px}.detail-heading h1{font-size:20px;margin:6px 0}
.detail-heading code{font-size:12px}.status{font-size:12px;color:var(--dc-success)}
.detail-body{padding-top:15px}.description h2,.values h2{font-size:14px;margin:0 0 9px}
.description p{font-size:13px;color:var(--dc-text-2);line-height:1.7;margin:0 0 16px;white-space:pre-wrap;overflow-wrap:anywhere}
.details{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.details>div{padding:11px 12px;background:#f8fbfd;border:1px solid var(--dc-border);border-radius:6px;min-width:0}
.details span{display:block;color:var(--dc-text-2);font-size:12px;margin-bottom:6px}
.details b,.details code{font-size:12px;overflow-wrap:anywhere}.details a{color:var(--dc-primary-strong)}
.values{margin-top:24px}.values-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}.values-head small{font-weight:400;color:var(--dc-text-2)}
.values-head :deep(.el-input){width:205px}.values .dc-table{min-width:500px}
@media(max-width:820px){.compact-page,.page-inner{height:auto}.work-layout{display:block}.side{height:340px;margin-bottom:12px}.detail{min-height:290px}.work-toolbar{flex-wrap:wrap}.work-toolbar :deep(.el-input){width:100%}}
@media(max-width:480px){.details{grid-template-columns:1fr}.segments{max-width:100%;overflow:auto}}
</style>
