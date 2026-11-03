<template>
  <div class="dc-page"><div class="dc-container">
    <section v-if="!loggedIn" class="dc-card notice">
      <b>登录后查看个人资产空间</b><RouterLink to="/login">前往登录</RouterLink>
    </section>
    <div class="columns">
      <section class="dc-card panel">
        <div class="panel-title"><b>我的收藏</b><span>{{favorites.length}} 条</span></div>
        <div class="items">
          <RouterLink v-for="item in favoritePage" :key="item.assetId" :to="'/datasets/'+item.assetId" class="item">
            <b>{{item.bizName||item.assetId}}</b><code>{{item.tableName||item.assetId}}</code>
          </RouterLink><div v-if="!favorites.length" class="dc-empty">暂无收藏记录</div>
        </div>
        <Pager v-model:page="fPage" :page-size="8" :total="favorites.length"/>
      </section>
      <section class="dc-card panel">
        <div class="panel-title"><b>最近浏览</b><span>最近 {{recent.length}} 条</span></div>
        <div class="items">
          <RouterLink v-for="item in recentPage" :key="item.assetId+'-'+item.viewedAt" :to="'/datasets/'+item.assetId" class="item">
            <b>{{item.bizName||item.assetId}}</b><code>{{item.tableName||item.assetId}}</code>
          </RouterLink><div v-if="!recent.length" class="dc-empty">暂无浏览记录</div>
        </div>
        <Pager v-model:page="rPage" :page-size="8" :total="recent.length"/>
      </section>
      <section class="dc-card panel">
        <div class="panel-title"><b>检索历史</b><span>最近 {{history.length}} 条</span></div>
        <div class="items">
          <RouterLink v-for="(item,i) in historyPage" :key="item.keyword+'-'+i" :to="{name:'search',query:{q:item.keyword}}" class="item">
            <b>{{item.keyword}}</b><small>{{fmt(item.searchedAt)}}</small>
          </RouterLink><div v-if="!history.length" class="dc-empty">暂无检索记录</div>
        </div>
        <Pager v-model:page="hPage" :page-size="8" :total="history.length"/>
      </section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { activityApi } from '@/api/client'
import Pager from '@/components/Pager.vue'
const loggedIn=ref(Boolean(localStorage.getItem('datacontrol_token')))
const favorites=ref<any[]>([]),recent=ref<any[]>([]),history=ref<any[]>([])
const fPage=ref(1),rPage=ref(1),hPage=ref(1)
const favoritePage=computed(()=>favorites.value.slice((fPage.value-1)*8,fPage.value*8))
const recentPage=computed(()=>recent.value.slice((rPage.value-1)*8,rPage.value*8))
const historyPage=computed(()=>history.value.slice((hPage.value-1)*8,hPage.value*8))
function fmt(v?:string){return v?String(v).replace('T',' ').slice(0,16):'—'}
onMounted(async()=>{
 if(!loggedIn.value)return
 const results=await Promise.allSettled([activityApi.favorites(),activityApi.recent(),activityApi.history()])
 if(results[0].status==='fulfilled')favorites.value=results[0].value as any[]
 if(results[1].status==='fulfilled')recent.value=results[1].value as any[]
 if(results[2].status==='fulfilled')history.value=results[2].value as any[]
})
</script>
<style scoped>
.notice{padding:14px 18px;margin-bottom:12px;display:flex;justify-content:space-between;font-size:13px}
.notice a{color:var(--dc-primary-strong)}
.columns{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.panel{padding:14px;display:flex;flex-direction:column;min-width:0;min-height:430px}
.panel-title{display:flex;justify-content:space-between;align-items:center;padding:2px 0 12px;border-bottom:1px solid var(--dc-border)}
.panel-title b{font-size:14px}.panel-title span{color:var(--dc-text-2);font-size:12px}
.items{flex:1;min-height:0}.item{display:grid;gap:4px;padding:12px 4px;border-bottom:1px solid #edf2f5;min-width:0}
.item:hover{background:#f8fbfd}.item b{font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.item code,.item small{font-size:12px;color:var(--dc-text-2);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
@media(max-width:960px){.columns{grid-template-columns:1fr}.panel{min-height:200px}}
</style>
