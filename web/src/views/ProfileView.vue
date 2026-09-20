<template>
  <div class="dc-page"><div class="dc-container">
    <section class="dc-page-head"><div><span class="dc-eyebrow">MY SPACE</span><h1 class="dc-title">个人中心</h1><p class="dc-subtitle">查看收藏、最近浏览和检索历史。</p></div></section>
    <div v-if="!loggedIn" class="login-tip dc-card"><div><b>登录后查看个人资产空间</b><p>开发环境可使用 demo / DataControl123! 体验收藏、浏览和搜索历史。</p></div><RouterLink to="/login">登录</RouterLink></div>
    <div class="profile-grid">
      <section class="dc-card panel"><div class="panel-head"><div><span class="dc-eyebrow">FAVORITES</span><h2>我的收藏</h2></div><span>{{favorites.length}}</span></div><div class="dc-list"><RouterLink v-for="x in favorites" :key="x.assetId" :to="`/datasets/${x.assetId}`" class="dc-list-item"><b>{{x.bizName||x.assetId}}</b><code class="dc-tech">{{x.tableName||x.assetId}}</code></RouterLink><div v-if="!favorites.length" class="dc-empty">暂无收藏。</div></div></section>
      <section class="dc-card panel"><div class="panel-head"><div><span class="dc-eyebrow">RECENT</span><h2>最近浏览</h2></div><span>{{recent.length}}</span></div><div class="dc-list"><RouterLink v-for="x in recent" :key="`${x.assetId}-${x.viewedAt}`" :to="`/datasets/${x.assetId}`" class="dc-list-item"><b>{{x.bizName||x.assetId}}</b><code class="dc-tech">{{x.tableName||x.assetId}}</code><small>{{fmt(x.viewedAt)}}</small></RouterLink><div v-if="!recent.length" class="dc-empty">暂无最近浏览。</div></div></section>
      <section class="dc-card panel history"><div class="panel-head"><div><span class="dc-eyebrow">SEARCH HISTORY</span><h2>检索历史</h2></div><span>{{history.length}}</span></div><div class="history-wrap"><RouterLink v-for="x in history" :key="`${x.keyword}-${x.searchedAt}`" :to="{name:'search',query:{q:x.keyword}}"><Search :size="14"/><span>{{x.keyword}}</span><small>{{fmt(x.searchedAt)}}</small></RouterLink><div v-if="!history.length" class="dc-empty">暂无搜索历史。</div></div></section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { activityApi } from '@/api/client'
const favorites=ref<any[]>([]); const recent=ref<any[]>([]); const history=ref<any[]>([]); const loggedIn=ref(Boolean(localStorage.getItem('datacontrol_token')))
function fmt(v?:string){return v?String(v).replace('T',' ').slice(0,16):'—'}
onMounted(async()=>{if(!loggedIn.value)return;const results=await Promise.allSettled([activityApi.favorites(),activityApi.recent(),activityApi.history()]);if(results[0].status==='fulfilled')favorites.value=results[0].value as any[];if(results[1].status==='fulfilled')recent.value=results[1].value as any[];if(results[2].status==='fulfilled')history.value=results[2].value as any[]})
</script>
<style scoped>
.login-tip{padding:18px 20px;display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.login-tip b{font-size:14px}.login-tip p{margin:5px 0 0;font-size:11px;color:var(--dc-text-2)}.login-tip a{padding:9px 16px;border-radius:9px;background:var(--dc-primary);color:#fff;font-size:12px}.profile-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{padding:20px}.panel.history{grid-column:1/-1}.panel-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:14px}.panel-head h2{font-size:17px;margin:5px 0 0}.panel-head>span{font-size:11px;color:var(--dc-text-3)}.dc-list-item{display:grid;gap:4px}.dc-list-item b{font-size:13px}.dc-list-item code{font-size:10px}.dc-list-item small{font-size:9px;color:var(--dc-text-3)}.history-wrap{display:flex;flex-wrap:wrap;gap:8px}.history-wrap a{display:flex;align-items:center;gap:7px;padding:8px 10px;border:1px solid var(--dc-border);border-radius:999px;background:#fbfdff;font-size:11px}.history-wrap small{color:var(--dc-text-3)}@media(max-width:820px){.profile-grid{grid-template-columns:1fr}.panel.history{grid-column:auto}.login-tip{align-items:flex-start;flex-direction:column;gap:12px}}
</style>
