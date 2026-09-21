<template>
  <section v-if="message.sql" class="sql-card">
    <div class="block-head">
      <div class="sql-head-main">
        <Code2 :size="16" />
        <b>生成 SQL</b>
        <span class="sql-type">{{ statementLabel(message.validation) }}</span>
        <span class="sql-state" :class="validationTone(message)">{{ sqlStatusText(message) }}</span>
        <span v-if="showRisk(message.validation)" class="risk-chip" :class="`risk-${message.validation?.risk_level}`">{{ riskLabel(message.validation) }}</span>
      </div>
      <button @click="copySql"><Copy :size="15" />复制</button>
    </div>
    <pre><code>{{ sql }}</code></pre>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Code2, Copy } from 'lucide-vue-next'
import type { AgentMessage } from '@/components/agent/types'
import { displaySql, riskLabel, showRisk, sqlStatusText, statementLabel, validationTone } from '@/components/agent/presentation'

const props = defineProps<{ message: AgentMessage }>()
const sql = computed(() => displaySql(props.message))

async function copySql() {
  try {
    await navigator.clipboard.writeText(sql.value)
    ElMessage.success('SQL 已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.sql-card { margin-top: 16px; border: 1px solid #79a9be; border-radius: 12px; overflow: hidden; background: #0b2737; box-shadow: 0 8px 22px rgba(15,59,82,.09); }
.block-head { min-height: 48px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: #deedf4; border-bottom: 1px solid #a9c9d8; color: #2d5a70; }
.sql-head-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.block-head b { font-size: 14px; color: #204c62; }
.block-head button { display: flex; align-items: center; gap: 5px; border: 1px solid #aac8d5; background: #fff; border-radius: 8px; padding: 6px 9px; color: #35657b; font-size: 12px; cursor: pointer; }
.block-head button:hover { border-color: #6da8bf; color: #0f668f; }
.sql-type,.sql-state,.risk-chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; }
.sql-type { color: #315767; background: #c5d9e3; }
.sql-state.success { color: #11623f; background: #c9e9da; border: 1px solid #7fbd9d; }
.sql-state.warning { color: #734a08; background: #ffe39a; border: 1px solid #dba840; }
.sql-state.pending { color: #485b65; background: #dbe3e7; border: 1px solid #9cabB3; }
.sql-state.danger { color: #882c2c; background: #f7c5c5; border: 1px solid #d36f6f; }
.risk-chip.risk-medium { color: #69500b; background: #f3dc8e; }
.risk-chip.risk-high { color: #82420c; background: #f6c99f; }
.risk-chip.risk-critical { color: #862929; background: #f1b3b3; }
pre { margin: 0; padding: 18px 20px; overflow: auto; white-space: pre; tab-size: 2; }
code { color: #e3eef4; font: 14px/1.75 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
</style>
