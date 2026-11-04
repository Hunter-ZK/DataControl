<template>
  <nav v-if="total>pageSize" class="dc-pager" aria-label="分页">
    <span>第 {{from}}–{{to}} 条 / 已加载 {{total}} 条</span>
    <div>
      <button type="button" :disabled="page<=1" @click="emit('update:page',page-1)">上一页</button>
      <span>{{page}} / {{pageCount}}</span>
      <button type="button" :disabled="page>=pageCount" @click="emit('update:page',page+1)">下一页</button>
    </div>
  </nav>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props=defineProps<{page:number;pageSize:number;total:number}>()
const emit=defineEmits<{ 'update:page':[value:number] }>()
const pageCount=computed(()=>Math.max(1,Math.ceil(props.total/props.pageSize)))
const from=computed(()=>props.total?(props.page-1)*props.pageSize+1:0)
const to=computed(()=>Math.min(props.total,props.page*props.pageSize))
</script>
<style scoped>
.dc-pager{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 0 2px;color:var(--dc-text-2);font-size:12px}.dc-pager>div{display:flex;align-items:center;gap:9px}.dc-pager button{border:1px solid var(--dc-border);background:#fff;border-radius:8px;padding:7px 11px;color:var(--dc-text-2);cursor:pointer}.dc-pager button:hover:not(:disabled){border-color:#a6d4e7;color:var(--dc-primary-strong)}.dc-pager button:disabled{opacity:.4;cursor:not-allowed}@media(max-width:560px){.dc-pager{align-items:flex-start;flex-direction:column}}
</style>
