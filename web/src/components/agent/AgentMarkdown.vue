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
.agent-markdown { margin-top: 12px; color: #365e72; font-size: 15px; line-height: 1.78; }
.agent-markdown :deep(h1),
.agent-markdown :deep(h2),
.agent-markdown :deep(h3),
.agent-markdown :deep(h4) { color: #173f53; line-height: 1.4; margin: 18px 0 8px; letter-spacing: -.01em; }
.agent-markdown :deep(h1) { font-size: 22px; }
.agent-markdown :deep(h2) { font-size: 19px; }
.agent-markdown :deep(h3) { font-size: 17px; }
.agent-markdown :deep(h4) { font-size: 15px; }
.agent-markdown :deep(p) { margin: 0 0 10px; }
.agent-markdown :deep(ul),
.agent-markdown :deep(ol) { margin: 7px 0 11px; padding-left: 24px; }
.agent-markdown :deep(li) { margin: 4px 0; padding-left: 2px; }
.agent-markdown :deep(strong) { color: #1b5068; font-weight: 750; }
.agent-markdown :deep(blockquote) { margin: 12px 0; padding: 10px 14px; border-left: 4px solid #378db2; border-radius: 0 9px 9px 0; background: #edf6fa; color: #3f687a; }
.agent-markdown :deep(code) { padding: 2px 5px; border-radius: 5px; background: #e7f0f5; color: #245d77; font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
.agent-markdown :deep(pre) { margin: 12px 0; padding: 14px 16px; overflow: auto; border-radius: 10px; background: #102b3a; color: #e3eef4; }
.agent-markdown :deep(pre code) { padding: 0; background: transparent; color: inherit; }
.agent-markdown :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; background: #fff; }
.agent-markdown :deep(th),
.agent-markdown :deep(td) { padding: 9px 11px; border: 1px solid #c9dce6; text-align: left; vertical-align: top; }
.agent-markdown :deep(th) { background: #eaf4f9; color: #24576e; font-weight: 750; }
.agent-markdown :deep(a) { color: #0f6f99; text-decoration: underline; text-underline-offset: 2px; }
.agent-markdown :deep(hr) { border: 0; border-top: 1px solid #d7e5ec; margin: 17px 0; }
</style>
