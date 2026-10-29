<template>
  <div class="dc-page naming-page"><div class="dc-container">
    <header class="dc-page-head">
      <div><span class="dc-eyebrow">DATA GOVERNANCE · NAMING WORKBENCH</span>
        <h1 class="dc-title">字段规范化命名</h1>
        <p class="dc-subtitle">上传字段清单、按词根规则匹配、逐行复核并导出。未知词根会明确标记，不生成未经确认的缩写。</p>
      </div>
      <RouterLink to="/word-roots" class="plain-link"><BookOpenCheck :size="17"/>查看词根库</RouterLink>
    </header>
    <div class="steps dc-card">
      <button v-for="(item,index) in stepLabels" :key="item" :class="{active:step===index,done:step>index}"
              :disabled="index>furthest" @click="step=index">
        <span>{{index+1}}</span><b>{{item}}</b><Check v-if="index<step" :size="16"/>
      </button>
    </div>
    <section v-if="error" class="notice error" role="alert"><TriangleAlert :size="17"/>{{error}}</section>
    <section v-if="step===0" class="dc-card step-content">
      <div class="pane-heading"><div><span class="dc-eyebrow">01 · INPUT</span><h2>导入字段材料</h2><p>支持 Excel（.xlsx）、CSV，或直接粘贴每行一个字段中文名。</p></div><span class="soft-flag">最多 2000 行</span></div>
      <div class="input-grid">
        <div class="file-zone">
          <FileSpreadsheet :size="28"/><b>上传字段清单</b><p>仅处理当前上传的文件，不在浏览器中保存原始文件</p>
          <input type="file" accept=".xlsx,.csv" aria-label="上传字段清单" @change="importSpreadsheet"/>
          <small v-if="fileName">已选择：{{fileName}} · {{sourceRows.length}} 行</small>
        </div>
        <div class="paste-zone"><label for="naming-paste">粘贴中文字段清单</label>
          <textarea id="naming-paste" v-model="pasted" rows="8" placeholder="客户名称&#10;贷款余额&#10;数据统计日期"></textarea>
          <button class="dc-outline" :disabled="!pasted.trim()" @click="usePasted">读取文本</button>
        </div>
      </div>
      <div v-if="headers.length" class="source-summary">
        <span><CheckCircle2 :size="16"/>已读取 {{sourceRows.length}} 行，{{headers.length}} 列</span>
        <label>中文名所在列
          <select v-model="cnColumn"><option v-for="h in headers" :key="h" :value="h">{{h}}</option></select>
        </label>
        <span v-if="sourceDataset" class="source-chip">来自数据集 {{sourceDataset}}</span>
      </div>
      <div class="step-footer"><span>表格中的其他原始列会在导出时保留</span>
        <button class="dc-primary" :disabled="!sourceRows.length||!cnColumn" @click="goSettings">下一步：设置规则 <ArrowRight :size="16"/></button>
      </div>
    </section>
    <section v-else-if="step===1" class="dc-card step-content">
      <div class="pane-heading"><div><span class="dc-eyebrow">02 · RULES</span><h2>命名规则</h2>
        <p>当前为试用规则，不代表单位正式规范。相同词根库和输入在同一版本下得到相同的规则建议。</p></div></div>
      <div class="rule-grid">
        <div><span>输出样式</span><b>小写 snake_case</b><small>如 loan_balance；不擅自附加 ODS/DWD/DWS 等表层前缀</small></div>
        <div><label for="naming-length">最大长度</label><input id="naming-length" type="number" min="8" max="128" v-model.number="maxLength"/><small>仅作为本次复核阈值，默认 64</small></div>
        <div><span>匹配优先级</span><b>唯一已有同名字段 → 已登记词根 → 人工复核</b><small>同名字段有多个不同英文名时不会自动选择</small></div>
        <div><span>未知词根</span><b>保持空白并提示</b><small>绝不冒充大模型建议；等待规范和词根库完善</small></div>
      </div>
      <div class="notice"><ShieldCheck :size="17"/>生成过程不会执行 SQL，也不会将字段内容发送给外部公共模型。</div>
      <div class="step-footer"><button class="dc-outline" @click="step=0">返回修改</button>
        <button class="dc-primary" :disabled="busy||maxLength<8||maxLength>128" @click="generate">
          <Sparkles :size="16"/>{{busy?'正在规则匹配…':'生成命名建议'}}</button>
      </div>
    </section>
    <section v-else-if="step===2" class="dc-card step-content review-section">
      <div class="pane-heading"><div><span class="dc-eyebrow">03 · REVIEW</span><h2>逐行复核</h2>
        <p>命名建议与人工编辑严格区分。即使规则命中，也要确认业务语义与实际命名规范。</p></div>
        <div class="review-stats"><span>共 <b>{{rows.length}}</b> 行</span><span>已确认 <b>{{confirmedCount}}</b></span><span>需关注 <b>{{attentionCount}}</b></span></div>
      </div>
      <div class="review-controls"><label>筛选<select v-model="filter"><option value="all">全部</option><option value="attention">需关注</option><option value="pending">待确认</option><option value="confirmed">已确认</option></select></label>
        <button class="dc-outline" @click="confirmReady">批量确认无校验问题的行</button>
        <button class="dc-outline" @click="step=1">调整规则并重新生成</button>
      </div>
      <div class="dc-table-wrap"><table class="dc-table naming-table"><thead><tr>
        <th>序号</th><th>中文名</th><th>建议英文名 / 最终英文名</th><th>命名依据与拆词</th><th>校验与状态</th><th>操作</th>
      </tr></thead><tbody><tr v-for="row in filtered" :key="row.key" :class="{pending:row.issues.length||rowIssues(row).length}">
        <td>{{row.key+1}}</td><td><b>{{row.cnName||'—'}}</b></td>
        <td><input v-model="row.finalName" class="name-edit" :aria-label="'编辑第'+(row.key+1)+'行英文名'" @input="row.confirmed=false" placeholder="需人工补全英文名"/>
          <small v-if="row.suggestedName && row.finalName!==row.suggestedName">原建议：{{row.suggestedName}}</small></td>
        <td><span class="source-label">{{row.source}}</span><div class="segment-list"><span v-for="(part,j) in row.segments" :key="j" :class="{missing:!part.root}">{{part.cn}} → {{part.root||'待补'}}</span></div></td>
        <td><div v-if="rowIssues(row).length" class="issues"><span v-for="issue in rowIssues(row)" :key="issue">{{issue}}</span></div>
          <span v-else class="valid">格式校验通过</span>
          <small>{{row.confirmed?'已确认':'待确认'}}</small></td>
        <td><button class="confirm-btn" :disabled="!!rowIssues(row).length" @click="row.confirmed=!row.confirmed">{{row.confirmed?'取消确认':'确认'}}</button></td>
      </tr><tr v-if="!filtered.length"><td colspan="6" class="dc-empty">当前筛选下没有记录</td></tr></tbody></table></div>
      <div class="step-footer"><span>提示：没有词根的条目可以手工填写并确认，仍会保留“人工修改”来源。</span>
        <button class="dc-primary" @click="step=3;furthest=3">查看导出 <ArrowRight :size="16"/></button>
      </div>
    </section>
    <section v-else class="dc-card step-content">
      <div class="pane-heading"><div><span class="dc-eyebrow">04 · EXPORT</span><h2>导出复核成果</h2><p>Excel 包含“命名结果”和“建议新增词根”两个工作表，保留输入中的其他列。</p></div></div>
      <div class="export-tiles">
        <div><FileSpreadsheet :size="24"/><h3>命名结果</h3><strong>{{rows.length}} 条</strong><p>建议英文名、拆词过程、来源、校验结果、复核状态及原始列</p></div>
        <div><BookOpenCheck :size="24"/><h3>建议新增词根</h3><strong>{{rootSuggestions.length}} 项</strong><p>未命中词根的中文词语、出现次数、示例字段；缩写留空供审核</p></div>
      </div>
      <div class="notice" :class="{error:confirmedCount!==rows.length}"><TriangleAlert :size="16"/>已确认 {{confirmedCount}}/{{rows.length}} 条。未确认行允许导出，但会明确标记为“待确认”，不得直接作为正式标准入库。</div>
      <div class="step-footer"><button class="dc-outline" @click="step=2">继续复核</button>
        <button class="dc-primary" :disabled="busy" @click="exportExcel"><Download :size="16"/>{{busy?'正在生成…':'下载 Excel 成果'}}</button>
      </div>
    </section>
    <p class="page-footnote">本工作台当前使用服务端规则引擎，真实命名规范、模型分词与持久化运行记录仍待后续接入。</p>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ArrowRight, BookOpenCheck, Check, CheckCircle2, Download, FileSpreadsheet, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { assetApi, namingApi } from '@/api/client'
