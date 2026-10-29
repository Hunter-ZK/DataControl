<template>
  <div class="asset-ops">
    <button class="asset-ask" @click="execute('ask')"><Sparkles :size="16"/>{{ askLabel }}</button>
    <button v-for="item in quick" :key="item.id" class="asset-secondary" @click="execute(item.id)">
      <Heart v-if="item.id==='favorite'" :size="15" :fill="favorited?'currentColor':'none'"/>
      <Copy v-else :size="15"/>{{ item.id==='favorite' && favorited ? '已收藏' : item.label }}
    </button>
    <el-dropdown v-if="grouped.length" trigger="click" placement="bottom-end">
      <button class="asset-more" aria-label="更多资产操作"><Ellipsis :size="16"/>更多</button>
      <template #dropdown>
        <el-dropdown-menu class="asset-operations-menu">
          <template v-for="group in grouped" :key="group.name">
            <div class="asset-group-name">{{ group.name }}</div>
            <el-dropdown-item v-for="item in group.actions" :key="item.id" @click="execute(item.id)">
              <Download v-if="item.group==='导出'" :size="15"/>
              <Sparkles v-else-if="item.group==='问 Agent'" :size="15"/>
              <Search v-else :size="15"/>
              {{ item.label }}
            </el-dropdown-item>
          </template>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <el-dialog v-model="previewOpen" :title="previewTitle" width="min(720px,95vw)" append-to-body>
      <p class="preview-hint">仅依据已登记元数据生成的草案，不执行 SQL。请在使用前确认方言、字段口径、时间条件及权限。</p>
      <pre class="preview-code">{{previewText}}</pre>
      <template #footer>
        <el-button @click="copyText(previewText)">复制内容</el-button>
        <el-button type="primary" @click="download(previewText,'datacontrol_asset_draft.sql','text/plain;charset=utf-8')">下载 SQL</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Copy, Download, Ellipsis, Heart, Search, Sparkles } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { activityApi } from '@/api/client'
import { activeAssetOperations, type AssetOperation } from '@/composables/assetOperations'
import { openAssetAgent } from '@/composables/assetAgentDrawer'
import { createCaseDraft, createDdlDraft, createSelectDraft, makeCsv, type ExportColumn } from '@/utils/assetExport'

type Kind = 'TABLE' | 'COLUMN' | 'METRIC' | 'CODE_TABLE' | 'STANDARD' | 'WORD_ROOT' | 'STAT_SYSTEM'
const props = withDefaults(defineProps<{
  kind: Kind
  asset: Record<string, any>
  columns?: ExportColumn[]
  columnsComplete?: boolean
}>(), { columns: () => [], columnsComplete: false })
const router = useRouter()
const route = useRoute()
const owner = Symbol('asset-operations')
const favorited = ref(false)
const savingFavorite = ref(false)
const previewOpen = ref(false)
const previewTitle = ref('')
const previewText = ref('')

const noun: Record<Kind, string> = {
  TABLE:'这张表', COLUMN:'这个字段', METRIC:'这个指标',
  CODE_TABLE:'这个码表', STANDARD:'这个标准', WORD_ROOT:'这个词根', STAT_SYSTEM:'这个制度',
}
const askLabel = computed(() => '问' + noun[props.kind])
const code = computed(() => String(props.asset.tableName || props.asset.columnName || props.asset.metricCode ||
  props.asset.codeTableNo || props.asset.standardNo || props.asset.root || props.asset.code || ''))
