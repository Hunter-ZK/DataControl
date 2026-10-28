<template>
  <div class="dc-page reference-atlas"><div class="dc-container">
    <header class="dc-page-head">
      <div><span class="dc-eyebrow">GOVERNED DATA KNOWLEDGE</span><h1 class="dc-title">{{config.title}}</h1><p class="dc-subtitle">{{config.desc}}</p></div>
      <div class="reference-switch">
        <RouterLink v-if="kind==='metrics'" to="/stat-systems"><FileText :size="18"/>统计制度 <ArrowRight :size="16"/></RouterLink>
        <RouterLink v-else-if="kind==='stat-systems'" to="/metrics"><ChartNoAxesCombined :size="18"/>业务指标 <ArrowRight :size="16"/></RouterLink>
        <RouterLink v-else to="/search"><Search :size="18"/>全局检索 <ArrowRight :size="16"/></RouterLink>
      </div>
    </header>
    <section class="reference-hero">
      <div class="reference-hero-icon"><AssetIcon :type="referenceType" :size="30"/></div>
      <div><span class="dc-eyebrow">{{config.eyebrow}}</span><h2>{{config.heading}}</h2><p>{{config.note}}</p></div>
      <div class="reference-total"><strong>{{visibleRows.length}}</strong><span>当前结果</span></div>
    </section>
    <section class="reference-toolbar dc-card">
      <div class="reference-search"><Search :size="21"/><input v-model="keyword" :placeholder="config.placeholder" @keydown.enter.prevent="load" aria-label="资产字典检索"/>
        <button @click="load">查询 <ArrowRight :size="16"/></button></div>
      <div class="toolbar-desc"><span>当前：{{config.title}}</span><button v-if="keyword||letter" @click="clearSearch">清空筛选</button></div>
    </section>

    <div v-if="kind==='code-tables'" class="code-workspace">
      <aside class="code-list dc-card">
        <div class="code-list-heading"><b>码表目录</b><span>{{visibleRows.length}} 张码表</span></div>
        <div class="code-items">
          <button v-for="row in visibleRows" :key="keyOf(row)" class="code-item"
            :class="{active:selectedCode===row.codeTableNo}" @click="selectCode(row.codeTableNo)">
            <AssetIcon type="CODE_TABLE" :size="20"/>
            <span><b>{{titleOf(row)}}</b><code>{{codeOf(row)}}</code></span><ChevronRight :size="17"/>
          </button>
          <div v-if="!visibleRows.length" class="dc-empty">没有匹配的码表。</div>
        </div>
      </aside>
      <section class="code-detail dc-card">
        <template v-if="selectedCode">
          <div class="code-detail-head"><div><span class="dc-eyebrow">CODE VALUES</span><h2>{{selectedDetail?.name||currentCodeList?.name||'码值详情'}}</h2><code>{{selectedCode}}</code></div>
            <RouterLink :to="`/code-tables/${selectedCode}`">查看完整码表 <ArrowRight :size="16"/></RouterLink></div>
          <p class="code-definition">{{selectedDetail?.description||currentCodeList?.description||'该码表尚未登记说明。'}}</p>
          <div class="code-values-toolbar"><b>码值明细 <span>{{filteredValues.length}} 项</span></b>
            <el-input v-model="valueKeyword" clearable :prefix-icon="Search" placeholder="筛选码值或含义"/></div>
          <div v-if="detailLoading" class="dc-empty">正在加载码值…</div>
          <div v-else-if="detailError" class="dc-empty">{{detailError}}</div>
          <div v-else class="table-clip"><table class="dictionary-table"><thead><tr><th>码值</th><th>名称 / 含义</th><th>业务说明</th></tr></thead>
            <tbody><tr v-for="value in filteredValues" :key="String(value.value)"><td><code>{{value.value}}</code></td><td>{{value.name}}</td><td>{{value.description||'—'}}</td></tr>
            <tr v-if="!filteredValues.length"><td colspan="3" class="empty-row">暂无匹配码值。</td></tr></tbody></table></div>
        </template>
        <div v-else class="dc-empty">从左侧选择一张码表，即可预览码值明细。</div>
      </section>
    </div>

    <section v-else-if="kind==='word-roots'" class="dc-card dictionary-panel">
      <div class="panel-heading"><div><span class="dc-eyebrow">WORD ROOT DICTIONARY</span><h2>字段命名词根字典</h2></div><span>英文词根与中文含义一一对应</span></div>
      <div class="alphabet" aria-label="按首字母筛选词根">
        <button :class="{active:!letter}" @click="letter=''">全部</button>
        <button v-for="x in letters" :key="x" :class="{active:letter===x}" @click="letter=letter===x?'':x">{{x}}</button>
      </div>
      <div class="table-clip"><table class="dictionary-table"><thead><tr><th>词根</th><th>中文名称</th><th>英文全称</th><th>同义词／说明</th><th></th></tr></thead>
        <tbody><tr v-for="row in visibleRows" :key="keyOf(row)"><td><RouterLink :to="target(row)" class="code-link">{{row.root}}</RouterLink></td>
          <td><strong>{{row.cnName||'—'}}</strong></td><td>{{row.enFull||'—'}}</td><td>{{row.synonyms||row.description||'—'}}</td>
          <td><RouterLink :to="target(row)" class="row-link"><ArrowRight :size="17"/></RouterLink></td></tr>
          <tr v-if="!visibleRows.length"><td colspan="5" class="empty-row">未找到符合条件的词根。</td></tr></tbody></table></div>
    </section>

    <section v-else-if="kind==='metrics'" class="dc-card dictionary-panel">
      <div class="panel-heading"><div><span class="dc-eyebrow">METRIC CATALOG</span><h2>业务指标字典</h2></div><span>点击指标名称查看完整计算口径</span></div>
      <div class="table-clip"><table class="dictionary-table"><thead><tr><th>指标名称与编码</th><th>定义／统计口径</th><th>聚合方式</th><th>来源数据集</th><th>所属制度</th><th></th></tr></thead>
        <tbody><tr v-for="row in visibleRows" :key="keyOf(row)">
          <td><RouterLink :to="target(row)" class="title-link">{{titleOf(row)}}</RouterLink><code class="sub-code">{{row.metricCode}}</code></td>
          <td class="description-cell">{{row.definition||row.caliber||'尚未登记口径'}}</td>
          <td><span class="aggregation">{{row.aggregation||'—'}}</span></td>
          <td><RouterLink v-if="row.sourceDatasetId" :to="`/datasets/${row.sourceDatasetId}`" class="code-link">{{row.sourceDatasetId}}</RouterLink><span v-else>—</span></td>
          <td><RouterLink v-if="row.statSystemCode" :to="`/stat-systems/${row.statSystemCode}`" class="code-link">{{row.statSystemCode}}</RouterLink><span v-else>—</span></td>
          <td><RouterLink :to="target(row)" class="row-link"><ArrowRight :size="17"/></RouterLink></td></tr>
          <tr v-if="!visibleRows.length"><td colspan="6" class="empty-row">未找到匹配指标。</td></tr></tbody></table></div>
    </section>

    <section v-else-if="kind==='data-standards'" class="dc-card dictionary-panel">
      <div class="panel-heading"><div><span class="dc-eyebrow">DATA STANDARDS</span><h2>字段标准目录</h2></div><span>统一定义、编码与关联码表</span></div>
      <div class="table-clip"><table class="dictionary-table"><thead><tr><th>标准编号</th><th>标准名称</th><th>业务定义</th><th>关联码表</th><th></th></tr></thead>
        <tbody><tr v-for="row in visibleRows" :key="keyOf(row)">
          <td><RouterLink :to="target(row)" class="code-link">{{row.standardNo}}</RouterLink></td><td><RouterLink :to="target(row)" class="title-link">{{titleOf(row)}}</RouterLink></td>
          <td class="description-cell">{{row.definition||'—'}}</td>
          <td><RouterLink v-if="row.codeTableNo" :to="`/code-tables/${row.codeTableNo}`" class="code-link">{{row.codeTableNo}}</RouterLink><span v-else>—</span></td>
          <td><RouterLink :to="target(row)" class="row-link"><ArrowRight :size="17"/></RouterLink></td></tr>
          <tr v-if="!visibleRows.length"><td colspan="5" class="empty-row">未找到匹配数据标准。</td></tr></tbody></table></div>
    </section>

    <section v-else class="dc-card documents-panel">
      <div class="panel-heading"><div><span class="dc-eyebrow">STATISTICAL DOCUMENTS</span><h2>统计制度文档目录</h2></div><span>按制度、文号与版本查看</span></div>
      <RouterLink v-for="row in visibleRows" :key="keyOf(row)" :to="target(row)" class="document-row">
        <span class="document-icon"><FileText :size="29"/></span>
        <span class="document-main"><b>{{titleOf(row)}}</b><small>{{row.documentNo||row.code||'未登记文号'}}</small></span>
        <span class="document-meta"><span>{{row.issuer||'发布机构未登记'}}</span><small>版本 {{row.version||'—'}}</small></span>
        <ArrowRight :size="20"/></RouterLink>
      <div v-if="!visibleRows.length" class="dc-empty">没有符合条件的统计制度。</div>
    </section>
  </div></div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, ChartNoAxesCombined, ChevronRight, FileText, Search } from 'lucide-vue-next'
