<template>
  <div class="dc-page"><div class="dc-container agent-page">
    <section class="agent-hero dc-card">
      <div><span class="dc-eyebrow">TRUSTED DATA Q&A</span><h1>智能问数</h1><p>DataAgent 已作为 DataControl 仓库内的独立子系统迁入：dsh 负责 Agent Loop，MCP Adapter 调用 Agent3 Core，Portal 负责产品入口与资产事实。当前仍在打通产品会话链路，不会执行 SQL。</p></div>
      <div class="runtime-pill" :class="{ready:status?.ready}"><span></span><div><b>{{status?.ready?'Agent 已就绪':'Agent 尚未开放'}}</b><small>{{status?.ready?`${status.provider} · ${status.model}`:(status?.reason||'正在检测运行环境')}}</small></div></div>
    </section>

    <div class="agent-layout">
      <section class="dc-card chat-panel">
        <div class="messages" ref="messageBox">
          <article class="message assistant"><div class="avatar"><Sparkles :size="17"/></div><div><b>DataControl Agent</b><p>问数入口会在真实 dsh → MCP → Agent3 Core 端到端链路验收后开放。在此之前，页面只展示真实运行状态，不返回模拟回答。</p></div></article>
          <article v-for="(item,index) in messages" :key="index" class="message" :class="item.role"><div class="avatar"><User v-if="item.role==='user'" :size="16"/><Sparkles v-else :size="17"/></div><div><b>{{item.role==='user'?'你':'DataControl Agent'}}</b><p v-if="item.text">{{item.text}}</p><pre v-if="item.sql">{{item.sql}}</pre></div></article>
          <article v-if="loading" class="message assistant"><div class="avatar"><LoaderCircle class="spin" :size="17"/></div><div><b>正在处理</b><p>正在通过仓库内 DataAgent / dsh / MCP / Agent3 Core 链路处理请求，不展示隐藏思维过程。</p></div></article>
        </div>
        <div class="composer">
          <textarea v-model="question" :disabled="!status?.ready||loading" @keydown.enter.exact.prevent="submit" placeholder="输入问题，例如：统计各地区最近一期贷款余额，需要用哪张表？" />
          <div class="composer-foot"><span><ShieldCheck :size="14"/>只读 · 不执行 SQL · 不展示隐藏推理</span><button :disabled="!status?.ready||loading||!question.trim()" @click="submit"><Send :size="15"/>发送</button></div>
        </div>
      </section>

      <aside class="agent-side">
        <section class="dc-card side-card"><span class="dc-eyebrow">RUNTIME</span><h3>运行链路</h3><div class="runtime-flow"><span>DataControl Portal</span><ArrowDown/><span>Embedded DataAgent</span><ArrowDown/><span>dsh → MCP</span><ArrowDown/><span>Agent3 Core</span></div></section>
        <section class="dc-card side-card"><span class="dc-eyebrow">STATUS</span><h3>环境状态</h3><dl><div><dt>运行模式</dt><dd>{{status?.mode||'—'}}</dd></div><div><dt>代码归属</dt><dd>{{status?.source||'DataControl/agent'}}</dd></div><div><dt>Agent 源码迁入</dt><dd>{{status?.sourceMigrated?'已完成':'未完成'}}</dd></div><div><dt>问数链路集成</dt><dd>{{status?.integrated?'已通过':'待验收'}}</dd></div><div><dt>Gateway</dt><dd>{{status?.serviceReachable?'可达':'未开放'}}</dd></div><div><dt>SQL 执行</dt><dd>关闭</dd></div><div><dt>隐藏推理</dt><dd>不展示</dd></div></dl></section>
        <section v-if="!status?.ready" class="dc-card side-card blocker"><TriangleAlert :size="18"/><div><b>当前阶段</b><p>{{status?.reason}}</p><small v-if="status?.nextGate">下一验收门：{{status.nextGate}}</small><small v-else>DataAgent-dsh 仅作为固定迁移基线，不是运行时外部依赖。</small></div></section>
      </aside>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ArrowDown, LoaderCircle, Send, ShieldCheck, Sparkles, TriangleAlert, User } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { agentApi, type AgentStatus } from '@/api/client'

