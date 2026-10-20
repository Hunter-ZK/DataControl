<template>
  <div class="home-page">
    <div class="home-container">
      <header class="home-intro">
        <div>
          <span class="section-label"><span class="violet-point"></span> DataControl · 数据资产智能工作台</span>
          <h1>把数据问题，交给 DataAgent。</h1>
          <p>找数据集、读懂字段、生成 SQL、规范命名。从一个业务问题开始。</p>
        </div>
        <RouterLink to="/catalog" class="browse-link">直接浏览数据资产 <ArrowUpRight :size="17"/></RouterLink>
      </header>

      <section id="home-agent" class="agent-studio" aria-label="DataAgent 智能工作区">
        <div class="studio-header">
          <div class="studio-identity"><span class="agent-glyph"><Sparkles :size="18"/></span><div><b>DataAgent</b><small>数据分析与开发助手</small></div></div>
          <div class="mode-toggle" role="group" aria-label="运行模式">
            <button type="button" :class="{active:mode==='demo'}" :aria-pressed="mode==='demo'" @click="switchMode('demo')">交互演示</button>
            <button type="button" :class="{active:mode==='live'}" :aria-pressed="mode==='live'" @click="switchMode('live')">真实 Agent</button>
          </div>
        </div>

        <div class="studio-body">
          <div class="studio-intro">
            <span class="studio-badge"><span></span>{{ mode==='demo'?'可以立即体验完整交互':'连接本地 Agent 服务' }}</span>
            <h2>{{ mode==='demo'?'你想从数仓里了解什么？':'向 DataAgent 提出业务问题' }}</h2>
            <p v-if="mode==='demo'">像真实用户一样提问，体验从问题解析、展示结果到点选数据继续探索的完整流程。</p>
            <p v-else>问题将发送至本地 Agent 接口。真实回答仅展示后端实际返回的内容和证据。</p>
          </div>

          <div class="composer">
            <textarea
              id="home-agent-input"
              ref="inputRef"
              v-model="question"
              :disabled="isBusy"
              rows="2"
              aria-label="输入数据问题"
              placeholder="例如：哪些数据集可以分析企业贷款余额？"
              @keydown.enter.exact.prevent="submitQuestion"
            />
            <div class="composer-foot">
              <span><Command :size="15" /> Enter 发送 · Shift + Enter 换行</span>
              <button class="send-button" type="button" :disabled="!question.trim()||isBusy" @click="submitQuestion">
                <span>{{ isBusy?'处理中':'发送问题' }}</span><ArrowUpRight :size="16"/>
              </button>
            </div>
          </div>

          <div class="suggestions">
            <span>可以试试</span>
            <button v-for="item in demoSuggestions" :key="item.kind" type="button" @click="fillExample(item.question)">
              {{ item.label }} <ArrowUpRight :size="13"/>
            </button>
          </div>
          <div class="studio-disclaimer" v-if="mode==='demo'"><Info :size="14"/> 演示模式：仅支持四类预设业务场景，数值、字段和 SQL 均为模拟；输入后才产生结果。</div>
          <div class="studio-disclaimer" v-else><Info :size="14"/> 服务状态：{{ agentReady?'可连接（请以实际响应为准）':'未就绪' }}。系统不执行生产 SQL。</div>
        </div>
      </section>

      <div v-if="mode==='demo' && demoPhase!=='idle'" class="result-area" id="agent-result" ref="resultRef">
        <div class="question-trace"><span>你刚才问了</span><strong>{{ activeQuestion }}</strong><button type="button" @click="resetDemo">重新提问 <RotateCcw :size="14"/></button></div>

        <div v-if="demoPhase==='processing'" class="progress-card" role="status" aria-live="polite">
          <div class="progress-spinner"><Sparkles :size="25"/></div>
          <div class="progress-main"><span>交互演示正在生成结果</span><h3>{{ demoStep }}</h3><p>此过程只是模拟界面状态，不会调用 AI 服务或访问数仓。</p>
            <div class="progress-steps"><span v-for="(step,index) in demoSteps" :key="step" :class="{completed:index<demoStepIndex,active:index===demoStepIndex}">{{ step }}</span></div>
          </div>
        </div>

        <InteractiveDemo v-else-if="demoPhase==='ready' && demoScenario" :scenario="demoScenario" :question="activeQuestion" @followup="runFollowup" @reset="resetDemo"/>

        <div v-else class="unsupported-card">
          <span class="unsupported-symbol"><HelpCircle :size="24"/></span>
          <h3>这个问题暂时没有对应的模拟场景</h3>
          <p>为了避免给你展示与提问无关的假结果，当前演示只支持贷款余额资产、贷款趋势、贷款余额 SQL 和“客户风险等级”命名。</p>
          <div class="unsupported-actions">
            <button type="button" v-for="item in demoSuggestions" :key="item.kind" @click="fillExample(item.question)">{{ item.label }} <ArrowRight :size="14"/></button>
          </div>
          <button class="real-switch" type="button" @click="switchMode('live')">切换真实 Agent 提问 <ArrowUpRight :size="15"/></button>
        </div>
      </div>

      <section v-if="mode==='live' && (liveMessages.length || liveNotice || liveLoading)" class="live-workspace" id="agent-result" ref="resultRef">
        <div class="live-heading"><span><Sparkles :size="16"/> DataAgent · 真实问答</span><RouterLink to="/agent">打开会话工作区 <ArrowUpRight :size="15"/></RouterLink></div>
        <p v-if="liveNotice" class="live-warning" role="alert">{{ liveNotice }}</p>
        <AgentMessageView
          v-for="(message,index) in liveMessages"
          :key="index"
          :message="message"
          @clarify="submitHomeClarification(index,$event)"
        />
        <p v-if="liveLoading" class="live-thinking" role="status"><span></span> 本地 Agent 正在生成答复……</p>
        <p class="live-footnote">真实问答与模拟可视化相互独立。动态关系图、业务图表只有在接入可信数据后才能展示。</p>
      </section>

      <section v-if="mode==='demo' && demoTurns.length>1" class="demo-history">
        <span>本次演示路径</span>
        <button type="button" v-for="(turn,index) in demoTurns.slice(-4)" :key="index" @click="fillExample(turn)" :title="turn">{{ index+1 }}. {{ turn }}</button>
      </section>

      <section class="asset-portal">
        <div class="portal-title-row">
          <div><span class="section-label">数仓资产</span><h2>不想提问？直接浏览数据。</h2><p>从业务主题开始，查看具体数据集和字段结构。</p></div>
          <RouterLink to="/catalog">查看全部数据集 <ArrowRight :size="15"/></RouterLink>
        </div>

        <div v-if="warehouseLoading" class="catalog-skeleton" role="status">正在加载真实业务目录…</div>
        <div v-else-if="catalogs.length" class="category-list">
          <RouterLink v-for="item in catalogs" :key="item.code"
            :to="{name:'catalog',query:{catalog:item.code}}" class="category-card">
            <span class="category-symbol"><Database :size="18"/></span>
            <div><b>{{ item.name }}</b><small>{{ item.code }}</small></div>
            <span class="category-count">{{ item.tableCount }} 张表</span><ArrowUpRight :size="16" class="category-arrow"/>
          </RouterLink>
        </div>
        <div v-else class="catalog-empty">当前无法读取数仓业务目录。可以先体验上方模拟问答，或 <RouterLink to="/catalog">打开数据资产页</RouterLink>。</div>
        <div class="portal-footer" v-if="datasetCount!==null"><span>已登记数据集 <strong>{{ datasetCount.toLocaleString() }}</strong></span><span>统计来自当前本地数据资产服务</span></div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowRight, ArrowUpRight, Command, Database, HelpCircle, Info, RotateCcw, Sparkles,
} from 'lucide-vue-next'
import { agentApi, assetApi, type AgentResult, type AgentStatus } from '@/api/client'
import AgentMessageView from '@/components/agent/AgentMessage.vue'
import type { AgentMessage } from '@/components/agent/types'
import { useAgentConversations } from '@/composables/useAgentConversations'
import InteractiveDemo from '@/components/demo/InteractiveDemo.vue'
import { classifyDemoQuestion, demoSuggestions, type DemoScenario } from '@/components/demo/demoScenarios'

