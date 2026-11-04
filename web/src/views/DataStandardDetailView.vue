<template><div class="dc-page"><div class="dc-container dc-empty">正在打开数据标准详情…</div></div></template>
<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
function redirectToWorkspace() {
  router.replace({ path: '/standards', query: { ...route.query, selected: String(route.params.no) } })
}
onMounted(redirectToWorkspace)
watch(() => route.fullPath, redirectToWorkspace)
</script>
