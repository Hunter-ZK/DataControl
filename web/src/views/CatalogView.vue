<template>
  <div class="dc-page catalog-page"><div class="dc-container">
    <section class="dc-page-head">
      <div><span class="dc-eyebrow">ASSET CATALOG</span>
        <h1 class="dc-title">资产目录</h1>
        <p class="dc-subtitle">从业务目录找到对应的数据集，查看字段、口径与来源。</p></div>
      <div class="dc-toolbar catalog-search">
        <el-input v-model="keyword" clearable placeholder="搜索数据集名称或物理表名" @keyup.enter="search" />
        <el-button type="primary" @click="search"><Search :size="16"/>查询</el-button>
      </div>
    </section>
    <div class="catalog-layout">
      <aside class="dc-card catalog-side">
        <div class="side-title"><FolderTree :size="17"/>业务主题</div>
        <button :class="{active:!selected}" @click="chooseCatalog('')">
          <AssetIcon type="CATALOG" mode="inline" :size="16"/>
          <span>全部资产</span><small>ALL</small>
        </button>
        <button v-for="c in catalogs" :key="c.code" :class="{active:selected===c.code}" @click="chooseCatalog(c.code)">
          <AssetIcon type="CATALOG" mode="inline" :size="16"/>
          <span>{{ c.name }}</span><small>{{ c.code }}</small>
        </button>
      </aside>
      <section class="dc-card asset-list">
        <div class="list-head"><div><AssetIcon type="TABLE" mode="inline" :size="18"/>
          <b>{{ total }} 个数据集</b><span v-if="selected">· {{ selected }}</span></div>
          <span>第 {{ startRow }}–{{ endRow }} 条</span>
        </div>
        <div v-if="loading" class="dc-empty">正在加载资产目录…</div>
        <RouterLink v-for="item in rows" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="asset-row">
          <AssetIcon type="TABLE" :size="19"/>
          <div class="asset-main">
            <div class="asset-title"><b>{{ item.bizName }}</b>
              <span class="layer-chip" :data-layer="item.layerCode">{{ item.layerCode }}</span></div>
            <code class="dc-tech">{{ item.tableName }}</code>
            <p><FolderTree :size="13"/> {{ item.catalogCode }} · {{ item.workspaceCode || '工作空间未登记' }}</p>
          </div>
          <div class="asset-meta">
            <span><UserRound :size="14"/>{{ item.techOwner || '未登记' }}</span>
            <span><RefreshCcw :size="14"/>{{ item.updateFreq || '—' }}</span>
            <span class="status-chip" :class="{online:item.status==='ONLINE'}">{{ item.status==='ONLINE'?'已发布':item.status }}</span>
            <ChevronRight :size="18"/>
          </div>
        </RouterLink>
        <div v-if="!loading && rows.length===0" class="dc-empty">没有符合条件的数据集。</div>
        <footer v-if="total" class="pagination">
          <button :disabled="page===1" @click="go(page-1)">上一页</button>
          <button v-for="p in visiblePages" :key="p" :class="{active:p===page}" @click="go(p)">{{ p }}</button>
          <button :disabled="page===totalPages" @click="go(page+1)">下一页</button>
        </footer>
      </section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronRight, FolderTree, RefreshCcw, Search, UserRound } from 'lucide-vue-next'
import AssetIcon from '@/components/AssetIcon.vue'
import { assetApi, type DatasetBrief } from '@/api/client'

const keyword=ref(''); const selected=ref(''); const catalogs=ref<any[]>([]); const rows=ref<DatasetBrief[]>([]); const total=ref(0); const page=ref(1); const pageSize=20; const loading=ref(false)
const totalPages=computed(()=>Math.max(1,Math.ceil(total.value/pageSize)))
const startRow=computed(()=>total.value?(page.value-1)*pageSize+1:0)
const endRow=computed(()=>Math.min(page.value*pageSize,total.value))
const visiblePages=computed(()=>{const result:number[]=[];const start=Math.max(1,Math.min(page.value-2,totalPages.value-4));for(let p=start;p<=Math.min(totalPages.value,start+4);p+=1)result.push(p);return result})
async function load(){loading.value=true;try{const data=await assetApi.tablePage({offset:(page.value-1)*pageSize,limit:pageSize,keyword:keyword.value.trim()||undefined,catalog:selected.value||undefined,status:'ONLINE'});rows.value=data.items;total.value=data.total;if(page.value>totalPages.value){page.value=totalPages.value;await load()}}finally{loading.value=false}}
function search(){page.value=1;load()}
function chooseCatalog(code:string){selected.value=code;page.value=1;load()}
function go(value:number){page.value=Math.min(Math.max(1,value),totalPages.value);load();window.scrollTo({top:0,behavior:'smooth'})}
onMounted(async()=>{try{catalogs.value=await assetApi.catalogs() as any[]}catch{};await load()})
</script>

