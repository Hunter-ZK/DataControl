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
.validation-panel { margin-top: 11px; padding: 15px 16px; border: 2px solid #9eafb8; border-radius: 12px; background: #eef2f4; }
.validation-panel.success { border-color: #62ad86; background: #e1f3ea; }
.validation-panel.warning { border-color: #d19b2f; background: #ffedb9; }
.validation-panel.pending { border-color: #929fa6; background: #e8edef; }
.validation-panel.danger { border-color: #cc6262; background: #fbdcdc; }
.validation-head { display: flex; gap: 11px; align-items: flex-start; }
.validation-icon { width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center; flex: none; background: #c5e8d6; color: #176f4c; }
.warning .validation-icon { background: #ffdc86; color: #85570e; }
.pending .validation-icon { background: #d1d9dd; color: #53656f; }
.danger .validation-icon { background: #efb7b7; color: #983333; }
.validation-head b { font-size: 15px; color: #204d61; }
.validation-head p { margin: 4px 0 0; font-size: 13px; line-height: 1.6; color: #4b6e7f; }
.validation-facts { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 9px; margin-top: 13px; }
.validation-facts > div { min-width: 0; padding: 10px 11px; border-radius: 9px; background: rgba(255,255,255,.8); border: 1px solid rgba(126,159,174,.68); }
.validation-facts span { display: block; font-size: 11px; color: #64808e; margin-bottom: 4px; }
.validation-facts b { display: block; font-size: 13px; color: #29576c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.issue-list { display: grid; gap: 9px; margin-top: 11px; }
.issue-row { display: grid; grid-template-columns: auto minmax(0,1fr); gap: 10px; align-items: flex-start; padding: 11px; border-radius: 9px; background: #fff; border: 1px solid #c8d8df; }
.issue-row.issue-error { border-color: #cf6c6c; background: #fff1f1; }
.issue-row.issue-warning { border-color: #ce9d38; background: #fff7dd; }
.issue-badge { border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; background: #dce5e9; color: #506a76; }
.issue-error .issue-badge { background: #f1bcbc; color: #8c3030; }
.issue-warning .issue-badge { background: #ffdc8c; color: #78500c; }
.issue-row b { font-size: 13px; line-height: 1.55; color: #315767; }
.issue-row p { margin: 4px 0 0; font-size: 12px; line-height: 1.55; color: #607c89; }
.validation-empty { margin-top: 11px; display: flex; gap: 7px; align-items: center; color: #246b50; font-size: 13px; font-weight: 650; }
.validation-empty.pending { color: #62563d; }
@media(max-width:980px){.validation-facts{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
