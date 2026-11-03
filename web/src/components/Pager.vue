<template>
  <nav v-if="total > pageSize" class="pager" aria-label="列表分页">
    <span>第 {{ from }}–{{ to }} 条 / 共 {{ total }} 条</span>
    <div class="pager-buttons">
      <button :disabled="page <= 1" @click="emit('update:page', page-1)">上一页</button>
      <span>{{ page }} / {{ pages }}</span>
      <button :disabled="page >= pages" @click="emit('update:page', page+1)">下一页</button>
    </div>
  </nav>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ page: number; pageSize: number; total: number }>()
const emit = defineEmits<{ 'update:page': [page: number] }>()
const pages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(props.pageSize, 1))))
const from = computed(() => props.total ? (props.page-1)*props.pageSize+1 : 0)
const to = computed(() => Math.min(props.total,props.page*props.pageSize))
</script>
<style scoped>
.pager{min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--dc-text-2);font-size:12px}
.pager-buttons{display:flex;gap:9px;align-items:center}
.pager button{padding:5px 9px;border:1px solid var(--dc-border-strong);border-radius:6px;background:#fff;color:var(--dc-primary-strong)}
.pager button:disabled{color:#718394;background:#f5f7f9}
</style>
