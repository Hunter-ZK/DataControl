<template>
  <section v-if="steps.length" class="analysis-trace">
    <div class="trace-head">
      <span class="trace-icon"><BrainCircuit :size="17" /></span>
      <div>
        <b>分析过程</b>
        <span>基于实际工具调用生成的可审计执行记录，不展示模型隐藏思维。</span>
      </div>
    </div>
    <div class="trace-flow">
      <div v-for="(step, index) in steps" :key="`${step.callId}-${index}`" class="trace-step" :class="step.status">
        <span class="trace-index">{{ index + 1 }}</span>
        <span>{{ step.label }}</span>
        <CheckCircle2 v-if="step.status === 'done'" :size="14" />
        <TriangleAlert v-else-if="step.status === 'error'" :size="14" />
        <LoaderCircle v-else class="spin" :size="14" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BrainCircuit, CheckCircle2, LoaderCircle, TriangleAlert } from 'lucide-vue-next'
import type { AgentActivity } from '@/api/client'
import { processSteps } from '@/components/agent/presentation'

const props = defineProps<{ events?: AgentActivity[] }>()
const steps = computed(() => processSteps(props.events))
</script>

<style scoped>
.analysis-trace { margin-top: 16px; padding: 14px 15px; border: 1px solid #9fc7d8; border-radius: 12px; background: #eaf5fa; }
.trace-head { display: flex; gap: 10px; align-items: flex-start; }
.trace-icon { width: 32px; height: 32px; border-radius: 9px; display: grid; place-items: center; flex: none; background: #c5e4f1; color: #116e98; }
.trace-head > div { display: grid; gap: 2px; }
.trace-head b { font-size: 14px; color: #1f4d64; }
.trace-head span { font-size: 11px; line-height: 1.45; color: #678695; }
.trace-flow { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 11px; }
.trace-step { display: inline-flex; align-items: center; gap: 6px; padding: 7px 9px; border: 1px solid #b3d3df; border-radius: 9px; background: #fff; color: #3d687d; font-size: 12px; font-weight: 650; }
.trace-step.done { border-color: #79b995; background: #e2f3ea; color: #206c4d; }
.trace-step.error { border-color: #d78383; background: #fbe2e2; color: #963939; }
.trace-index { width: 18px; height: 18px; display: grid; place-items: center; border-radius: 50%; background: rgba(32,120,158,.13); font-size: 10px; font-weight: 800; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