import { missingRoots, validateNamingRows, type NamingRow, type NamingSuggestion } from '@/utils/namingReview'

const route=useRoute()
const stepLabels=['输入','设置','复核','导出']
const step=ref(0)
const furthest=ref(0)
const busy=ref(false)
const error=ref('')
const fileName=ref('')
const pasted=ref('')
const headers=ref<string[]>([])
const cnColumn=ref('')
const sourceRows=ref<Array<Record<string,string>>>([])
const sourceDataset=ref('')
const maxLength=ref(64)
const rows=ref<NamingRow[]>([])
const filter=ref('all')
const validation=computed(()=>validateNamingRows(rows.value,maxLength.value))
const confirmedCount=computed(()=>rows.value.filter(x=>x.confirmed&&!validation.value.get(x.key)?.length).length)
const attentionCount=computed(()=>rows.value.filter(x=>x.issues.length||validation.value.get(x.key)?.length).length)
const rootSuggestions=computed(()=>missingRoots(rows.value))
const filtered=computed(()=>rows.value.filter(x=>filter.value==='all'||(filter.value==='confirmed'&&x.confirmed)
  ||(filter.value==='pending'&&!x.confirmed)||(filter.value==='attention'&&(x.issues.length||rowIssues(x).length))))
function rowIssues(row:NamingRow){return validation.value.get(row.key)||[]}
function changeSource(items:Array<Record<string,string>>,keys:string[],filename:string){
  if(!items.length){error.value='材料中没有可处理的记录';return}
  sourceRows.value=items.slice(0,2000);headers.value=keys;fileName.value=filename
  cnColumn.value=keys.find(x=>/中文名|字段中文|中文名称|字段名称/.test(x))||keys[0]||''
  step.value=0;furthest.value=0;rows.value=[];error.value=''
}
async function importSpreadsheet(event:Event){
  const input=event.target as HTMLInputElement
  const file=input.files?.[0]
  if(!file)return
  busy.value=true;error.value=''
  try{
    const result=await namingApi.importFile(file)
    changeSource(result.items,result.headers,file.name)
  }catch{error.value='文件读取失败。请确认已登录，文件为有效的 .xlsx/.csv，且不超过 8MB、2000 行。'}
  finally{busy.value=false;input.value=''}
}
function usePasted(){
  const lines=pasted.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).slice(0,2000)
  changeSource(lines.map(x=>({'中文名':x})),['中文名'],'粘贴文本')
}
function goSettings(){if(sourceRows.value.length&&cnColumn.value){error.value='';step.value=1;furthest.value=Math.max(furthest.value,1)}}
async function generate(){
  busy.value=true;error.value=''
  try{
    const result=await namingApi.suggest(sourceRows.value.map(x=>String(x[cnColumn.value]||'')),maxLength.value)
    if(result.items.length!==sourceRows.value.length)throw Error('rows mismatch')
    rows.value=result.items.map((item:NamingSuggestion,index:number)=>({
      ...item,key:index,original:sourceRows.value[index],finalName:item.suggestedName,confirmed:false,note:'',
    }))
    step.value=2;furthest.value=2;filter.value='all'
  }catch{error.value='规则匹配服务暂不可用，请检查登录状态、词根库和服务日志。'}
  finally{busy.value=false}
}
function confirmReady(){
  let count=0
  for(const row of rows.value){if(!rowIssues(row).length&&!row.issues.length){row.confirmed=true;count++}}
  ElMessage.info('已确认 '+count+' 行；其他行仍需逐项核对。')
}
async function exportExcel(){
  busy.value=true;error.value=''
  try{
    const blob=await namingApi.exportExcel({
      originalHeaders:headers.value,
      entries:rows.value.map(x=>({
        original:x.original,cnName:x.cnName,suggestedName:x.finalName,
        segments:x.segments.map(s=>s.cn+' → '+(s.root||'待补')).join(' / '),
        source:x.finalName!==x.suggestedName?'人工修改':x.source,
        issues:[...new Set([...x.issues,...rowIssues(x)])].join('；'),
        status:x.confirmed?'已确认':'待确认',note:x.note,
      })),
      rootSuggestions:rootSuggestions.value,
    })
    const url=URL.createObjectURL(blob)
    const link=document.createElement('a');link.href=url;link.download='datacontrol_naming_results.xlsx'
    document.body.appendChild(link);link.click();link.remove()
    window.setTimeout(()=>URL.revokeObjectURL(url),0)
    ElMessage.success('已生成 Excel 文件')
  }catch{error.value='导出失败，请检查文件内容和服务连接。'}
  finally{busy.value=false}
}
onMounted(async()=>{
  const dataset=typeof route.query.dataset==='string'?route.query.dataset:''
  if(dataset){
    busy.value=true
    try{
      const result=await assetApi.completeColumns(dataset)
      changeSource(result.items.map(x=>({
        '中文名':String(x.cnName||''),'字段英文名':x.columnName,
        '业务定义':String(x.bizDefinition||''),'数据类型':x.dataType,
        '所属数据集':dataset,
      })),['中文名','字段英文名','业务定义','数据类型','所属数据集'],'已登记数据集')
      sourceDataset.value=dataset
    }catch{error.value='无法预填当前数据集字段，请检查完整字段接口。'}
    finally{busy.value=false}
  }
  if(typeof route.query.root==='string'&&route.query.root)ElMessage.info('已从词根 '+route.query.root+' 进入命名工作台')
})
</script>

