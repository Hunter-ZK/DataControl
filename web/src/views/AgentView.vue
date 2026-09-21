<template>
  <div class="dc-page agent-screen">
    <div class="dc-container agent-page">
      <header class="agent-head">
        <div>
          <span class="dc-eyebrow">INTELLIGENT DATA Q&A</span>
          <h1>智能问数</h1>
          <p>用自然语言查找指标与资产，生成经过校验的可信 SQL。系统只生成和校验，不执行生产 SQL。</p>
        </div>
        <div class="head-actions">
          <span class="service-status" :class="{ready:status?.ready}"><i></i>{{status?.ready?'服务正常':'服务未就绪'}}</span>
          <button class="new-chat" :disabled="loading" @click="newSession"><Plus :size="16"/>新会话</button>
        </div>
      </header>

      <section class="chat-shell dc-card">
        <div v-if="contextAsset" class="context-strip">
          <Database :size="17"/>
          <div><span>当前数据资产</span><b>{{contextAsset.bizName||contextAsset.tableName}}</b><code>{{contextAsset.tableName}}</code></div>
          <button @click="clearContext"><X :size="15"/>清除</button>
        </div>
        <div v-if="!status?.ready" class="runtime-warning"><TriangleAlert :size="17"/><span>{{status?.reason||'智能问数服务正在初始化，请稍后重试。'}}</span></div>

        <div class="messages" ref="messageBox">
          <div v-if="messages.length===0" class="welcome">
            <div class="welcome-icon"><Sparkles :size="24"/></div>
            <h2>想查什么数据？</h2>
            <p>我会先确认指标、数据资产和统计口径，再生成并校验 SQL。</p>
            <div class="prompt-grid">
              <button v-for="item in quickPrompts" :key="item" @click="usePrompt(item)">{{item}}<ArrowUpRight :size="14"/></button>
            </div>
          </div>

          <article v-for="(item,index) in messages" :key="index" class="message" :class="item.role">
            <div v-if="item.role==='user'" class="user-bubble">{{item.text}}</div>
            <div v-else class="assistant-answer">
              <div class="answer-label"><span class="agent-avatar"><Sparkles :size="15"/></span><b>DataAgent</b></div>
              <div class="answer-summary">{{item.summary || firstLine(item.text)}}</div>
              <div v-for="(paragraph,p) in answerParagraphs(item.text,item.summary)" :key="p" class="answer-paragraph">{{paragraph}}</div>

              <div v-if="hasEvidence(item.evidence)" class="evidence-area">
                <div class="evidence-row" v-if="item.evidence?.period"><span>统计期间</span><b>{{item.evidence.period.label}}</b></div>
                <div class="evidence-row" v-if="item.evidence?.metrics?.length"><span>使用指标</span><div class="chips"><span v-for="(metric,m) in item.evidence.metrics" :key="metric.code||metric.name||`metric-${m}`" class="evidence-chip metric"><BarChart3 :size="13"/>{{metric.name||metric.code}}</span></div></div>
                <div class="evidence-row" v-if="item.evidence?.datasets?.length"><span>引用资产</span><div class="chips"><span v-for="(table,t) in item.evidence.datasets.slice(0,4)" :key="table.tableName||table.name||`dataset-${t}`" class="evidence-chip"><Database :size="13"/>{{shortTable(table.tableName||table.name||'')}}</span></div></div>
                <div class="evidence-row" v-if="item.evidence?.dimensions?.length"><span>分析维度</span><div class="chips"><span v-for="dim in item.evidence.dimensions" :key="dim" class="evidence-chip neutral">{{dimensionName(dim)}} <code>{{dim}}</code></span></div></div>
                <div class="caliber" v-if="item.evidence?.caliber"><span>统计口径</span><p>{{item.evidence.caliber}}</p></div>
              </div>

              <section v-if="item.sql" class="sql-card">
                <div class="block-head"><div><Code2 :size="15"/><b>生成 SQL</b><span>已校验 · 未执行</span></div><button @click="copySql(item.sql)"><Copy :size="14"/>复制</button></div>
                <pre>{{item.sql}}</pre>
              </section>

              <details v-if="item.validation" class="detail-card validation-card">
                <summary><span :class="['validation-dot',{pass:validationPassed(item.validation)}]"></span><b>{{validationPassed(item.validation)?'SQL 校验通过':'查看 SQL 校验结果'}}</b><ChevronDown :size="15"/></summary>
                <pre>{{formatValidation(item.validation)}}</pre>
              </details>
              <details v-if="item.events?.length" class="detail-card">
                <summary><Workflow :size="15"/><b>查看处理过程</b><span>{{visibleEvents(item.events).length}} 步</span><ChevronDown :size="15"/></summary>
                <div class="activity-list"><div v-for="(event,i) in visibleEvents(item.events)" :key="i" class="activity-row"><CheckCircle2 :size="14"/><span>{{activityText(event)}}</span></div></div>
              </details>
            </div>
          </article>

          <article v-if="loading" class="message assistant">
            <div class="assistant-answer loading-answer"><div class="answer-label"><span class="agent-avatar"><LoaderCircle class="spin" :size="15"/></span><b>DataAgent 正在分析</b></div><p>正在解析指标、资产与统计口径，并执行 SQL 校验…</p></div>
          </article>
        </div>

        <div class="composer-wrap">
          <div class="composer" :class="{disabled:!status?.ready}">
            <textarea ref="composer" v-model="question" rows="1" :disabled="!status?.ready||loading" @input="resizeComposer" @keydown.enter.exact.prevent="submit" placeholder="输入你的问题，例如：本期各地区贷款余额是多少？" />
            <button class="send" :disabled="!status?.ready||loading||!question.trim()" @click="submit"><Send :size="18"/></button>
          </div>
          <div class="composer-hint"><span>Enter 发送 · Shift+Enter 换行</span><span><ShieldCheck :size="13"/>只读分析 · SQL 不执行</span></div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, BarChart3, CheckCircle2, ChevronDown, Code2, Copy, Database, LoaderCircle, Plus, Send, ShieldCheck, Sparkles, TriangleAlert, Workflow, X } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { agentApi, assetApi, type AgentActivity, type AgentEvidence, type AgentResult, type AgentStatus } from '@/api/client'

