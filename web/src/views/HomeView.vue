<template>
  <div class="dc-page">
    <div class="dc-container">
      <section class="hero">
        <div class="hero-copy">
          <h1>找到数据，读懂口径，追溯来源</h1>
          <p>搜索数据集、字段、指标、标准与码表，快速定位可用数据资产。</p>
          <div class="hero-search-wrap">
            <div class="hero-search">
              <Search :size="20" />
              <input v-model="keyword" @focus="previewOpen = Boolean(keyword.trim())" @keydown.enter="submit" @keydown.esc="previewOpen=false" placeholder="搜索资产，例如：贷款余额、region_code、dwd_loan_snapshot" />
              <button @click="submit">搜索</button>
            </div>
            <div v-if="previewOpen" class="home-search-results">
              <div v-if="previewLoading" class="preview-empty">正在搜索相关资产…</div>
              <template v-else>
                <section v-for="group in previewGroups" :key="group.type" class="preview-group">
                  <h3>{{group.label}}</h3>
                  <button v-for="item in group.items" :key="item.asset_id" type="button" @click="openPreview(item)">
                    <span>{{item.title}}</span><code>{{item.technical_name}}</code><ArrowRight :size="14"/>
                  </button>
                </section>
                <div v-if="!previewRows.length" class="preview-empty">没有找到匹配资产，按 Enter 查看完整检索结果。</div>
                <button v-if="previewRows.length" class="preview-all" type="button" @click="submit">查看全部检索结果</button>
              </template>
            </div>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const router = useRouter()
const keyword = ref('')
const hot = ['贷款余额', '企业风险', 'region_code', '监管报送']
const recent = ref<any[]>([])
const favorites = ref<any[]>([])
const previewRows = ref<any[]>([])
const previewOpen = ref(false)
const previewLoading = ref(false)
const recentPreview = computed(() => recent.value.slice(0, 5))
const favoritePreview = computed(() => favorites.value.slice(0, 5))
const previewGroups = computed(() => [
  { type: 'TABLE', label: '数据集' },
  { type: 'COLUMN', label: '字段' },
  { type: 'METRIC', label: '指标' },
  { type: 'CODE_TABLE', label: '码表' },
  { type: 'DATA_STANDARD', label: '数据标准' },
  { type: 'WORD_ROOT', label: '词根' },
  { type: 'STAT_SYSTEM', label: '统计制度' },
].map((group) => ({ ...group, items: previewRows.value.filter((item) => item.asset_type === group.type) })).filter((group) => group.items.length))
let searchTimer: number | undefined
let searchSequence = 0

