<template>
  <div class="dc-page"><div class="dc-container">
    <section class="dc-page-head"><div><h1 class="dc-title">资产目录</h1><p class="dc-subtitle">按业务主题、数仓层级和关键词浏览在用数据资产。</p></div><div class="dc-toolbar">
  <el-input v-model="keyword" clearable placeholder="搜索数据集" @keyup.enter="load"/>
  <el-select v-model="layerFilter" clearable placeholder="数仓层级" class="catalog-select">
    <el-option v-for="layer in ['ODS','DWD','DWS','ADS','DIM']" :key="layer" :label="layer" :value="layer"/>
  </el-select>
  <el-select v-model="statusFilter" clearable placeholder="资产状态" class="catalog-select">
    <el-option label="在用" value="ONLINE"/><el-option label="已下线" value="OFFLINE"/><el-option label="已废弃" value="DEPRECATED"/>
  </el-select>
  <el-button type="primary" @click="load">查询</el-button>
</div></section>
    <div class="catalog-layout">
      <aside class="dc-card catalog-side"><div class="side-title">业务目录</div><button :class="{active:!selected}" @click="selected=''">全部资产</button><button v-for="c in catalogs" :key="c.code" :class="{active:selected===c.code}" @click="selected=c.code"><span>{{c.name}}</span><small>{{c.code}}</small></button></aside>
      <section class="dc-card asset-list"><div class="list-head"><b>已加载 {{filtered.length}} 个数据集</b><span>可按业务目录、层级和状态筛选</span></div><RouterLink v-for="item in pageRows" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="asset-row"><div class="asset-main"><div class="asset-title"><span class="dc-chip">{{item.layerCode}}</span><b>{{item.bizName}}</b></div><code class="dc-tech">{{item.tableName}}</code><p>{{item.bizDefinition}}</p></div><div class="asset-meta"><span>{{item.techOwner||'未登记'}}</span><span>{{item.updateFreq||'—'}}</span><ArrowRight :size="17"/></div></RouterLink><div v-if="filtered.length===0" class="dc-empty">没有符合条件的数据集。</div>
        <Pager v-model:page="page" :page-size="pageSize" :total="filtered.length"/>
        <p v-if="rows.length===200" class="catalog-limit-note">当前分页仅覆盖接口已返回的前 200 条。完整数据集分页需要后端接口支持。</p>
      </section>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
const keyword=ref(''); const selected=ref(''); const catalogs=ref<any[]>([]); const rows=ref<any[]>([])
const layerFilter=ref('');const statusFilter=ref('');const page=ref(1);const pageSize=10
const filtered=computed(()=>rows.value.filter(x=>(!selected.value||x.catalogCode===selected.value)&&(!layerFilter.value||x.layerCode===layerFilter.value)&&(!statusFilter.value||x.status===statusFilter.value)))
const pageRows=computed(()=>filtered.value.slice((page.value-1)*pageSize,page.value*pageSize))
watch([selected,layerFilter,statusFilter],()=>{page.value=1})
async function load(){page.value=1;rows.value=await assetApi.tables({limit:200,keyword:keyword.value||undefined}) as any[]}
onMounted(async()=>{try{catalogs.value=await assetApi.catalogs() as any[]}catch{};await load()})
</script>

<style scoped>
.dc-toolbar :deep(.el-input){width:260px}.catalog-layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:16px;align-items:start}.catalog-side{padding:14px;position:sticky;top:86px;display:grid;gap:4px}.side-title{font-size:12px;color:#7f95a4;font-weight:700;padding:6px 9px 8px}.catalog-side button{border:0;background:transparent;border-radius:9px;padding:10px;text-align:left;color:#587587;cursor:pointer;display:grid;gap:3px}.catalog-side button small{font-size:12px;color:#9aacb8}.catalog-side button.active,.catalog-side button:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.asset-list{padding:4px 20px 12px;min-width:0}.list-head{height:52px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf2f5}.list-head span{font-size:12px;color:var(--dc-text-3)}.asset-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;padding:18px 3px;border-bottom:1px solid #edf2f5;align-items:center}.asset-row:last-child{border-bottom:0}.asset-main{min-width:0}.asset-title{display:flex;align-items:center;gap:8px}.asset-title b{font-size:15px}.asset-main code{display:block;font-size:12px;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.asset-main p{font-size:12px;color:var(--dc-text-2);margin:8px 0 0;line-height:1.55}.asset-meta{display:flex;align-items:center;gap:14px;color:#7d95a4;font-size:12px}@media(max-width:980px){.catalog-layout{grid-template-columns:1fr}.catalog-side{position:static;display:flex;overflow:auto}.catalog-side .side-title{display:none}.catalog-side button{flex:0 0 auto;min-width:120px}}@media(max-width:700px){.dc-toolbar :deep(.el-input){width:100%}.asset-row{grid-template-columns:1fr}.asset-meta{justify-content:space-between}.list-head{align-items:flex-start;flex-direction:column;height:auto;padding:14px 0;gap:5px}}
.catalog-select{width:132px}.catalog-limit-note{font-size:12px;color:var(--dc-text-2);margin:8px 0 0}@media(max-width:720px){.catalog-select{width:100%}}
</style>
