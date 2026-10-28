<template>
  <div v-if="html" class="agent-markdown" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderAgentMarkdown } from '@/components/agent/markdown'

const props = defineProps<{
  text: string
  summary?: string | null
}>()

const html = computed(() => renderAgentMarkdown(props.text, props.summary))
</script>

<style scoped>
.agent-markdown { color: #314d60; font-size: 14px; line-height: 1.85; overflow-wrap: anywhere; }
.agent-markdown :deep(h1),.agent-markdown :deep(h2),.agent-markdown :deep(h3),.agent-markdown :deep(h4) { color: #183e53; line-height:1.5; margin:18px 0 9px; font-weight:720; }
.agent-markdown :deep(h1:first-child),.agent-markdown :deep(h2:first-child),.agent-markdown :deep(h3:first-child) { margin-top:0; }
.agent-markdown :deep(h1) { font-size:20px; }
.agent-markdown :deep(h2) { font-size:17px; }
.agent-markdown :deep(h3) { font-size:15px; }
.agent-markdown :deep(h4) { font-size:14px; }
.agent-markdown :deep(p) { margin: 0 0 11px; }
.agent-markdown :deep(p:last-child) { margin-bottom:0; }
.agent-markdown :deep(ul),.agent-markdown :deep(ol) { margin:8px 0 12px; padding-left:23px; }
.agent-markdown :deep(li) { margin:3px 0; padding-left:2px; }
.agent-markdown :deep(li::marker) { color: #5596b3; }
.agent-markdown :deep(strong) { color:#174a63; font-weight:750; }
.agent-markdown :deep(blockquote) { margin:12px 0; padding:11px 15px; border-left:3px solid #8cbdd1; background:#f5f9fc; border-radius:0 7px 7px 0; color:#577387; }
.agent-markdown :deep(code) { padding:2px 5px; border-radius:4px; background:#edf3f6; color:#285e78; font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; }
.agent-markdown :deep(pre) { margin:13px 0; padding:15px; overflow:auto; border-radius:9px; background:#142e3f; color:#dbe9f1; }
.agent-markdown :deep(pre code) { padding:0; background:transparent; color:inherit; }
.agent-markdown :deep(table) { display:block; width:100%; overflow-x:auto; border-collapse:collapse; margin:13px 0; font-size:13px; }
.agent-markdown :deep(th),.agent-markdown :deep(td) { padding:9px 12px; border-bottom:1px solid #e1ebf0; text-align:left; vertical-align:top; }
.agent-markdown :deep(th) { background:#f3f8fb; color:#345c71; font-weight:720; white-space:nowrap; }
.agent-markdown :deep(tr:nth-child(even) td) { background:#fafcfd; }
.agent-markdown :deep(a) { color:#16739a; text-decoration:underline; text-underline-offset:2px; }
.agent-markdown :deep(hr) { border:0; border-top:1px solid #e3edf2; margin:17px 0; }


.agent-markdown{font-size:15px;color:#324b6f;line-height:1.9}
.agent-markdown :deep(h1),.agent-markdown :deep(h2),.agent-markdown :deep(h3){color:#193965}
.agent-markdown :deep(h2){font-size:19px}
.agent-markdown :deep(h3){font-size:16px}
.agent-markdown :deep(strong){color:#1b4a88}
.agent-markdown :deep(blockquote){border-color:#6da0ef;background:#edf5ff;color:#46688f}
.agent-markdown :deep(code){font-size:13px;background:#eaf2ff;color:#285fc1}
.agent-markdown :deep(pre){background:#111f3b}
.agent-markdown :deep(th){background:#ecf3ff;color:#2d517b}
.agent-markdown :deep(td){font-size:14px}
.agent-markdown :deep(a){color:#276bd8}

</style>
