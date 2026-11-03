<template>
  <div class="dc-page detail-page"><div class="dc-container page-inner">
    <div v-if="error" class="dc-empty">{{error}} <RouterLink to="/catalog">返回资产目录</RouterLink></div>
    <div v-else-if="loading" class="dc-empty">正在加载数据集详情…</div>
    <template v-else-if="data">
      <section class="dc-card heading">
        <div class="heading-line">
          <div class="identity"><div class="tags"><LayerTag :layer="data.layerCode"/><span class="status">{{statusLabel(data.status)}}</span></div>
            <h1>{{data.bizName}}</h1>
            <div class="technical"><code class="dc-tech">{{data.tableName}}</code><button title="复制表名" aria-label="复制表名" @click="copyText(data.tableName)"><Copy :size="14"/></button>
              <button v-if="loggedIn" class="favorite-button" :aria-pressed="favorited" @click="toggleFavorite"><Star :size="15" :fill="favorited?'currentColor':'none'"/>{{favorited?'已收藏':'收藏'}}</button>
            </div>
          </div>
          <details class="more"><summary>更多信息</summary><div><span>资产标识</span><code>{{data.assetId}}</code></div>
            <div><span>工作空间</span><code>{{data.workspaceCode||'—'}}</code></div>
            <div><span>所属目录</span><code>{{data.catalogCode||'—'}}</code></div></details>
        </div>
        <div class="metadata">
          <div><span>技术负责人</span><b>{{data.techOwner||'—'}}</b></div>
          <div><span>业务负责人</span><b>{{data.bizOwner||'—'}}</b></div>
          <div><span>更新频率</span><b>{{data.updateFreq||'—'}}</b></div>
          <div><span>最近更新</span><b>{{fmt(data.dataUpdatedAt)}}</b></div>
        </div>
      </section>
      <section class="dc-card body">
        <el-tabs v-model="tab" class="tabs">
          <el-tab-pane label="基本信息" name="overview">
            <div class="pane-scroll">
              <div class="definitions">
                <div><h2>业务定义</h2><p>{{data.bizDefinition||'暂无业务定义。'}}</p></div>
                <div><h2>统计口径</h2><p>{{data.statCaliber||'暂无统计口径。'}}</p></div>
              </div>
              <div class="property-grid">
                <div><span>数据粒度</span><b>{{data.grain||'—'}}</b></div>
                <div><span>数据来源</span><b>{{data.dataSourceDesc||'—'}}</b></div>
                <div><span>使用说明</span><b>{{data.usageNotes||'—'}}</b></div>
                <div><span>资产标签</span><div class="label-line"><span v-for="tag in tags" :key="tag.code" class="small-tag">{{tag.name}}</span><b v-if="!tags.length">—</b></div></div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="字段信息" name="columns">
            <div class="pane-flex">
              <div class="inline-toolbar"><b>{{filteredColumns.length}} 个字段</b>
                <el-input v-model="fieldQuery" clearable placeholder="字段名、中文名、业务定义"/></div>
              <div class="dc-table-wrap grow"><table class="dc-table">
                <thead><tr><th>序号</th><th>字段名</th><th>中文名</th><th>类型</th><th>业务定义</th><th>标准/码表</th></tr></thead>
                <tbody><tr v-for="field in visibleColumns" :key="field.assetId">
                  <td>{{field.ordinalNo}}</td>
                  <td><button class="field-link" @click="openField(field)"><code class="dc-tech">{{field.columnName}}</code></button></td>
                  <td><button class="field-link" @click="openField(field)">{{field.cnName||'—'}}</button></td>
                  <td>{{field.dataType}}</td><td>{{field.bizDefinition||'—'}}</td>
                  <td><RouterLink v-if="field.standardNo" class="foreign-link" :to="'/standards/'+field.standardNo">{{field.standardNo}}</RouterLink>
                    <RouterLink v-else-if="field.codeTableNo" class="foreign-link" :to="'/code-tables/'+field.codeTableNo">{{field.codeTableNo}}</RouterLink><span v-else>—</span></td>
                </tr></tbody>
              </table></div>
              <Pager v-model:page="fieldPage" :page-size="fieldPageSize" :total="filteredColumns.length"/>
            </div>
          </el-tab-pane>
          <el-tab-pane label="常用 SQL" name="sql">
            <div v-if="sqlRows.length" class="sql-workspace">
              <div class="sql-links">
                <button v-for="item in sqlRows" :key="item.sqlCode" :class="{selected:sqlCode===item.sqlCode}" @click="sqlCode=item.sqlCode">
                  <b>{{item.title}}</b><span>{{item.dialect}}</span>
                </button>
              </div>
              <div v-if="currentSql" class="sql-body"><div class="sql-head"><div><b>{{currentSql.title}}</b><p>{{currentSql.question||currentSql.description}}</p></div>
                  <button @click="copyText(currentSql.sqlText)">复制 SQL</button></div>
                <pre>{{currentSql.sqlText}}</pre>
              </div>
            </div><div v-else class="dc-empty">暂无常用 SQL。</div>
          </el-tab-pane>
          <el-tab-pane label="变更记录" name="changes">
            <div class="pane-flex"><div class="pane-scroll grow">
              <div v-for="item in visibleChanges" :key="item.id" class="change-row">
                <time>{{fmt(item.changeDate)}}</time><div><b>{{item.changeType}}</b><p>{{item.content}}</p><small>{{item.changedBy||'系统'}}</small></div>
              </div><div v-if="!changes.length" class="dc-empty">暂无变更记录。</div>
            </div><Pager v-model:page="changePage" :page-size="8" :total="changes.length"/></div>
          </el-tab-pane>
          <el-tab-pane label="血缘关系" name="relations">
            <div class="pane-scroll">
              <div class="relation-stats"><span>上游 {{relations.upstream.length}} 个</span><span>当前资产</span><span>下游 {{relations.downstream.length}} 个</span></div>
              <div v-for="(item,i) in allRelations" :key="item.srcAssetId+'-'+item.dstAssetId+'-'+i" class="relation-row">
                <RouterLink :to="'/datasets/'+item.srcAssetId">{{item.srcName}}</RouterLink><ArrowRight :size="16"/>
                <RouterLink :to="'/datasets/'+item.dstAssetId">{{item.dstName}}</RouterLink><small>{{item.taskName||'—'}}</small>
              </div>
              <div v-if="!allRelations.length" class="dc-empty">暂无血缘关系。</div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="调度与运行" name="schedule">
            <div class="pane-scroll"><div class="property-grid">
              <div><span>调度计划</span><b>{{data.scheduleDesc||'—'}}</b></div>
              <div><span>调度节点</span><code class="dc-tech">{{data.scheduleNode||'—'}}</code></div>
              <div><span>数据量（行）</span><b>{{number(data.rowCount)}}</b></div>
              <div><span>存储量（字节）</span><b>{{number(data.storageBytes)}}</b></div>
            </div></div>
          </el-tab-pane>
        </el-tabs>
      </section>
      <el-drawer v-model="drawerOpen" title="字段详情" :size="drawerSize" @close="closeField">
        <div v-if="selectedField" class="field-drawer">
          <span class="drawer-label">字段</span><h2>{{selectedField.cnName||selectedField.columnName}}</h2>
          <div class="field-tech"><code class="dc-tech">{{selectedField.columnName}}</code><button @click="copyText(selectedField.columnName)" title="复制字段名"><Copy :size="15"/></button></div>
          <p>{{selectedField.bizDefinition||'暂无业务定义。'}}</p>
          <div class="property-grid drawer-properties">
            <div><span>数据类型</span><b>{{selectedField.dataType}}</b></div>
            <div><span>字段序号</span><b>{{selectedField.ordinalNo}}</b></div>
            <div><span>单位</span><b>{{selectedField.unit||'—'}}</b></div>
            <div><span>稳定标识</span><code>{{selectedField.assetId}}</code></div>
          </div>
          <div class="field-links">
            <RouterLink v-if="selectedField.standardNo" :to="'/standards/'+selectedField.standardNo">数据标准：{{selectedField.standardNo}}</RouterLink>
            <RouterLink v-if="selectedField.codeTableNo" :to="'/code-tables/'+selectedField.codeTableNo">关联码表：{{selectedField.codeTableNo}}</RouterLink>
          </div>
        </div>
      </el-drawer>
    </template>
  </div></div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, Copy, Star } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { assetApi, activityApi } from '@/api/client'
