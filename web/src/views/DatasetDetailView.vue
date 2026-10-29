<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回资产列表</button>
    <section v-if="data" class="detail-head dc-card">
      <div class="head-main"><div class="head-tags"><AssetIcon type="TABLE" :size="18"/><span class="dc-chip">{{data.layerCode}}</span><span class="status"><CircleCheck v-if="data.status==='ONLINE'" :size="13"/><Clock3 v-else :size="13"/>{{data.status==='ONLINE'?'在用':data.status}}</span></div><h1>{{data.bizName}}</h1><code class="dc-tech">{{data.tableName}}</code><p>{{data.catalogCode}} · {{data.assetId}}</p></div>
      <AssetOperationBar kind="TABLE" :asset="data" :columns="columns" :columns-complete="columnsComplete"/>
    </section>

    <section v-if="data" class="meta-strip dc-card">
      <div><span>技术负责人</span><b>{{data.techOwner||'—'}}</b></div><div><span>业务负责人</span><b>{{data.bizOwner||'—'}}</b></div><div><span>更新频率</span><b>{{data.updateFreq||'—'}}</b></div><div><span>最近更新</span><b>{{formatTime(data.dataUpdatedAt)}}</b></div><div><span>工作空间</span><b>{{data.workspaceCode||'—'}}</b></div>
    </section>

    <div v-if="data" class="detail-layout">
      <section class="dc-card detail-main">
        <el-tabs v-model="tab">
          <el-tab-pane label="基本信息" name="overview"><div class="section-block"><span class="dc-eyebrow">OVERVIEW</span><h2>资产定义</h2><p>{{data.bizDefinition||'暂无业务定义。'}}</p><div class="caliber"><b>统计口径</b><p>{{data.statCaliber||'暂无统计口径。'}}</p></div><div class="kv-grid"><div><span>数据粒度</span><b>{{data.grain||'—'}}</b></div><div><span>数据来源</span><b>{{data.dataSourceDesc||'—'}}</b></div><div><span>使用说明</span><b>{{data.usageNotes||'—'}}</b></div><div><span>所属目录</span><b>{{data.catalogCode||'—'}}</b></div></div></div></el-tab-pane>
          <el-tab-pane label="字段信息" name="columns"><div class="table-actions"><b>{{columns.length}} 个字段</b><el-input v-model="columnKeyword" clearable placeholder="搜索字段"/></div><div class="dc-table-wrap"><table class="dc-table"><thead><tr><th>序号</th><th>字段名</th><th>中文名</th><th>类型</th><th>业务定义</th><th>标准/码表</th></tr></thead><tbody><tr v-for="c in filteredColumns" :key="c.assetId"><td>{{c.ordinalNo}}</td><td><RouterLink class="field-link field-with-icon" :to="`/fields/${c.assetId}`"><AssetIcon type="COLUMN" :size="16" mode="inline"/><code class="dc-tech">{{c.columnName}}</code></RouterLink></td><td><RouterLink class="field-link" :to="`/fields/${c.assetId}`">{{c.cnName||'—'}}</RouterLink></td><td><span class="data-type"><Code2 :size="13"/>{{c.dataType}}</span></td><td>{{c.bizDefinition||'—'}}</td><td><div class="reference-actions">
  <button v-if="c.standardNo" class="reference-preview" :title="'速览数据标准 '+c.standardNo" @click="openPreview('STANDARD',c.standardNo)"><AssetIcon type="STANDARD" :size="14" mode="inline"/>{{c.standardNo}}<PanelRightOpen :size="13"/></button>
  <button v-if="c.codeTableNo" class="reference-preview" :title="'速览码表 '+c.codeTableNo" @click="openPreview('CODE_TABLE',c.codeTableNo)"><AssetIcon type="CODE_TABLE" :size="14" mode="inline"/>{{c.codeTableNo}}<PanelRightOpen :size="13"/></button>
  <span v-if="!c.standardNo && !c.codeTableNo">—</span>
