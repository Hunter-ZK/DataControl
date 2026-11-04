<template>
  <div class="dc-page">
    <div class="dc-container">
      <section class="hero">
        <div class="hero-copy">
          <h1>找到数据，读懂口径，追溯来源</h1>
          <p>搜索数据集、字段、指标、标准与码表，快速定位可用数据资产。</p>
          <div class="hero-search">
            <Search :size="20" />
            <input v-model="keyword" @keydown.enter="submit" placeholder="搜索资产，例如：贷款余额、region_code、dwd_loan_snapshot" />
            <button @click="submit">搜索</button>
          </div>
          <div class="hot"><span>热门搜索</span><button v-for="x in hot" :key="x" @click="quick(x)">{{ x }}</button></div>
        </div>
        <div class="hero-orbit" aria-hidden="true"><div class="orb orb-a"/><div class="orb orb-b"/><div class="grid-dot"/></div>
      </section>

      <section class="home-row">
        <div class="dc-card recent-panel">
          <div class="panel-head"><h2>最近浏览</h2><RouterLink to="/profile">查看全部</RouterLink></div>
          <div class="recent-grid" v-if="recentPreview.length">
            <RouterLink v-for="item in recentPreview" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="recent-item">
              <div>
                <span v-if="item.layerCode" class="dc-chip">{{ item.layerCode }}</span>
                <b>{{ item.bizName || item.assetId }}</b>
                <code>{{ item.tableName || item.assetId }}</code>
              </div>
              <ArrowRight :size="17" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无最近浏览记录。</div>
        </div>
        <div class="dc-card favorite-panel">
          <div class="panel-head"><h2>我的收藏</h2><RouterLink to="/profile">查看全部</RouterLink></div>
          <div class="recent-grid" v-if="favoritePreview.length">
            <RouterLink v-for="item in favoritePreview" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="recent-item">
              <div>
                <span v-if="item.layerCode" class="dc-chip">{{ item.layerCode }}</span>
                <b>{{ item.bizName || item.assetId }}</b>
                <code>{{ item.tableName || item.assetId }}</code>
              </div>
              <ArrowRight :size="17" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无收藏记录。</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const router = useRouter()
const keyword = ref('')
const hot = ['贷款余额', '企业风险', 'region_code', '监管报送']
const recent = ref<any[]>([])
const favorites = ref<any[]>([])
const recentPreview = computed(() => recent.value.slice(0, 5))
const favoritePreview = computed(() => favorites.value.slice(0, 5))

function submit() {
  const value = keyword.value.trim()
  if (value) router.push({ name: 'search', query: { q: value } })
}
function quick(value: string) {
  keyword.value = value
  submit()
}
onMounted(async () => {
  const [recentResult, favoriteResult] = await Promise.allSettled([
    activityApi.recent(),
    activityApi.favorites(),
  ])
  if (recentResult.status === 'fulfilled') recent.value = recentResult.value as any[]
  else {
    try { recent.value = (await assetApi.tables({ limit: 5 }) as any[]).slice(0, 5) } catch {}
  }
  if (favoriteResult.status === 'fulfilled') favorites.value = favoriteResult.value as any[]
})
</script>

<style scoped>
.hero{position:relative;min-height:340px;overflow:hidden;border:1px solid #d9ebf4;border-radius:26px;background:linear-gradient(135deg,#eef9fd 0%,#fbfdff 58%,#edf8fc 100%);padding:54px 58px;box-shadow:var(--dc-shadow-md)}.hero-copy{position:relative;z-index:2;max-width:820px}.hero h1{font-size:42px;line-height:1.16;letter-spacing:-.04em;margin:12px 0 10px}.hero p{font-size:15px;color:var(--dc-text-2);margin:0}.hero-search{margin-top:30px;height:60px;display:flex;align-items:center;gap:10px;padding:6px 6px 6px 17px;background:#fff;border:1px solid #cfe4ef;border-radius:15px;box-shadow:0 18px 42px rgba(50,120,157,.12);color:#6b9db6}.hero-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text);font-size:15px}.hero-search button{height:48px;padding:0 27px;border:0;border-radius:11px;background:linear-gradient(135deg,#51add2,#72c8db);color:#fff;font-weight:700;cursor:pointer}.hot{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:12px;font-size:12px;color:#5B6B7A}.hot button{border:0;background:transparent;color:#4e8eab;cursor:pointer;padding:3px 5px}.hero-orbit{position:absolute;right:0;top:0;width:36%;height:100%}.orb{position:absolute;border-radius:50%;filter:blur(2px)}.orb-a{width:220px;height:220px;right:40px;top:34px;background:radial-gradient(circle at 35% 35%,rgba(123,207,226,.38),rgba(109,171,213,.04) 68%)}.orb-b{width:120px;height:120px;right:160px;bottom:22px;background:radial-gradient(circle,rgba(80,167,209,.22),transparent 70%)}.grid-dot{position:absolute;inset:0;background-image:radial-gradient(rgba(69,143,180,.15) 1px,transparent 1px);background-size:18px 18px;mask-image:linear-gradient(to left,#000,transparent)}.home-row{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:18px;margin-top:22px}.recent-panel,.favorite-panel{padding:22px}.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.panel-head h2{font-size:18px;margin:0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.recent-grid{display:grid;grid-template-columns:1fr;gap:9px}.recent-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 14px;border:1px solid #e7eff4;border-radius:11px;transition:.16s}.recent-item:hover{border-color:#bfdde9;background:#fbfdff}.recent-item div{min-width:0;display:grid;gap:5px}.recent-item b{font-size:13px}.recent-item code{font-size:12px;color:#5B6B7A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}@media(max-width:1200px){.home-row{grid-template-columns:1fr 1fr}}@media(max-width:760px){.hero{padding:34px 24px;min-height:auto}.hero h1{font-size:32px}.hero-orbit{opacity:.45;width:45%}.home-row{grid-template-columns:1fr}}@media(max-width:520px){.hero-search{height:54px}.hero-search button{height:42px;padding:0 16px}}
</style>
