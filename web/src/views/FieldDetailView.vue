<template>
  <div class="dc-page"><div class="dc-container"><div class="dc-empty">
    {{error||'正在定位所属数据集和字段…'}}
    <RouterLink v-if="error" to="/catalog">返回资产目录</RouterLink>
  </div></div></div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
const route=useRoute(),router=useRouter(),error=ref('')
onMounted(async()=>{
  try{
    const field:any=await api.get('/columns/'+encodeURIComponent(String(route.params.id)))
    await router.replace({name:'dataset',params:{id:field.datasetId},
      query:{tab:'columns',field:field.assetId}})
  }catch{error.value='未找到该字段或所属数据集。'}
})
</script>
