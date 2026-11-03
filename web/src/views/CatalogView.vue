<template>
  <div class="dc-page compact-page">
    <div class="dc-container page-inner">
      <div class="toolbar">
        <div class="toolbar-title"><span>共 {{total.toLocaleString()}} 条资产</span></div>
        <el-input v-model="keyword" clearable placeholder="按业务名称或物理表名搜索" @keyup.enter="applyKeyword"/>
        <el-select v-model="layer" aria-label="数仓分层" class="layer-filter">
          <el-option label="全部层级" value=""/>
          <el-option v-for="item in layers" :key="item" :label="item" :value="item"/>
        </el-select>
        <el-select v-model="status" aria-label="资产状态" class="status-filter">
          <el-option label="在用" value="ONLINE"/><el-option label="已废弃" value="DEPRECATED"/>
          <el-option label="已下线" value="OFFLINE"/><el-option label="全部状态" value="ALL"/>
        </el-select>
        <el-button type="primary" @click="applyKeyword">查询</el-button>
      </div>
      <div class="layout">
        <aside class="dc-card catalogs">
          <div class="pane-title">业务目录</div>
          <button :class="{selected:selected===''}" @click="selected=''">全部业务资产</button>
          <button v-for="item in catalogTree" :key="item.code" :class="{selected:selected===item.code}"
            :style="{paddingLeft:(12+item.depth*13)+'px'}" @click="selected=item.code">
            <span>{{item.name}}</span><small>{{item.code}}</small>
          </button>
        </aside>
        <section class="dc-card listing">
          <div class="list-head"><span>业务名称 / 物理表名</span><span>负责人</span><span>更新频率</span></div>
          <div ref="rowContainer" class="rows">
            <div v-if="loading" class="dc-empty">正在加载数据集…</div>
            <div v-else-if="!rows.length" class="dc-empty">没有符合当前条件的资产，可调整目录或筛选条件。</div>
            <RouterLink v-for="item in rows" v-else :key="item.assetId" class="asset-row" :to="'/datasets/'+item.assetId">
              <div class="asset-main"><LayerTag :layer="item.layerCode"/><div class="names"><b>{{item.bizName}}</b><code class="dc-tech">{{item.tableName}}</code></div></div>
              <span class="owner">{{item.techOwner||'未登记'}}</span>
              <span class="freq">{{item.updateFreq||'—'}}</span>
            </RouterLink>
          </div>
          <Pager :page="page" :page-size="pageSize" :total="total" @update:page="page=$event"/>
        </section>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { assetApi } from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
const keyword=ref(''),applied=ref(''),selected=ref(''),layer=ref(''),status=ref('ONLINE')
const layers=['ODS','DWD','DWS','ADS','DIM']
const catalogs=ref<any[]>([]),rows=ref<any[]>([]),total=ref(0),loading=ref(false),page=ref(1)
const rowContainer=ref<HTMLElement|null>(null)
const pageSize=useFitPageSize(rowContainer,54,5)
const catalogTree=computed(()=>{
  const result:Array<{code:string;name:string;depth:number}>=[]
  const seen=new Set<string>()
  const walk=(parent:string|null,depth:number)=>{
    for(const item of catalogs.value.filter(x=>(x.parentCode||null)===parent)){
      if(seen.has(item.code))continue
      seen.add(item.code);result.push({code:item.code,name:item.name,depth});walk(item.code,depth+1)
    }
  }
  walk(null,0)
  for(const item of catalogs.value){if(!seen.has(item.code))result.push({code:item.code,name:item.name,depth:0})}
  return result
})
let request=0
async function load(){
  const i=++request;loading.value=true
  try{
    const result=await assetApi.tablesPage({limit:pageSize.value,offset:(page.value-1)*pageSize.value,
      keyword:applied.value||undefined,catalog_code:selected.value||undefined,
      layer_code:layer.value||undefined,status:status.value})
    if(i===request){rows.value=result.items;total.value=result.total}
  }catch{if(i===request){rows.value=[];total.value=0}}
  finally{if(i===request)loading.value=false}
}
function applyKeyword(){applied.value=keyword.value.trim();page.value=1;load()}
watch([selected,layer,status,pageSize],()=>{page.value=1;load()})
watch(page,load)
onMounted(async()=>{try{catalogs.value=await assetApi.catalogs() as any[]}catch{catalogs.value=[]};load()})
</script>
<style scoped>
.compact-page{height:100%;min-height:470px}.page-inner{height:100%;display:flex;flex-direction:column;min-height:0}
.toolbar{display:flex;align-items:center;gap:9px;min-height:42px;margin-bottom:12px}
.toolbar-title{display:flex;align-items:center;gap:10px;white-space:nowrap;margin-right:auto}
.toolbar-title b{font-size:15px}.toolbar-title span{font-size:12px;color:var(--dc-text-2)}
.toolbar :deep(.el-input){width:min(260px,24vw)}.layer-filter{width:125px}.status-filter{width:124px}
.layout{display:grid;grid-template-columns:210px minmax(0,1fr);gap:12px;flex:1;min-height:0}
.catalogs{display:flex;flex-direction:column;gap:2px;padding:12px 8px;min-width:0;overflow:auto}
.pane-title{padding:5px 9px 9px;color:var(--dc-text-2);font-size:12px;font-weight:700}
.catalogs button{display:flex;align-items:center;justify-content:space-between;gap:7px;text-align:left;flex:0 0 auto;border:0;border-radius:5px;background:transparent;padding:9px 10px;font-size:13px;color:var(--dc-text-2)}
.catalogs button:hover,.catalogs button.selected{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}
.catalogs button small{font-size:11px;color:var(--dc-text-2);overflow:hidden;text-overflow:ellipsis}
.listing{padding:10px 14px 4px;display:flex;flex-direction:column;min-height:0;min-width:0}
.list-head,.asset-row{display:grid;grid-template-columns:minmax(0,1fr) 120px 100px;align-items:center;gap:12px}
.list-head{font-size:12px;color:var(--dc-text-2);height:35px;flex:0 0 auto;border-bottom:1px solid var(--dc-border)}
.rows{flex:1;min-height:0;overflow:auto}
.asset-row{min-height:54px;border-bottom:1px solid #edf2f5;padding:6px 0;font-size:12px}
.asset-row:hover{background:#f8fbfd}.asset-main{min-width:0;display:flex;align-items:center;gap:9px}
.names{min-width:0}.names b,.names code{display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.names b{font-size:13px}.names code{font-size:12px;margin-top:3px}
.owner,.freq{color:var(--dc-text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:1100px){.layout{grid-template-columns:175px minmax(0,1fr)}.list-head,.asset-row{grid-template-columns:minmax(0,1fr) 85px 78px}}
@media(max-width:820px){.compact-page{height:auto}.page-inner{height:auto}.layout{display:block}.catalogs{display:flex;flex-direction:row;overflow:auto;margin-bottom:12px}.catalogs button{white-space:nowrap}.pane-title{display:none}.rows{overflow:visible}.toolbar{flex-wrap:wrap}.toolbar :deep(.el-input){width:100%}.listing{min-height:320px}}
@media(max-width:540px){.list-head,.asset-row{grid-template-columns:minmax(0,1fr) 70px}.list-head span:nth-child(3),.asset-row .freq{display:none}.layer-filter,.status-filter{width:calc(50% - 12px)}}
</style>