type Message={role:'user'|'assistant';text:string;summary?:string|null;sql?:string|null;validation?:unknown;events?:AgentActivity[];evidence?:AgentEvidence}
type ContextAsset={assetId:string;tableName:string;bizName?:string|null}
const route=useRoute();const router=useRouter()
const status=ref<AgentStatus|null>(null);const question=ref('');const loading=ref(false);const messages=ref<Message[]>([])
const messageBox=ref<HTMLElement|null>(null);const composer=ref<HTMLTextAreaElement|null>(null);const sessionId=ref<string|null>(null);const contextAsset=ref<ContextAsset|null>(null)
const quickPrompts=['本期各地区贷款余额是多少？','本期各机构普惠贷款余额','本期不良贷款余额怎么统计？','本期各地区存款余额','region_code 是什么字段？','贷款余额使用哪张数据表？']
async function refreshStatus(){try{status.value=await agentApi.status()}catch{status.value=null}}
async function loadContext(){const asset=typeof route.query.asset==='string'?route.query.asset:'';if(!asset)return;try{const row=await assetApi.table(asset);contextAsset.value={assetId:row.assetId,tableName:row.tableName,bizName:row.bizName}}catch{contextAsset.value=null}}
async function clearContext(){contextAsset.value=null;await router.replace({name:'agent'})}
function newSession(){sessionId.value=null;messages.value=[];question.value='';nextTick(resizeComposer)}
function usePrompt(value:string){question.value=value;nextTick(()=>{resizeComposer();submit()})}
async function scrollBottom(){await nextTick();if(messageBox.value)messageBox.value.scrollTo({top:messageBox.value.scrollHeight,behavior:'smooth'})}
function resizeComposer(){const el=composer.value;if(!el)return;el.style.height='auto';el.style.height=`${Math.min(el.scrollHeight,144)}px`}
function firstLine(text:string){return text.split(/\n+/).find(Boolean)||'分析完成'}
function answerParagraphs(text:string,summary?:string|null){const first=summary||firstLine(text);return text.split(/\n{2,}|\n/).map(x=>x.trim()).filter(x=>x&&x!==first).slice(0,8)}
function hasEvidence(e?:AgentEvidence){return !!(e?.metrics?.length||e?.datasets?.length||e?.dimensions?.length||e?.period||e?.caliber)}
function shortTable(value:string){return value.includes('.')?value.split('.').pop()||value:value}
function dimensionName(value:string){return ({region_code:'地区',org_code:'机构',customer_type:'客户类型',loan_type:'贷款类型',currency_cd:'币种',product_code:'产品'} as Record<string,string>)[value]||'维度'}
function validationPassed(value:any){return value?.valid===true||value?.ok===true||value?.passed===true}
function formatValidation(value:unknown){return typeof value==='string'?value:JSON.stringify(value,null,2)}
function visibleEvents(events:AgentActivity[]){return events.filter(x=>x.type==='tool_call'||x.type==='tool_result').slice(-14)}
function activityText(event:AgentActivity){const labels:Record<string,string>={resolve_metric:'解析指标',get_schema:'读取表结构',search_tables:'检索数据资产',get_semantic_model:'读取指标口径',compile_query:'生成可信 SQL',validate_sql:'校验 SQL',explain_sql:'解析 SQL',search_verified_sql:'检索可信 SQL'};const name=labels[event.tool||'']||event.tool||'Agent3 工具';return event.type==='tool_call'?name:`${name}${event.status==='error'?'失败':'完成'}`}
async function copySql(value:string){try{await navigator.clipboard.writeText(value);ElMessage.success('SQL 已复制')}catch{ElMessage.warning('复制失败，请手动复制')}}
async function submit(){
  const q=question.value.trim();if(!q||!status.value?.ready||loading.value)return
  messages.value.push({role:'user',text:q});question.value='';resizeComposer();loading.value=true;await scrollBottom()
  const prompt=contextAsset.value?`当前问题针对 DataControl 数据资产：${contextAsset.value.bizName||contextAsset.value.tableName}（asset_id=${contextAsset.value.assetId}，table=${contextAsset.value.tableName}）。请优先通过 Agent3 MCP 读取该资产及关联事实后回答，不要凭空猜测。\n用户问题：${q}`:q
  try{
    const result:AgentResult=await agentApi.query(prompt,sessionId.value);if(result.sessionId)sessionId.value=result.sessionId
    messages.value.push({role:'assistant',text:result.answer||'分析完成。',summary:result.summary,sql:result.sql,validation:result.validation,events:result.events,evidence:result.evidence});await scrollBottom()
  }catch(e:any){const detail=e?.response?.data?.detail;ElMessage.error(typeof detail==='string'?detail:(detail?.reason||detail?.message||'智能问数调用失败'));await refreshStatus()}
  finally{loading.value=false;await scrollBottom()}
}
onMounted(async()=>{await Promise.all([refreshStatus(),loadContext()]);resizeComposer()})
</script>

