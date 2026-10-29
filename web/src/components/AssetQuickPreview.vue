<template>
  <div class="preview-control" @click.stop>
    <el-popover placement="left-start" :width="390" trigger="hover" :show-after="180" :hide-after="240"
      popper-class="dc-asset-preview-popper" @show="loadDetail">
      <template #reference><button class="preview-trigger" type="button" @click.stop="pin" aria-label="快捷预览资产">
        <Eye :size="16"/> 快捷预览
      </button></template>
      <div class="preview-body">
        <div class="preview-eyebrow"><AssetIcon :type="item.assetType" :size="21"/> {{ typeName }} <span>悬浮预览</span></div>
        <strong class="preview-title">{{ item.title }}</strong>
        <code>{{ item.technicalName }}</code>
        <div class="preview-pills"><span v-if="item.layerCode">{{item.layerCode}}</span><span v-if="item.catalogCode">目录 {{item.catalogCode}}</span><span v-if="item.status">{{item.status}}</span></div>
        <p>{{ description }}</p>
        <div v-if="detailLoading" class="preview-muted">正在补充已登记的元数据…</div>
        <dl v-else-if="detail" class="preview-facts">
          <div v-for="fact in facts" :key="fact.label"><dt>{{fact.label}}</dt><dd>{{fact.value}}</dd></div>
        </dl>
        <div v-if="detailError" class="preview-muted">详细信息暂不可用，以上为搜索索引信息。</div>
        <div v-if="codeValues.length" class="preview-code-values">
          <b>码值预览（前 4 项）</b><span v-for="v in codeValues" :key="v.value"><code>{{v.value}}</code>{{v.name}}</span>
        </div>
        <footer><button @click.stop="pin"><Pin :size="15"/> 固定预览</button>
          <button @click.stop="emit('open',item)">打开详情 <ArrowRight :size="15"/></button></footer>
      </div>
    </el-popover>
    <el-dialog v-model="dialogOpen" :width="'min(540px, calc(100vw - 28px))'" :append-to-body="true"
      class="dc-quick-preview-dialog" :show-close="true" :title="'资产快捷预览'" @open="loadDetail">
      <div class="preview-body pinned">
        <div class="preview-eyebrow"><AssetIcon :type="item.assetType" :size="22"/> {{typeName}}</div>
        <strong class="preview-title">{{item.title}}</strong><code>{{item.technicalName}}</code>
        <div class="preview-pills"><span v-if="item.layerCode">{{item.layerCode}}</span><span v-if="item.catalogCode">{{item.catalogCode}}</span></div>
        <p>{{description}}</p>
        <div v-if="detailLoading" class="preview-muted">正在读取元数据…</div>
        <dl v-else-if="detail" class="preview-facts"><div v-for="fact in facts" :key="fact.label"><dt>{{fact.label}}</dt><dd>{{fact.value}}</dd></div></dl>
        <div v-if="detailError" class="preview-muted">详细信息暂不可用，保留搜索索引摘要。</div>
        <div v-if="codeValues.length" class="preview-code-values"><b>码值预览</b><span v-for="v in codeValues" :key="v.value"><code>{{v.value}}</code>{{v.name}}</span></div>
        <footer><button @click.stop="dialogOpen=false">关闭</button><button @click.stop="dialogOpen=false;emit('open',item)">打开资产详情 <ArrowRight :size="15"/></button></footer>
      </div>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight, Eye, Pin } from 'lucide-vue-next'
import api, { assetApi, semanticApi, type SearchItem } from '@/api/client'
import AssetIcon from '@/components/AssetIcon.vue'

