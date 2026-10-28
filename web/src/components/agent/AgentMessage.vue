<template>
  <article class="message" :class="message.role">
    <div v-if="message.role === 'user'" class="user-bubble">{{ message.text }}</div>
    <div v-else class="assistant-answer">
      <div class="answer-toolbar">
        <div class="assistant-identity">
          <span class="agent-avatar"><Sparkles :size="16" /></span>
          <b>DataAgent</b>
          <span class="assistant-caption">回答</span>
          <span v-if="typeof message.durationMs === 'number'" class="assistant-caption">
            {{ (message.durationMs / 1000).toFixed(1) }} 秒 · {{ message.toolCallCount ?? 0 }} 次工具调用
          </span>
        </div>
        <span v-if="message.sql" class="answer-status" :class="validationTone(message)">
          <CheckCircle2 v-if="validationState(message) === 'passed'" :size="14" />
          <AlertCircle v-else :size="14" />
          {{ sqlStatusText(message) }}
        </span>
      </div>
      <details v-if="message.events?.length" class="answer-progress"><summary><ListChecks :size="17"/>任务执行进度 <ChevronDown :size="17"/></summary><AgentTaskJourney :events="message.events" :tier="tier" :running="false"/></details>
      <div class="answer-content">
        <AgentMarkdown :text="message.text" />
        <AgentClarification
          v-if="message.clarification"
          :clarification="message.clarification"
          :resolved="message.clarificationResolved"
          :selection="message.clarificationSelection"
          @clarify="emit('clarify', $event)"
        />
      </div>

      <div v-if="message.sql" class="sql-result">
        <AgentSqlCard :message="message" />
        <AgentValidationPanel :message="message" />
      </div>

      <details v-if="hasSupportingDetails" class="supporting-details">
        <summary>
          <span class="details-summary"><FileSearch :size="16" />数据依据与调用记录</span>
          <span class="details-meta">查看来源及工具步骤 <ChevronDown :size="15" /></span>
        </summary>
        <div class="details-body">
          <AgentEvidence :evidence="message.evidence" />
          <AgentTrace :events="message.events" />
        </div>
      </details>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertCircle, CheckCircle2, ChevronDown, FileSearch, ListChecks, Sparkles } from 'lucide-vue-next'
import AgentClarification from '@/components/agent/AgentClarification.vue'
import AgentEvidence from '@/components/agent/AgentEvidence.vue'
import AgentMarkdown from '@/components/agent/AgentMarkdown.vue'
import AgentSqlCard from '@/components/agent/AgentSqlCard.vue'
import AgentTrace from '@/components/agent/AgentTrace.vue'
import AgentTaskJourney from '@/components/agent/AgentTaskJourney.vue'
import AgentValidationPanel from '@/components/agent/AgentValidationPanel.vue'
import { sqlStatusText, validationState, validationTone } from '@/components/agent/presentation'
import type { AgentMessage } from '@/components/agent/types'

const props = withDefaults(defineProps<{ message: AgentMessage; tier?: 'standard' | 'multi' }>(), { tier:'standard' })
const emit = defineEmits<{
  clarify: [payload: { values: string[]; labels: string[]; custom?: string }]
}>()

const hasSupportingDetails = computed(() => {
  const evidence = props.message.evidence
  return Boolean(
    props.message.events?.length ||
    evidence?.assets?.length ||
    evidence?.metrics?.length ||
    evidence?.datasets?.length ||
    evidence?.dimensions?.length ||
    evidence?.period ||
    evidence?.caliber,
  )
})
</script>

