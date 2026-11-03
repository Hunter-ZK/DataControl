<template><ReferenceWorkspace :kind="kind" :selected-key="key"/></template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ReferenceWorkspace from '@/components/ReferenceWorkspace.vue'
defineProps<{kind:string}>()
const route=useRoute()
const key=computed(()=>String(route.params.root||route.params.code||''))
</script>
