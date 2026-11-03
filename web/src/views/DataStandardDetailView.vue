<template><ReferenceWorkspace kind="data-standards" :selected-key="String(route.params.no)"/></template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
import ReferenceWorkspace from '@/components/ReferenceWorkspace.vue'
const route=useRoute()
</script>
