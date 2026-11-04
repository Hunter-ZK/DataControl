<template>
  <span class="copy-tech" @click.stop>
    <code v-if="showText" class="dc-tech">{{value}}</code>
    <button type="button" class="copy-action" :aria-label="'复制 '+value" :title="'复制 '+value" @click.stop.prevent="copy"><Copy :size="13"/></button>
  </span>
</template>
<script setup lang="ts">
import { Copy } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
const props=withDefaults(defineProps<{value:string;showText?:boolean}>(),{showText:true})
async function copy(){
  try {await navigator.clipboard.writeText(props.value);ElMessage.success('已复制')}
  catch {ElMessage.warning('复制失败，请手动复制')}
}
</script>
<style scoped>
.copy-tech{display:inline-flex;align-items:center;gap:3px;min-width:0;max-width:100%;vertical-align:middle}
.copy-tech code{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.copy-action{opacity:0;display:grid;place-items:center;width:24px;height:24px;flex:none;background:#eef4ff;color:#2563eb;border:0;border-radius:6px;cursor:pointer}
.copy-tech:hover .copy-action,.copy-tech:focus-within .copy-action{opacity:1}.copy-action:hover{background:#dceaff}
@media(hover:none){.copy-action{opacity:1}}
</style>