</div></td></tr></tbody></table></div></el-tab-pane>
          <el-tab-pane label="关系与血缘" name="relations"><DatasetRelationPanel :dataset-id="data.assetId" /></el-tab-pane>
          <el-tab-pane label="常用 SQL" name="sql"><div v-if="sqlRows.length" class="sql-list"><article v-for="x in sqlRows" :key="x.sqlCode"><div><span class="dc-chip">{{x.dialect}}</span><h3>{{x.title}}</h3><p>{{x.question}}</p></div><pre>{{x.sqlText}}</pre></article></div><div v-else class="dc-empty">暂无常用 SQL。</div></el-tab-pane>
          <el-tab-pane label="变更记录" name="changes"><div class="timeline" v-if="changes.length"><article v-for="x in changes" :key="x.id"><span>{{formatTime(x.changeDate)}}</span><div><b>{{x.changeType}}</b><p>{{x.content}}</p><small>{{x.changedBy||'系统'}}</small></div></article></div><div v-else class="dc-empty">暂无变更记录。</div></el-tab-pane>
          <el-tab-pane label="调度与运行" name="schedule"><div class="schedule-grid"><div><span>更新频率</span><b>{{data.updateFreq||'—'}}</b></div><div><span>调度计划</span><b>{{data.scheduleDesc||'—'}}</b></div><div><span>调度节点</span><code class="dc-tech">{{data.scheduleNode||'—'}}</code></div><div><span>最近数据更新时间</span><b>{{formatTime(data.dataUpdatedAt)}}</b></div></div></el-tab-pane>
        </el-tabs>
      </section>

      <aside class="detail-side">
        <section class="dc-card side-card"><span class="dc-eyebrow">ASSET PROFILE</span><h3>资产标识</h3><dl><div><dt>Asset ID</dt><dd>{{data.assetId}}</dd></div><div><dt>物理表名</dt><dd class="dc-tech">{{data.tableName}}</dd></div><div><dt>生命周期</dt><dd>{{data.status}}</dd></div></dl></section>
        <section class="dc-card side-card"><span class="dc-eyebrow">TAGS</span><h3>资产标签</h3><div class="tag-wrap"><span v-for="x in tags" :key="x.code" class="dc-chip">{{x.name}}</span><span v-if="!tags.length" class="dc-muted">暂无标签</span></div></section>
        <section class="dc-card side-card lineage-entry"><span class="dc-eyebrow">RELATIONS</span><h3>关联与血缘</h3><p>查看这张表的上下游关系与字段级来源。</p><button @click="tab='relations'"><GitFork :size="14"/>查看关系与血缘</button></section>
      </aside>
    </div>
    <el-drawer v-model="previewOpen" :size="previewDrawerWidth" direction="rtl" :with-header="false" append-to-body>
      <div class="reference-drawer">
        <header class="drawer-header">
          <AssetIcon :type="previewKind" :size="20"/>
          <div><span class="dc-eyebrow">CONTEXT PREVIEW</span><h2>{{previewKind==='CODE_TABLE'?'码表速览':'数据标准速览'}}</h2></div>
          <button class="drawer-close" title="关闭速览" aria-label="关闭速览" @click="previewOpen=false"><X :size="18"/></button>
        </header>
        <div v-if="previewLoading" class="dc-empty">正在获取关联资产…</div>
        <div v-else-if="previewError" class="preview-error"><TriangleAlert :size="18"/>{{previewError}}</div>
        <template v-else-if="previewData">
          <h3 class="preview-name">{{previewData.name || previewData.standardName || previewData.codeTableName || previewCode}}</h3>
          <code class="dc-tech">{{previewCode}}</code>
          <p class="preview-definition">{{previewData.definition || previewData.description || '暂无已登记的业务定义。'}}</p>
          <div class="preview-info"><span>资产编号</span><b>{{previewData.assetId || '—'}}</b></div>
          <div class="preview-info"><span>状态</span><b>{{previewData.status || '未登记'}}</b></div>
          <div v-if="previewKind==='STANDARD' && previewData.codeTableNo" class="preview-info">
            <span>关联码表</span>
            <button @click="openPreview('CODE_TABLE',previewData.codeTableNo)">{{previewData.codeTableNo}} <PanelRightOpen :size="13"/></button>
          </div>
          <section v-if="previewKind==='CODE_TABLE'" class="preview-values">
            <h4><ListTree :size="16"/>码值列表 <small>{{previewValues.length}} 项</small></h4>
            <div v-if="previewValues.length" class="dc-table-wrap"><table class="dc-table"><thead><tr><th>代码</th><th>名称</th></tr></thead><tbody>
              <tr v-for="row in previewValues.slice(0,40)" :key="String(row.value)"><td><code class="dc-tech">{{row.value}}</code></td><td>{{row.name || '—'}}</td></tr>
            </tbody></table></div>
            <p v-if="previewValues.length>40" class="preview-hint">仅预览前 40 项，请打开完整详情查看全部码值。</p>
            <p v-else-if="!previewValues.length" class="preview-hint">暂无可展示码值。</p>
          </section>
          <RouterLink class="preview-full-link" :to="previewKind==='CODE_TABLE' ? `/code-tables/${previewCode}` : `/standards/${previewCode}`" @click="previewOpen=false">打开完整资产详情 <ArrowUpRight :size="15"/></RouterLink>
        </template>
      </div>
    </el-drawer>
    <div v-if="!data" class="dc-empty">正在加载数据集详情…</div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowUpRight, CircleCheck, Clock3, Code2, GitFork, ListTree, PanelRightOpen, TriangleAlert, X } from 'lucide-vue-next'