<style scoped>
.agent-screen{height:calc(100dvh - var(--dc-topbar));min-height:680px;padding:20px 0;background:linear-gradient(180deg,#eaf5fb 0,#f4f8fb 34%,#f4f8fb 100%);overflow:hidden}.agent-page{height:100%;display:flex;flex-direction:column;max-width:1240px}.agent-head{flex:none;display:flex;align-items:flex-end;justify-content:space-between;gap:28px;padding:2px 4px 18px}.agent-head h1{font-size:36px;letter-spacing:-.035em;margin:6px 0 7px;color:#173b4d}.agent-head p{font-size:14px;line-height:1.65;margin:0;color:#496b7e;max-width:720px}.head-actions{display:flex;align-items:center;gap:10px}.service-status{display:flex;align-items:center;gap:7px;padding:9px 12px;border-radius:999px;background:#fff7e8;border:1px solid #efd8a7;font-size:12px;font-weight:700;color:#8b6426}.service-status i{width:8px;height:8px;border-radius:50%;background:#d79b39}.service-status.ready{background:#edf9f4;border-color:#c9e7d9;color:#277b5c}.service-status.ready i{background:#34a477}.new-chat{display:flex;align-items:center;gap:6px;border:1px solid #c8dce7;background:#fff;color:#285a73;border-radius:10px;padding:9px 13px;font-size:13px;font-weight:700;cursor:pointer}.new-chat:hover{background:#f4fafc}.chat-shell{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden;border-color:#cfe1ea;box-shadow:0 18px 50px rgba(34,91,123,.11);background:rgba(255,255,255,.98)}.context-strip{flex:none;display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:11px 18px;background:#edf7fb;border-bottom:1px solid #d7e8f0;color:#315f75}.context-strip>div{display:flex;align-items:baseline;gap:9px;min-width:0}.context-strip span{font-size:12px;color:#668697}.context-strip b{font-size:13px}.context-strip code{font-size:11px;color:#718e9e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.context-strip button{display:flex;align-items:center;gap:4px;border:0;background:transparent;color:#557889;font-size:12px;cursor:pointer}.runtime-warning{flex:none;display:flex;gap:8px;align-items:center;padding:10px 18px;background:#fff8e9;border-bottom:1px solid #efdcb5;color:#8b672d;font-size:13px}.messages{flex:1;min-height:0;overflow-y:auto;padding:28px clamp(22px,5vw,68px);scrollbar-gutter:stable}.welcome{max-width:760px;margin:6vh auto 0;text-align:center}.welcome-icon{width:52px;height:52px;border-radius:16px;display:grid;place-items:center;margin:0 auto 14px;color:#197aa6;background:linear-gradient(145deg,#dff3fb,#eef9fd);border:1px solid #c7e5f1}.welcome h2{font-size:27px;margin:0;color:#1b4559}.welcome p{font-size:14px;color:#648091;margin:8px 0 22px}.prompt-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.prompt-grid button{min-height:48px;display:flex;justify-content:space-between;align-items:center;text-align:left;gap:12px;padding:12px 14px;border:1px solid #d9e8ef;border-radius:12px;background:#fbfdfe;color:#345c70;font-size:13px;cursor:pointer}.prompt-grid button:hover{border-color:#9fcede;background:#eef8fc;color:#176d94}.message{margin:0 0 24px}.message.user{display:flex;justify-content:flex-end}.user-bubble{max-width:72%;padding:11px 15px;border-radius:16px 16px 4px 16px;background:#196f98;color:#fff;font-size:14px;line-height:1.65;box-shadow:0 7px 20px rgba(25,111,152,.14)}.assistant-answer{max-width:920px}.answer-label{display:flex;align-items:center;gap:8px;margin-bottom:9px;color:#244d61;font-size:13px}.agent-avatar{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;background:#e7f5fb;color:#1679a5}.answer-summary{font-size:16px;line-height:1.72;font-weight:650;color:#213f50}.answer-paragraph{margin-top:7px;font-size:14px;line-height:1.72;color:#496779;white-space:pre-wrap}.evidence-area{margin-top:14px;padding:13px 15px;background:#f4f9fb;border:1px solid #dceaf0;border-radius:12px;display:grid;gap:10px}.evidence-row{display:grid;grid-template-columns:74px minmax(0,1fr);gap:10px;align-items:flex-start}.evidence-row>span,.caliber>span{font-size:12px;font-weight:700;color:#78909e;padding-top:4px}.evidence-row>b{font-size:13px;color:#294e61;padding-top:3px}.chips{display:flex;flex-wrap:wrap;gap:7px}.evidence-chip{display:inline-flex;align-items:center;gap:5px;border-radius:8px;padding:6px 8px;background:#e7f4fa;color:#23627e;font-size:12px;font-weight:650}.evidence-chip.metric{background:#e8f6f0;color:#287257}.evidence-chip.neutral{background:#fff;border:1px solid #dce8ee;color:#506e7e;font-weight:600}.evidence-chip code{font-size:10px;color:#78909d}.caliber{display:grid;grid-template-columns:74px minmax(0,1fr);gap:10px;border-top:1px solid #e1ebef;padding-top:9px}.caliber p{margin:0;font-size:13px;line-height:1.65;color:#476879}.sql-card{margin-top:14px;border:1px solid #cbdde6;border-radius:12px;overflow:hidden;background:#102b3b}.block-head{min-height:42px;padding:0 12px;display:flex;align-items:center;justify-content:space-between;background:#f4f8fa;color:#365c70}.block-head>div{display:flex;align-items:center;gap:7px}.block-head b{font-size:13px}.block-head span{font-size:11px;color:#378064;background:#e5f4ed;border-radius:999px;padding:3px 7px}.block-head button{display:flex;align-items:center;gap:5px;border:0;background:transparent;color:#517486;font-size:12px;cursor:pointer}.sql-card pre{margin:0;padding:16px 17px;color:#dcecf4;font-size:13px;line-height:1.7;overflow:auto;white-space:pre-wrap}.detail-card{margin-top:10px;border:1px solid #dde9ee;border-radius:10px;background:#fff;overflow:hidden}.detail-card summary{list-style:none;display:flex;align-items:center;gap:7px;padding:10px 12px;cursor:pointer;color:#4d6d7d;font-size:12px}.detail-card summary::-webkit-details-marker{display:none}.detail-card summary b{font-size:12px;color:#35586a}.detail-card summary span:not(.validation-dot){margin-left:auto;color:#8095a0}.detail-card summary svg:last-child{margin-left:auto}.detail-card pre{margin:0;padding:12px 14px;border-top:1px solid #e5edf1;background:#f7fafb;color:#405f6f;font-size:11px;overflow:auto;max-height:240px}.validation-dot{width:9px;height:9px;border-radius:50%;background:#d6a047}.validation-dot.pass{background:#36a176}.activity-list{padding:6px 12px 10px;border-top:1px solid #edf2f4}.activity-row{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12px;color:#66808e}.activity-row svg{color:#43a17d}.loading-answer p{font-size:13px;color:#6b8593;margin:4px 0}.composer-wrap{flex:none;padding:12px 18px 13px;border-top:1px solid #dce8ee;background:#fbfdfe;box-shadow:0 -8px 22px rgba(48,91,115,.04)}.composer{display:flex;align-items:flex-end;gap:8px;max-width:1000px;margin:0 auto;border:1px solid #bcd8e5;background:#fff;border-radius:14px;padding:9px 9px 9px 14px;box-shadow:0 5px 20px rgba(41,102,134,.07)}.composer:focus-within{border-color:#58a7c9;box-shadow:0 0 0 3px rgba(48,151,195,.1)}.composer.disabled{background:#f6f8f9}.composer textarea{flex:1;border:0;outline:0;resize:none;min-height:26px;max-height:144px;overflow-y:auto;padding:4px 2px;background:transparent;color:#244658;font-size:14px;line-height:1.55}.composer textarea::placeholder{color:#96a9b3}.send{width:38px;height:38px;flex:none;border:0;border-radius:10px;display:grid;place-items:center;background:#197da8;color:#fff;cursor:pointer}.send:disabled{opacity:.38;cursor:not-allowed}.composer-hint{max-width:1000px;margin:7px auto 0;display:flex;justify-content:space-between;color:#849aa6;font-size:11px}.composer-hint span:last-child{display:flex;align-items:center;gap:4px}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:760px){.agent-screen{min-height:620px;padding:12px 0}.agent-head{align-items:flex-start;flex-direction:column;gap:10px;padding-bottom:12px}.agent-head h1{font-size:30px}.head-actions{width:100%;justify-content:space-between}.messages{padding:20px 14px}.prompt-grid{grid-template-columns:1fr}.user-bubble{max-width:88%}.context-strip>div{display:grid;gap:2px}.context-strip code{display:none}.composer-wrap{padding:10px}.composer-hint span:first-child{display:none}.composer-hint{justify-content:flex-end}.evidence-row,.caliber{grid-template-columns:1fr;gap:4px}}
</style>