<style scoped>
.message { margin: 0 0 28px; }
.message.user { display: flex; justify-content: flex-end; }
.user-bubble { max-width: min(78%,740px); padding: 12px 17px; border: 1px solid #c9e1ed; border-radius: 16px 16px 5px 16px; background: #eaf4fa; color: #23485d; font-size: 14px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.assistant-answer { max-width: 980px; color: #243f51; }
.answer-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 9px; padding-bottom: 12px; border-bottom: 1px solid #e5eef3; }
.assistant-identity { display:flex; align-items:center; gap: 8px; color: #183f55; font-size: 14px; }
.agent-avatar { width: 29px; height: 29px; border-radius: 9px; display:grid; place-items:center; background: #e4f2f9; color: #267ca3; }
.assistant-caption { color: #8aa0ac; font-size: 12px; font-weight: 450; }
.answer-status { display:inline-flex; align-items:center; gap:5px; font-size: 11px; color: #667e89; }
.answer-status.success { color: #287454; }
.answer-status.warning { color: #936d29; }
.answer-status.danger { color: #a04a4a; }
.answer-content { padding: 15px 0 1px; }
.sql-result { margin-top: 16px; }
.supporting-details { margin-top: 17px; border: 1px solid #e0e9ee; border-radius: 11px; background: #fbfdfe; overflow: hidden; }
.supporting-details summary { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:13px 15px; cursor:pointer; list-style:none; user-select:none; color:#44687b; }
.supporting-details summary::-webkit-details-marker { display: none; }
.supporting-details summary:hover { background:#f3f9fc; }
.details-summary { display:flex; align-items:center; gap:9px; font-size:13px; font-weight:700; }
.details-meta { display:flex; align-items:center; gap:6px; font-size:11px; color:#7894a3; }
.details-meta svg { transition: transform .16s ease; }
.supporting-details[open] .details-meta svg { transform:rotate(180deg); }
.details-body { padding: 0 15px 15px; border-top: 1px solid #e9f0f4; }
.details-body :deep(.evidence-area),.details-body :deep(.analysis-trace) { margin-top:12px; }
@media(max-width:760px){.user-bubble{max-width:94%}.details-meta{font-size:0}.details-meta svg{font-size:initial}}

.message{margin-bottom:25px}
.user-bubble{background:#edf4ff;border-color:#dbe8fc;color:#2c486e;border-radius:12px 12px 3px 12px}
.assistant-answer{color:var(--dc-text)}
.answer-toolbar{border-color:var(--dc-border)}
.assistant-identity{color:var(--dc-text)}
.agent-avatar{background:#eaf2ff;color:var(--dc-primary)}
.assistant-caption{color:var(--dc-text-3);font-size:12px}
.answer-status{font-size:12px}
.answer-content{padding:13px 0 1px}
.supporting-details{background:#fbfcff;border-color:var(--dc-border)}
.supporting-details summary{color:#526986}
.details-meta{font-size:12px}


.message{margin-bottom:27px}
.user-bubble{max-width:min(82%,760px);font-size:15px;line-height:1.75;background:linear-gradient(110deg,#e9f2ff,#f2f7ff);color:#25456e;border-color:#c7dbfa;padding:15px 19px;border-radius:16px 16px 5px 16px}
.assistant-answer{max-width:1000px;background:#fff;border:1px solid #d5e3f6;border-radius:15px;padding:21px 23px;box-shadow:0 7px 25px rgba(30,83,159,.055)}
.assistant-identity{font-size:15px;color:#203f6d}
.agent-avatar{width:36px;height:36px;border-radius:11px;background:linear-gradient(125deg,#e0ebff,#eff5ff);color:#3477e6}
.assistant-caption{font-size:12px}
.answer-content{padding:19px 0 6px}
.answer-status{font-size:12px;font-weight:700}
.answer-progress{margin-top:12px;background:#f6f9ff;border:1px solid #e0eafa;border-radius:10px}
.answer-progress summary{display:flex;align-items:center;gap:9px;cursor:pointer;padding:12px 14px;font-size:13px;color:#3970cb;font-weight:730;list-style:none}
.answer-progress summary::-webkit-details-marker{display:none}
.answer-progress summary>svg:last-child{margin-left:auto;transition:transform .17s}
.answer-progress[open] summary>svg:last-child{transform:rotate(180deg)}
.answer-progress :deep(.task-journey){border:0;border-top:1px solid #e0eafa;margin:0;border-radius:0;background:#f9fbff}
.supporting-details{background:#f7faff;border-color:#d7e5f9}
.supporting-details summary{font-size:13px;color:#3c639b}
.details-summary{font-size:13px}
@media(max-width:760px){.assistant-answer{padding:15px;border-radius:12px}.user-bubble{max-width:96%;font-size:14px}.answer-content{padding:13px 0}}


/* Atlas 2.1 — premium AI workspace without fabricated progress */

.assistant-answer{position:relative;overflow:hidden;border-color:#c8daf4;box-shadow:0 10px 28px #24599b13}
.assistant-answer:before{content:'';position:absolute;left:0;top:0;width:4px;height:100%;background:linear-gradient(180deg,#3777ea 0,#8fbcff 55%,#eaf3ff)}
.answer-toolbar{background:linear-gradient(100deg,#f1f7ff,#fff);margin:-21px -23px 0;padding:14px 20px 14px 25px;border-color:#d9e6f7}
.assistant-identity b{font-size:15px;color:#2459a6}
.answer-content{padding:21px 2px 8px}
.sql-result{padding:14px 1px 2px;border-top:1px solid #e3ecf9}
.answer-progress{background:#f3f8ff;border-color:#d6e4f7}
.supporting-details{background:#f6faff;border-color:#d4e3f7}
.supporting-details:hover{border-color:#a8c9f7}
@media(max-width:760px){.answer-toolbar{margin:-15px -15px 0;padding:12px 13px 12px 17px}.answer-content{padding:13px 0}}

</style>
