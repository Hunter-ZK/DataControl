<template>
  <span v-if="layer" class="layer" :class="layerClass">{{ layer }}</span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ layer?: string | null }>()
const layerClass = computed(() => String(props.layer || '').toLowerCase())
</script>
<style scoped>
.layer{display:inline-flex;justify-content:center;min-width:38px;padding:2px 6px;border-radius:5px;font-size:12px;font-weight:650;border:1px solid transparent}
.ods{color:#475569;background:#f1f5f9;border-color:#e2e8f0}
.dwd{color:#1d4ed8;background:#eff6ff;border-color:#dbeafe}
.dws{color:#0f766e;background:#f0fdfa;border-color:#ccfbf1}
.ads{color:#6d28d9;background:#f5f3ff;border-color:#ede9fe}
.dim{color:#92400e;background:#fffbeb;border-color:#fde68a}
</style>
