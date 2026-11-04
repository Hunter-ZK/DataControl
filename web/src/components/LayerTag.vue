<template>
  <span v-if="layer" class="layer-tag" :class="layerClass">{{ layer }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ layer?: string | null }>()
const layerClass = computed(() => String(props.layer || '').toLowerCase())
</script>

<style scoped>
.layer-tag{display:inline-flex;align-items:center;justify-content:center;min-width:40px;padding:3px 7px;border:1px solid transparent;border-radius:7px;font-size:11px;font-weight:700;line-height:1.4}.ods{color:#64748b;background:#f1f5f9;border-color:#e2e8f0}.dwd{color:#2563eb;background:#eff6ff;border-color:#dbeafe}.dws{color:#0f766e;background:#f0fdfa;border-color:#ccfbf1}.ads{color:#7c3aed;background:#f5f3ff;border-color:#ede9fe}.dim{color:#b45309;background:#fffbeb;border-color:#fde68a}
</style>