import api from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'
import Pager from '@/components/Pager.vue'
import { statusLabel } from '@/utils/labels'
const route=useRoute(),router=useRouter(),data=ref<any|null>(null),loading=ref(true),error=ref('')
const columns=ref<any[]>([]),tags=ref<any[]>([]),sqlRows=ref<any[]>([]),changes=ref<any[]>([])
const relations=ref<any>({upstream:[],downstream:[]})
const tab=ref('overview'),fieldQuery=ref(''),fieldPage=ref(1),changePage=ref(1),sqlCode=ref('')
const selectedField=ref<any|null>(null),drawerOpen=ref(false)
const loggedIn=ref(Boolean(localStorage.getItem('datacontrol_token'))),favorited=ref(false)
const drawerSize=ref('440px')
const fieldPageSize=8
const filteredColumns=computed(()=>{
 const k=fieldQuery.value.trim().toLowerCase()
 return k?columns.value.filter(x=>(String(x.columnName)+' '+(x.cnName||'')+' '+(x.bizDefinition||'')).toLowerCase().includes(k)):columns.value
})
const visibleColumns=computed(()=>filteredColumns.value.slice((fieldPage.value-1)*fieldPageSize,fieldPage.value*fieldPageSize))
const visibleChanges=computed(()=>changes.value.slice((changePage.value-1)*8,changePage.value*8))
const allRelations=computed<any[]>(()=>[...(relations.value.upstream||[]),...(relations.value.downstream||[])])
const currentSql=computed(()=>sqlRows.value.find(x=>x.sqlCode===sqlCode.value)||sqlRows.value[0]||null)
function fmt(v?:string){return v?String(v).replace('T',' ').slice(0,16):'—'}
function number(n?:number){return n===undefined||n===null?'—':Number(n).toLocaleString()}
async function copyText(text:string){try{await navigator.clipboard.writeText(text);ElMessage.success('已复制')}catch{ElMessage.warning('复制失败，请手动选择文本')}}
async function toggleFavorite(){
 if(!data.value)return
 try{
  if(favorited.value)await activityApi.removeFavorite(data.value.assetId)
  else await activityApi.addFavorite(data.value.assetId)
  favorited.value=!favorited.value
  ElMessage.success(favorited.value?'已加入收藏':'已取消收藏')
 }catch{ElMessage.error('收藏操作失败')}
}
function openField(field:any){
 selectedField.value=field;drawerOpen.value=true;tab.value='columns'
 router.replace({query:{...route.query,tab:'columns',field:field.assetId}})
}
function closeField(){
 if(route.query.field){const query={...route.query};delete query.field;router.replace({query})}
 selectedField.value=null
}
async function resolveField(){
 const id=String(route.query.field||'')
 if(!id){drawerOpen.value=false;selectedField.value=null;return}
 const row=columns.value.find(x=>x.assetId===id)
 try{selectedField.value=row||await api.get('/columns/'+encodeURIComponent(id))}
 catch{selectedField.value=null}
 if(selectedField.value?.datasetId && selectedField.value.datasetId!==String(route.params.id))return
 if(selectedField.value){tab.value='columns';drawerOpen.value=true}
}
let seq=0
async function load(id:string){
 const request=++seq;loading.value=true;error.value='';data.value=null;columns.value=[];tags.value=[];sqlRows.value=[];changes.value=[];relations.value={upstream:[],downstream:[]}
 drawerOpen.value=false;selectedField.value=null;tab.value=String(route.query.tab||'overview')
 try{
  const dataset=await assetApi.table(id)
  if(request!==seq)return
  data.value=dataset
  const results=await Promise.allSettled([
    assetApi.columns({dataset_id:id,limit:500}),assetApi.tags(id),assetApi.commonSql(id),
    assetApi.changes(id),assetApi.relations(id),activityApi.recordView(id),
    loggedIn.value?activityApi.favorites():Promise.resolve([])
  ])
  if(request!==seq)return
  if(results[0].status==='fulfilled')columns.value=results[0].value as any[]
  if(results[1].status==='fulfilled')tags.value=results[1].value as any[]
  if(results[2].status==='fulfilled')sqlRows.value=results[2].value as any[]
  if(results[3].status==='fulfilled')changes.value=results[3].value as any[]
  if(results[4].status==='fulfilled')relations.value=results[4].value as any
  if(results[6].status==='fulfilled')favorited.value=(results[6].value as any[]).some(x=>x.assetType==='TABLE'&&x.assetId===id)
  if(sqlRows.value.length)sqlCode.value=sqlRows.value[0].sqlCode
  drawerSize.value=window.innerWidth<540?'92%':'440px'
  await resolveField()
 }catch{if(request===seq)error.value='无法加载数据集详情。'}
 finally{if(request===seq)loading.value=false}
}
watch(()=>route.params.id,id=>{if(typeof id==='string')load(id)},{immediate:true})
watch(()=>route.query.field,()=>{if(!loading.value)resolveField()})
watch(()=>route.query.tab,v=>{if(typeof v==='string'&&v!==tab.value)tab.value=v})
watch(fieldQuery,()=>fieldPage.value=1)
</script>
<style scoped>
.detail-page{height:100%;min-height:520px}.page-inner{height:100%;display:flex;flex-direction:column;min-height:0;gap:12px}
.heading{padding:13px 18px 0;flex:0 0 auto}
.heading-line{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}
.identity{min-width:0}.tags{display:flex;gap:8px;align-items:center}.status{font-size:12px;color:var(--dc-success)}
.heading h1{font-size:19px;margin:4px 0}
.technical{display:flex;align-items:center;gap:9px}.technical code{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.technical button,.field-tech button{border:0;color:var(--dc-primary-strong);background:transparent}
.technical .favorite-button{display:flex;align-items:center;gap:5px;padding:4px 8px;border:1px solid var(--dc-border);border-radius:5px;font-size:12px;white-space:nowrap}
.more{position:relative;font-size:12px;color:var(--dc-primary-strong);margin-top:5px}
.more summary{cursor:pointer}.more>div{display:flex;gap:9px;justify-content:space-between;margin-top:8px}
.more code{color:var(--dc-text-2);max-width:220px;overflow-wrap:anywhere}
.metadata{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--dc-border);margin-top:12px}
.metadata>div{padding:9px 13px 11px;border-right:1px solid var(--dc-border)}
.metadata>div:last-child{border-right:0}.metadata span,.property-grid span{display:block;color:var(--dc-text-2);font-size:12px;margin-bottom:5px}
.metadata b,.property-grid b,.property-grid code{font-size:12px;overflow-wrap:anywhere}
.body{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden;padding:0 14px}
.tabs{height:100%;min-height:0;display:flex;flex-direction:column}
.tabs :deep(.el-tabs__header){flex:0 0 auto;margin:0 0 10px}
.tabs :deep(.el-tabs__content){flex:1;min-height:0}
.tabs :deep(.el-tab-pane){height:100%;min-height:0}
.pane-scroll{height:100%;min-height:0;overflow:auto}
.pane-flex{height:100%;min-height:0;display:flex;flex-direction:column;gap:9px}
.grow{flex:1;min-height:0}
.definitions{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.definitions>div{padding:14px;border:1px solid var(--dc-border);border-radius:6px;min-height:110px}
.definitions h2{font-size:14px;margin:0 0 8px}.definitions p{font-size:13px;line-height:1.7;color:var(--dc-text-2);margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.property-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.property-grid>div{border:1px solid var(--dc-border);background:#f8fbfd;padding:12px;border-radius:6px;min-width:0}
.label-line{display:flex;gap:5px;flex-wrap:wrap}.small-tag{padding:3px 7px;border-radius:5px;background:#eaf4fa;color:var(--dc-primary-strong);font-size:12px}
.inline-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px}.inline-toolbar b{font-size:13px}.inline-toolbar :deep(.el-input){width:260px}
.dc-table{min-width:750px}.dc-table th,.dc-table td{padding:10px;font-size:12px}
.field-link{border:0;background:transparent;color:var(--dc-primary-strong);padding:2px;text-align:left}.field-link code{color:var(--dc-primary-strong)}
.foreign-link{color:var(--dc-primary-strong)}
.sql-workspace{height:100%;display:grid;grid-template-columns:225px minmax(0,1fr);gap:10px;min-height:0}
.sql-links{border-right:1px solid var(--dc-border);overflow:auto;padding-right:8px}
.sql-links button{border:0;border-radius:6px;background:transparent;display:grid;text-align:left;padding:12px;width:100%;gap:5px}
.sql-links button.selected,.sql-links button:hover{background:var(--dc-primary-soft)}.sql-links button b{font-size:12px}
.sql-links button span{font-size:12px;color:var(--dc-text-2)}
.sql-body{min-width:0;display:flex;flex-direction:column;overflow:hidden}
.sql-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;padding:5px 0 10px}
.sql-head b{font-size:13px}.sql-head p{font-size:12px;color:var(--dc-text-2);margin:5px 0}
.sql-head button{border:1px solid var(--dc-border-strong);background:white;border-radius:5px;padding:6px 9px;color:var(--dc-primary-strong);white-space:nowrap}
.sql-body pre{flex:1;min-height:0;overflow:auto;margin:0;padding:15px;background:#142b3c;color:#e8f2f8;border-radius:6px;font-size:12px;line-height:1.65}
.change-row{display:grid;grid-template-columns:140px minmax(0,1fr);gap:12px;padding:13px 4px;border-bottom:1px solid #eaf0f4;font-size:12px}
.change-row time,.change-row small{color:var(--dc-text-2)}.change-row p{margin:5px 0;white-space:pre-wrap}
.relation-stats{display:flex;justify-content:center;gap:16px;padding:16px;border-bottom:1px solid var(--dc-border);font-size:13px}
.relation-stats span{background:#eff7fb;padding:9px;border-radius:6px}
.relation-row{display:flex;gap:10px;align-items:center;padding:12px;border-bottom:1px solid var(--dc-border);font-size:13px;flex-wrap:wrap}
.relation-row a{color:var(--dc-primary-strong)}.relation-row small{margin-left:auto;color:var(--dc-text-2)}
.field-drawer h2{font-size:20px;margin:6px 0}.drawer-label{font-size:12px;color:var(--dc-text-2)}
.field-tech{display:flex;align-items:center;gap:8px}.field-drawer>p{font-size:13px;line-height:1.7;color:var(--dc-text-2);white-space:pre-wrap}
.drawer-properties{grid-template-columns:1fr 1fr}.field-links{margin-top:20px;display:grid;gap:12px}.field-links a{color:var(--dc-primary-strong);font-size:13px}
@media(max-width:820px){.detail-page,.page-inner{height:auto}.heading-line{flex-wrap:wrap}.metadata{grid-template-columns:repeat(2,1fr)}.body{min-height:500px}.tabs :deep(.el-tabs__content){min-height:440px}.definitions{grid-template-columns:1fr}}
@media(max-width:550px){.drawer-properties{grid-template-columns:1fr}.sql-workspace{grid-template-columns:1fr;grid-template-rows:120px minmax(250px,1fr)}.sql-links{border-right:0;border-bottom:1px solid var(--dc-border)}.inline-toolbar :deep(.el-input){width:180px}}
</style>
