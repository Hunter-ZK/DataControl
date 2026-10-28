<template>
  <div class="dc-page catalog-atlas"><div class="dc-container">
    <header class="dc-page-head">
      <div><span class="dc-eyebrow">DATA ASSET DIRECTORY</span>
        <h1 class="dc-title">资产目录<span class="heading-accent"> / Explore</span></h1>
        <p class="dc-subtitle">沿业务主题逐级发现数据资产，再按数仓分层定位数据集。</p>
      </div>
      <RouterLink to="/search" class="explore-link"><Search :size="18"/> 切换到全局检索 <ArrowUpRight :size="17"/></RouterLink>
    </header>
    <section class="catalog-banner">
      <div class="banner-mark"><FolderTree :size="30"/></div>
      <div><span>BUSINESS DATA CATALOG</span><h2>按业务层级发现数据</h2><p>主题 → 子目录 → 数据集。目录名称与层级均来自元数据，不按代码猜测。</p></div>
      <div class="banner-metrics"><strong>{{ allCatalogs.length }}</strong><span>已登记目录</span></div>
    </section>
    <div class="catalog-workspace">
      <aside class="tree-pane dc-card">
        <div class="pane-title"><div><FolderTree :size="21"/><b>业务目录</b></div><span>{{ allCatalogs.length }} 个</span></div>
        <el-input v-model="treeKeyword" clearable placeholder="查找业务目录" class="tree-filter" :prefix-icon="Search"/>
        <button class="tree-all" :class="{active:!selected}" @click="chooseCatalog('')"><Layers3 :size="20"/><span>全部资产目录</span><ChevronRight :size="16"/></button>
        <div class="tree-scroll">
          <el-tree ref="treeRef" :data="catalogTree" node-key="code" highlight-current
            default-expand-all :expand-on-click-node="false" :filter-node-method="filterTreeNode"
            :props="{label:'name',children:'children'}" @node-click="onTreeClick">
            <template #default="{data}">
              <span class="tree-node" :title="data.name"><FolderClosed :size="17"/><span>{{data.name}}</span></span>
            </template>
          </el-tree>
          <p v-if="!catalogTree.length" class="tree-empty">暂无业务目录</p>
        </div>
      </aside>
      <main class="catalog-main">
        <div class="catalog-breadcrumb"><button @click="chooseCatalog('')">全部目录</button>
          <template v-for="(name,index) in selectedPath" :key="index"><ChevronRight :size="15"/><span>{{name}}</span></template>
        </div>
        <section class="directory-heading">
          <div><span class="dc-eyebrow">CURRENT DIRECTORY</span><h2>{{ activeNode?.name || '全部资产' }}</h2>
            <p>{{activeNode?.description || (selected ? '浏览当前业务目录下的直属数据集，或进入下级目录。' : '选择业务目录开始浏览；下方展示全库已发布数据集。')}}</p>
          </div>
          <div class="directory-badge"><FolderTree :size="22"/><span>{{childNodes.length}} 个下级目录</span></div>
        </section>
        <section v-if="childNodes.length" class="directory-section">
          <div class="section-bar"><h3>下级目录</h3><span>选择后进入对应目录</span></div>
          <div class="folder-grid">
            <button v-for="node in childNodes" :key="node.code" class="folder-card" @click="chooseCatalog(node.code)">
              <span class="folder-icon"><FolderClosed :size="25"/></span>
              <span class="folder-copy"><b>{{node.name}}</b><small>{{node.code}}</small></span>
              <ChevronRight :size="20"/>
            </button>
          </div>
        </section>
        <section class="dc-card datasets-section">
          <div class="datasets-header"><div><span class="dc-eyebrow">DATASETS</span><h3>数据集 <em>{{total}}</em></h3></div>
            <div class="dataset-tools">
              <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="检索当前目录下的数据集" @keyup.enter="search" @clear="search"/>
              <button class="query-btn" @click="search"><Search :size="17"/>查询</button>
            </div>
          </div>
          <div class="layer-tabs" role="group" aria-label="数仓分层">
            <button v-for="option in layerOptions" :key="option.value" :class="{active:selectedLayer===option.value}"
              @click="chooseLayer(option.value)">{{option.name}}</button>
            <span>仅展示当前目录直属数据集</span>
          </div>
          <div v-if="loading" class="dc-empty">正在读取数据集…</div>
          <div v-else-if="!rows.length" class="dc-empty"><Database :size="29"/><p>当前筛选下暂无数据集。可进入下级目录或切换数仓层级。</p></div>
          <div v-else class="dataset-table">
            <RouterLink v-for="item in rows" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="dataset-row">
              <AssetIcon type="TABLE" :size="23"/>
              <div class="dataset-info"><b>{{item.bizName}}</b><code>{{item.tableName}}</code><small>{{item.catalogCode}} · {{item.workspaceCode || '工作空间未登记'}}</small></div>
              <span class="layer-badge" :data-layer="item.layerCode">{{item.layerCode}}</span>
              <span class="dataset-owner">{{item.techOwner || '未登记负责人'}}</span>
              <span class="dataset-frequency">{{item.updateFreq || '—'}}</span>
              <ChevronRight :size="20" class="row-arrow"/>
            </RouterLink>
          </div>
          <footer v-if="total>pageSize" class="pager">
            <span>第 {{startRow}}–{{endRow}} 条，共 {{total}} 条</span>
            <div><button :disabled="page===1" @click="go(page-1)">上一页</button><button v-for="p in visiblePages" :key="p" :class="{active:p===page}" @click="go(p)">{{p}}</button><button :disabled="page===totalPages" @click="go(page+1)">下一页</button></div>
          </footer>
        </section>
      </main>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, ChevronRight, Database, FolderClosed, FolderTree, Layers3, Search } from 'lucide-vue-next'
