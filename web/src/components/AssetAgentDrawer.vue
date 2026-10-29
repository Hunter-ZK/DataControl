<template>
  <el-drawer v-model="visible" :size="drawerWidth" direction="rtl" :with-header="false"
             append-to-body class="dc-agent-drawer" @closed="resetIfIdle">
    <div class="drawer-layout">
      <header class="drawer-head">
        <div class="heading-icon"><Sparkles :size="20"/></div>
        <div class="heading-copy"><span>CONTEXTUAL DATAAGENT</span><h2>问当前资产</h2></div>
        <button type="button" class="close-control" aria-label="关闭 Agent 抽屉" @click="closeDrawer"><X :size="20"/></button>
      </header>
      <div v-if="context" class="asset-context">
        <span>已关联资产 · {{context.assetType}}</span>
        <b>{{context.name}}</b><code>{{context.technicalName}}</code>
      </div>
      <div class="drawer-modes"><span><ShieldCheck :size="14"/> DeepSeek 官方 · 标准问数</span>
        <span :class="status?.ready?'ready':'offline'">{{status?.ready?'服务就绪':'服务暂不可用'}}</span></div>
      <div v-if="!authenticated" class="notice warning">
        当前未登录。Agent 运行需要登录身份，不会在匿名状态下调用。
        <button @click="goLogin">去登录</button>
      </div>
      <div v-else-if="!status?.ready" class="notice warning">Agent 服务未就绪，仍可查看资产信息。{{status?.reason||''}}</div>
      <section ref="scrollRegion" class="drawer-messages" aria-live="polite">
        <div v-if="!messages.length" class="drawer-welcome">
          <Sparkles :size="30"/><h3>基于当前资产提问</h3>
          <p>将资产标识与类型作为可追溯上下文，利用现有 Agent3 工具检索证据。回答不会执行 SQL。</p>
        </div>
        <AgentMessage v-for="(message,index) in messages" :key="index" :message="message"
          @clarify="clarify(index,$event)"/>
        <div v-if="running" class="drawer-activity">
          <span class="working-pulse"/><b>Agent 正在处理</b>
          <span v-if="events.length"> · 已收到 {{events.length}} 条工具事件</span>
          <div v-for="(event,index) in events.slice(-5)" :key="index" class="event-row">
            {{event.type==='tool_call'?'开始':'完成'}} · {{event.tool||event.phase||'内部工具'}} · {{event.status||'处理中'}}
          </div>
        </div>
      </section>
      <div v-if="error" class="notice warning" role="alert">{{error}}</div>
      <footer class="drawer-footer">
        <textarea v-model="question" rows="3" aria-label="向当前资产提问" placeholder="输入问题，按 Ctrl+Enter 发送"
          @keydown.ctrl.enter.prevent="send" @keydown.meta.enter.prevent="send"/>
        <div class="drawer-footer-row">
          <button class="full-chat" @click="continueInChat"><PanelsTopLeft :size="16"/>在完整对话中继续 <ArrowUpRight :size="14"/></button>
          <button v-if="running" class="stop" @click="stop"><Square :size="14"/>停止</button>
          <button v-else class="send" :disabled="!authenticated||!status?.ready||!question.trim()" @click="send">
            <Send :size="15"/>发送
          </button>
        </div>
      </footer>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, PanelsTopLeft, Send, ShieldCheck, Sparkles, Square, X } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import AgentMessage from '@/components/agent/AgentMessage.vue'
import type { AgentMessage as Message } from '@/components/agent/types'
import { assetAgentRequest, type AssetAgentContext } from '@/composables/assetAgentDrawer'
import { agentApi, AgentTurnCancelledError, type AgentActivity, type AgentResult, type AgentStatus, type AgentStreamEvent } from '@/api/client'

const router=useRouter()
const route=useRoute()
const visible=ref(false)
const context=ref<AssetAgentContext|null>(null)
const question=ref('')
const status=ref<AgentStatus|null>(null)
const messages=ref<Message[]>([])
const events=ref<AgentActivity[]>([])
const running=ref(false)
const error=ref('')
const conversationId=ref<string|null>(null)
const scrollRegion=ref<HTMLElement|null>(null)
const authenticated=computed(()=>Boolean(localStorage.getItem('datacontrol_token')&&localStorage.getItem('datacontrol_user')))
const drawerWidth='min(660px, 96vw)'
let controller: AbortController|null=null
let runId:string|null=null
let requestToken=0

