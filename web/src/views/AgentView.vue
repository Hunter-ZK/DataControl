<template>
  <div class="dc-page"><div class="dc-container agent-page">
    <section class="agent-hero dc-card">
      <div><span class="dc-eyebrow">TRUSTED DATA Q&A</span><h1>智能问数</h1><p>DataAgent 已内置于 DataControl：dsh Headless 负责 Agent Loop，MCP 调用 Agent3 Core，并通过只读 Portal Metadata 获取资产事实。系统可以生成和校验 SQL，但不会执行 SQL。</p></div>
      <div class="runtime-pill" :class="{ready:status?.ready}"><span></span><div><b>{{status?.ready?'Agent 可用':'Agent 未就绪'}}</b><small>{{status?.ready?`${status.provider} · ${status.model}`:(status?.reason||'正在检测运行环境')}}</small></div></div>
    </section>

    <div class="agent-layout">
      <section class="dc-card chat-panel">
        <div class="messages" ref="messageBox">
          <article class="message assistant"><div class="avatar"><Sparkles :size="17"/></div><div><b>DataControl Agent</b><p>可查询资产、字段、指标口径和标准，也可以生成可信 SQL。所有 SQL 只生成、解释和校验，不执行。</p></div></article>
          <article v-for="(item,index) in messages" :key="index" class="message" :class="item.role">
            <div class="avatar"><User v-if="item.role==='user'" :size="16"/><Sparkles v-else :size="17"/></div>
            <div class="message-body"><b>{{item.role==='user'?'你':'DataControl Agent'}}</b><p v-if="item.text">{{item.text}}</p>
              <section v-if="item.sql" class="result-block"><div class="result-title"><Code2 :size="14"/>生成 SQL <span>未执行</span></div><pre>{{item.sql}}</pre></section>
              <section v-if="item.validation" class="result-block validation"><div class="result-title"><ShieldCheck :size="14"/>SQL Validation</div><pre>{{formatValidation(item.validation)}}</pre></section>
              <section v-if="item.events?.length" class="activity"><div class="result-title"><Workflow :size="14"/>处理记录</div><div v-for="(event,i) in visibleEvents(item.events)" :key="i" class="activity-row"><CheckCircle2 :size="13"/><span>{{activityText(event)}}</span></div></section>
            </div>
          </article>
          <article v-if="loading" class="message assistant"><div class="avatar"><LoaderCircle class="spin" :size="17"/></div><div><b>正在处理</b><p>正在通过 dsh → MCP → Agent3 Core → Portal Metadata 处理请求。隐藏推理不会展示。</p></div></article>
        </div>
        <div class="composer">
          <textarea v-model="question" :disabled="!status?.ready||loading" @keydown.enter.exact.prevent="submit" placeholder="例如：生成各地区最近一期贷款余额 SQL，并说明使用了哪些资产和指标口径" />
          <div class="composer-foot"><span><ShieldCheck :size="14"/>只读 · 不执行 SQL · 不展示隐藏推理</span><div class="composer-actions"><button class="secondary" :disabled="loading||messages.length===0" @click="newSession">新会话</button><button :disabled="!status?.ready||loading||!question.trim()" @click="submit"><Send :size="15"/>发送</button></div></div>
        </div>
      </section>

      <aside class="agent-side">
        <section class="dc-card side-card"><span class="dc-eyebrow">RUNTIME</span><h3>运行链路</h3><div class="runtime-flow"><span>DataControl Portal</span><ArrowDown/><span>Agent Gateway</span><ArrowDown/><span>dsh Headless → MCP</span><ArrowDown/><span>Agent3 Core</span><ArrowDown/><span>Portal Metadata</span></div></section>
        <section class="dc-card side-card"><span class="dc-eyebrow">STATUS</span><h3>环境状态</h3><dl><div><dt>Agent 源码迁入</dt><dd>{{yesNo(status?.sourceMigrated)}}</dd></div><div><dt>会话桥接</dt><dd>{{yesNo(status?.sessionBridgeImplemented)}}</dd></div><div><dt>Gateway</dt><dd>{{status?.serviceReachable?'已启动':'未启动'}}</dd></div><div><dt>真实模型验收</dt><dd>{{status?.realModelAccepted?'已记录':'待本机验收'}}</dd></div><div><dt>SQL 执行</dt><dd>关闭</dd></div><div><dt>隐藏推理</dt><dd>不展示</dd></div><div v-if="sessionId"><dt>Session</dt><dd class="session-id">{{sessionId}}</dd></div></dl></section>
        <section v-if="!status?.ready" class="dc-card side-card blocker"><TriangleAlert :size="18"/><div><b>当前阻塞</b><p>{{status?.reason}}</p><small>源码已经迁入 DataControl。通常只需完成 Agent 环境安装、启动本地 Gateway/MCP，并在启动前设置 DEEPSEEK_API_KEY。</small></div></section>
      </aside>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ArrowDown, CheckCircle2, Code2, LoaderCircle, Send, ShieldCheck, Sparkles, TriangleAlert, User, Workflow } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { agentApi, type AgentActivity, type AgentStatus } from '@/api/client'

