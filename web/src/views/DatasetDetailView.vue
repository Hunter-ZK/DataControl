<template>
  <div class="dc-page"><div class="dc-container">
    <section v-if="data" class="detail-head dc-card">
      <div class="head-main"><div class="head-tags"><LayerTag :layer="data.layerCode" /><span class="status">● {{formatStatus(data.status)}}</span></div><h1>{{data.bizName}}</h1><code class="dc-tech">{{data.tableName}}</code><p>{{data.catalogCode}}</p></div>
      <div class="head-actions"><el-button @click="copyName"><Copy :size="15"/>复制表名</el-button></div>
    </section>

    <section v-if="data" class="meta-strip dc-card">
      <div><span>技术负责人</span><b>{{data.techOwner||'—'}}</b></div><div><span>业务负责人</span><b>{{data.bizOwner||'—'}}</b></div><div><span>更新频率</span><b>{{data.updateFreq||'—'}}</b></div><div><span>最近更新</span><b>{{formatTime(data.dataUpdatedAt)}}</b></div><div><span>工作空间</span><b>{{data.workspaceCode||'—'}}</b></div>
    </section>

    <div v-if="data" class="detail-layout">
      <section class="dc-card detail-main">
        <el-tabs v-model="tab">
          <el-tab-pane label="基本信息" name="overview"><div class="section-block"><h2>资产定义</h2><p>{{data.bizDefinition||'暂无业务定义。'}}</p><div class="caliber"><b>统计口径</b><p>{{data.statCaliber||'暂无统计口径。'}}</p></div><div class="kv-grid"><div><span>数据粒度</span><b>{{data.grain||'—'}}</b></div><div><span>数据来源</span><b>{{data.dataSourceDesc||'—'}}</b></div><div><span>使用说明</span><b>{{data.usageNotes||'—'}}</b></div></div></div></el-tab-pane>
          <el-tab-pane label="字段信息" name="columns">
            <div class="table-actions"><b>{{filteredColumns.length}} 个字段</b><el-input v-model="columnKeyword" clearable placeholder="搜索字段"/></div>
            <div ref="columnsEl" class="dc-table-wrap columns-table">
              <table class="dc-table"><thead><tr><th>序号</th><th>字段名</th><th>中文名</th><th>类型</th><th>业务定义</th><th>标准/码表</th></tr></thead>
                <tbody>
                  <tr v-for="c in visibleColumns" :key="c.assetId">
                    <td>{{c.ordinalNo}}</td>
                    <td><button class="field-link" type="button" @click="openField(c)"><code class="dc-tech">{{c.columnName}}</code></button></td>
                    <td><button class="field-link" type="button" @click="openField(c)">{{c.cnName||'—'}}</button></td>
                    <td>{{c.dataType}}</td><td>{{c.bizDefinition||'—'}}</td>
                    <td><RouterLink v-if="c.standardNo" :to="`/standards/${c.standardNo}`" class="dc-chip">{{c.standardNo}}</RouterLink><RouterLink v-else-if="c.codeTableNo" :to="`/code-tables/${c.codeTableNo}`" class="dc-chip">{{c.codeTableNo}}</RouterLink><span v-else>—</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <Pager v-model:page="columnsPage" :page-size="columnsPageSize" :total="filteredColumns.length"/>
          </el-tab-pane>
          <el-tab-pane label="常用 SQL" name="sql">
            <div v-if="sqlRows.length" class="sql-workspace">
              <div class="sql-select-list">
                <button v-for="(x,index) in sqlRows" :key="x.sqlCode" type="button" :class="{active:selectedSqlIndex===index}" @click="selectedSqlIndex=index">
                  <span class="dc-chip">{{x.dialect}}</span><b>{{x.title}}</b><small>{{x.question}}</small>
                </button>
              </div>
              <div v-if="selectedSql" class="sql-code-panel">
                <div class="sql-code-head"><div><h3>{{selectedSql.title}}</h3><p>{{selectedSql.question}}</p></div><el-button size="small" @click="copySql"><Copy :size="14"/>复制 SQL</el-button></div>
                <pre>{{selectedSql.sqlText}}</pre>
              </div>
            </div>
            <div v-else class="dc-empty">暂无常用 SQL。</div>
          </el-tab-pane>
          <el-tab-pane label="变更记录" name="changes">
            <div ref="changesEl" class="timeline" v-if="changes.length">
              <article v-for="x in visibleChanges" :key="x.id"><span>{{formatTime(x.changeDate)}}</span><div><b>{{x.changeType}}</b><p>{{x.content}}</p><small>{{x.changedBy||'系统'}}</small></div></article>
            </div>
            <div v-else class="dc-empty">暂无变更记录。</div>
            <Pager v-if="changes.length" v-model:page="changesPage" :page-size="changesPageSize" :total="changes.length"/>
          </el-tab-pane>
          <el-tab-pane label="血缘关系" name="relations">
            <div class="relation-summary"><div><span>上游</span><strong>{{relations.upstream.length || 0}}</strong></div><ArrowRight/><div class="current-node"><span>当前资产</span><strong>{{data.layerCode}}</strong></div><ArrowRight/><div><span>下游</span><strong>{{relations.downstream?.length||0}</strong></div></div>
            <div v-if="relationItems.length" ref="relationsEl" class="relation-list"><article v-for="x in visibleRelations" :key="x.srcAssetId + '-' + x.dstAssetId"><RouterLink :to="'/datasets/' + x.srcAssetId"><b>{{x.srcName}}</b></RouterLink><ArrowRight :size="14"/><RouterLink :to="'/datasets/' + x.dstAssetId"><b>{{x.dstName}}</b></RouterLink><span>{{x.taskName}}</span></article></div>
            <div v-else class="dc-empty">暂无血缘关系。</div>
            <Pager v-if="relationItems.length" v-model:page="relationsPage" :page-size="relationsPageSize" :total="relationItems.length"/>
          </el-tab-pane>
          <el-tab-pane label="调度与运行" name="schedule"><div class="schedule-grid"><div><span>调度计划</span><b>{{data.scheduleDesc||'—'}}</b></div><div><span>调度节点</span><code class="dc-tech">{{data.scheduleNode||'—'}}</code></div></div></el-tab-pane>
        </el-tabs>
      </section>

      <aside class="detail-side">
        <section class="dc-card side-card"><h3>资产标签</h3><div class="tag-wrap"><span v-for="x in tags" :key="x.code" class="dc-chip">{{x.name}}</span><span v-if="!tags.length" class="dc-muted">暂无标签</span></div></section>
        <details class="dc-card side-card more-info"><summary>更多信息</summary><dl><div><dt>资产标识</dt><dd class="dc-tech">{{data.assetId}}</dd></div></dl></details>
      </aside>
    </div>
    <div v-else class="dc-empty">正在加载数据集详情…</div>
    <el-drawer v-model="fieldDrawerOpen" :title="fieldDrawerTitle" size="420px" @closed="clearFieldQuery">
      <div v-if="selectedField" class="field-drawer-content">
        <div><span>字段名</span><code class="dc-tech">{{selectedField.columnName}}</code></div>
        <div><span>中文名称</span><b>{{selectedField.cnName||'—'}}</b></div>
        <p>{{selectedField.bizDefinition||'暂无业务定义。'}}</p>
        <div class="field-drawer-grid">
          <div><span>数据类型</span><b>{{selectedField.dataType||'—'}}</b></div>
          <div><span>字段序号</span><b>{{selectedField.ordinalNo??'—'}}</b></div>
          <div><span>单位</span><b>{{selectedField.unit||'—'}}</b></div>
          <div><span>资产标识</span><code class="dc-tech">{{selectedField.assetId||'—'}}</code></div>
        </div>
        <div class="field-associations">
          <div><span>数据标准</span><RouterLink v-if="selectedField.standardNo" :to="`/standards/${selectedField.standardNo}`">{{selectedField.standardNo}}</RouterLink><b v-else>未关联</b></div>
          <div><span>码表</span><RouterLink v-if="selectedField.codeTableNo" :to="`/code-tables/${selectedField.codeTableNo}`">{{selectedField.codeTableNo}}</RouterLink><b v-else>未关联</b></div>
        </div>
      </div>
    </el-drawer>
  </div></div>
</template>

<script setup lang="ts">
import { computed, inject, reactive, ref, watch, type Ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowRight, Copy } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import api, { activityApi, assetApi } from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'
import Pager from '@/components/Pager.vue'
import { useFitPageSize } from '@/composables/useFitPageSize'
import { statusLabel } from '@/utils/labels'
const route=useRoute(); const router=useRouter(); const pageContextTitle=inject<Ref<string>>('dataControlPageTitle'); const data=ref<any|null>(null); const columns=ref<any[]>([]); const tags=ref<any[]>([]); const sqlRows=ref<any[]>([]); const changes=ref<any[]>([]); const relations=reactive<any>({upstream:[],downstream:[]}); const tab=ref('overview'); const columnKeyword=ref('')
const columnsEl=ref<HTMLElement|null>(null); const columnsPageSize=useFitPageSize(columnsEl,44,5); const columnsPage=ref(1)
const changesEl=ref<HTMLElement|null>(null); const changesPageSize=useFitPageSize(changesEl,62,5); const changesPage=ref(1)
const relationsEl=ref<HTMLElement|null>(null); const relationsPageSize=useFitPageSize(relationsEl,46,5); const relationsPage=ref(1)
const fieldDrawerOpen=ref(false); const selectedField=ref<any|null>(null); const selectedSqlIndex=ref(0)
const filteredColumns=computed(()=>{const k=columnKeyword.value.trim().toLowerCase();return k?columns.value.filter(x=>`${x.columnName} ${x.cnName||''} ${x.bizDefinition||''}`.toLowerCase().includes(k)):columns.value})
const visibleColumns=computed(()=>{const start=(columnsPage.value-1)*columnsPageSize.value;return filteredColumns.value.slice(start,start+columnsPageSize.value)})
const visibleChanges=computed(()=>{const start=(changesPage.value-1)*changesPageSize.value;return changes.value.slice(start,start+changesPageSize.value)})
const relationItems=computed(()=>[...(relations.upstream||[]),...(relations.downstream||[])])
const visibleRelations=computed(()=>{const start=(relationsPage.value-1)*relationsPageSize.value;return relationItems.value.slice(start,start+relationsPageSize.value)})
const selectedSql=computed(()=>sqlRows.value[selectedSqlIndex.value]||sqlRows.value[0]||null)
const fieldDrawerTitle=computed(()=>selectedField.value?.cnName||selectedField.value?.columnName||'字段详情')
watch([columnKeyword,columnsPageSize],()=>{columnsPage.value=1})
watch(sqlRows,()=>{selectedSqlIndex.value=0})
watch([changesPageSize,relationsPageSize],()=>{changesPage.value=1;relationsPage.value=1})
watch(()=>route.query.field,()=>{void syncFieldDrawer()})
function formatTime(v?:string){return v?String(v).replace('T',' ').slice(0,16):'—'}
function formatStatus(v?:string){return statusLabel(v)}
async function copyName(){if(!data.value)return;await navigator.clipboard.writeText(data.value.tableName);ElMessage.success('已复制表名')}
async function copySql(){if(!selectedSql.value?.sqlText)return;await navigator.clipboard.writeText(selectedSql.value.sqlText);ElMessage.success('已复制 SQL')}
async function openField(field:any){selectedField.value=field;fieldDrawerOpen.value=true;await router.replace({query:{...route.query,field:String(field.assetId)}})}
async function syncFieldDrawer(){const id=String(route.query.field||'');if(!id){selectedField.value=null;fieldDrawerOpen.value=false;return}let field=columns.value.find(x=>String(x.assetId)===id);if(!field){try{field=await api.get(`/columns/${encodeURIComponent(id)}`)}catch{field=null}}if(field){selectedField.value=field;fieldDrawerOpen.value=true}}
function clearFieldQuery(){if(!route.query.field)return;const query={...route.query};delete query.field;void router.replace({query})}
async function loadDataset(){const id=String(route.params.id);data.value=await assetApi.table(id);if(pageContextTitle)pageContextTitle.value=data.value.bizName||data.value.tableName||'数据集详情';columns.value=[];changes.value=[];sqlRows.value=[];relations.upstream=[];relations.downstream=[];selectedSqlIndex.value=0;await Promise.allSettled([assetApi.columns({dataset_id:id,limit:500}).then((v:any)=>columns.value=v),assetApi.tags(id).then((v:any)=>tags.value=v),assetApi.commonSql(id).then((v:any)=>sqlRows.value=v),assetApi.changes(id).then((v:any)=>changes.value=v),assetApi.relations(id).then((v:any)=>Object.assign(relations,v)),activityApi.recordView(id)]);columnsPage.value=1;changesPage.value=1;relationsPage.value=1;await syncFieldDrawer()}
watch(()=>route.params.id,()=>{void loadDataset()},{immediate:true})
</script>

<style scoped>
.detail-head{padding:18px 22px;display:flex;justify-content:space-between;gap:24px;align-items:center}.head-main{min-width:0}.head-tags{display:flex;gap:8px;align-items:center}.status{font-size:12px;color:var(--dc-success)}.detail-head h1{font-size:25px;margin:7px 0 4px}.detail-head code{font-size:12px}.detail-head p{font-size:12px;color:var(--dc-text-3);margin:7px 0 0}.head-actions{display:flex;gap:8px;flex-wrap:wrap}.head-actions :deep(.el-button>span){display:flex;align-items:center;gap:6px}.meta-strip{margin-top:14px;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}.meta-strip>div{padding:17px 20px;border-right:1px solid var(--dc-border)}.meta-strip>div:last-child{border:0}.meta-strip span,.kv-grid span,.schedule-grid span{display:block;color:var(--dc-text-3);font-size:12px;margin-bottom:5px}.meta-strip b{font-size:12px}.detail-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px;align-items:start}.detail-main{padding:6px 22px 22px;min-width:0}.detail-main :deep(.el-tabs__header){margin-bottom:20px}.section-block h2{font-size:19px;margin:6px 0 10px}.section-block>p{font-size:13px;line-height:1.75;color:var(--dc-text-2)}.caliber{margin-top:18px;padding:16px 18px;border-radius:12px;background:linear-gradient(135deg,#eef9fd,#f8fcfe);border:1px solid #d8ebf4}.caliber b{font-size:12px;color:#347d9d}.caliber p{font-size:12px;line-height:1.7;margin:7px 0 0}.kv-grid,.schedule-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}.kv-grid>div,.schedule-grid>div{padding:15px;border:1px solid var(--dc-border);border-radius:11px}.kv-grid b,.schedule-grid b,.schedule-grid code{font-size:12px;line-height:1.55}.detail-side{display:grid;gap:14px}.side-card{padding:18px}.side-card h3{font-size:15px;margin:6px 0 14px}.side-card dl{margin:0;display:grid;gap:12px}.side-card dl div{display:grid;gap:4px}.side-card dt{font-size:12px;color:var(--dc-text-3)}.side-card dd{margin:0;font-size:12px;overflow-wrap:anywhere}.tag-wrap{display:flex;gap:7px;flex-wrap:wrap}.table-actions{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.table-actions :deep(.el-input){width:240px}.field-link{border:0;background:transparent;padding:0;color:var(--dc-primary-strong);cursor:pointer;text-align:left}.columns-table{max-height:calc(100vh - 440px);min-height:220px;overflow:auto}.more-info summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--dc-text)}.more-info dl{margin:14px 0 0}.more-info dl div{display:grid;gap:4px}.field-drawer-content{display:grid;gap:16px}.field-drawer-content>div>span,.field-associations span{display:block;margin-bottom:5px;color:var(--dc-text-2);font-size:12px}.field-drawer-content>div>b,.field-drawer-content>div>code,.field-associations a,.field-associations b{font-size:13px}.field-drawer-content>p{margin:0;color:var(--dc-text-2);font-size:13px;line-height:1.7}.field-drawer-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.field-drawer-grid>div,.field-associations>div{padding:12px;border:1px solid var(--dc-border);border-radius:10px}.field-associations{display:grid;gap:10px}.field-associations a{color:var(--dc-primary-strong)}.sql-workspace{display:grid;grid-template-columns:240px minmax(0,1fr);gap:14px;min-width:0}.sql-select-list{display:grid;align-content:start;gap:8px;max-height:calc(100vh - 440px);overflow:auto}.sql-select-list button{display:grid;gap:6px;padding:12px;border:1px solid var(--dc-border);border-radius:11px;background:#fff;text-align:left;cursor:pointer}.sql-select-list button:hover,.sql-select-list button.active{border-color:#bcddea;background:#f5fbfe}.sql-select-list button b{font-size:13px;color:var(--dc-text)}.sql-select-list button small{font-size:12px;color:var(--dc-text-2);line-height:1.45}.sql-code-panel{min-width:0;border:1px solid var(--dc-border);border-radius:12px;overflow:hidden}.sql-code-head{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 16px;background:#fff;border-bottom:1px solid var(--dc-border)}.sql-code-head h3{font-size:14px;margin:0 0 4px}.sql-code-head p{font-size:12px;color:var(--dc-text-2);margin:0}.sql-code-panel pre{margin:0;padding:17px;max-height:calc(100vh - 500px);min-height:220px;overflow:auto;background:#122738;color:#d9eef9;font-size:12px;line-height:1.65}.timeline{display:grid;gap:0;max-height:calc(100vh - 440px);overflow:auto}.timeline article{display:grid;grid-template-columns:120px minmax(0,1fr);gap:18px;padding:14px 0;border-bottom:1px solid #edf2f5}.timeline article>span{font-size:12px;color:var(--dc-text-3)}.timeline b{font-size:12px}.timeline p{font-size:12px;color:var(--dc-text-2);margin:5px 0}.timeline small{color:#8ca0ad}.relation-summary{display:flex;align-items:center;justify-content:center;gap:18px;padding:26px 10px}.relation-summary>div{min-width:120px;text-align:center;padding:15px;border:1px solid var(--dc-border);border-radius:12px}.relation-summary span{display:block;font-size:12px;color:var(--dc-text-3)}.relation-summary strong{display:block;margin-top:6px}.current-node{background:var(--dc-primary-soft);border-color:#cae6f1!important}.relation-list{display:grid;gap:8px;max-height:calc(100vh - 470px);overflow:auto}.relation-list article{display:flex;align-items:center;gap:8px;padding:10px;border:1px solid #edf2f5;border-radius:9px;font-size:12px}.relation-list article a{color:#315e75}.relation-list article span{margin-left:auto;color:var(--dc-text-3)}@media(max-width:1100px){.meta-strip{grid-template-columns:repeat(3,1fr)}.meta-strip>div:nth-child(3){border-right:0}.detail-layout{grid-template-columns:1fr}.detail-side{grid-template-columns:1fr 1fr}}@media(max-width:820px){.columns-table,.timeline,.relation-list,.sql-select-list{max-height:none;overflow:visible}.sql-code-panel pre{max-height:360px;overflow:auto}}@media(max-width:760px){.sql-workspace{grid-template-columns:1fr}.sql-select-list{max-height:210px}.sql-code-panel pre{max-height:360px}.detail-head{align-items:flex-start;flex-direction:column}.meta-strip{grid-template-columns:1fr 1fr}.meta-strip>div{border-right:1px solid var(--dc-border)!important;border-bottom:1px solid var(--dc-border)}.meta-strip>div:nth-child(2n){border-right:0!important}.kv-grid,.schedule-grid,.detail-side{grid-template-columns:1fr}.table-actions{align-items:flex-start;flex-direction:column;gap:9px}.table-actions :deep(.el-input){width:100%}.relation-summary{gap:8px}.relation-summary>div{min-width:0;flex:1;padding:12px 6px}}@media(max-width:520px){.detail-main{padding:4px 14px 16px}.head-actions{width:100%}.head-actions :deep(.el-button){flex:1}.meta-strip{grid-template-columns:1fr}.meta-strip>div{border-right:0!important}.relation-list article{align-items:flex-start;flex-direction:column}.relation-list article span{margin-left:0}}
</style>