const id = computed(() => String(props.asset.assetId || code.value))
const label = computed(() => String(props.asset.bizName || props.asset.cnName || props.asset.name || props.asset.metricName || code.value))
const actions = computed<AssetOperation[]>(() => {
  const common: AssetOperation[] = [{ id:'ask', label:askLabel.value, group:'问 Agent' }]
  const action = (id:string,label:string,group:AssetOperation['group']):AssetOperation => ({ id,label,group })
  switch (props.kind) {
    case 'TABLE': return [...common,action('copy','复制表名','常用'),action('favorite','收藏','常用'),
      action('ddl','预览建表 DDL 草案','导出'),action('dictionary','导出字段字典 CSV','导出'),
      action('select','生成全字段查询模板','生成'),action('naming','检查本表字段命名','生成'),action('lineage','查看完整血缘','分析'),
      action('explain','解释这张表','问 Agent'),action('sql','基于这张表生成 SQL','问 Agent')]
    case 'COLUMN': return [...common,action('copy','复制字段名','常用'),action('parent','查看所属数据集','常用'),
      action('lineage','查看字段血缘','分析'),action('sameName','搜索字段名','分析'),action('explain','解释这个字段','问 Agent')]
    case 'METRIC': return [...common,action('copy','复制指标编码','常用'),
      action('parent','查看来源数据集','分析'),action('metricCsv','导出指标定义 CSV','导出'),action('explain','解释统计口径','问 Agent')]
    case 'CODE_TABLE': return [...common,action('copyValues','复制码值','常用'),
      action('valuesCsv','导出码值 CSV','导出'),action('references','查看引用字段','分析'),action('case','生成 CASE WHEN 模板','生成'),action('explain','解释码值含义','问 Agent')]
    case 'STANDARD': return [...common,action('copy','复制标准编号','常用'),
      action('definitionCsv','导出标准定义 CSV','导出'),action('references','查看落标字段','分析'),...(props.asset.codeTableNo ? [action('linkedCode','查看关联码表','分析')] : []),
      action('explain','解释适用规则','问 Agent')]
    case 'WORD_ROOT': return [...common,action('naming','用于字段命名','常用'),action('copy','复制英文词根','生成'),action('copyCn','复制中文名称','生成'),
      action('explain','解释这个词根','问 Agent')]
    case 'STAT_SYSTEM': return [...common,action('copy','复制制度编码','常用'),action('definitionCsv','导出制度信息 CSV','导出'),action('references','查看下属指标','分析'),
      action('explain','解释统计制度','问 Agent')]
  }
})
const quick = computed(() => actions.value.filter(x => x.group==='常用'))
const grouped = computed(() => (['导出','生成','分析','问 Agent'] as const).map(name => ({
  name, actions: actions.value.filter(x => x.group===name && x.id!=='ask'),
})).filter(group => group.actions.length))
watchEffect(() => {
  activeAssetOperations.value = {
    owner, path:route.fullPath, label:label.value,
    actions:actions.value, execute,
  }
})
onBeforeUnmount(() => { if (activeAssetOperations.value?.owner===owner) activeAssetOperations.value=null })
let favoriteEpoch=0
watch(() => [props.kind,id.value], async () => {
  const epoch=++favoriteEpoch
  if (props.kind!=='TABLE') return
  try {
    const rows=await activityApi.favorites()
    if(epoch===favoriteEpoch)favorited.value=rows.some(x=>x.assetType==='TABLE'&&x.assetId===id.value)
  } catch { if(epoch===favoriteEpoch)favorited.value=false }
}, {immediate:true})
async function copyText(text:string) {
  try { await navigator.clipboard.writeText(text); ElMessage.success('已复制') }
  catch { ElMessage.error('复制失败，请检查剪贴板权限') }
}
function download(content:string,name:string,mime:string) {
  const url=URL.createObjectURL(new Blob([content],{type:mime}))
  const a=document.createElement('a')
  a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove()
  window.setTimeout(()=>URL.revokeObjectURL(url),0)
}
function preview(title:string,content:string) {
  previewTitle.value=title;previewText.value=content;previewOpen.value=true
}
function ask(task:string) {
  openAssetAgent({assetType:props.kind,assetId:id.value,name:label.value,
    technicalName:code.value,task:task==='sql'?'sql':task==='explain'?'explain':'ask'})
}
async function toggleFavorite() {
  if(savingFavorite.value)return
  savingFavorite.value=true
  try {
    if(favorited.value)await activityApi.removeFavorite('TABLE',id.value)
    else await activityApi.addFavorite('TABLE',id.value)
    favorited.value=!favorited.value;ElMessage.success(favorited.value?'已收藏':'已取消收藏')
  }catch{ElMessage.error('收藏失败，请登录后重试')}
  finally{savingFavorite.value=false}
}
function execute(operation:string) {
  try {
    if(['ask','explain','sql'].includes(operation)){ask(operation);return}
    if(operation==='copy'){void copyText(code.value);return}
    if(operation==='copyCn'){void copyText(String(props.asset.cnName||''));return}
    if(operation==='favorite'){void toggleFavorite();return}
    if(operation==='naming'){void router.push({name:'namingWorkbench',query:props.kind==='TABLE'?{dataset:id.value}:{root:code.value}});return}
    if(operation==='parent'){
      const target=props.asset.datasetId||props.asset.source?.assetId
      if(!target)throw Error('未找到已登记的来源数据集')
      void router.push({name:'dataset',params:{id:String(target)}});return
    }
    if(operation==='lineage'){
      void router.push(props.kind==='COLUMN'?{name:'relations',query:{mode:'field',field:id.value}}:{name:'relations',params:{id:id.value}});return
    }
    if(operation==='sameName'){void router.push({name:'search',query:{q:code.value}});return}
    if(operation==='references'){document.querySelector('.refs-panel')?.scrollIntoView({behavior:'smooth',block:'start'});return}
    if(operation==='linkedCode'){void router.push({name:'codeTable',params:{no:String(props.asset.codeTableNo)}});return}
    if(operation==='ddl'){preview('建表 DDL 草案',createDdlDraft(code.value,props.columns,props.columnsComplete));return}
    if(operation==='select'){preview('全字段查询模板',createSelectDraft(code.value,props.columns,props.columnsComplete));return}
    if(operation==='dictionary'){
      if(!props.columnsComplete||!props.columns.length)throw Error('字段列表尚未完整加载')
      const lines=[['序号','字段英文名','字段中文名','类型','业务定义','数据标准','码表'],
        ...props.columns.map(x=>[x.ordinalNo,x.columnName,x.cnName,x.dataType,x.bizDefinition,x.standardNo,x.codeTableNo])]
      download(makeCsv(lines),'datacontrol_dictionary.csv','text/csv;charset=utf-8');return
    }
    const values=Array.isArray(props.asset.values)?props.asset.values:[]
    if(operation==='copyValues'){void copyText(values.map((v:any)=>String(v.value)+'\t'+String(v.name||'')).join('\n'));return}
    if(operation==='valuesCsv'){
      download(makeCsv([['码值','名称','说明'],...values.map((v:any)=>[v.value,v.name,v.description])]),
        'datacontrol_code_values.csv','text/csv;charset=utf-8');return
    }
    if(operation==='case'){preview('CASE WHEN 翻译模板',createCaseDraft(values));return}
    if(operation==='metricCsv'){
      const m=props.asset
      download(makeCsv([['属性','值'],['指标编码',m.metricCode],['名称',m.name],['定义',m.definition],['统计口径',m.caliber],
        ['来源数据集',m.source?.tableName],['聚合方式',m.aggregation],['度量字段',m.measureColumn],
        ['时间字段',m.time?.field],['维度',(m.validDimensions||[]).map((v:any)=>v.name).join(',')],
        ['必选过滤',JSON.stringify(m.mandatoryFilters||[])]]),
        'datacontrol_metric_definition.csv','text/csv;charset=utf-8');return
    }
    if(operation==='definitionCsv'){
      download(makeCsv([['属性','已登记值'],...Object.entries(props.asset).filter(([,v])=>v==null||['string','number','boolean'].includes(typeof v))]),
        'datacontrol_asset_definition.csv','text/csv;charset=utf-8')
    }
  }catch(error){ElMessage.warning(error instanceof Error?error.message:'操作失败')}
}
</script>