type Message={role:'user'|'assistant';text:string;sql?:string|null;validation?:unknown;events?:AgentActivity[]}
const status=ref<AgentStatus|null>(null)
const question=ref('')
const loading=ref(false)
const messages=ref<Message[]>([])
const messageBox=ref<HTMLElement|null>(null)
const sessionId=ref<string|null>(null)
async function refreshStatus(){try{status.value=await agentApi.status()}catch{status.value=null}}
async function scrollBottom(){await nextTick();if(messageBox.value)messageBox.value.scrollTop=messageBox.value.scrollHeight}
function yesNo(value?:boolean){return value?'是':'否'}
function formatValidation(value:unknown){return typeof value==='string'?value:JSON.stringify(value,null,2)}
function visibleEvents(events:AgentActivity[]){return events.filter(x=>x.type==='tool_call'||x.type==='tool_result').slice(-12)}
function activityText(event:AgentActivity){if(event.type==='tool_call')return `调用 ${event.tool||'Agent3 工具'}`;return `${event.tool||'Agent3 工具'} ${event.status==='error'?'返回异常':'完成'}`}
function newSession(){sessionId.value=null;messages.value=[]}
async function submit(){
  const q=question.value.trim();if(!q||!status.value?.ready||loading.value)return
  messages.value.push({role:'user',text:q});question.value='';loading.value=true;await scrollBottom()
  try{
    const result=await agentApi.query(q,sessionId.value)
    if(result.sessionId)sessionId.value=result.sessionId
    messages.value.push({role:'assistant',text:result.answer||'Agent 已完成处理，但没有返回可展示文本。',sql:result.sql,validation:result.validation,events:result.events})
    await scrollBottom()
  }catch(e:any){
    const detail=e?.response?.data?.detail
    ElMessage.error(typeof detail==='string'?detail:(detail?.reason||detail?.message||'智能问数调用失败'))
    await refreshStatus()
  }finally{loading.value=false}
}
onMounted(refreshStatus)
</script>