import type { TreeInstance } from 'element-plus'
import AssetIcon from '@/components/AssetIcon.vue'
import { assetApi, type DatasetBrief } from '@/api/client'
import { buildCatalogTree, flattenCatalogs, type CatalogEntry, type CatalogNode } from '@/utils/catalogTree'

const route=useRoute(), router=useRouter()
const treeRef=ref<TreeInstance>()
const treeKeyword=ref('')
const catalogs=ref<CatalogEntry[]>([])
const selected=ref(String(route.query.catalog||''))
const selectedLayer=ref('')
const keyword=ref('')
const rows=ref<DatasetBrief[]>([])
const total=ref(0),page=ref(1),pageSize=20,loading=ref(false)
const catalogTree=computed(()=>buildCatalogTree(catalogs.value))
const allCatalogs=computed(()=>flattenCatalogs(catalogTree.value))
const activeNode=computed(()=>allCatalogs.value.find(node=>node.code===selected.value))
const selectedPath=computed(()=>activeNode.value?.path||[])
const childNodes=computed(()=>activeNode.value?.children||catalogTree.value)
const layerOptions=[{value:'',name:'全部层级'},{value:'DWD',name:'DWD'},{value:'DWS',name:'DWS'},{value:'ADS',name:'ADS'},{value:'ODS',name:'ODS'},{value:'DIM',name:'DIM'}]
const totalPages=computed(()=>Math.max(1,Math.ceil(total.value/pageSize)))
const startRow=computed(()=>total.value?(page.value-1)*pageSize+1:0)
const endRow=computed(()=>Math.min(page.value*pageSize,total.value))
const visiblePages=computed(()=>{const out:number[]=[];const from=Math.max(1,Math.min(page.value-2,totalPages.value-4));for(let i=from;i<=Math.min(totalPages.value,from+4);i++)out.push(i);return out})
let requestId=0
async function load(){
  const seq=++requestId
  loading.value=true
  try {
    const data=await assetApi.tablePage({offset:(page.value-1)*pageSize,limit:pageSize,
      keyword:keyword.value.trim()||undefined,catalog:selected.value||undefined,layer:selectedLayer.value||undefined,status:'ONLINE'})
    if(seq!==requestId)return
    rows.value=data.items
    total.value=data.total
    if(page.value>Math.max(1,Math.ceil(data.total/pageSize))){page.value=1;await load()}
  }catch{if(seq===requestId){rows.value=[];total.value=0}}
  finally{if(seq===requestId)loading.value=false}
}
function chooseCatalog(code:string){
  selected.value=code;page.value=1;keyword.value=''
  router.replace({query:code?{catalog:code}:{}})
  nextTick(()=>{treeRef.value?.setCurrentKey(code||undefined)})
  load()
}
function onTreeClick(data:CatalogNode){chooseCatalog(data.code)}
function filterTreeNode(value:string,data:CatalogNode){return !value||data.name.toLocaleLowerCase().includes(value.toLocaleLowerCase())||data.code.toLocaleLowerCase().includes(value.toLocaleLowerCase())}
function chooseLayer(value:string){selectedLayer.value=value;page.value=1;load()}
function search(){page.value=1;load()}
function go(value:number){page.value=Math.min(Math.max(1,value),totalPages.value);load()}
watch(treeKeyword,value=>treeRef.value?.filter(value))
watch(()=>route.query.catalog,value=>{const code=String(value||'');if(code!==selected.value){selected.value=code;page.value=1;load()}})
onMounted(async()=>{try{catalogs.value=await assetApi.catalogs() as CatalogEntry[]}catch{catalogs.value=[]};await nextTick();treeRef.value?.setCurrentKey(selected.value||undefined);await load()})
</script>
<style scoped>
.catalog-atlas{min-height:100%}
.heading-accent{font-size:14px;color:#89a4cf;vertical-align:middle;letter-spacing:.05em;margin-left:8px}
.explore-link{display:flex;align-items:center;gap:8px;background:#fff;padding:11px 15px;border:1px solid #c8dcf8;border-radius:10px;color:#285eb9;font-size:14px;font-weight:690;box-shadow:var(--dc-shadow-sm)}
.explore-link:hover{background:#eff6ff}
.catalog-banner{display:flex;align-items:center;gap:21px;position:relative;overflow:hidden;padding:22px 27px;margin-bottom:20px;border-radius:16px;background:linear-gradient(108deg,#17427e,#317be4);color:#fff;box-shadow:0 13px 31px rgba(33,91,166,.16)}
.catalog-banner:after{content:'';position:absolute;width:340px;height:220px;right:45px;top:-60px;background:radial-gradient(circle,rgba(147,207,255,.28),transparent 72%);pointer-events:none}
.banner-mark{display:grid;place-items:center;width:60px;height:60px;flex:none;border:1px solid #86b7ef;border-radius:16px;background:rgba(255,255,255,.15)}
.catalog-banner span{font-size:12px;color:#c0e2ff;letter-spacing:.09em;font-weight:720}
.catalog-banner h2{margin:3px 0 4px;font-size:21px;color:white}
.catalog-banner p{margin:0;color:#e0eeff;font-size:13px}
.banner-metrics{margin-left:auto;display:grid;justify-items:center;gap:2px;min-width:108px;z-index:1}
.banner-metrics strong{font-size:31px}
.catalog-workspace{display:grid;grid-template-columns:290px minmax(0,1fr);align-items:start;gap:18px}
.tree-pane{position:sticky;top:80px;padding:17px 15px 19px;min-height:380px;background:linear-gradient(160deg,#fff,#fafcff)}
.pane-title{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:3px 5px 15px;color:#1c3963}
.pane-title>div{display:flex;align-items:center;gap:10px}.pane-title b{font-size:16px}
.pane-title>span{font-size:12px;color:#8295b1}
.tree-filter{margin-bottom:11px}
.tree-all{display:flex;align-items:center;gap:11px;width:100%;border:0;border-radius:9px;background:transparent;color:#527099;font-size:14px;font-weight:680;text-align:left;padding:11px 12px;cursor:pointer}
.tree-all span{flex:1}
.tree-all:hover,.tree-all.active{background:#e9f2ff;color:#215fd3}
.tree-scroll{max-height:calc(100dvh - 305px);min-height:200px;overflow:auto}
.tree-pane :deep(.el-tree){background:transparent;--el-tree-node-hover-bg-color:#eff6ff}
.tree-pane :deep(.el-tree-node__content){height:42px;border-radius:8px;margin:2px 0}
.tree-pane :deep(.el-tree--highlight-current .el-tree-node.is-current>.el-tree-node__content){background:#e5f0ff;color:#195bce}
.tree-node{display:flex;align-items:center;gap:9px;min-width:0;color:#3f597a;font-size:14px}
.tree-node>svg{color:#6195e4;flex:none}
.tree-node span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tree-empty{padding:15px;color:#8799b4;font-size:13px}
.catalog-main{min-width:0}
.catalog-breadcrumb{display:flex;align-items:center;flex-wrap:wrap;gap:7px;color:#7c91af;font-size:13px;margin:1px 0 16px}
.catalog-breadcrumb button{border:0;padding:0;background:transparent;color:#2869d9;font-size:13px;cursor:pointer}
.catalog-breadcrumb span:last-child{color:#254569;font-weight:680}
.directory-heading{display:flex;gap:14px;justify-content:space-between;align-items:center;margin-bottom:20px}
.directory-heading h2{font-size:26px;color:#162f53;margin:4px 0;font-weight:780}
.directory-heading p{font-size:14px;color:#647b9b;margin:0;line-height:1.6}
.directory-badge{display:flex;align-items:center;gap:8px;padding:12px 14px;border:1px solid #ccddf4;border-radius:11px;background:#f8fbff;color:#3870c1;white-space:nowrap;font-size:13px}
.directory-section{margin-bottom:19px}
.section-bar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}
.section-bar h3{font-size:17px;margin:0;color:#284467}
.section-bar span{font-size:12px;color:#879bb7}
.folder-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}
.folder-card{display:flex;align-items:center;gap:12px;min-height:100px;padding:17px 14px;text-align:left;background:linear-gradient(145deg,#fff,#f4f9ff);border:1px solid #c9ddf8;border-radius:13px;box-shadow:0 7px 18px rgba(40,94,170,.075);cursor:pointer;transition:transform .17s,box-shadow .17s}
.folder-card:hover{transform:translateY(-2px);box-shadow:0 12px 25px rgba(40,94,170,.16);border-color:#98baf0}
.folder-icon{width:43px;height:43px;flex:none;display:grid;place-items:center;background:#e7f0ff;color:#2f70df;border:1px solid #cfe1fb;border-radius:11px}
.folder-copy{display:grid;flex:1;gap:5px;min-width:0}
.folder-copy b{font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#234167}
.folder-copy small{font:12px var(--dc-mono);color:#8c9eb8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.folder-card>svg{flex:none;color:#91a8c7}
.datasets-section{overflow:hidden}
.datasets-header{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:19px 21px}
.datasets-header h3{font-size:19px;margin:4px 0 0;color:#203a60}
.datasets-header h3 em{font-style:normal;font-size:13px;color:#386fd0;background:#eaf2ff;padding:4px 9px;border-radius:14px;margin-left:7px}
.dataset-tools{display:flex;align-items:center;gap:8px;min-width:0}
.dataset-tools :deep(.el-input){width:290px}
.query-btn{display:flex;align-items:center;gap:7px;padding:9px 14px;border:0;border-radius:9px;background:#2869ea;color:white;font-size:13px;font-weight:700;cursor:pointer}
.layer-tabs{display:flex;align-items:center;gap:4px;flex-wrap:wrap;padding:11px 20px;background:#f3f8ff;border-top:1px solid #e2ebf9;border-bottom:1px solid #e2ebf9}
.layer-tabs button{border:0;background:transparent;border-radius:7px;padding:8px 14px;color:#597492;font-size:13px;cursor:pointer;font-weight:660}
.layer-tabs button:hover,.layer-tabs button.active{background:white;color:#2163d4;box-shadow:0 2px 8px rgba(30,83,151,.12)}
.layer-tabs>span{margin-left:auto;color:#8b9eb6;font-size:12px}
.dataset-row{display:flex;align-items:center;gap:15px;padding:18px 20px;border-bottom:1px solid #edf2fa;transition:background .12s}
.dataset-row:hover{background:#f7fbff}
.dataset-info{display:grid;gap:4px;flex:1;min-width:0}
.dataset-info b{font-size:15px;color:#263f63;font-weight:740}
.dataset-info code{font:13px var(--dc-mono);color:#6a81a1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dataset-info small{font-size:12px;color:#8b9ab1}
.layer-badge{font-size:12px;font-weight:790;background:#e8f2ff;color:#2868d3;padding:5px 9px;border-radius:6px}
.layer-badge[data-layer="DWD"]{background:#dcf8f2;color:#05796b}
.layer-badge[data-layer="ADS"]{background:#fff0d7;color:#956312}
.dataset-owner,.dataset-frequency{font-size:12px;color:#6d819d;min-width:80px}
.row-arrow{color:#a1b5ce}
.pager{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 20px;color:#7d91ac;font-size:12px}
.pager>div{display:flex;gap:5px}
.pager button{border:1px solid #d1e0f4;background:#fff;border-radius:7px;padding:6px 10px;font-size:12px;cursor:pointer}
.pager button.active{color:#2164d8;background:#e7f1ff;border-color:#aac8f8}
.pager button:disabled{opacity:.4;cursor:default}
.dc-empty>svg{color:#82a5d9}
@media(max-width:1280px){.folder-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.catalog-workspace{grid-template-columns:255px minmax(0,1fr)}.dataset-owner,.dataset-frequency{display:none}}
@media(max-width:850px){.catalog-workspace{grid-template-columns:1fr}.tree-pane{position:static;min-height:0}.tree-scroll{max-height:240px}.folder-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.catalog-banner{padding:20px}.banner-metrics{display:none}}
@media(max-width:580px){.catalog-banner{gap:12px}.banner-mark{width:46px;height:46px}.catalog-banner h2{font-size:17px}.catalog-banner p{font-size:12px}.folder-grid{grid-template-columns:1fr}.directory-heading{flex-direction:column;align-items:flex-start}.datasets-header{align-items:stretch;flex-direction:column}.dataset-tools{width:100%}.dataset-tools :deep(.el-input){flex:1;width:auto}.layer-tabs>span{width:100%;margin:5px 0}.dataset-row{gap:9px;padding:13px}.dataset-info b{font-size:14px}.dataset-info small{display:none}.pager{flex-direction:column;align-items:flex-start}.explore-link{font-size:12px}}
</style>
