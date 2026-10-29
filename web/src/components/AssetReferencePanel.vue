<template>
  <section class="dc-card refs-panel">
    <header><div><span class="dc-eyebrow">REFERENCES</span><h2>{{title}}</h2><p>依据已登记的字段或指标引用，非模糊匹配</p></div>
      <button :disabled="!data?.total||busy" @click="exportAll"><Download :size="16"/>导出完整清单</button>
    </header>
    <div v-if="busy" class="dc-empty">正在查询…</div>
    <div v-else-if="error" class="dc-empty">{{error}}</div>
    <div v-else-if="data">
      <p class="refs-count">共 <b>{{data.total??data.references.length}}</b> 项
        <span v-if="data.status==='truncated'">仅显示前 {{data.references.length}} 项</span></p>
      <div class="refs-list">
        <RouterLink v-for="item in data.references" :key="item.assetId"
            :to="item.assetType==='METRIC'?{name:'metric',params:{code:item.technicalName||item.assetId}}:{name:'field',params:{id:item.assetId}}">
          <span>{{item.assetType==='METRIC'?'指标':'字段'}}</span><b>{{item.title}}</b><code>{{item.technicalName}}</code><ArrowUpRight :size="15"/>
        </RouterLink>
        <div v-if="!data.references.length" class="dc-empty">尚无登记引用</div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import {ref,watch} from 'vue'
import {RouterLink} from 'vue-router'
import {ArrowUpRight,Download} from 'lucide-vue-next'
import {ElMessage} from 'element-plus'
import {assetApi} from '@/api/client'
import {makeCsv} from '@/utils/assetExport'
const props=defineProps<{kind:'CODE_TABLE'|'STANDARD'|'STAT_SYSTEM';assetId:string;title:string}>()
type Result=Awaited<ReturnType<typeof assetApi.references>>
const data=ref<Result|null>(null)
const error=ref('')
const busy=ref(false)
let epoch=0
watch(()=>[props.kind,props.assetId],async()=>{
 const current=++epoch;busy.value=true;data.value=null;error.value=''
 try {const response=await assetApi.references(props.kind,props.assetId,100);if(epoch===current)data.value=response}
 catch {if(epoch===current)error.value='未能获取已登记引用'}
 finally {if(epoch===current)busy.value=false}
},{immediate:true})
async function exportAll(){
 busy.value=true
 try{
  const result=await assetApi.references(props.kind,props.assetId,5000)
  if(result.status!=='complete')throw Error('超过 5000 项导出上限，为防止遗漏已阻止导出')
  const rows=[['资产类型','资产ID','技术编码','名称'],...result.references.map(x=>[x.assetType,x.assetId,x.technicalName||'',x.title])]
  const url=URL.createObjectURL(new Blob([makeCsv(rows)],{type:'text/csv;charset=utf-8'}))
  const anchor=document.createElement('a');anchor.href=url;anchor.download='datacontrol_references.csv'
  document.body.appendChild(anchor);anchor.click();anchor.remove()
  setTimeout(()=>URL.revokeObjectURL(url),0)
  ElMessage.success('引用清单已导出')
 }catch(e){ElMessage.warning(e instanceof Error?e.message:'导出失败')}
 finally{busy.value=false}
}
</script>
<style scoped>
.refs-panel{margin-top:16px;padding:22px}.refs-panel header{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}
.refs-panel h2{font-size:19px;margin:5px 0}.refs-panel header p{margin:5px 0;color:var(--dc-text-2);font-size:13px}
.refs-panel button{display:flex;align-items:center;gap:7px;border:1px solid var(--dc-border);background:var(--dc-primary-soft);color:var(--dc-primary);border-radius:9px;padding:9px 12px;cursor:pointer}
.refs-panel button:disabled{opacity:.5;cursor:not-allowed}.refs-count{padding:10px 14px;background:#f1f7ff;border-radius:9px;font-size:13px}.refs-count b{font-size:18px;color:var(--dc-primary)}.refs-count span{margin-left:10px;color:var(--dc-warning)}
.refs-list{max-height:400px;overflow:auto;border:1px solid var(--dc-border);border-radius:9px}.refs-list a{display:flex;align-items:center;gap:11px;padding:12px 14px;border-bottom:1px solid var(--dc-border);font-size:13px}.refs-list a:nth-child(even){background:#f7faff}.refs-list a:hover{background:var(--dc-primary-soft)}.refs-list a:last-child{border:0}
.refs-list a span{color:var(--dc-primary);background:#e9f2ff;padding:3px 7px;border-radius:6px;font-size:12px}.refs-list a b{flex:1}.refs-list a code{color:var(--dc-text-3);font-size:12px}.refs-list a svg{color:var(--dc-primary)}
</style>