<template>
  <section class="task-journey" aria-label="任务执行阶段">
    <div class="journey-title">
      <span class="journey-icon"><ListChecks :size="17"/></span>
      <div><b>{{ tier === 'multi' ? '多步任务进度' : '本轮处理进度' }}</b>
        <p>按真实工具事件更新状态；尚未触发的阶段不代表已执行。</p>
      </div>
      <span class="journey-count">{{ completed }} / {{ stages.length }}</span>
    </div>
    <ol class="journey-stages">
      <li v-for="(stage, index) in stages" :key="stage.id" :class="stage.state">
        <span class="stage-number">
          <Check v-if="stage.state==='done'" :size="13"/>
          <X v-else-if="stage.state==='error'" :size="13"/>
          <LoaderCircle v-else-if="stage.state==='running'" :size="13" class="spin"/>
          <template v-else>{{index+1}}</template>
        </span>
        <span class="stage-main"><b>{{stage.title}}</b><small>{{stage.description}}</small></span>
        <span class="stage-status">{{statusName(stage.state)}}</span>
      </li>
    </ol>
  </section>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Check, ListChecks, LoaderCircle, X } from 'lucide-vue-next'
import type { AgentActivity } from '@/api/client'

type PhaseState = 'done' | 'running' | 'error' | 'idle'
const props = withDefaults(defineProps<{
  events?: AgentActivity[]
  tier?: 'standard' | 'multi'
  running?: boolean
}>(), { tier: 'standard', running: false })
const definitions = [
  { id: 'discovery', title: '识别任务与数据依据', tools: ['search_assets','search_tables','get_asset','plan_metric','resolve_metric','get_semantic_model','get_schema'] },
  { id: 'context', title: '核对字段和依赖关系', tools: ['get_schema','get_asset','find_references','get_lineage_summary','resolve_code_value','search_verified_sql'] },
  { id: 'generation', title: '生成受治理的 SQL 或草案', tools: ['compile_query','revise_query','check_naming','generate_ddl','generate_etl','generate_dq_checks'] },
  { id: 'validation', title: '静态校验和结果说明', tools: ['validate_sql','explain_sql'] },
] as const

const activity = computed(() => {
  const calls = new Map<string, { tool: string; state: PhaseState }>()
  for (const event of props.events || []) {
    if (!event.callId) continue
    if (event.type === 'tool_call') calls.set(event.callId, {tool:event.tool || '', state:'running'})
    if (event.type === 'tool_result' && calls.has(event.callId)) {
      const call = calls.get(event.callId)!
      call.state = event.status === 'error' ? 'error' : 'done'
    }
  }
  return [...calls.values()]
})
const stages = computed(() => {
  const available = props.tier === 'multi' ? definitions : definitions.filter(row => row.id !== 'context')
  return available.map(row => {
    const matches = activity.value.filter(call => (row.tools as readonly string[]).includes(call.tool))
    const state: PhaseState = matches.some(x=>x.state==='error') ? 'error'
      : matches.some(x=>x.state==='running') ? 'running'
      : matches.length && matches.every(x=>x.state==='done') ? 'done' : 'idle'
    const description = state === 'idle' ? '尚未触发此阶段的工具'
      : state === 'running' ? '已开始调用工具，等待真实结果'
      : state === 'error' ? '工具返回异常，需要检查'
      : `已完成 ${matches.length} 次相关工具调用`
    return { id:row.id,title:row.title,state,description }
  })
})
const completed = computed(() => stages.value.filter(x=>x.state==='done').length)
function statusName(s:PhaseState) {
  return ({done:'已完成',running:'进行中',error:'异常',idle:props.running?'待触发':'未触发'} as Record<PhaseState,string>)[s]
}
</script>
<style scoped>
.task-journey{padding:15px 16px;margin:14px 0;border:1px solid var(--dc-border);border-radius:11px;background:#fbfcff}
.journey-title{display:flex;align-items:center;gap:10px}
.journey-icon{display:grid;place-items:center;width:31px;height:31px;border-radius:8px;color:var(--dc-primary);background:#e8f1ff;flex:none}
.journey-title div{flex:1;min-width:0}
.journey-title b{font-size:13px;color:var(--dc-text)}
.journey-title p{font-size:12px;color:var(--dc-text-3);margin:1px 0 0;line-height:1.5}
.journey-count{color:var(--dc-primary);font-size:12px;font-weight:740;font-variant-numeric:tabular-nums}
.journey-stages{list-style:none;padding:13px 0 0;margin:0;display:grid;gap:2px}
.journey-stages li{display:flex;gap:10px;align-items:center;padding:9px 5px;position:relative}
.journey-stages li+li:before{content:'';position:absolute;left:16px;top:-11px;width:1px;height:18px;background:#dfe7f3}
.stage-number{width:23px;height:23px;border-radius:50%;display:grid;place-items:center;flex:none;font-size:12px;font-weight:700;color:#96a4b7;background:#edf1f7;z-index:1}
.stage-main{flex:1;min-width:0;display:grid;gap:1px}
.stage-main b{font-size:12px;color:#52657f;font-weight:650}
.stage-main small{font-size:12px;color:#99a6b8}
.stage-status{font-size:12px;color:#8798ad}
li.done .stage-number{background:#e0f5eb;color:#087e66}
li.done .stage-main b,li.done .stage-status{color:#087e66}
li.running .stage-number{background:#e9f1ff;color:#2563eb}
li.running .stage-main b,li.running .stage-status{color:#2563eb}
li.error .stage-number{background:#fee9e9;color:#cb3845}
li.error .stage-status{color:#cb3845}
.spin{animation:turn 1s linear infinite}
@keyframes turn{to{transform:rotate(360deg)}}
@media(max-width:600px){.task-journey{padding:11px}.journey-title p{font-size:12px}.stage-main small{font-size:12px}}
</style>