function promptFor(c:AssetAgentContext) {
  const noun=c.assetType==='TABLE'?'数据集':c.assetType==='COLUMN'?'字段':c.assetType==='METRIC'?'指标':'数据资产'
  const subject=noun+'“'+c.name+'”（type='+c.assetType+', asset_id='+c.assetId+', code='+c.technicalName+'）'
  if(c.task==='sql')return '请基于'+subject+'生成可信查询 SQL，核对真实字段和业务口径，明确缺失条件，不执行 SQL。'
  if(c.task==='explain')return '请根据元数据及可信证据解释'+subject+'的含义、用途与依赖关系。'
  return '请解释'+subject+'，包括用途、相关来源和可能的查询方式。'
}
watch(assetAgentRequest,async next=>{
  if(!next)return
  const token=++requestToken
  if(running.value&&context.value){
    ElMessage.warning('当前资产任务仍在执行。请先停止任务再切换资产。')
    return
  }
  context.value=next;question.value=promptFor(next);visible.value=true
  messages.value=[];events.value=[];error.value='';conversationId.value=null;status.value=null
  if(authenticated.value){
    try{const state=await agentApi.status('deepseek','standard');if(requestToken===token)status.value=state}
    catch{if(requestToken===token)error.value='无法获取 Agent 状态'}
  }
})
function assistant(result:AgentResult):Message {
  return {role:'assistant',text:result.answer||'处理完成。',summary:result.summary,
    sql:result.sql,validation:result.validation,validationState:result.validationState,
    events:result.events,evidence:result.evidence,clarification:result.clarification,
    durationMs:result.durationMs,toolCallCount:result.toolCallCount}
}
async function scrollBottom(){await nextTick();scrollRegion.value?.scrollTo({top:scrollRegion.value.scrollHeight,behavior:'smooth'})}
async function send(){
  const msg=question.value.trim()
  if(!msg||running.value||!context.value||!authenticated.value||!status.value?.ready)return
  const c=context.value
  error.value=''
  running.value=true;events.value=[];question.value=''
  const first=messages.value.length===0
  try{
    if(!conversationId.value){
      const boundContext=c.assetType==='TABLE'?{
        assetId:c.assetId,bizName:c.name,tableName:c.technicalName,
      }:null
      const saved=await agentApi.createConversation('资产问答 · '+c.name,'deepseek',boundContext,'standard')
      conversationId.value=saved.id
    }
    messages.value.push({role:'user',text:msg})
    const prompt=first
      ? '当前对象：'+c.assetType+'（asset_id='+c.assetId+'，technical_name='+c.technicalName+'，name='+c.name+'）。请先通过 Agent3 MCP 获取真实资产事实并说明依据，不使用外部网络；不执行 SQL。\n问题：'+msg
      : msg
    controller=new AbortController()
    runId=crypto.randomUUID()
    const result=await agentApi.stream(prompt,null,runId,(update:AgentStreamEvent)=>{
      if(update.type==='activity'&&(update.event.type==='tool_call'||update.event.type==='tool_result')){
        events.value=[...events.value,update.event].slice(-30)
        void scrollBottom()
      }
    },controller.signal,'deepseek',conversationId.value,msg,'standard',false)
    messages.value.push(assistant(result));await scrollBottom()
  }catch(e){
    if(e instanceof AgentTurnCancelledError){
      messages.value.push({role:'assistant',text:'本轮已由服务端取消。后续问题将由服务端重新建立安全上下文。'})
    }else{
      error.value='本轮请求未完成，结果不可采信。请检查 Agent 服务。'
    }
  }finally{running.value=false;runId=null;controller=null}
}
async function clarify(index:number,payload:{values:string[];labels:string[];custom?:string}){
  const row=messages.value[index];if(!row||!row.clarification||running.value)return
  row.clarificationResolved=true;row.clarificationSelection=payload.values
  question.value=payload.custom?'补充口径：'+payload.custom:'选择口径：'+payload.labels.join('、')
  await send()
}
async function stop(){
  if(!runId||!running.value)return
  try{const result=await agentApi.cancel(runId);if(!result.cancelled)ElMessage.warning('服务端尚未确认停止，任务仍在进行中。')}
  catch{ElMessage.error('停止请求失败，任务状态仍以服务端为准。')}
}
function closeDrawer(){visible.value=false}
function resetIfIdle(){if(!running.value){context.value=null;messages.value=[];conversationId.value=null}}
function goLogin(){visible.value=false;void router.push({name:'login',query:{redirect:route.fullPath}})}
function continueInChat(){
  const c=context.value
  if(!c)return
  visible.value=false
  if(conversationId.value){void router.push({name:'agent',query:{conversationId:conversationId.value}})}
  else{void router.push({name:'agent',query:{
    ...(c.assetType==='TABLE'?{asset:c.assetId}:{}),
    q:question.value.trim()||promptFor(c),
  }})}
}
onBeforeUnmount(()=>{if(running.value)ElMessage.warning('Agent 任务可能仍在服务端执行，可从会话历史查看状态。')})
</script>