import AssetIcon from '@/components/AssetIcon.vue'
import AssetOperationBar from '@/components/AssetOperationBar.vue'
import api from '@/api/client'
import DatasetRelationPanel from '@/components/DatasetRelationPanel.vue'
import { activityApi, assetApi } from '@/api/client'
const route=useRoute(); const router=useRouter(); const data=ref<any|null>(null); const columns=ref<any[]>([]); const tags=ref<any[]>([]); const sqlRows=ref<any[]>([]); const changes=ref<any[]>([]); const tab=ref(String(route.query.tab||'overview')); const columnKeyword=ref('')
const columnsLoaded=ref(false)
const columnsComplete=computed(()=>columnsLoaded.value && columns.value.length>0 && columns.value.length<500)
const previewOpen=ref(false)
const previewLoading=ref(false)
const previewError=ref('')
const previewKind=ref<'STANDARD'|'CODE_TABLE'>('CODE_TABLE')
const previewCode=ref('')
const previewData=ref<Record<string,any>|null>(null)
const previewDrawerWidth='min(440px, 94vw)'
const previewValues=computed<Array<{value:string;name?:string}>>(()=>Array.isArray(previewData.value?.values)?previewData.value.values:[])
let previewEpoch=0
async function openPreview(kind:'STANDARD'|'CODE_TABLE',code:string){
  previewKind.value=kind
  previewCode.value=code
  previewOpen.value=true
  previewLoading.value=true
  previewError.value=''
  previewData.value=null
  const epoch=++previewEpoch
  try {
    const result=kind==='CODE_TABLE'
      ? await api.get<Record<string,any>>(`/code-tables/${encodeURIComponent(code)}`)
      : (await assetApi.reference('/data-standards',code) as any[]).find(row=>row.standardNo===code)
    if(epoch!==previewEpoch)return
    if(!result) throw new Error('未找到相应数据标准')
    previewData.value=result
  }catch{
    if(epoch===previewEpoch)previewError.value='无法加载关联资产。可以打开完整详情页重试。'
  }finally{
    if(epoch===previewEpoch)previewLoading.value=false
  }
}
const filteredColumns=computed(()=>{const k=columnKeyword.value.trim().toLowerCase();return k?columns.value.filter(x=>`${x.columnName} ${x.cnName||''} ${x.bizDefinition||''}`.toLowerCase().includes(k)):columns.value})
function formatTime(v?:string){return v?String(v).replace('T',' ').slice(0,16):'—'}
watch(()=>route.params.id,async(value)=>{
  const id=String(value)
  data.value=null;columns.value=[];columnsLoaded.value=false;tags.value=[];sqlRows.value=[];changes.value=[];columnKeyword.value=''
  previewOpen.value=false;previewEpoch++
  const result=await assetApi.table(id)
  if(String(route.params.id)!==id)return
  data.value=result
  await Promise.allSettled([
    assetApi.columns({dataset_id:id,limit:500}).then((v:any)=>{if(String(route.params.id)===id){columns.value=v;columnsLoaded.value=true}}),
    assetApi.tags(id).then((v:any)=>{if(String(route.params.id)===id)tags.value=v}),
    assetApi.commonSql(id).then((v:any)=>{if(String(route.params.id)===id)sqlRows.value=v}),
    assetApi.changes(id).then((v:any)=>{if(String(route.params.id)===id)changes.value=v}),
    activityApi.recordView(id),
  ])
},{immediate:true})
watch(()=>route.query.tab,(value)=>{tab.value=String(value||'overview')})
</script>

