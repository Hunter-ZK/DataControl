<template>
  <article class="message" :class="message.role">
    <div v-if="message.role === 'user'" class="user-bubble">{{ message.text }}</div>
    <div v-else class="assistant-answer">
      <div class="answer-label"><span class="agent-avatar"><Sparkles :size="16" /></span><b>DataAgent</b></div>
      <div class="answer-summary">{{ summaryText }}</div>
      <AgentMarkdown :text="message.text" :summary="summaryText" />
      <AgentClarification
        v-if="message.clarification"
        :clarification="message.clarification"
        :resolved="message.clarificationResolved"
        :selection="message.clarificationSelection"
        @clarify="emit('clarify', $event)"
      />
      <AgentTrace :events="message.events" />
      <AgentEvidence :evidence="message.evidence" />
      <AgentSqlCard :message="message" />
      <AgentValidationPanel :message="message" />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles } from 'lucide-vue-next'
import AgentClarification from '@/components/agent/AgentClarification.vue'
import AgentEvidence from '@/components/agent/AgentEvidence.vue'
import AgentMarkdown from '@/components/agent/AgentMarkdown.vue'
import AgentSqlCard from '@/components/agent/AgentSqlCard.vue'
import AgentTrace from '@/components/agent/AgentTrace.vue'
import AgentValidationPanel from '@/components/agent/AgentValidationPanel.vue'
import type { AgentMessage } from '@/components/agent/types'

const props = defineProps<{ message: AgentMessage }>()
const emit = defineEmits<{
  clarify: [payload: { values: string[]; labels: string[]; custom?: string }]
}>()

const summaryText = computed(() => {
  const explicit = props.message.summary?.trim()
  if (explicit) return explicit.replace(/^\s{0,3}#{1,6}\s*/, '').replace(/[*_`~]/g, '')
  const first = props.message.text.split(/\n+/).find((value) => value.trim()) || '分析完成'
  return first.replace(/^\s{0,3}#{1,6}\s*/, '').replace(/[*_`~]/g, '').trim()
})
</script>

<style scoped>
.message { margin: 0 0 28px; }
.message.user { display: flex; justify-content: flex-end; }
.user-bubble { max-width: 74%; padding: 12px 16px; border-radius: 14px 14px 4px 14px; background: #252b38; color: #fff; font-size: 14px; line-height: 1.68; box-shadow: 0 6px 18px rgba(17,25,39,.09); white-space: pre-wrap; }
.assistant-answer { max-width: 980px; }
.answer-label { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; color: #5d47df; font-size: 14px; }
.agent-avatar { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; background: #f0edff; color: #5d47df; }
.answer-summary { padding: 2px 0 2px 13px; border-left: 3px solid #7c67f2; font-size: 17px; line-height: 1.72; font-weight: 750; color: #252b36; }
@media(max-width:760px){.user-bubble{max-width:90%}.answer-summary{font-size:17px}}
</style>
