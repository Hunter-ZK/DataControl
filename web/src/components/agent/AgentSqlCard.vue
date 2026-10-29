<template>
  <section v-if="message.sql" class="sql-card">
    <div class="block-head">
      <div class="sql-head-main">
        <Code2 :size="16" />
        <b>生成的 SQL</b>
        <span class="sql-type">{{ statementLabel(message.validation) }}</span>
        <span class="sql-state" :class="validationTone(message)">{{ sqlStatusText(message) }}</span>
        <span v-if="showRisk(message.validation)" class="risk-chip" :class="`risk-${message.validation?.risk_level}`">{{ riskLabel(message.validation) }}</span>
      </div>
      <button @click="copySql"><Copy :size="15" />复制</button>
    </div>
    <div class="code-editor" role="region" aria-label="生成的 SQL"><div class="editor-gutter"><span v-for="(_,i) in sqlLines" :key="i">{{i+1}}</span></div><pre><code>{{sql}}</code></pre></div>
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
const sqlLines = computed(() => sql.value.split('\n'))

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
.sql-card { margin-top: 0; border: 1px solid #d5e5ed; border-radius: 10px; overflow: hidden; background: #132c3e; }
.block-head { min-height: 47px; padding: 0 14px; display:flex; align-items:center; justify-content:space-between; gap:12px; background:#f3f8fb; border-bottom:1px solid #d9e6ed; color:#2d5a70; }
.sql-head-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.block-head b { font-size: 14px; color: #204c62; }
.block-head button { display: flex; align-items: center; gap: 5px; border: 1px solid #aac8d5; background: #fff; border-radius: 8px; padding: 6px 9px; color: #35657b; font-size: 12px; cursor: pointer; }
.block-head button:hover { border-color: #6da8bf; color: #0f668f; }
.sql-type,.sql-state,.risk-chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 800; }
.sql-type { color: #315767; background: #c5d9e3; }
.sql-state.success { color:#2d8060; background:#e8f5ee; border:1px solid #cce4d8; }
.sql-state.warning { color:#98702a; background:#fcf4df; border:1px solid #ecdfc2; }
.sql-state.pending { color: #485b65; background: #dbe3e7; border: 1px solid #9cabB3; }
.sql-state.danger { color:#aa5656; background:#fff1f1; border:1px solid #e9caca; }
.risk-chip.risk-medium { color: #69500b; background: #f3dc8e; }
.risk-chip.risk-high { color: #82420c; background: #f6c99f; }
.risk-chip.risk-critical { color: #862929; background: #f1b3b3; }
pre { margin: 0; padding: 18px 20px; overflow: auto; white-space: pre; tab-size: 2; }
code { color: #e3eef4; font: 14px/1.75 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }


.sql-card{background:#101d37;border-color:#abc5e9;border-radius:13px;box-shadow:0 7px 24px rgba(19,50,99,.13)}
.block-head{background:linear-gradient(98deg,#f1f6ff,#fff);min-height:55px;padding:0 17px;border-color:#d5e3f6}
.block-head b{font-size:14px;color:#203d67}
.block-head button{font-size:13px;border-color:#c6d8f4;color:#285fc5;border-radius:8px;padding:7px 12px}
.sql-type,.sql-state,.risk-chip{font-size:12px;border-radius:7px}
.sql-type{background:#dfeaff;color:#2b64c7}
.code-editor{display:flex;overflow:auto;background:linear-gradient(138deg,#0e1e3b,#142647);tab-size:2}
.editor-gutter{position:sticky;left:0;flex:none;display:flex;flex-direction:column;padding:18px 11px 18px 17px;text-align:right;min-width:43px;background:#122340;color:#6280a7;user-select:none;font:13px/1.85 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;border-right:1px solid #2b4464}
.code-editor pre{flex:1;min-width:max-content;padding:18px 19px;margin:0;overflow:visible;white-space:pre}
.code-editor code{font:13px/1.85 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#d7e7ff}

</style>