const props = defineProps<{ item: SearchItem }>()
const emit = defineEmits<{ open: [item: SearchItem] }>()
const dialogOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const detailLoading = ref(false)
const detailError = ref(false)
const typeName = computed(() => ({ TABLE:'数据集',COLUMN:'字段',METRIC:'业务指标',CODE_TABLE:'标准码表',STANDARD:'数据标准',WORD_ROOT:'词根',STAT_SYSTEM:'统计制度' } as Record<string,string>)[props.item.assetType]||'资产')
function value(key:string) { const x=detail.value?.[key]; return typeof x==='string'||typeof x==='number' ? String(x) : '' }
const description=computed(()=>value('bizDefinition')||value('definition')||value('description')||value('caliber')||props.item.snippet||'暂未登记业务说明。')
const facts=computed(()=>[
  {label:'业务名称',value:value('bizName')||value('cnName')||value('name')},
  {label:'数据类型',value:value('dataType')},
  {label:'所属数据集',value:value('datasetId')},
  {label:'数仓层级',value:value('layerCode')},
  {label:'统计时间字段',value: typeof detail.value?.time==='object' && detail.value.time ? String((detail.value.time as Record<string,unknown>).field||'') : ''},
  {label:'关联数据标准',value:value('standardNo')},
  {label:'关联码表',value:value('codeTableNo')},
  {label:'负责人员',value:value('techOwner')},
].filter(x=>x.value).slice(0,6))
const codeValues=computed(()=>Array.isArray(detail.value?.values)
  ? (detail.value.values as Array<{value:string;name:string}>).slice(0,4):[])
let fetchedKey=''
async function loadDetail(){
  const item=props.item
  const key=item.assetType+':'+item.assetId+':'+item.technicalName
  if(fetchedKey===key)return
  fetchedKey=key;detail.value=null;detailError.value=false
  const name=encodeURIComponent(item.technicalName)
  const id=encodeURIComponent(item.assetId)
  detailLoading.value=true
  try{
    if(item.assetType==='TABLE') detail.value=await assetApi.table(item.assetId)
    else if(item.assetType==='COLUMN') detail.value=await api.get('/columns/'+id)
    else if(item.assetType==='METRIC') detail.value=await semanticApi.metric(item.technicalName) as unknown as Record<string,unknown>
    else if(item.assetType==='CODE_TABLE') detail.value=await api.get('/code-tables/'+name)
    // Reference types without a single-asset detail API keep the trustworthy search summary.
  }catch{detailError.value=true}
  finally{detailLoading.value=false}
}
function pin(){dialogOpen.value=true;loadDetail()}
</script>
<style scoped>
.preview-trigger{display:inline-flex;gap:6px;align-items:center;padding:6px 10px;border:1px solid #c8dcf8;background:#fff;border-radius:8px;color:#306dc5;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.preview-trigger:hover{border-color:#76a7ed;background:#e8f2ff}
.preview-body{display:grid;gap:10px;padding:6px 2px;color:#23436e}
.preview-eyebrow{display:flex;gap:8px;align-items:center;font-size:12px;color:#2e6ecf;font-weight:750}
.preview-eyebrow span{margin-left:auto;color:#8da0b9;font-weight:500}
.preview-title{font-size:18px;line-height:1.45;color:#193e70}
.preview-body>code{font:12px/1.65 var(--dc-mono);color:#526d91;background:#edf4ff;padding:8px 10px;border:1px solid #d5e4f9;border-radius:7px;overflow-wrap:anywhere}
.preview-pills{display:flex;gap:6px;flex-wrap:wrap}
.preview-pills span{font-size:12px;color:#326bc4;background:#e9f2ff;padding:4px 8px;border-radius:7px}
.preview-body>p{font-size:13px;line-height:1.75;margin:0;color:#607896;white-space:normal;overflow-wrap:anywhere}
.preview-muted{font-size:12px;color:#93a1b4}
.preview-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:0}
.preview-facts div{padding:9px 10px;background:#f4f8ff;border:1px solid #e2ecf9;border-radius:8px;min-width:0}
.preview-facts dt{font-size:11px;color:#879ab6}.preview-facts dd{font-size:13px;margin:3px 0 0;color:#2b4a75;overflow-wrap:anywhere}
.preview-code-values{display:grid;gap:6px;background:#f6faff;padding:11px;border:1px solid #dae7f9;border-radius:9px}
.preview-code-values b{font-size:12px}.preview-code-values span{display:flex;gap:10px;font-size:12px;color:#526b8d}
.preview-code-values code{font-family:var(--dc-mono);color:#2868c9}
.preview-body footer{display:flex;justify-content:flex-end;gap:8px;border-top:1px solid #e2ecf8;padding-top:11px}
.preview-body footer button{display:flex;align-items:center;gap:6px;border:1px solid #c9dcf7;border-radius:8px;background:#fff;padding:9px 12px;color:#2f68c5;cursor:pointer;font-size:12px;font-weight:720}
.preview-body footer button:last-child{background:#2c6deb;border-color:#2c6deb;color:white}
@media(max-width:600px){.preview-facts{grid-template-columns:1fr}}
</style>
