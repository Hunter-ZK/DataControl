<template><ReferenceWorkspace :kind="kind"/></template>
<script setup lang="ts">
import ReferenceWorkspace from '@/components/ReferenceWorkspace.vue'
defineProps<{kind:string}>()
</script>
