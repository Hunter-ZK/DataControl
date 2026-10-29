<template>
  <section v-if="message.sql" class="validation-panel" :class="validationTone(message)">
    <div class="validation-head">
      <span class="validation-icon">
        <CheckCircle2 v-if="validationState(message) === 'passed'" :size="19" />
        <TriangleAlert v-else :size="19" />
      </span>
      <div>
        <b>{{ validationTitle(message) }}</b>
        <p>{{ validationDescription(message) }}</p>
      </div>
    </div>

    <div class="validation-facts">
      <div><span>方言</span><b>{{ message.validation?.dialect || 'MaxCompute' }}</b></div>
      <div><span>语句类型</span><b>{{ statementLabel(message.validation) }}</b></div>
      <div><span>风险等级</span><b>{{ riskLabel(message.validation) }}</b></div>
      <div><span>执行状态</span><b>不会执行</b></div>
    </div>

    <div v-if="validationIssues(message.validation).length" class="issue-list">
      <div v-for="issue in validationIssues(message.validation)" :key="`${issue.code}-${issue.message}`" class="issue-row" :class="`issue-${issue.severity}`">
        <span class="issue-badge">{{ severityLabel(issue.severity) }}</span>
        <div>
          <b>{{ issue.message }}</b>
          <p v-if="issue.suggestion">{{ issue.suggestion }}</p>
        </div>
      </div>
    </div>
    <div v-else-if="validationState(message) === 'passed'" class="validation-empty"><CheckCircle2 :size="16" />静态校验未发现阻断项。</div>
    <div v-else-if="validationState(message) === 'not_validated'" class="validation-empty pending"><TriangleAlert :size="16" />当前 SQL 尚未完成静态校验，不应显示为可信结果。</div>
  </section>
</template>

<script setup lang="ts">
import { CheckCircle2, TriangleAlert } from 'lucide-vue-next'
import type { AgentMessage } from '@/components/agent/types'
import {
  riskLabel,
  severityLabel,
  statementLabel,
  validationDescription,
  validationIssues,
  validationState,
  validationTitle,
  validationTone,
} from '@/components/agent/presentation'

defineProps<{ message: AgentMessage }>()
</script>

<style scoped>
.validation-panel { margin-top: 8px; padding: 12px 14px; border: 1px solid #e0e9ee; border-radius: 10px; background: #fafcfd; }
.validation-panel.success { border-color: #d7e8de; background: #fafdfb; }
.validation-panel.warning { border-color: #ecdfbb; background: #fffdf7; }
.validation-panel.danger { border-color: #edcbcb; background: #fffafa; }
.validation-head { display:flex; align-items:flex-start; gap:10px; }
.validation-icon { display:grid; place-items:center; width:24px; height:24px; flex:none; color:#3d8967; }
.warning .validation-icon { color:#ab833a; }
.pending .validation-icon { color:#6c7e89; }
.danger .validation-icon { color:#b75c5c; }
.validation-head b { color:#38596b; font-size:12px; }
.validation-head p { margin:3px 0 0; font-size:11px; line-height:1.55; color:#708796; }
.validation-facts { display:flex; flex-wrap:wrap; gap:7px 15px; margin-top:10px; }
.validation-facts>div { display:flex; align-items:center; gap:5px; }
.validation-facts span { color:#8599a4; font-size:10px; }
.validation-facts b { color:#4b697a; font-size:11px; font-weight:650; }
.issue-list { display:grid; gap:8px; margin-top:11px; }
.issue-row { display:flex; gap:9px; padding:10px 11px; border:1px solid #e1ebf0; border-radius:8px; background:#fff; }
.issue-row.issue-error { border-color:#e8c7c7; }
.issue-row.issue-warning { border-color:#ebdfc8; }
.issue-badge { align-self:flex-start; white-space:nowrap; font-size:10px; color:#718795; }
.issue-error .issue-badge { color:#a75151; }
.issue-warning .issue-badge { color:#987333; }
.issue-row b { font-size:12px; color:#456376; font-weight:650; }
.issue-row p { margin:3px 0 0; font-size:11px; color:#738b98; }
.validation-empty { display:flex; align-items:center; gap:7px; margin-top:9px; color:#388363; font-size:11px; }
.validation-empty.pending { color:#8a7139; }
</style>