type Mode='demo'|'live'
type DemoPhase='idle'|'processing'|'ready'|'unsupported'
type CatalogEntry={code:string;name:string;tableCount:number}
const route=useRoute()
const mode=ref<Mode>('demo')
const question=ref('')
const inputRef=ref<HTMLTextAreaElement|null>(null)
const resultRef=ref<HTMLElement|null>(null)
const demoPhase=ref<DemoPhase>('idle')
const demoScenario=ref<DemoScenario|null>(null)
const activeQuestion=ref('')
const demoTurns=ref<string[]>([])
const demoSteps=['理解问题','选择展示方式','准备模拟分析结果']
const demoStepIndex=ref(0)
const demoStep=computed(()=>demoSteps[Math.min(demoStepIndex.value,demoSteps.length-1)]||'')
let demoRunId=0

const agentStatus=ref<AgentStatus|null>(null)
const agentReady=computed(()=>agentStatus.value?.ready===true)
const liveMessages=ref<AgentMessage[]>([])
const liveLoading=ref(false)
const liveNotice=ref('')
const sessionId=ref<string|null>(null)
const conversationStarted=ref(false)
const {load:loadConversations,create:createConversation,syncActive}=useAgentConversations()
const isBusy=computed(()=>demoPhase.value==='processing'||liveLoading.value)

