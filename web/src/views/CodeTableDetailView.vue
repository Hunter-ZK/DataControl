<template><div class="dc-page"><div class="dc-container dc-empty">正在打开码表详情…</div></div></template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
onMounted(() => {
  router.replace({ path: '/code-tables', query: { ...route.query, selected: String(route.params.no) } })
})
</script>
