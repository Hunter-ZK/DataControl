<template>
  <div class="dc-page">
    <div class="dc-container">
      <section class="hero">
        <div class="hero-copy">
          <h1>找到数据，读懂口径，追溯来源</h1>
          <p>搜索数据集、字段、指标、标准与码表，快速定位可用数据资产。</p>

          <div class="hero-search">
            <Search :size="20" />
            <input
              v-model="keyword"
              @keydown.enter="submit"
              placeholder="搜索资产，例如：贷款余额、region_code、dwd_loan_snapshot"
            />
            <button @click="submit">搜索</button>
          </div>

          <div class="hot">
            <span>热门搜索</span>
            <button v-for="x in hot" :key="x" @click="quick(x)">{{ x }}</button>
          </div>
        </div>
      </section>

      <section class="home-row">
        <div class="dc-card recent-panel">
          <div class="panel-head">
            <h2>最近使用</h2>
            <RouterLink to="/profile">查看全部</RouterLink>
          </div>
          <div v-if="recent.length" class="recent-grid">
            <RouterLink
              v-for="item in recent"
              :key="item.assetId"
              :to="`/datasets/${item.assetId}`"
              class="recent-item"
            >
              <div>
                <span class="dc-chip">{{ item.layerCode || 'TABLE' }}</span>
                <b>{{ item.bizName }}</b>
                <code>{{ item.tableName }}</code>
              </div>
              <ArrowRight :size="17" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无最近浏览，先从资产目录或搜索开始。</div>
        </div>

        <div class="dc-card overview-panel">
          <h2>资产概览</h2>
          <div class="mini-stats">
            <div><strong>{{ format(overview.tableCount) }}</strong><span>数据集</span></div>
            <div><strong>{{ format(overview.columnCount) }}</strong><span>字段</span></div>
            <div><strong>{{ format(overview.metricCount) }}</strong><span>指标</span></div>
            <div><strong>{{ format(overview.codeTableCount) }}</strong><span>码表</span></div>
          </div>
          <RouterLink class="overview-link" to="/overview">
            进入数据概览 <ArrowRight :size="16" />
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const router = useRouter()
const keyword = ref('')
const hot = ['贷款余额', '企业风险', 'region_code', '监管报送']
const overview = reactive({ tableCount: 0, columnCount: 0, metricCount: 0, codeTableCount: 0 })
const recent = ref<any[]>([])

function submit() {
  const value = keyword.value.trim()
  if (value) router.push({ name: 'search', query: { q: value } })
}

function quick(value: string) {
  keyword.value = value
  submit()
}

function format(value: number) {
  return Number(value || 0).toLocaleString()
}

onMounted(async () => {
  try {
    Object.assign(overview, await assetApi.overview())
  } catch {}

  try {
    recent.value = await activityApi.recent() as any[]
  } catch {
    try {
      recent.value = (await assetApi.tables({ limit: 4 }) as any[]).slice(0, 4)
    } catch {}
  }
})
</script>

<style scoped>
.hero{
  position:relative;
  min-height:auto;
  overflow:hidden;
  border:1px solid #dce8ee;
  border-radius:14px;
  background:#fff;
  padding:32px 40px;
  box-shadow:0 8px 24px rgba(38,94,126,.05)
}
.hero-copy{position:relative;z-index:2;max-width:820px}
.hero h1{font-size:34px;line-height:1.18;letter-spacing:-.025em;margin:0 0 10px}
.hero p{font-size:14px;color:var(--dc-text-2);margin:0}
.hero-search{
  margin-top:20px;
  height:54px;
  display:flex;
  align-items:center;
  gap:10px;
  padding:5px 5px 5px 16px;
  background:#fff;
  border:1px solid #cfe3ec;
  border-radius:10px;
  box-shadow:0 8px 24px rgba(50,120,157,.08);
  color:#6b9db6
}
.hero-search:focus-within{border-color:#65aac6;box-shadow:0 0 0 3px rgba(72,157,194,.09)}
.hero-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text);font-size:14px}
.hero-search button{height:42px;padding:0 24px;border:0;border-radius:8px;background:#2787ae;color:#fff;font-weight:700;cursor:pointer}
.hot{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:11px;font-size:11px;color:#89a0af}
.hot button{border:0;background:transparent;color:#4e8eab;cursor:pointer;padding:3px 5px}
.home-row{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(300px,.8fr);gap:18px;margin-top:18px}
.recent-panel,.overview-panel{padding:22px}
.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.panel-head h2,.overview-panel h2{font-size:18px;margin:0}
.panel-head a{font-size:12px;color:var(--dc-primary-strong)}
.recent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.recent-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px;border:1px solid #e7eff4;border-radius:10px}
.recent-item:hover{border-color:#cfe1ea;background:#fbfdfe}
.recent-item div{min-width:0;display:grid;gap:5px}
.recent-item b{font-size:13px}
.recent-item code{font-size:10px;color:#718b9a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}
.mini-stats div{padding:13px;border-radius:10px;background:#f7fbfd;border:1px solid #e5f0f5}
.mini-stats strong{display:block;font-size:22px;color:#276b8e}
.mini-stats span{font-size:11px;color:#8297a5}
.overview-link{margin-top:14px;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dc-primary-strong)}
@media(max-width:1200px){.home-row{grid-template-columns:1fr}}
@media(max-width:760px){
  .hero{padding:30px 24px;min-height:auto}
  .hero h1{font-size:30px}
  .recent-grid{grid-template-columns:1fr}
}
@media(max-width:520px){
  .hero-search{height:50px}
  .hero-search button{height:38px;padding:0 16px}
}
</style>
