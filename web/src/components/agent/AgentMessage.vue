<template>
  <article class="message" :class="message.role">
    <div v-if="message.role === 'user'" class="user-bubble">{{ message.text }}</div>
    <div v-else class="assistant-answer">
      <div class="answer-toolbar">
        <div class="assistant-identity">
          <span class="agent-avatar"><Sparkles :size="16" /></span>
          <b>DataAgent</b>
          <span class="assistant-caption">回答</span>
        </div>
        <span v-if="message.sql" class="answer-status" :class="validationTone(message)">
          <CheckCircle2 v-if="validationState(message) === 'passed'" :size="14" />
          <AlertCircle v-else :size="14" />
          {{ sqlStatusText(message) }}
        </span>
      </div>
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
import { AlertCircle, CheckCircle2, ChevronDown, FileSearch, Sparkles } from 'lucide-vue-next'
import AgentClarification from '@/components/agent/AgentClarification.vue'
import AgentEvidence from '@/components/agent/AgentEvidence.vue'
import AgentMarkdown from '@/components/agent/AgentMarkdown.vue'
import AgentSqlCard from '@/components/agent/AgentSqlCard.vue'
import AgentTrace from '@/components/agent/AgentTrace.vue'
import AgentValidationPanel from '@/components/agent/AgentValidationPanel.vue'
import { sqlStatusText, validationState, validationTone } from '@/components/agent/presentation'
import type { AgentMessage } from '@/components/agent/types'

const props = defineProps<{ message: AgentMessage }>()
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
</style>
