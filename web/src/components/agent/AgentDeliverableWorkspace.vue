<template>
  <section class="deliverable-workspace" aria-label="Agent 独立成果工作区">
    <header class="workspace-head">
      <div class="workspace-brand"><span class="workspace-icon"><PanelsTopLeft :size="24"/></span>
        <div><span class="work-eyebrow">DELIVERABLE WORKSPACE</span><h2>任务成果工作区</h2>
          <p>集中查看当前会话真实返回的回答、SQL 草案、依据和执行记录。</p></div>
      </div>
      <button class="workspace-close" @click="emit('close')" aria-label="关闭成果工作区"><X :size="19"/></button>
    </header>
    <div class="workspace-meta">
      <span><FileCheck2 :size="16"/> {{items.length}} 轮实际回答</span>
      <span><Code2 :size="16"/> {{sqlCount}} 份 SQL</span>
      <span v-if="running"><LoaderCircle :size="16" class="spin"/> 本轮仍在执行中</span>
    </div>
    <div v-if="!items.length" class="workspace-empty">
      <Boxes :size="43"/><h3>当前会话还没有可查看的成果</h3>
      <p>完成一轮 Agent 回答后，这里会收集实际返回的内容。不会提前生成模拟成果。</p>
    </div>
    <template v-else>
      <div class="deliverable-selector">
        <label for="deliverable-turn">选择成果</label>
        <select id="deliverable-turn" v-model.number="selectedIndex">
          <option v-for="entry in items" :key="entry.index" :value="entry.index">
            第 {{entry.number}} 次回答 · {{entry.message.sql?'含 SQL':'分析说明'}} · {{entry.label}}
          </option>
        </select>
      </div>
      <nav class="deliverable-tabs" aria-label="成果内容">
        <button :class="{active:tab==='summary'}" @click="tab='summary'"><FileText :size="17"/>成果说明</button>
        <button :class="{active:tab==='sql'}" @click="tab='sql'"><Code2 :size="17"/>SQL 草案</button>
        <button :class="{active:tab==='evidence'}" @click="tab='evidence'"><Database :size="17"/>依据</button>
        <button :class="{active:tab==='process'}" @click="tab='process'"><Workflow :size="17"/>任务记录</button>
      </nav>
      <div class="deliverable-scroll" v-if="selectedMessage">
        <div class="section-caption">
          <span>{{ currentHeading }}</span><span v-if="selectedMessage.durationMs">耗时 {{(selectedMessage.durationMs/1000).toFixed(1)}} 秒</span>
        </div>
        <section v-if="tab==='summary'" class="deliverable-section">
          <AgentMarkdown :text="selectedMessage.text"/>
        </section>
        <section v-else-if="tab==='sql'" class="deliverable-section">
          <template v-if="selectedMessage.sql">
            <AgentSqlCard :message="selectedMessage"/>
            <AgentValidationPanel :message="selectedMessage"/>
          </template>
          <p v-else class="section-empty">这一轮没有返回独立的 SQL 草案。可查看成果说明，或选择其他回答。</p>
        </section>
        <section v-else-if="tab==='evidence'" class="deliverable-section">
          <AgentEvidence v-if="selectedMessage.evidence" :evidence="selectedMessage.evidence"/>
          <p v-else class="section-empty">这一轮未提供结构化数据依据，不补造资产或引用。</p>
        </section>
        <section v-else class="deliverable-section">
          <template v-if="selectedMessage.events?.length">
            <AgentTaskJourney :events="selectedMessage.events" :tier="tier" :running="false"/>
            <AgentTrace :events="selectedMessage.events"/>
          </template>
          <p v-else class="section-empty">这一轮没有可展示的真实工具事件。</p>
        </section>
      </div>
      <footer class="deliverable-actions">
        <span><ShieldCheck :size="16"/> 仅展示与导出，不执行 SQL</span>
        <button @click="copyCurrent"><Copy :size="16"/>复制{{tab==='sql'?' SQL':'内容'}}</button>
        <button @click="downloadCurrent"><Download :size="16"/>导出{{tab==='sql'&&selectedMessage?.sql?' .sql':' .md'}}</button>
      </footer>
    </template>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Boxes, Code2, Copy, Database, Download, FileCheck2, FileText, LoaderCircle, PanelsTopLeft, ShieldCheck, Workflow, X } from 'lucide-vue-next'