function submit() {
  const value = keyword.value.trim()
  if (value) {
    previewOpen.value = false
    router.push({ name: 'search', query: { q: value } })
  }
}
function quick(value: string) {
  keyword.value = value
  submit()
}
function openPreview(item: any) {
  previewOpen.value = false
  if (item.asset_type === 'TABLE') router.push(`/datasets/${item.asset_id}`)
  else if (item.asset_type === 'COLUMN') router.push(`/fields/${item.asset_id}`)
  else if (item.asset_type === 'METRIC') router.push(`/metrics/${item.technical_name}`)
  else if (item.asset_type === 'CODE_TABLE') router.push(`/code-tables/${item.technical_name}`)
  else if (item.asset_type === 'DATA_STANDARD') router.push(`/standards/${item.technical_name}`)
  else if (item.asset_type === 'WORD_ROOT') router.push(`/word-roots/${item.technical_name}`)
  else if (item.asset_type === 'STAT_SYSTEM') router.push(`/stat-systems/${item.technical_name}`)
  else submit()
}
watch(keyword, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer)
  const query = value.trim()
  const sequence = ++searchSequence
  if (!query) {
    previewRows.value = []
    previewOpen.value = false
    previewLoading.value = false
    return
  }
  previewOpen.value = true
  searchTimer = window.setTimeout(async () => {
    previewLoading.value = true
    try {
      const result = await assetApi.search(query, 6) as any[]
      if (sequence === searchSequence) previewRows.value = result
    } catch {
      if (sequence === searchSequence) previewRows.value = []
    } finally {
      if (sequence === searchSequence) previewLoading.value = false
    }
  }, 180)
})
onBeforeUnmount(() => { if (searchTimer) window.clearTimeout(searchTimer) })
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
.dc-page{padding:18px 0 24px}.hero{position:relative;min-height:240px;overflow:hidden;border:1px solid #d9ebf4;border-radius:26px;background:linear-gradient(135deg,#eef9fd 0%,#fbfdff 58%,#edf8fc 100%);padding:34px 44px;box-shadow:var(--dc-shadow-md)}.hero-copy{position:relative;z-index:2;max-width:820px}.hero h1{font-size:36px;line-height:1.16;letter-spacing:-.04em;margin:8px 0 8px}.hero p{font-size:15px;color:var(--dc-text-2);margin:0}.hero-search-wrap{position:relative;max-width:820px}.hero-search{margin-top:20px;height:54px;display:flex;align-items:center;gap:10px;padding:6px 6px 6px 17px;background:#fff;border:1px solid #cfe4ef;border-radius:15px;box-shadow:0 18px 42px rgba(50,120,157,.12);color:#6b9db6}.hero-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text);font-size:15px}.hero-search button{height:42px;padding:0 27px;border:0;border-radius:11px;background:linear-gradient(135deg,#51add2,#72c8db);color:#fff;font-weight:700;cursor:pointer}.home-search-results{position:absolute;left:0;right:0;top:calc(100% + 8px);z-index:12;padding:10px;background:#fff;border:1px solid #d8e8f1;border-radius:13px;box-shadow:0 18px 42px rgba(50,120,157,.16);max-height:390px;overflow:auto}.preview-group{padding:3px 0 7px}.preview-group h3{margin:7px 9px 5px;font-size:12px;color:var(--dc-text-2)}.preview-group button{width:100%;display:flex;align-items:center;gap:10px;padding:9px;border:0;border-radius:8px;background:#fff;text-align:left;cursor:pointer;color:var(--dc-text)}.preview-group button:hover{background:#f2f9fc}.preview-group button span{flex:1;min-width:0;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.preview-group button code{font-size:12px;color:var(--dc-text-2);max-width:42%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.preview-empty{padding:18px 10px;text-align:center;color:var(--dc-text-2);font-size:12px}.preview-all{width:100%;padding:10px;border:0;border-top:1px solid var(--dc-border);background:#fff;color:var(--dc-primary-strong);font-size:12px;cursor:pointer}.hot{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:8px;font-size:12px;color:#5B6B7A}.hot button{border:0;background:transparent;color:#4e8eab;cursor:pointer;padding:3px 5px}.hero-orbit{position:absolute;right:0;top:0;width:36%;height:100%}.orb{position:absolute;border-radius:50%;filter:blur(2px)}.orb-a{width:220px;height:220px;right:40px;top:34px;background:radial-gradient(circle at 35% 35%,rgba(123,207,226,.38),rgba(109,171,213,.04) 68%)}.orb-b{width:120px;height:120px;right:160px;bottom:22px;background:radial-gradient(circle,rgba(80,167,209,.22),transparent 70%)}.grid-dot{position:absolute;inset:0;background-image:radial-gradient(rgba(69,143,180,.15) 1px,transparent 1px);background-size:18px 18px;mask-image:linear-gradient(to left,#000,transparent)}.home-row{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:16px;margin-top:16px}.recent-panel,.favorite-panel{padding:16px}.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px}.panel-head h2{font-size:18px;margin:0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.recent-grid{display:grid;grid-template-columns:1fr;gap:6px}.recent-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 11px;border:1px solid #e7eff4;border-radius:11px;transition:.16s}.recent-item:hover{border-color:#bfdde9;background:#fbfdff}.recent-item div{min-width:0;display:grid;gap:5px}.recent-item b{font-size:13px}.recent-item code{font-size:12px;color:#5B6B7A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}@media(max-width:1200px){.home-row{grid-template-columns:1fr 1fr}}@media(max-width:760px){.hero{padding:34px 24px;min-height:auto}.hero h1{font-size:32px}.hero-orbit{opacity:.45;width:45%}.home-row{grid-template-columns:1fr}}@media(max-width:520px){.hero-search{height:54px}.hero-search button{height:42px;padding:0 16px}}
</style>