<style scoped>
.agent-page{max-width:1320px}.agent-hero{padding:28px 30px;display:flex;justify-content:space-between;gap:24px;align-items:center;background:linear-gradient(135deg,#f0fafd,#fff 62%)}.agent-hero h1{font-size:31px;margin:8px 0}.agent-hero p{max-width:780px;margin:0;color:var(--dc-text-2);font-size:12px;line-height:1.7}.runtime-pill{min-width:230px;display:flex;align-items:center;gap:10px;padding:12px 14px;border:1px solid #ead8b6;border-radius:12px;background:#fffbf3}.runtime-pill>span{width:9px;height:9px;border-radius:50%;background:#d99b37}.runtime-pill.ready{border-color:#cfe9dd;background:#f4fbf8}.runtime-pill.ready>span{background:#3ba57a}.runtime-pill div{display:grid;gap:3px}.runtime-pill b{font-size:11px}.runtime-pill small{font-size:9px;color:var(--dc-text-3);max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.agent-layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:16px;margin-top:16px}.chat-panel{min-height:650px;display:grid;grid-template-rows:minmax(0,1fr) auto;overflow:hidden}.messages{padding:24px;overflow:auto;max-height:700px}.message{display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px;margin-bottom:22px}.avatar{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:#eef8fc;color:#2b7e9f}.message.user .avatar{background:#f2f4f6;color:#617480}.message b{font-size:11px}.message p{margin:6px 0 0;font-size:13px;line-height:1.75;color:#415f70;white-space:pre-wrap}.message-body{min-width:0}.result-block,.activity{margin-top:12px;border:1px solid #e0ebf0;border-radius:10px;overflow:hidden;background:#fbfdfe}.result-title{display:flex;align-items:center;gap:6px;padding:9px 11px;font-size:10px;font-weight:700;color:#567687}.result-title span{margin-left:auto;color:#4d9a78;font-weight:600}.result-block pre{margin:0;padding:14px;background:#122738;color:#dceef7;overflow:auto;font-size:11px;line-height:1.65}.validation pre{background:#f6fafb;color:#36596b;border-top:1px solid #e4edf1}.activity{padding-bottom:7px}.activity-row{display:flex;align-items:center;gap:7px;padding:5px 11px;color:#5d7887;font-size:10px}.activity-row svg{color:#52a17d;flex:none}.composer{border-top:1px solid var(--dc-border);padding:14px;background:#fbfdfe}.composer textarea{width:100%;min-height:88px;resize:vertical;border:1px solid #d6e6ee;border-radius:12px;padding:13px;outline:0;font:inherit;color:var(--dc-text);background:#fff}.composer textarea:focus{border-color:#8bc7df;box-shadow:0 0 0 3px rgba(82,164,199,.08)}.composer-foot{display:flex;justify-content:space-between;align-items:center;margin-top:9px}.composer-foot>span{display:flex;align-items:center;gap:5px;color:#718a99;font-size:10px}.composer-actions{display:flex;gap:8px}.composer-actions button{border:0;border-radius:9px;background:var(--dc-primary);color:#fff;padding:9px 14px;display:flex;align-items:center;gap:6px;cursor:pointer}.composer-actions button.secondary{background:#eef4f7;color:#55717f}.composer-actions button:disabled{opacity:.45;cursor:not-allowed}.agent-side{display:grid;gap:14px;align-content:start}.side-card{padding:18px}.side-card h3{font-size:15px;margin:6px 0 14px}.runtime-flow{display:grid;justify-items:center;gap:5px}.runtime-flow span{width:100%;padding:9px;border-radius:9px;text-align:center;background:#f5fafc;border:1px solid #e2edf2;font-size:10px;font-weight:700;color:#47758b}.runtime-flow svg{color:#91aab7}.side-card dl{display:grid;gap:9px;margin:0}.side-card dl div{display:flex;justify-content:space-between;padding-bottom:8px;border-bottom:1px solid #edf3f6}.side-card dt,.side-card dd{font-size:10px}.side-card dt{color:var(--dc-text-3)}.side-card dd{margin:0;font-weight:700;text-align:right}.session-id{max-width:145px;overflow:hidden;text-overflow:ellipsis}.blocker{display:flex;gap:10px;border-color:#ead9b8;background:#fffcf6;color:#86602a}.blocker b{font-size:11px}.blocker p{font-size:10px;line-height:1.55;margin:5px 0}.blocker small{font-size:9px;line-height:1.5;color:#9b7a48}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:920px){.agent-layout{grid-template-columns:1fr}.agent-side{grid-template-columns:1fr 1fr}.blocker{grid-column:1/-1}}@media(max-width:620px){.agent-hero{align-items:flex-start;flex-direction:column}.runtime-pill{width:100%}.agent-side{grid-template-columns:1fr}.composer-foot{align-items:flex-start;gap:10px;flex-direction:column}.composer-actions{align-self:flex-end}}
</style>