const catalogs=ref<CatalogEntry[]>([])
const datasetCount=ref<number|null>(null)
const warehouseLoading=ref(true)

function switchMode(next:Mode){
  if(mode.value===next)return
  demoRunId+=1
  demoPhase.value='idle'
  mode.value=next
  question.value=''
  nextTick(()=>inputRef.value?.focus())
}
function fillExample(value:string){
  question.value=value
  nextTick(()=>{inputRef.value?.focus();inputRef.value?.scrollIntoView({block:'center',behavior:'smooth'})})
}
function resetDemo(){
  demoRunId+=1
  demoPhase.value='idle'
  demoScenario.value=null
  activeQuestion.value=''
  question.value=''
  nextTick(()=>inputRef.value?.focus())
}
function pause(ms:number){return new Promise<void>(resolve=>setTimeout(resolve,ms))}
async function showResults(){
  await nextTick()
  resultRef.value?.scrollIntoView({behavior:'smooth',block:'start'})
}
async function runDemo(value:string){
  const normalized=value.trim()
  if(!normalized)return
  const id=++demoRunId
  activeQuestion.value=normalized
  demoTurns.value.push(normalized)
  question.value=''
  demoScenario.value=classifyDemoQuestion(normalized)
  if(!demoScenario.value){
    demoPhase.value='unsupported'
    await showResults()
    return
  }
  demoPhase.value='processing'
  demoStepIndex.value=0
  await showResults()
  for(let step=0;step<demoSteps.length;step++){
    if(id!==demoRunId||mode.value!=='demo')return
    demoStepIndex.value=step
    await pause(340)
  }
  if(id!==demoRunId||mode.value!=='demo')return
  demoPhase.value='ready'
  await showResults()
}
function runFollowup(value:string){void runDemo(value)}
function toAssistantMessage(result:AgentResult):AgentMessage{
  return{
    role:'assistant',text:result.answer||'分析完成。',
    summary:result.summary,sql:result.sql,validation:result.validation,
    validationState:result.validationState,events:result.events,
    evidence:result.evidence,clarification:result.clarification,
    clarificationResolved:false,clarificationSelection:[],
  }
}
async function sendLiveTurn(displayText:string,prompt=displayText){
  if(liveLoading.value)return
  if(!agentReady.value){
    liveNotice.value='本地 Agent 服务尚未就绪，问题未发送。可切回交互演示体验操作流程。'
    await showResults()
    return
  }
  liveNotice.value=''
  if(!conversationStarted.value){createConversation(displayText);conversationStarted.value=true}
  liveMessages.value.push({role:'user',text:displayText})
  syncActive(liveMessages.value,sessionId.value,null)
  liveLoading.value=true
  await showResults()
  try{
    const result=await agentApi.query(prompt,sessionId.value)
    sessionId.value=result.sessionId||sessionId.value
    liveMessages.value.push(toAssistantMessage(result))
    syncActive(liveMessages.value,sessionId.value,null)
  }catch{
    liveNotice.value='Agent 请求未完成，请检查后端和网关状态后再试。本次请求没有生成结果。'
  }finally{liveLoading.value=false}
}
function submitQuestion(){
  const value=question.value.trim()
  if(!value||isBusy.value)return
  if(mode.value==='demo'){void runDemo(value);return}
  question.value=''
  void sendLiveTurn(value)
}
async function submitHomeClarification(index:number,payload:{values:string[];labels:string[];custom?:string}){
  if(mode.value!=='live'||liveLoading.value||!agentReady.value)return
  const message=liveMessages.value[index]
  if(!message||message.role!=='assistant'||!message.clarification||message.clarificationResolved)return
  message.clarificationResolved=true
  message.clarificationSelection=[...payload.values]
  syncActive(liveMessages.value,sessionId.value,null)
  const displayText=payload.custom?`补充口径：${payload.custom}`:`选择口径：${payload.labels.join('、')}`
  const prompt=payload.custom
    ?`用户对上一轮问题补充了业务口径：“${payload.custom}”。请基于内部证据继续回答。`
    :`用户已选择上一轮澄清选项：${payload.labels.map((label,i)=>`${label}（metric_id=${payload.values[i]}）`).join('；')}。请继续原问题。`
  await sendLiveTurn(displayText,prompt)
}
async function loadCatalog(){
  warehouseLoading.value=true
  try{
    const data=await assetApi.overview() as {tableCount?:number;topCatalogs?:Array<{code:string;name:string;tableCount:number}>}
    datasetCount.value=typeof data.tableCount==='number'?data.tableCount:null
    catalogs.value=Array.isArray(data.topCatalogs)?data.topCatalogs.filter(item=>item.code&&item.name).slice(0,6):[]
  }catch{catalogs.value=[]}
  finally{warehouseLoading.value=false}
}
onMounted(async()=>{
  loadConversations()
  void loadCatalog()
  try{agentStatus.value=await agentApi.status()}catch{agentStatus.value=null}
  if(route.hash==='#home-agent'){await nextTick();inputRef.value?.focus()}
})
onBeforeUnmount(()=>{demoRunId+=1})
</script>