<style scoped>
.drawer-layout{display:flex;flex-direction:column;height:100%;min-height:0;background:#f7faff;color:var(--dc-text)}
.drawer-head{display:flex;align-items:center;gap:12px;background:#fff;border-bottom:1px solid var(--dc-border);padding:18px 21px}.heading-icon{width:40px;height:40px;border-radius:12px;background:var(--dc-agent-soft);color:var(--dc-agent);display:grid;place-items:center}.heading-copy{flex:1}.heading-copy>span{font-size:11px;color:var(--dc-text-3);letter-spacing:.07em}.heading-copy h2{font-size:19px;margin:2px 0}.close-control{border:1px solid var(--dc-border);background:#fff;border-radius:9px;width:34px;height:34px;display:grid;place-items:center;cursor:pointer;color:var(--dc-text-2)}.asset-context{display:grid;gap:4px;margin:14px 18px 8px;border:1px solid var(--dc-border);border-radius:12px;padding:13px 16px;background:linear-gradient(110deg,#fff,#eef5ff)}.asset-context>span{font-size:12px;color:var(--dc-text-3)}.asset-context b{font-size:16px}.asset-context code{font-size:12px;color:var(--dc-primary);overflow-wrap:anywhere}.drawer-modes{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 19px 13px;font-size:12px;color:var(--dc-text-2)}.drawer-modes span{display:flex;align-items:center;gap:5px}.drawer-modes .ready{color:var(--dc-success)}.drawer-modes .offline{color:var(--dc-warning)}.drawer-messages{flex:1;min-height:0;overflow:auto;padding:20px 18px}.drawer-messages :deep(.assistant-answer){padding:15px}.drawer-messages :deep(.user-bubble){max-width:94%}.drawer-welcome{padding:40px 24px;text-align:center;color:var(--dc-primary)}.drawer-welcome h3{color:var(--dc-text);font-size:17px}.drawer-welcome p{color:var(--dc-text-2);font-size:13px;line-height:1.7}.drawer-activity{border:1px solid var(--dc-border);padding:14px;border-radius:12px;background:#fff;font-size:12px}.event-row{padding:5px 0;color:var(--dc-text-2);border-top:1px solid var(--dc-border)}.working-pulse{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;background:var(--dc-primary)}.notice{margin:9px 17px;padding:12px;border-radius:9px;font-size:12px;background:#fff6e7;border:1px solid #ecd6ad;color:#875b20}.notice button{border:0;color:var(--dc-primary);background:transparent;cursor:pointer}.drawer-footer{padding:15px 18px 20px;background:#fff;border-top:1px solid var(--dc-border)}.drawer-footer textarea{display:block;width:100%;resize:vertical;border:1px solid var(--dc-border-strong);border-radius:11px;padding:12px;color:var(--dc-text);font:inherit;min-height:82px;max-height:190px}.drawer-footer-row{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:10px}.drawer-footer button{border:1px solid var(--dc-border-strong);border-radius:9px;display:flex;align-items:center;gap:7px;padding:9px 12px;background:#fff;color:var(--dc-primary);cursor:pointer;font-size:12px;font-weight:700}.drawer-footer button.send{color:white;background:var(--dc-primary);border-color:var(--dc-primary)}.drawer-footer button.stop{color:#a15b2f}.drawer-footer button:disabled{opacity:.5;cursor:not-allowed}
</style>
