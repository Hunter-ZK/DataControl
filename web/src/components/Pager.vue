<template>
  <nav v-if="total > pageSize" class="pager" aria-label="列表分页">
    <span>第 {{ from }}–{{ to }} 条 / 共 {{ total.toLocaleString() }} 条</span>
    <div class="pager-buttons">
      <button type="button" :disabled="page <= 1" @click="emit('update:page', page - 1)">上一页</button>
      <span>{{ page }} / {{ pages }}</span>
      <button type="button" :disabled="page >= pages" @click="emit('update:page', page + 1)">下一页</button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ page: number; pageSize: number; total: number }>()
const emit = defineEmits<{ 'update:page': [page: number] }>()
const pages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(props.pageSize, 1))))
const from = computed(() => props.total ? (props.page - 1) * props.pageSize + 1 : 0)
const to = computed(() => Math.min(props.total, props.page * props.pageSize))
</script>

<style scoped>
.pager{min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--dc-text-2);font-size:12px}.pager-buttons{display:flex;gap:9px;align-items:center}.pager button{padding:6px 10px;border:1px solid var(--dc-border);border-radius:8px;background:#fff;color:var(--dc-text-2);cursor:pointer}.pager button:hover:not(:disabled){border-color:#bfdde9;color:var(--dc-primary-strong)}.pager button:disabled{opacity:.45;cursor:not-allowed}@media(max-width:520px){.pager{align-items:flex-start;flex-direction:column;padding-top:9px}}
</style>