<style scoped>
.detail-head{padding:26px 28px;display:flex;justify-content:space-between;gap:24px;align-items:center}.head-main{min-width:0}.head-tags{display:flex;gap:8px;align-items:center}.status{font-size:11px;color:var(--dc-success)}.detail-head h1{font-size:29px;margin:10px 0 6px}.detail-head code{font-size:12px}.detail-head p{font-size:11px;color:var(--dc-text-3);margin:7px 0 0}.head-actions{display:flex;gap:8px;flex-wrap:wrap}.head-actions :deep(.el-button>span){display:flex;align-items:center;gap:6px}.meta-strip{margin-top:14px;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}.meta-strip>div{padding:17px 20px;border-right:1px solid var(--dc-border)}.meta-strip>div:last-child{border:0}.meta-strip span,.kv-grid span,.schedule-grid span{display:block;color:var(--dc-text-3);font-size:10px;margin-bottom:5px}.meta-strip b{font-size:12px}.detail-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;margin-top:16px;align-items:start}.detail-main{padding:6px 22px 22px;min-width:0}.detail-main :deep(.el-tabs__header){margin-bottom:20px}.section-block h2{font-size:19px;margin:6px 0 10px}.section-block>p{font-size:13px;line-height:1.75;color:var(--dc-text-2)}.caliber{margin-top:18px;padding:16px 18px;border-radius:12px;background:linear-gradient(135deg,#eef9fd,#f8fcfe);border:1px solid #d8ebf4}.caliber b{font-size:12px;color:#347d9d}.caliber p{font-size:12px;line-height:1.7;margin:7px 0 0}.kv-grid,.schedule-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}.kv-grid>div,.schedule-grid>div{padding:15px;border:1px solid var(--dc-border);border-radius:11px}.kv-grid b,.schedule-grid b,.schedule-grid code{font-size:12px;line-height:1.55}.detail-side{display:grid;gap:14px}.side-card{padding:18px}.side-card h3{font-size:15px;margin:6px 0 14px}.side-card dl{margin:0;display:grid;gap:12px}.side-card dl div{display:grid;gap:4px}.side-card dt{font-size:9px;color:var(--dc-text-3)}.side-card dd{margin:0;font-size:11px;overflow-wrap:anywhere}.tag-wrap{display:flex;gap:7px;flex-wrap:wrap}.table-actions{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.table-actions :deep(.el-input){width:240px}.field-link{color:var(--dc-primary-strong)}.sql-list{display:grid;gap:14px}.sql-list article{border:1px solid var(--dc-border);border-radius:12px;overflow:hidden}.sql-list article>div{padding:16px}.sql-list h3{font-size:14px;margin:8px 0 4px}.sql-list p{font-size:11px;color:var(--dc-text-2);margin:0}.sql-list pre{margin:0;padding:16px;overflow:auto;background:#122738;color:#d9eef9;font-size:11px;line-height:1.6}.timeline{display:grid;gap:0}.timeline article{display:grid;grid-template-columns:120px minmax(0,1fr);gap:18px;padding:14px 0;border-bottom:1px solid #edf2f5}.timeline article>span{font-size:10px;color:var(--dc-text-3)}.timeline b{font-size:12px}.timeline p{font-size:12px;color:var(--dc-text-2);margin:5px 0}.timeline small{color:#8ca0ad}.lineage-entry p{font-size:10px;line-height:1.6;color:var(--dc-text-2);margin:0 0 10px}.lineage-entry button{width:100%;border:1px solid #c8e0e9;background:#eef8fb;color:#176f92;border-radius:8px;padding:8px 10px;display:flex;align-items:center;justify-content:center;gap:6px;font-size:10px;cursor:pointer}@media(max-width:1100px){.meta-strip{grid-template-columns:repeat(3,1fr)}.meta-strip>div:nth-child(3){border-right:0}.detail-layout{grid-template-columns:1fr}.detail-side{grid-template-columns:1fr 1fr 1fr}}@media(max-width:760px){.detail-head{align-items:flex-start;flex-direction:column}.meta-strip{grid-template-columns:1fr 1fr}.meta-strip>div{border-right:1px solid var(--dc-border)!important;border-bottom:1px solid var(--dc-border)}.meta-strip>div:nth-child(2n){border-right:0!important}.kv-grid,.schedule-grid,.detail-side{grid-template-columns:1fr}.table-actions{align-items:flex-start;flex-direction:column;gap:9px}.table-actions :deep(.el-input){width:100%}}@media(max-width:520px){.detail-main{padding:4px 14px 16px}.head-actions{width:100%}.head-actions :deep(.el-button){flex:1}.meta-strip{grid-template-columns:1fr}.meta-strip>div{border-right:0!important}}
 .field-with-icon{display:inline-flex;align-items:center;gap:7px}
 .data-type{display:inline-flex;align-items:center;gap:6px;color:var(--dc-text-2);font-family:var(--dc-mono);font-size:12px}
 .reference-actions{display:flex;align-items:center;flex-wrap:wrap;gap:6px}
 .reference-preview{display:inline-flex;align-items:center;gap:5px;padding:6px 8px;border:1px solid #dbeafe;border-radius:7px;background:#f8fbff;color:var(--dc-primary);font-size:12px;cursor:pointer}
 .reference-preview:hover{background:var(--dc-primary-soft);border-color:var(--dc-primary)}
 .detail-layout{grid-template-columns:minmax(0,7fr) minmax(260px,3fr)}
 .detail-head,.meta-strip,.detail-main,.side-card{border-color:var(--dc-border)}
 .status{display:inline-flex;align-items:center;gap:5px}

/* Detail shell: the asset name and fields are primary, relations are secondary. */
.detail-head{background:#fff;border-color:var(--dc-border);border-radius:12px;padding:25px 26px}
.detail-head h1{color:var(--dc-text);font-size:26px;font-weight:750;margin:11px 0 6px}
.detail-head .head-tags{display:flex;align-items:center;gap:9px}
.detail-head p{color:var(--dc-text-3);font-size:12px}
.head-actions{align-items:center}
.meta-strip{padding:16px 22px;border-radius:12px;border-color:var(--dc-border)}
.meta-strip>div{gap:4px}
.meta-strip span{font-size:12px;color:var(--dc-text-3)}
.meta-strip b{font-size:13px;color:var(--dc-text)}
.detail-layout{grid-template-columns:minmax(0,1fr) 265px;gap:16px;align-items:start}
.detail-main{border-radius:12px;min-width:0}
.detail-side{display:grid;gap:14px}
.side-card{padding:18px;border-radius:12px}
.side-card h3{color:var(--dc-text);font-size:14px;margin:7px 0 11px}
.side-card p{font-size:12px;line-height:1.7;color:var(--dc-text-2)}
.section-block h2{color:var(--dc-text);font-size:17px}
.section-block p{font-size:13px;line-height:1.75}
.field-link:hover{color:var(--dc-primary);text-decoration:underline}
.reference-preview{background:#f5f8ff;border-color:#dce6f8;font-size:12px}
.reference-preview:hover{background:#e9f1ff}
@media(max-width:1060px){.detail-layout{grid-template-columns:1fr}.detail-side{grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
@media(max-width:720px){.detail-head{padding:18px}.detail-head h1{font-size:21px}.meta-strip{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.detail-side{grid-template-columns:1fr}}
</style>
<style>
.reference-drawer{padding:20px 4px 28px;color:var(--dc-text)}
.drawer-header{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--dc-border);padding-bottom:18px}
.drawer-header>div{flex:1}.drawer-header h2{font-size:19px;margin:4px 0 0}
.drawer-close{width:32px;height:32px;display:grid;place-items:center;border:1px solid var(--dc-border);border-radius:8px;background:#fff;cursor:pointer}
.preview-name{font-size:20px;margin:22px 0 8px}
.preview-definition{font-size:14px;color:var(--dc-text-2);line-height:1.7;padding:14px;border-radius:10px;background:var(--dc-primary-soft)}
.preview-info{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid var(--dc-border);padding:12px 0;font-size:13px}
.preview-info span{color:var(--dc-text-2)}.preview-info b{font-size:12px;overflow-wrap:anywhere;text-align:right}
.preview-info button{display:inline-flex;align-items:center;gap:6px;color:var(--dc-primary);border:0;background:transparent;cursor:pointer}
.preview-values{margin-top:22px}.preview-values h4{display:flex;align-items:center;gap:8px;margin:0 0 10px}
.preview-values h4 small{color:var(--dc-text-3);font-weight:400}
.preview-values .dc-table{min-width:0}.preview-values .dc-table th,.preview-values .dc-table td{padding:9px;font-size:12px}
.preview-hint{font-size:12px;color:var(--dc-text-3)}
.preview-full-link{display:flex;justify-content:center;align-items:center;gap:8px;margin-top:24px;padding:12px;border-radius:9px;background:var(--dc-primary);color:#fff;font-size:13px;font-weight:700}
.preview-error{display:flex;align-items:center;gap:8px;margin-top:24px;color:var(--dc-danger);font-size:13px}
.detail-head{border-color:#cbdff8;background:linear-gradient(120deg,#fff,#f4f9ff);box-shadow:var(--dc-shadow-md);padding:29px}.detail-head h1{font-size:29px;color:#1a3a6a}.detail-head .head-actions :deep(.el-button){font-size:14px}.meta-strip{background:#fff;border-color:#d1e2f8;box-shadow:0 5px 19px rgba(35,84,156,.07)}.meta-strip span{font-size:13px}.meta-strip b{font-size:14px}.detail-main{border-color:#d3e2f7;box-shadow:var(--dc-shadow-sm)}.detail-main :deep(.el-tabs__item){font-size:14px;font-weight:680;height:52px}.detail-main :deep(.el-tabs__item.is-active){color:#2466d5}.detail-main :deep(.el-tabs__active-bar){background:#276dec}.side-card{border-color:#d4e3f7;background:linear-gradient(140deg,#fff,#fafcff);box-shadow:var(--dc-shadow-sm)}.side-card h3{font-size:16px;color:#274a7b}.side-card dl{font-size:13px}.reference-preview{font-size:13px;padding:6px 9px}.reference-preview:hover{border-color:#a8c8f9}.dc-table td{font-size:14px}.dc-table th{font-size:13px}@media(max-width:760px){.detail-head{padding:20px}.detail-head h1{font-size:24px}}
</style>