<style scoped>
.asset-ops{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px}
.asset-ops button{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:36px;padding:8px 12px;font-size:13px;font-weight:650;border-radius:10px;white-space:nowrap;cursor:pointer}
.asset-ask{background:var(--dc-agent);color:#fff;border:1px solid var(--dc-agent)}
.asset-ask:hover{background:var(--dc-primary-strong)}
.asset-secondary,.asset-more{color:var(--dc-primary-strong);background:var(--dc-surface);border:1px solid var(--dc-border-strong)}
.asset-secondary:hover,.asset-more:hover{background:var(--dc-primary-soft)}
.preview-hint{background:var(--dc-surface-soft);border:1px solid var(--dc-border);border-radius:10px;padding:12px;color:var(--dc-text-2);font-size:13px;line-height:1.6}
.preview-code{max-height:48vh;overflow:auto;background:#f7fbff;border:1px solid var(--dc-border);padding:14px;border-radius:10px;font-size:12px;line-height:1.6}
@media(max-width:700px){.asset-ops{justify-content:flex-start}}
</style>
<style>
.asset-operations-menu{min-width:228px;padding:8px}
.asset-group-name{padding:10px 12px 5px;font-size:12px;font-weight:700;color:var(--dc-text-3)}
.asset-operations-menu .el-dropdown-menu__item{display:flex;align-items:center;gap:10px;border-radius:8px;font-size:13px}
</style>
