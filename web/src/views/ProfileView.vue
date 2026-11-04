<template>
  <div class="dc-page"><div class="dc-container">
    <div v-if="!loggedIn" class="login-tip dc-card">
      <div><b>登录后查看个人资产空间</b><p>开发环境可使用 demo / DataControl123! 体验收藏、浏览和搜索历史。</p></div>
      <RouterLink to="/login">登录</RouterLink>
    </div>
    <div class="profile-grid">
      <section class="dc-card panel">
        <div class="panel-head"><h2>我的收藏</h2><span>{{favorites.length}} 条</span></div>
        <div class="dc-list">
          <RouterLink v-for="item in favoritePage" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="dc-list-item">
            <b>{{item.bizName||item.assetId}}</b><code class="dc-tech">{{item.tableName||item.assetId}}</code>
          </RouterLink>
          <div v-if="!favorites.length" class="dc-empty">暂无收藏。</div>
        </div>
        <Pager v-model:page="favoritePageNo" :page-size="8" :total="favorites.length" />
      </section>
      <section class="dc-card panel">
        <div class="panel-head"><h2>最近浏览</h2><span>{{recent.length}} 条</span></div>
        <div class="dc-list">
          <RouterLink v-for="item in recentPage" :key="`${item.assetId}-${item.viewedAt}`" :to="`/datasets/${item.assetId}`" class="dc-list-item">
            <b>{{item.bizName||item.assetId}}</b><code class="dc-tech">{{item.tableName||item.assetId}}</code><small>{{fmt(item.viewedAt)}}</small>
          </RouterLink>
          <div v-if="!recent.length" class="dc-empty">暂无最近浏览。</div>
        </div>
        <Pager v-model:page="recentPageNo" :page-size="8" :total="recent.length" />
      </section>
      <section class="dc-card panel history">
        <div class="panel-head"><h2>检索历史</h2><span>{{history.length}} 条</span></div>
        <div class="history-wrap">
          <RouterLink v-for="item in historyPage" :key="`${item.keyword}-${item.searchedAt}`" :to="{name:'search',query:{q:item.keyword}}">
            <Search :size="14"/><span>{{item.keyword}}</span><small>{{fmt(item.searchedAt)}}</small>
          </RouterLink>
          <div v-if="!history.length" class="dc-empty">暂无检索历史。</div>
        </div>
        <Pager v-model:page="historyPageNo" :page-size="8" :total="history.length" />
      </section>
    </div>
  </div></div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { activityApi } from '@/api/client'
import Pager from '@/components/Pager.vue'

const favorites = ref<any[]>([])
const recent = ref<any[]>([])
const history = ref<any[]>([])
const loggedIn = ref(Boolean(localStorage.getItem('datacontrol_token')))
const favoritePageNo = ref(1)
const recentPageNo = ref(1)
const historyPageNo = ref(1)
const favoritePage = computed(() => favorites.value.slice((favoritePageNo.value - 1) * 8, favoritePageNo.value * 8))
const recentPage = computed(() => recent.value.slice((recentPageNo.value - 1) * 8, recentPageNo.value * 8))
const historyPage = computed(() => history.value.slice((historyPageNo.value - 1) * 8, historyPageNo.value * 8))
function fmt(value?: string) { return value ? String(value).replace('T', ' ').slice(0, 16) : '—' }
onMounted(async () => {
  if (!loggedIn.value) return
  const results = await Promise.allSettled([activityApi.favorites(), activityApi.recent(), activityApi.history()])
  if (results[0].status === 'fulfilled') favorites.value = results[0].value as any[]
  if (results[1].status === 'fulfilled') recent.value = results[1].value as any[]
  if (results[2].status === 'fulfilled') history.value = results[2].value as any[]
})
</script>
<style scoped>
.login-tip{padding:18px 20px;display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.login-tip b{font-size:14px}.login-tip p{margin:5px 0 0;font-size:12px;color:var(--dc-text-2)}.login-tip a{padding:9px 16px;border-radius:9px;background:var(--dc-primary);color:#fff;font-size:12px}.profile-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.panel{padding:20px;min-width:0}.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.panel-head h2{font-size:17px;margin:0}.panel-head>span{font-size:12px;color:var(--dc-text-2)}.dc-list-item{display:grid;gap:4px}.dc-list-item b{font-size:13px}.dc-list-item code{font-size:12px}.dc-list-item small{font-size:12px;color:var(--dc-text-2)}.history-wrap{display:flex;flex-wrap:wrap;gap:8px}.history-wrap a{display:flex;align-items:center;gap:7px;padding:8px 10px;border:1px solid var(--dc-border);border-radius:999px;background:#fbfdff;font-size:12px}.history-wrap small{color:var(--dc-text-2)}.panel :deep(.pager){margin-top:8px;border-top:1px solid #edf2f5}@media(max-width:1100px){.profile-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.panel.history{grid-column:1/-1}}@media(max-width:820px){.profile-grid{grid-template-columns:1fr}.panel.history{grid-column:auto}.login-tip{align-items:flex-start;flex-direction:column;gap:12px}}
</style>