<style scoped>
.catalog-page{background:var(--dc-bg);min-height:100%}
.catalog-search :deep(.el-input){width:300px}
.catalog-layout{display:grid;grid-template-columns:242px minmax(0,1fr);gap:16px;align-items:start}
.catalog-side{padding:14px;position:sticky;top:82px;display:grid;gap:5px}
.side-title{display:flex;gap:8px;align-items:center;font-size:13px;color:var(--dc-text-2);font-weight:750;padding:8px 10px 12px;border-bottom:1px solid var(--dc-border);margin-bottom:5px}
.catalog-side button{border:0;background:transparent;border-radius:9px;padding:10px;text-align:left;color:var(--dc-text-2);cursor:pointer;display:flex;align-items:center;gap:9px;min-width:0;font-size:13px}
.catalog-side button span{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.catalog-side button small{color:var(--dc-text-3);font-size:12px}
.catalog-side button.active,.catalog-side button:hover{background:var(--dc-primary-soft);color:var(--dc-primary)}
.asset-list{padding:0 20px 16px;min-width:0}
.list-head{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--dc-border)}
.list-head div{display:flex;align-items:center;gap:9px}
.list-head b{font-size:14px}.list-head span{color:var(--dc-text-3);font-size:12px}
.asset-row{display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;padding:16px 8px;border-bottom:1px solid var(--dc-border);align-items:center;transition:background .15s}
.asset-row:hover{background:#f8fbff}
.asset-main{min-width:0}.asset-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.asset-title b{font-size:14px;color:var(--dc-text)}
.asset-main code{display:block;font-size:12px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.asset-main p{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--dc-text-3);margin:7px 0 0}
.asset-meta{display:flex;align-items:center;gap:14px;color:var(--dc-text-2);font-size:12px}
.asset-meta>span{display:inline-flex;gap:5px;align-items:center}
.status-chip{color:var(--dc-text-2);background:#f1f5f9;border-radius:6px;padding:5px 8px}
.status-chip.online{color:#047857;background:#ecfdf5}
.layer-chip{padding:4px 8px;border-radius:6px;background:#eff6ff;color:var(--dc-primary);font-size:12px;font-weight:700}
.layer-chip[data-layer="ODS"]{background:#eef2ff;color:#4f46e5}
.layer-chip[data-layer="DWD"]{background:#ecfdf5;color:#047857}
.layer-chip[data-layer="DWS"]{background:#eff6ff;color:#2563eb}
.layer-chip[data-layer="ADS"]{background:#fffbeb;color:#b45309}
.pagination{display:flex;justify-content:flex-end;gap:6px;padding:16px 0 0}
.pagination button{min-width:36px;height:34px;border:1px solid var(--dc-border);border-radius:8px;background:#fff;color:var(--dc-text-2);font-size:12px;cursor:pointer}
.pagination button.active{border-color:var(--dc-primary);background:var(--dc-primary-soft);color:var(--dc-primary)}
.pagination button:disabled{opacity:.4}
@media(max-width:1100px){.asset-meta>span:nth-child(2){display:none}}
@media(max-width:980px){.catalog-layout{grid-template-columns:1fr}.catalog-side{position:static;display:flex;overflow-x:auto}.catalog-side .side-title{display:none}.catalog-side button{flex:0 0 auto}}
@media(max-width:650px){.catalog-search :deep(.el-input){width:100%}.asset-row{grid-template-columns:36px minmax(0,1fr)}.asset-meta{grid-column:2;justify-content:flex-start}.asset-meta>span:nth-child(2){display:none}.list-head{flex-wrap:wrap;padding:12px 0}}

/* B2: table-like asset directory with restrained surface and readable metadata */
.catalog-side{border-radius:11px;padding:15px;background:#fff}
.side-title{color:#607692;font-size:12px}
.catalog-side button{font-size:13px;color:#5a708d;min-height:42px}
.catalog-side button.active{background:#edf4ff;color:var(--dc-primary);font-weight:700}
.catalog-side button small{font-size:12px}
.asset-list{border-radius:12px;padding:0 19px 14px}
.list-head{min-height:58px}
.list-head b{font-size:14px}
.asset-row{padding:17px 8px;grid-template-columns:42px minmax(0,1fr) auto;border-bottom:1px solid #edf2f8}
.asset-row:hover{background:#f8fbff}
.asset-main code{font-size:12px}
.asset-title b{font-size:14px}
.asset-main p,.asset-meta{font-size:12px}
.layer-chip{font-size:12px;background:#eef4ff;color:var(--dc-primary)}
.pagination button.active{border-color:#c4d6f7;color:var(--dc-primary);background:var(--dc-primary-soft)}
@media(max-width:980px){.catalog-side{border-radius:10px}}
</style>
