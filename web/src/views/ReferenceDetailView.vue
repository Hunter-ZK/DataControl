<template><div class="dc-page"><div class="dc-container dc-empty">正在打开资产详情…</div></div></template>
<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps<{ kind: string }>()
const route = useRoute()
const router = useRouter()

function redirectToWorkspace() {
  const paths: Record<string, string> = {
    'word-roots': '/word-roots',
    metrics: '/metrics',
    'stat-systems': '/stat-systems',
  }
  const key = String(route.params.root || route.params.code || '')
  router.replace({ path: paths[props.kind] || '/metrics', query: { ...route.query, selected: key } })
}
onMounted(redirectToWorkspace)
watch(() => route.fullPath, redirectToWorkspace)
</script>