<style scoped>
.naming-page{min-height:calc(100dvh - var(--dc-topbar))}
.plain-link,.dc-outline{border:1px solid var(--dc-border-strong);border-radius:10px;padding:10px 14px;background:#fff;color:var(--dc-primary);display:inline-flex;gap:8px;align-items:center;cursor:pointer;font-size:13px;font-weight:680}
.dc-primary{border:1px solid var(--dc-primary);border-radius:10px;padding:10px 16px;background:var(--dc-primary);color:#fff;display:inline-flex;gap:8px;align-items:center;justify-content:center;cursor:pointer;font-size:13px;font-weight:720}
button:disabled{opacity:.48;cursor:not-allowed}.steps{display:grid;grid-template-columns:repeat(4,1fr);margin-bottom:18px;padding:10px;gap:8px}.steps button{display:flex;align-items:center;gap:10px;border:0;border-radius:9px;background:transparent;color:var(--dc-text-3);padding:14px 18px;cursor:pointer;text-align:left}.steps button.active{background:var(--dc-primary-soft);color:var(--dc-primary)}.steps button.done{color:var(--dc-success)}.steps button>span{border-radius:50%;width:26px;height:26px;display:grid;place-items:center;border:1px solid var(--dc-border-strong)}.steps button.active>span{background:var(--dc-primary);color:#fff}
.step-content{padding:28px}.pane-heading,.step-footer{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}.pane-heading{margin-bottom:22px}.pane-heading h2{font-size:23px;margin:5px 0}.pane-heading p{font-size:14px;color:var(--dc-text-2);margin:5px 0}.soft-flag,.source-chip{padding:7px 11px;border-radius:9px;background:var(--dc-primary-soft);color:var(--dc-primary);font-size:12px}
.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.file-zone,.paste-zone{background:#f8fbff;border:1px solid var(--dc-border);border-radius:12px;min-height:255px;padding:24px;display:flex;flex-direction:column;gap:10px}.file-zone{align-items:center;justify-content:center;border-style:dashed;text-align:center;color:var(--dc-primary)}.file-zone p,.paste-zone p{color:var(--dc-text-2);font-size:13px;margin:0}.file-zone input{max-width:100%;font-size:12px}.file-zone small{color:var(--dc-text-2)}.paste-zone label{font-weight:720}.paste-zone textarea{resize:vertical;border:1px solid var(--dc-border-strong);border-radius:9px;background:#fff;padding:12px;color:var(--dc-text);flex:1;min-height:140px}.paste-zone button{align-self:flex-end}.source-summary{background:var(--dc-primary-soft);display:flex;align-items:center;gap:18px;padding:14px;border-radius:10px;margin-top:20px;flex-wrap:wrap;font-size:13px}.source-summary>span{display:flex;align-items:center;gap:8px}.source-summary label{margin-left:auto;display:flex;gap:9px;align-items:center}.source-summary select,.rule-grid input,.review-controls select{padding:7px;border:1px solid var(--dc-border-strong);background:#fff;border-radius:8px;max-width:200px}.step-footer{margin-top:24px;padding-top:20px;border-top:1px solid var(--dc-border)}.step-footer>span{font-size:13px;color:var(--dc-text-2)}.rule-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.rule-grid>div{padding:21px;background:#f8fbff;border:1px solid var(--dc-border);border-radius:11px;display:grid;gap:9px}.rule-grid span,.rule-grid label{font-size:13px;color:var(--dc-text-2)}.rule-grid b{font-size:15px}.rule-grid small{color:var(--dc-text-3)}.rule-grid input{width:115px}.notice{border-radius:10px;border:1px solid var(--dc-border);background:var(--dc-primary-soft);color:var(--dc-text-2);font-size:13px;display:flex;gap:10px;align-items:center;padding:14px;margin:16px 0}.notice.error{background:#fff8ec;color:#8c5b17;border-color:#efd5a3}.review-stats{display:flex;gap:14px;color:var(--dc-text-2);font-size:13px}.review-stats b{color:var(--dc-primary)}.review-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}.review-controls label{font-size:13px;color:var(--dc-text-2);display:flex;align-items:center;gap:9px}.naming-table{min-width:1050px}.naming-table td{vertical-align:top}.naming-table tbody tr:nth-child(even) td{background:#f8fbff}.naming-table tbody tr.pending td:first-child{border-left:3px solid #edbd6e}.name-edit{min-width:195px;width:100%;border:1px solid var(--dc-border-strong);border-radius:8px;padding:9px;color:var(--dc-text);background:#fff;font-family:var(--dc-mono);font-size:13px}.naming-table small{display:block;color:var(--dc-text-3);margin-top:5px;font-size:12px}.source-label{font-size:12px;color:var(--dc-primary);font-weight:700}.segment-list{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.segment-list span{background:#eef5ff;border:1px solid #dbe8f8;padding:3px 7px;border-radius:6px;font-size:12px}.segment-list span.missing{color:#996417;background:#fff7e8;border-color:#f1ddbc}.issues{display:grid;gap:3px;color:#9a6217;font-size:12px}.valid{color:var(--dc-success);font-size:12px}.confirm-btn{background:#fff;border:1px solid var(--dc-border-strong);color:var(--dc-primary);border-radius:8px;padding:7px 10px;cursor:pointer}.export-tiles{display:grid;grid-template-columns:1fr 1fr;gap:16px}.export-tiles>div{background:#f8fbff;border:1px solid var(--dc-border);border-radius:12px;padding:24px;color:var(--dc-primary)}.export-tiles h3{color:var(--dc-text);margin:12px 0 0}.export-tiles strong{display:block;font-size:27px;margin:4px 0}.export-tiles p{color:var(--dc-text-2);font-size:13px}.page-footnote{font-size:12px;color:var(--dc-text-3);margin:16px 0}@media(max-width:800px){.input-grid,.rule-grid,.export-tiles{grid-template-columns:1fr}.step-content{padding:17px}.steps button{padding:10px;justify-content:center}.steps button b{display:none}.source-summary label{margin-left:0}.review-stats{flex-wrap:wrap}}
</style>