import AgentMarkdown from './AgentMarkdown.vue'
import AgentSqlCard from './AgentSqlCard.vue'
import AgentEvidence from './AgentEvidence.vue'
import AgentTaskJourney from './AgentTaskJourney.vue'
import AgentValidationPanel from './AgentValidationPanel.vue'
import AgentTrace from './AgentTrace.vue'
import type { AgentMessage } from './types'
import { displaySql } from './presentation'

const props=withDefaults(defineProps<{ messages:AgentMessage[]; tier?:'standard'|'multi'; running?:boolean }>(),{tier:'standard',running:false})
const emit=defineEmits<{close:[]}>()
const tab=ref<'summary'|'sql'|'evidence'|'process'>('summary')
const items=computed(()=>props.messages.map((message,index)=>({message,index,number:props.messages.slice(0,index+1).filter(x=>x.role==='assistant').length,label:(message.summary||message.text||'分析结果').replace(/\s+/g,' ').slice(0,27)}))
  .filter(x=>x.message.role==='assistant'&&!!(x.message.text||x.message.sql||x.message.events?.length)))
const selectedIndex=ref(-1)
watch(items,rows=>{if(!rows.some(x=>x.index===selectedIndex.value))selectedIndex.value=rows[rows.length-1]?.index??-1},{immediate:true})
const selectedMessage=computed(()=>items.value.find(x=>x.index===selectedIndex.value)?.message||null)
const sqlCount=computed(()=>items.value.filter(x=>!!x.message.sql).length)
const currentHeading=computed(()=>({summary:'最终回答与草案说明',sql:'生成的 SQL 与静态校验',evidence:'来源资产与统计口径',process:'真实工具调用记录'} as const)[tab.value])
function currentContent(){
  const item=selectedMessage.value
  if(!item)return ''
  if(tab.value==='sql')return item.sql?displaySql(item):''
  if(tab.value==='summary')return item.text||''
  if(tab.value==='evidence')return item.evidence?JSON.stringify(item.evidence,null,2):''
  return item.events?.length?JSON.stringify(item.events,null,2):''
}
async function copyCurrent(){
  const content=currentContent()
  if(!content){ElMessage.info('当前栏目没有可复制的结果');return}
  try{await navigator.clipboard.writeText(content);ElMessage.success('已复制当前成果')}
  catch{ElMessage.warning('复制失败，请手动选取内容')}
}
function downloadCurrent(){
  const content=currentContent()
  if(!content){ElMessage.info('当前栏目没有可导出的结果');return}
  const isSql=tab.value==='sql'
  const ext=isSql?'sql':tab.value==='summary'?'md':'json'
  const file=new Blob([content],{type:isSql?'text/plain;charset=utf-8':ext==='json'?'application/json;charset=utf-8':'text/markdown;charset=utf-8'})
  const url=URL.createObjectURL(file)
  const anchor=document.createElement('a')
  anchor.href=url;anchor.download='datacontrol-result-'+(selectedIndex.value+1)+'.'+ext
  document.body.appendChild(anchor);anchor.click();anchor.remove()
  URL.revokeObjectURL(url)
}
</script>
<style scoped>
.deliverable-workspace{min-width:0;min-height:0;display:flex;flex-direction:column;background:linear-gradient(155deg,#f7fbff,#edf4ff);border-left:1px solid #b7d2f4;color:#223e65;overflow:hidden}
.workspace-head{display:flex;justify-content:space-between;gap:15px;padding:21px 21px 17px;background:linear-gradient(107deg,#193f7b,#316fd3);color:#fff;flex:none}
.workspace-brand{display:flex;gap:12px;align-items:center;min-width:0}
.workspace-icon{display:grid;place-items:center;width:49px;height:49px;flex:none;border-radius:14px;background:#ffffff27;border:1px solid #a6c8ff8a}
.work-eyebrow{font-size:11px;font-weight:760;letter-spacing:.1em;color:#c0dfff}
.workspace-brand h2{font-size:19px;margin:3px 0 2px;color:white}
.workspace-brand p{font-size:12px;line-height:1.45;color:#dceaff;margin:0}
.workspace-close{display:grid;place-items:center;align-self:flex-start;border:1px solid #ffffff63;background:#ffffff23;color:white;border-radius:8px;width:33px;height:33px;cursor:pointer;flex:none}
.workspace-meta{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:12px 19px;border-bottom:1px solid #d7e5fa;background:#ebf4ff}
.workspace-meta>span{display:inline-flex;align-items:center;gap:6px;color:#4576b7;font-size:12px;font-weight:700}
.deliverable-selector{display:flex;align-items:center;gap:10px;padding:14px 19px;background:#fff;border-bottom:1px solid #dce8f8}
.deliverable-selector label{white-space:nowrap;color:#627a9b;font-size:13px;font-weight:700}
.deliverable-selector select{flex:1;min-width:0;border:1px solid #bdd3f3;border-radius:8px;padding:9px 10px;background:#f8fbff;color:#2c507c;font-size:13px;cursor:pointer}
.deliverable-tabs{display:flex;align-items:center;gap:4px;padding:10px 12px;background:#f3f8ff;border-bottom:1px solid #d9e7f8;overflow-x:auto;flex:none}
.deliverable-tabs button{display:inline-flex;align-items:center;justify-content:center;gap:7px;flex:1;min-width:max-content;border:0;background:transparent;border-radius:8px;color:#7087a6;font-size:13px;font-weight:700;padding:10px 8px;cursor:pointer}
.deliverable-tabs button.active{background:#fff;color:#2469d7;box-shadow:0 3px 11px #3266a51c}
.deliverable-scroll{flex:1;overflow-y:auto;padding:19px 22px;min-height:0;overscroll-behavior:contain}
.section-caption{display:flex;align-items:center;justify-content:space-between;gap:10px;color:#6a88b0;font-size:12px;font-weight:720;margin-bottom:12px}
.deliverable-section{background:#fff;border:1px solid #d4e4f8;border-radius:12px;padding:17px 19px;min-width:0;box-shadow:0 6px 23px #3669a310}
.deliverable-section:has(.sql-card){padding:10px}
.deliverable-section :deep(.sql-card){max-width:100%}
.section-empty{font-size:13px;line-height:1.8;color:#8196b2;margin:0}
.deliverable-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:13px 18px;background:#fff;border-top:1px solid #d3e3f8}
.deliverable-actions>span{display:flex;gap:6px;align-items:center;margin-right:auto;color:#7389a6;font-size:11px}
.deliverable-actions button{display:inline-flex;align-items:center;gap:6px;border:1px solid #c3d8f5;border-radius:8px;background:#f2f7ff;color:#296bd4;font-size:12px;font-weight:750;cursor:pointer;padding:9px 11px}
.deliverable-actions button:hover{background:#e7f0ff;border-color:#8db6ee}
.workspace-empty{display:grid;justify-items:center;align-content:center;gap:12px;flex:1;text-align:center;padding:45px 22px;color:#6290cf}
.workspace-empty h3{margin:0;font-size:17px;color:#2b507b}
.workspace-empty p{margin:0;color:#8095b0;font-size:13px;line-height:1.7;max-width:350px}
.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:720px){.workspace-head{padding:16px}.workspace-brand h2{font-size:16px}.workspace-brand p{font-size:11px}.workspace-meta{gap:8px;padding:10px 14px}.deliverable-scroll{padding:12px}.deliverable-section{padding:12px}.deliverable-selector{padding:11px 13px}.deliverable-actions{padding:10px}}
</style>