import api, { assetApi } from '@/api/client'
import AssetIcon from '@/components/AssetIcon.vue'

type ReferenceRow = Record<string, any>
type CodeValue = {value:string;name:string;description?:string|null}
const props=defineProps<{kind:string}>()
const keyword=ref(''),letter=ref(''),rows=ref<ReferenceRow[]>([])
const selectedCode=ref(''),selectedDetail=ref<ReferenceRow|null>(null),valueKeyword=ref(''),detailLoading=ref(false),detailError=ref('')
const configs:Record<string,{title:string;desc:string;placeholder:string;eyebrow:string;heading:string;note:string}>={
  'code-tables':{title:'标准码值',desc:'查找编码体系，直接预览完整码值和含义。',placeholder:'搜索码表编号或名称',eyebrow:'CODE TABLE LIBRARY',heading:'标准码值工作台',note:'左侧选择码表，右侧直接查看码值，无需来回跳转。'},
  'data-standards':{title:'数据标准',desc:'按编号与名称检索字段标准、定义和关联码表。',placeholder:'搜索标准编号或名称',eyebrow:'DATA STANDARD DICTIONARY',heading:'让字段语义与标准保持一致',note:'统一对照标准名称、定义、编码和关联取值。'},
  'word-roots':{title:'词根索引',desc:'可按首字母定位英文词根并对照中文名和规范释义。',placeholder:'搜索词根、中文名或同义词',eyebrow:'NAMING DICTIONARY',heading:'规范字段命名，快速查找词根',note:'使用字典式视图，比逐张卡片查看更方便。'},
  metrics:{title:'业务指标',desc:'按指标名称、代码查询计算语义、业务口径及来源数据集。',placeholder:'搜索指标名称或编码',eyebrow:'METRIC KNOWLEDGE BASE',heading:'可查、可追溯的业务指标字典',note:'聚合方式、来源数据集、关联制度在同一行可比较。'},
  'stat-systems':{title:'统计制度',desc:'以文档目录方式查看统计制度、版本、文号和发布机构。',placeholder:'按制度名称、文号、发布机构筛选',eyebrow:'GOVERNANCE DOCUMENTS',heading:'统计制度与文档索引',note:'清晰对照制度名称、发布机构和版本。'},
}
const config=computed(()=>configs[props.kind]||configs.metrics)
const referenceType=computed(():string=>({'code-tables':'CODE_TABLE','data-standards':'STANDARD','word-roots':'WORD_ROOT','metrics':'METRIC','stat-systems':'STAT_SYSTEM'} as Record<string,string>)[props.kind]||'REFERENCE')
const letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')
const visibleRows=computed(()=>{
  let list=rows.value
  if(props.kind==='word-roots'&&letter.value)list=list.filter(x=>String(x.root||'').toUpperCase().startsWith(letter.value))
  if(props.kind==='stat-systems'&&keyword.value.trim()){const q=keyword.value.trim().toLowerCase();list=list.filter(x=>[x.name,x.code,x.documentNo,x.issuer].some(v=>String(v||'').toLowerCase().includes(q)))}
  return list
})
const currentCodeList=computed(()=>rows.value.find(row=>row.codeTableNo===selectedCode.value))
const filteredValues=computed<CodeValue[]>(()=>{
  const list=(selectedDetail.value?.values||[]) as CodeValue[]
  const q=valueKeyword.value.trim().toLowerCase()
  return q?list.filter(v=>[v.value,v.name,v.description].some(s=>String(s||'').toLowerCase().includes(q))):list
})
let listRequest=0,detailRequest=0
async function load(){
  const seq=++listRequest
  try{
    const data=await assetApi.reference('/'+props.kind,props.kind==='stat-systems'?undefined:keyword.value.trim()||undefined) as ReferenceRow[]
    if(seq!==listRequest)return
    rows.value=data
    if(props.kind==='code-tables'){
      const code=data.find(row=>row.codeTableNo===selectedCode.value)?.codeTableNo||data[0]?.codeTableNo||''
      if(code&&code!==selectedCode.value)await selectCode(code)
      else if(!code){selectedCode.value='';selectedDetail.value=null}
    }
  }catch{if(seq===listRequest)rows.value=[]}
}
async function selectCode(code:string){
  selectedCode.value=code;selectedDetail.value=null;detailError.value='';valueKeyword.value=''
  const seq=++detailRequest
  detailLoading.value=true
  try{const data=await api.get('/code-tables/'+encodeURIComponent(code)) as ReferenceRow;if(seq===detailRequest)selectedDetail.value=data}
  catch{if(seq===detailRequest)detailError.value='码值加载失败，可打开完整码表详情重试。'}
  finally{if(seq===detailRequest)detailLoading.value=false}
}
function clearSearch(){keyword.value='';letter.value='';load()}
function keyOf(r:ReferenceRow){return String(r.assetId||r.codeTableNo||r.standardNo||r.root||r.metricCode||r.code)}
function titleOf(r:ReferenceRow){return String(r.name||r.cnName||r.metricName||r.root||'未命名资产')}
function codeOf(r:ReferenceRow){return String(r.codeTableNo||r.standardNo||r.root||r.metricCode||r.code||r.assetId||'—')}
function target(r:ReferenceRow){
 if(props.kind==='code-tables')return '/code-tables/'+encodeURIComponent(String(r.codeTableNo))
 if(props.kind==='data-standards')return '/standards/'+encodeURIComponent(String(r.standardNo))
 if(props.kind==='word-roots')return '/word-roots/'+encodeURIComponent(String(r.root))
 if(props.kind==='metrics')return '/metrics/'+encodeURIComponent(String(r.metricCode))
 return '/stat-systems/'+encodeURIComponent(String(r.code))
}
watch(()=>props.kind,()=>{keyword.value='';letter.value='';rows.value=[];selectedCode.value='';selectedDetail.value=null;load()},{immediate:true})
</script>
<style scoped>
.reference-atlas{min-height:100%}
.reference-switch a{display:flex;align-items:center;gap:9px;padding:12px 16px;border:1px solid #c8dbf7;background:#fff;border-radius:10px;box-shadow:var(--dc-shadow-sm);font-size:14px;font-weight:720;color:#2c6bd7}
.reference-switch a:hover{background:#edf5ff}
.reference-hero{display:flex;align-items:center;gap:18px;padding:23px 27px;margin-bottom:18px;border-radius:16px;background:linear-gradient(112deg,#173c76,#3278dc);box-shadow:0 14px 33px #265da42a;color:#fff;position:relative;overflow:hidden}
.reference-hero:after{content:'';position:absolute;right:5%;top:-50px;width:300px;height:190px;background:radial-gradient(circle,#92c2ff63,transparent 73%);pointer-events:none}
.reference-hero-icon{display:grid;place-items:center;width:64px;height:64px;flex:none;background:#ffffff27;border:1px solid #ffffff59;border-radius:17px}
.reference-hero-icon :deep(.asset-icon){color:#fff!important;background:transparent!important;border:0!important;box-shadow:none!important}
.reference-hero .dc-eyebrow{color:#b9ddff}
.reference-hero h2{font-size:21px;color:white;margin:3px 0 4px}
.reference-hero p{margin:0;font-size:13px;color:#daebff}
.reference-total{display:grid;justify-items:center;gap:0;margin-left:auto;min-width:93px;z-index:1}
.reference-total strong{font-size:33px;color:#fff;line-height:1.2}
.reference-total span{font-size:12px;color:#e4efff}
.reference-toolbar{display:flex;align-items:center;gap:15px;padding:13px 17px;margin-bottom:18px}
.reference-search{display:flex;align-items:center;gap:11px;flex:1;max-width:740px;height:48px;color:#4a82db;background:#f7fbff;border:1px solid #ccddf5;border-radius:9px;padding:6px 7px 6px 14px}
.reference-search input{flex:1;min-width:0;background:transparent;border:0;outline:0;font-size:14px;color:#1f3d65}
.reference-search button{display:flex;align-items:center;gap:7px;border:0;border-radius:7px;color:#fff;background:#286be5;padding:8px 15px;font-size:13px;font-weight:710;cursor:pointer}
.toolbar-desc{display:flex;justify-content:flex-end;gap:13px;align-items:center;flex:1;color:#7c92ac;font-size:12px}
.toolbar-desc button{border:0;background:none;color:#2369d5;cursor:pointer}
.dictionary-panel,.documents-panel{padding:0;overflow:hidden}
.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:22px 24px;border-bottom:1px solid #dce7f8;background:linear-gradient(100deg,#f5f9ff,#fff)}
.panel-heading h2{font-size:19px;margin:4px 0 0;color:#22426d}
.panel-heading>span{color:#8197b3;font-size:13px}
.table-clip{overflow:auto}
.dictionary-table{width:100%;min-width:750px;border-collapse:collapse;background:white}
.dictionary-table th,.dictionary-table td{padding:16px 20px;text-align:left;vertical-align:middle;border-bottom:1px solid #e8effa;line-height:1.65}
.dictionary-table th{font-size:13px;font-weight:740;color:#5b7191;background:#f0f6ff;white-space:nowrap}
.dictionary-table td{font-size:14px;color:#546d8c}
.dictionary-table tbody tr:hover{background:#f8fbff}
.dictionary-table .title-link{font-size:15px;font-weight:750;color:#234a7f}
.dictionary-table .title-link:hover,.dictionary-table .code-link:hover{text-decoration:underline;color:#1d65d4}
.dictionary-table .code-link{color:#2d69c9;font:13px var(--dc-mono)}
.dictionary-table .sub-code{display:block;color:#8598b1;font:12px var(--dc-mono);margin-top:4px}
.description-cell{max-width:310px;color:#627b9a!important}
.aggregation{display:inline-block;padding:4px 8px;color:#286ad1;background:#eaf3ff;border-radius:7px;font:12px var(--dc-mono)}
.row-link{display:inline-flex;align-items:center;color:#4783e2}
.empty-row{text-align:center!important;color:#9aabc0!important;padding:37px 0!important}
.alphabet{display:flex;gap:3px;flex-wrap:wrap;padding:15px 20px;border-bottom:1px solid #e6eef9}
.alphabet button{font-size:13px;font-weight:710;border:0;background:transparent;border-radius:7px;padding:7px 9px;color:#627c9b;cursor:pointer}
.alphabet button.active,.alphabet button:hover{background:#e7f1ff;color:#2464d5}
.code-workspace{display:grid;grid-template-columns:326px minmax(0,1fr);gap:18px;align-items:start}
.code-list{overflow:hidden}
.code-list-heading{display:flex;justify-content:space-between;align-items:center;padding:20px 18px;background:#f4f9ff;border-bottom:1px solid #dbe7f9}
.code-list-heading b{font-size:17px;color:#24466f}
.code-list-heading span{font-size:12px;color:#8ca0b8}
.code-items{max-height:670px;overflow:auto}
.code-item{display:flex;gap:11px;align-items:center;text-align:left;width:100%;padding:15px;border:0;border-bottom:1px solid #edf2fa;background:#fff;cursor:pointer}
.code-item:hover,.code-item.active{background:#edf5ff}
.code-item.active{box-shadow:inset 4px 0 #2d6ee1}
.code-item>span:nth-child(2){display:grid;gap:4px;flex:1;min-width:0}
.code-item b{font-size:14px;color:#294971;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.code-item code{font:12px var(--dc-mono);color:#8b9eb5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.code-item>svg{color:#9db1ca}
.code-detail{overflow:hidden;min-height:360px}
.code-detail-head{padding:25px 25px 10px;display:flex;gap:10px;justify-content:space-between;align-items:start}
.code-detail-head h2{font-size:22px;color:#213e65;margin:6px 0}
.code-detail-head code{font:13px var(--dc-mono);color:#8199b3}
.code-detail-head a{display:flex;align-items:center;gap:7px;color:#2b6bd4;font-size:13px;font-weight:720;white-space:nowrap}
.code-definition{font-size:14px;color:#647a99;margin:0;padding:0 25px 18px}
.code-values-toolbar{display:flex;align-items:center;justify-content:space-between;gap:13px;padding:13px 22px;background:#f1f7ff;border-top:1px solid #dce8f9}
.code-values-toolbar b{font-size:15px;color:#304e73}
.code-values-toolbar b span{color:#2868d1;font-size:13px;margin-left:5px}
.code-values-toolbar :deep(.el-input){width:245px}
.document-row{display:flex;align-items:center;gap:17px;padding:21px 25px;border-bottom:1px solid #e5edf8}
.document-row:last-child{border-bottom:0}
.document-row:hover{background:#f7fbff}
.document-icon{display:grid;place-items:center;width:54px;height:54px;background:#eaf2ff;border:1px solid #c9ddf9;border-radius:13px;flex:none;color:#3676df}
.document-main{display:grid;gap:6px;flex:1;min-width:0}
.document-main b{font-size:16px;color:#25466f}
.document-main small{font:13px var(--dc-mono);color:#7a91b0}
.document-meta{display:grid;gap:4px;min-width:170px;color:#6882a1;font-size:13px;text-align:right}
.document-meta small{font-size:12px}
.document-row>svg{color:#9bb3d2;flex:none}
@media(max-width:1000px){.code-workspace{grid-template-columns:260px minmax(0,1fr)}.reference-toolbar{align-items:stretch;flex-direction:column}.toolbar-desc{justify-content:flex-start}.reference-search{max-width:none}}
@media(max-width:760px){.code-workspace{grid-template-columns:1fr}.code-items{max-height:230px}.reference-hero{padding:19px;gap:12px}.reference-total{display:none}.panel-heading{align-items:flex-start;flex-direction:column}.document-meta{display:none}.code-detail-head{align-items:flex-start;flex-direction:column}.code-values-toolbar{align-items:stretch;flex-direction:column}.code-values-toolbar :deep(.el-input){width:100%}.reference-hero h2{font-size:18px}.reference-hero-icon{width:47px;height:47px}}

/* Atlas 2.1 — enhanced intra-panel readability */

/* Gentle zebra stripes apply to dictionary rows, never to the entire card. */
.dictionary-table{background:#fff}
.dictionary-table thead th{position:sticky;top:0;z-index:2;background:#e6f0ff;border-bottom:2px solid #c4d9f4;color:#34567e}
.dictionary-table tbody tr:nth-child(odd){background:#fff}
.dictionary-table tbody tr:nth-child(even){background:#eef5ff}
.dictionary-table tbody tr:nth-child(even) td{border-bottom-color:#d6e5f8}
.dictionary-table tbody tr:hover{background:#dfeeff}
.dictionary-table tbody tr:focus-within{outline:2px solid #7cacef;outline-offset:-2px}
.dictionary-table td:first-child{border-left:3px solid transparent}
.dictionary-table tbody tr:nth-child(even) td:first-child{border-left-color:#bfd7f6}
.dictionary-table tbody tr:hover td:first-child{border-left-color:#3477e8}
.dictionary-table .description-cell{line-height:1.75}
.dictionary-table .row-link{padding:7px;border-radius:7px;background:#e3efff}
.dictionary-table .row-link:hover{background:#cdddff}
.code-items{background:#f2f7ff}
.code-item:nth-child(odd){background:#fff}
.code-item:nth-child(even){background:#eff6ff}
.code-item.active{background:#d9eaff!important;border-left:4px solid #2d6ee1;padding-left:11px}
.code-item:hover:not(.active){background:#e6f1ff}
.code-item:focus-visible,.alphabet button:focus-visible{outline:2px solid #367bf0;outline-offset:-2px}
.alphabet{background:#f8fbff}
.alphabet button.active{box-shadow:inset 0 -2px #2a6bec}
.document-row:nth-child(even){background:#f0f6ff}
.document-row:hover{background:#e7f0ff}
.document-row{border-bottom-color:#dce8f8}
@media(max-width:760px){.dictionary-table th,.dictionary-table td{padding:13px 15px}.table-clip{overscroll-behavior-x:contain}}

</style>