type Message={role:'user'|'assistant';text:string;sql?:string}
const status=ref<AgentStatus|null>(null);const question=ref('');const loading=ref(false);const messages=ref<Message[]>([]);const messageBox=ref<HTMLElement|null>(null)
async function refreshStatus(){try{status.value=await agentApi.status()}catch{status.value=null}}
async function scrollBottom(){await nextTick();if(messageBox.value)messageBox.value.scrollTop=messageBox.value.scrollHeight}
async function submit(){const q=question.value.trim();if(!q||!status.value?.ready||loading.value)return;messages.value.push({role:'user',text:q});question.value='';loading.value=true;await scrollBottom();try{const result=await agentApi.query(q);messages.value.push({role:'assistant',text:result.answer||'Agent 已完成处理，但没有返回可展示文本。'});await scrollBottom()}catch(e:any){const detail=e?.response?.data?.detail;ElMessage.error(typeof detail==='string'?detail:(detail?.reason||'智能问数调用失败'));await refreshStatus()}finally{loading.value=false}}
onMounted(refreshStatus)
</script>

<style scoped>
.agent-page{max-width:1320px}.agent-hero{padding:28px 30px;display:flex;justify-content:space-between;gap:24px;align-items:center;background:linear-gradient(135deg,#f0fafd,#fff 62%)}.agent-hero h1{font-size:31px;margin:8px 0}.agent-hero p{max-width:760px;margin:0;color:var(--dc-text-2);font-size:12px;line-height:1.7}.runtime-pill{min-width:230px;display:flex;align-items:center;gap:10px;padding:12px 14px;border:1px solid #ead8b6;border-radius:12px;background:#fffbf3}.runtime-pill>span{width:9px;height:9px;border-radius:50%;background:#d99b37}.runtime-pill.ready{border-color:#cfe9dd;background:#f4fbf8}.runtime-pill.ready>span{background:#3ba57a}.runtime-pill div{display:grid;gap:3px}.runtime-pill b{font-size:11px}.runtime-pill small{font-size:9px;color:var(--dc-text-3);max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.agent-layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:16px;margin-top:16px}.chat-panel{min-height:650px;display:grid;grid-template-rows:minmax(0,1fr) auto;overflow:hidden}.messages{padding:24px;overflow:auto;max-height:650px}.message{display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px;margin-bottom:22px}.avatar{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:#eef8fc;color:#2b7e9f}.message.user .avatar{background:#f2f4f6;color:#617480}.message b{font-size:11px}.message p{margin:6px 0 0;font-size:13px;line-height:1.75;color:#415f70;white-space:pre-wrap}.message pre{margin:10px 0 0;padding:14px;border-radius:10px;background:#122738;color:#dceef7;overflow:auto;font-size:11px}.composer{border-top:1px solid var(--dc-border);padding:14px;background:#fbfdfe}.composer textarea{width:100%;min-height:88px;resize:vertical;border:1px solid #d6e6ee;border-radius:12px;padding:13px;outline:0;font:inherit;color:var(--dc-text);background:#fff}.composer textarea:focus{border-color:#8bc7df;box-shadow:0 0 0 3px rgba(82,164,199,.08)}.composer-foot{display:flex;justify-content:space-between;align-items:center;margin-top:9px}.composer-foot span{display:flex;align-items:center;gap:5px;color:#718a99;font-size:10px}.composer-foot button{border:0;border-radius:9px;background:var(--dc-primary);color:#fff;padding:9px 14px;display:flex;align-items:center;gap:6px;cursor:pointer}.composer-foot button:disabled{opacity:.45;cursor:not-allowed}.agent-side{display:grid;gap:14px;align-content:start}.side-card{padding:18px}.side-card h3{font-size:15px;margin:6px 0 14px}.runtime-flow{display:grid;justify-items:center;gap:5px}.runtime-flow span{width:100%;padding:9px;border-radius:9px;text-align:center;background:#f5fafc;border:1px solid #e2edf2;font-size:10px;font-weight:700;color:#47758b}.runtime-flow svg{color:#91aab7}.side-card dl{display:grid;gap:9px;margin:0}.side-card dl div{display:flex;justify-content:space-between;padding-bottom:8px;border-bottom:1px solid #edf3f6}.side-card dt,.side-card dd{font-size:10px}.side-card dt{color:var(--dc-text-3)}.side-card dd{margin:0;font-weight:700;text-align:right}.blocker{display:flex;gap:10px;border-color:#ead9b8;background:#fffcf6;color:#86602a}.blocker b{font-size:11px}.blocker p{font-size:10px;line-height:1.55;margin:5px 0}.blocker small{display:block;font-size:9px;line-height:1.5;color:#9b7a48}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:920px){.agent-layout{grid-template-columns:1fr}.agent-side{grid-template-columns:1fr 1fr}.blocker{grid-column:1/-1}}@media(max-width:620px){.agent-hero{align-items:flex-start;flex-direction:column}.runtime-pill{width:100%}.agent-side{grid-template-columns:1fr}.composer-foot{align-items:flex-start;gap:10px;flex-direction:column}.composer-foot button{align-self:flex-end}}
</style>
