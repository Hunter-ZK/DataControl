<template>
  <div class="dc-page"><div class="dc-container dc-empty">{{message}}</div></div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()
const message = ref('正在定位字段所属的数据集…')

async function openField() {
  try {
    const id = String(route.params.id)
    const field = await api.get(`/columns/${encodeURIComponent(id)}`)
    if (!field?.datasetId) throw new Error('Dataset not found for field')
    await router.replace({
      name: 'dataset',
      params: { id: field.datasetId },
      query: { field: String(field.assetId || id) },
    })
  } catch {
    message.value = '无法定位该字段所属的数据集，请检查字段链接是否有效。'
  }
}
watch(() => route.params.id, openField, { immediate: true })
</script>