<style scoped>
.home-page{background:#f6f6f8;min-height:calc(100vh - 70px);padding:44px 0 80px}
.home-container{width:min(1240px,calc(100% - 64px));margin:0 auto}
.home-intro{display:flex;align-items:flex-end;justify-content:space-between;gap:30px;margin-bottom:30px}
.section-label{display:flex;align-items:center;gap:9px;color:#7763b2;letter-spacing:.04em;font-size:11px;font-weight:800}
.violet-point{width:7px;height:7px;border-radius:50%;background:#8d6ff0;box-shadow:0 0 0 4px #eeeaff}
.home-intro h1{margin:14px 0 10px;color:#1e2030;font-size:35px;letter-spacing:-.045em;line-height:1.2}
.home-intro p{margin:0;color:#79808c;font-size:14px;line-height:1.7}
.browse-link{display:flex;align-items:center;gap:8px;background:white;border:1px solid #e8e5ef;padding:11px 14px;border-radius:10px;color:#47445d;font-size:12px;font-weight:700;white-space:nowrap}
.browse-link:hover{border-color:#baaaf1;color:#6b53dd}

.agent-studio{position:relative;border:1px solid #ddd9eb;border-radius:20px;background:#fff;box-shadow:0 20px 60px rgba(38,30,76,.08);overflow:hidden}
.studio-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:19px 24px;border-bottom:1px solid #eeeaf4;background:#fdfdff}
.studio-identity{display:flex;gap:11px;align-items:center}
.agent-glyph{width:37px;height:37px;display:grid;place-items:center;border-radius:11px;background:#7258db;color:white;box-shadow:0 8px 22px rgba(114,88,219,.22)}
.studio-identity>div{display:grid;gap:3px}.studio-identity b{font-size:14px;color:#25243a}.studio-identity small{font-size:11px;color:#8a899b}
.mode-toggle{display:flex;gap:2px;padding:4px;border-radius:11px;background:#f2f0f6}
.mode-toggle button{border:0;border-radius:8px;background:transparent;padding:9px 13px;font-size:12px;color:#777485;cursor:pointer}
.mode-toggle button.active{background:#fff;color:#5946bd;font-weight:800;box-shadow:0 2px 9px rgba(20,20,45,.08)}
.studio-body{padding:35px 40px 27px}
.studio-intro{text-align:center;margin-bottom:27px}
.studio-badge{display:inline-flex;gap:8px;align-items:center;padding:7px 11px;background:#f3f0ff;border:1px solid #e7dffd;color:#6851cc;border-radius:999px;font-size:11px;font-weight:750}
.studio-badge span{width:7px;height:7px;background:#9175e6;border-radius:50%}
.studio-intro h2{font-size:29px;letter-spacing:-.03em;margin:15px 0 7px;color:#212236}
.studio-intro p{font-size:13px;color:#82828f;line-height:1.7;margin:0}
.composer{margin:0 auto;max-width:890px;border:1px solid #dcd9e6;border-radius:15px;padding:17px;background:#fff;box-shadow:0 10px 27px rgba(29,21,61,.06);transition:.15s}
.composer:focus-within{border-color:#9d89ed;box-shadow:0 0 0 3px rgba(124,103,242,.12),0 10px 27px rgba(29,21,61,.06)}
.composer textarea{min-height:65px;width:100%;border:0;outline:0;resize:vertical;background:transparent;color:#24233a;font-size:15px;line-height:1.65}
.composer textarea::placeholder{color:#a8a5b2}
.composer-foot{display:flex;align-items:center;justify-content:space-between;gap:16px;border-top:1px solid #f1f0f4;padding-top:10px}
.composer-foot>span{display:flex;gap:8px;align-items:center;color:#a09dac;font-size:11px}
.send-button{display:flex;align-items:center;gap:8px;background:#7357df;border:1px solid #7357df;color:#fff;border-radius:9px;padding:11px 15px;cursor:pointer;font-size:12px;font-weight:800;box-shadow:0 7px 16px rgba(115,87,223,.17)}
.send-button:hover{background:#6147cf}.send-button:disabled{opacity:.4;cursor:not-allowed;box-shadow:none}
.suggestions{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:19px}
.suggestions>span{font-size:11px;color:#8d8a9b;margin-right:3px}
.suggestions button{display:flex;gap:7px;align-items:center;border:1px solid #e6e3ee;background:#fafaff;border-radius:999px;color:#615a78;padding:8px 12px;font-size:11px;cursor:pointer}
.suggestions button:hover{border-color:#bbaafa;background:#f7f3ff;color:#624bd1}
.studio-disclaimer{display:flex;gap:7px;align-items:center;justify-content:center;color:#9692a4;font-size:11px;margin-top:23px}
.studio-disclaimer svg{flex:0 0 auto}

.result-area,.live-workspace{margin-top:28px;scroll-margin-top:88px}
.question-trace{display:flex;align-items:center;gap:13px;padding:0 4px 14px}
.question-trace span{color:#92909c;font-size:11px}.question-trace strong{font-size:14px;color:#29283a;min-width:0}
.question-trace button{margin-left:auto;display:flex;align-items:center;gap:7px;background:transparent;border:0;color:#6960a5;cursor:pointer;font-size:11px;white-space:nowrap}
.progress-card,.unsupported-card{padding:38px 30px;border:1px solid #e5e0ee;border-radius:17px;background:white;display:flex;gap:24px;align-items:center;box-shadow:0 10px 27px rgba(22,20,48,.03)}
.progress-spinner{width:64px;height:64px;display:grid;place-items:center;border-radius:18px;background:#efebff;color:#765ce3;animation:pulse 1s ease-in-out infinite alternate}
@keyframes pulse{to{box-shadow:0 0 0 10px rgba(118,92,227,.055);transform:scale(1.025)}}
.progress-main{flex:1}.progress-main>span{font-size:11px;color:#7663be}.progress-main h3{margin:7px 0;font-size:19px}.progress-main p{font-size:12px;color:#898896}
.progress-steps{display:flex;gap:8px;margin-top:18px;flex-wrap:wrap}
.progress-steps span{font-size:10px;background:#f2f1f4;color:#8e8b99;border-radius:999px;padding:7px 11px}
.progress-steps span.completed{background:#ede9fb;color:#7060bf}.progress-steps span.active{background:#7357df;color:white}
.unsupported-card{flex-direction:column;text-align:center;gap:8px}
.unsupported-symbol{color:#7766cb}.unsupported-card h3{margin:6px 0;font-size:20px}.unsupported-card p{max-width:580px;color:#7d7f8c;font-size:13px;line-height:1.75;margin:0}
.unsupported-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:14px}
.unsupported-actions button{display:flex;align-items:center;gap:7px;border:1px solid #e0dcec;background:#fff;padding:10px 12px;border-radius:8px;color:#5e547c;font-size:11px;cursor:pointer}
.real-switch{border:0;background:transparent;display:flex;align-items:center;gap:5px;color:#6850cb;font-size:12px;cursor:pointer;margin-top:8px}
.live-workspace{padding:24px 28px;border:1px solid #e5e2ee;border-radius:17px;background:#fff}
.live-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}
.live-heading>span,.live-heading>a{display:flex;align-items:center;gap:8px;font-size:12px;color:#6553bd}
.live-heading>span{font-weight:800}
.live-warning{padding:13px 15px;color:#88602f;background:#fcf5e8;border-radius:9px;font-size:13px}
.live-thinking{color:#6860a1;font-size:13px}
.live-thinking span{display:inline-block;width:7px;height:7px;margin-right:5px;border-radius:50%;background:#9376fa;animation:pulse 1s infinite alternate}
.live-footnote{font-size:11px;color:#888492;margin-top:22px}
.demo-history{display:flex;gap:8px;align-items:center;margin:14px 0 0;flex-wrap:wrap}
.demo-history span{font-size:11px;color:#8e8c9c}
.demo-history button{border:1px solid #e6e3ec;background:#fff;border-radius:6px;padding:7px 10px;font-size:10px;color:#7c7590;cursor:pointer;max-width:230px;text-overflow:ellipsis;white-space:nowrap;overflow:hidden}

.asset-portal{margin-top:52px}
.portal-title-row{display:flex;align-items:end;justify-content:space-between;gap:15px;margin-bottom:20px}
.portal-title-row h2{margin:9px 0 6px;color:#26263b;font-size:24px;letter-spacing:-.025em}
.portal-title-row p{margin:0;color:#878a96;font-size:13px}
.portal-title-row>a{display:flex;align-items:center;gap:8px;color:#6354bd;font-size:12px;font-weight:750}
.category-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.category-card{display:flex;align-items:center;gap:12px;min-height:90px;padding:18px;border:1px solid #e4e2eb;border-radius:13px;background:#fff;box-shadow:0 5px 20px rgba(22,20,48,.02);transition:.16s}
.category-card:hover{border-color:#b8a7eb;transform:translateY(-2px);box-shadow:0 11px 26px rgba(22,20,48,.055)}
.category-symbol{width:39px;height:39px;border-radius:10px;display:grid;place-items:center;background:#f1eefc;color:#7660dc}
.category-card>div{display:grid;gap:5px;min-width:0}.category-card b{font-size:13px;color:#2f3041}.category-card small{font-size:10px;color:#9691a4;overflow:hidden;text-overflow:ellipsis}
.category-count{margin-left:auto;font-size:11px;color:#727485;white-space:nowrap}
.category-arrow{color:#b2adc4}
.catalog-skeleton,.catalog-empty{border:1px dashed #d8d4e5;border-radius:12px;padding:25px;background:#fff;color:#7d7c8c;font-size:13px}
.catalog-empty a{color:#6e58dd;font-weight:700}
.portal-footer{display:flex;align-items:center;justify-content:space-between;margin-top:15px;color:#9a98a5;font-size:11px}
.portal-footer strong{font-size:15px;color:#39364d}
@media(max-width:900px){.home-container{width:min(100% - 36px,1240px)}.category-list{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:650px){.home-page{padding:25px 0 50px}.home-container{width:calc(100% - 24px)}.home-intro{align-items:flex-start;flex-direction:column}.home-intro h1{font-size:28px}.studio-header{padding:14px}.studio-body{padding:24px 15px}.studio-intro h2{font-size:24px}.composer{padding:12px}.composer-foot>span{font-size:9px}.studio-disclaimer{text-align:center;align-items:flex-start}.category-list{grid-template-columns:1fr}.portal-title-row{align-items:flex-start;flex-direction:column}.question-trace{flex-wrap:wrap}.question-trace button{margin-left:0}.live-workspace{padding:15px}.progress-card{flex-direction:column;text-align:center}.report-title-row{flex-direction:column}}
</style>
