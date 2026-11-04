<template>
  <div class="dc-page">
    <div class="dc-container">
      <section class="hero" :class="{'hero-preview-open': previewOpen}">
        <div class="hero-copy">
          
          <h1>找到数据，读懂口径，追溯来源</h1>
          <p>搜索数据集、字段、指标、标准与码表，快速定位可用数据资产。</p>
          <div class="hero-search-wrap">
            <div class="hero-search">
              <Search :size="20" />
              <input v-model="keyword" @focus="previewOpen=Boolean(keyword.trim())" @keydown.enter="submit" @keydown.esc="previewOpen=false" placeholder="搜索资产，例如：贷款余额、region_code、dwd_loan_snapshot" />
              <button @click="submit">搜索</button>
            </div>
            <div v-if="previewOpen" class="hero-preview">
              <div v-if="previewLoading" class="preview-hint">正在查找相关资产…</div>
              <template v-else>
                <section v-for="group in previewGroups" :key="group.type" class="preview-group">
                  <b>{{group.label}}</b>
                  <button v-for="item in group.items" :key="item.asset_id" type="button" @click="openPreview(item)">
                    <span>{{item.title}}</span><code>{{item.technical_name}}</code><ArrowRight :size="14"/>
                  </button>
                </section>
                <div v-if="!previewRows.length" class="preview-hint">暂无建议，按 Enter 查看完整检索页。</div>
                <button v-else type="button" class="preview-all" @click="submit">查看全部结果</button>
              </template>
            </div>
          </div>
          <div class="hot"><span>热门搜索</span><button v-for="x in hot" :key="x" @click="quick(x)">{{ x }}</button></div>
        </div>
        <div class="hero-orbit" aria-hidden="true"><div class="orb orb-a"/><div class="orb orb-b"/><div class="grid-dot"/></div>
      </section>

      <section class="launch-grid">
        <RouterLink v-for="item in launchers" :key="item.to" :to="item.to" class="launch-card">
          <span class="launch-icon"><component :is="item.icon" :size="21" stroke-width="1.8" /></span>
          <div><b>{{ item.title }}</b><p>{{ item.desc }}</p></div>
          <ArrowUpRight :size="17" class="launch-arrow" />
        </RouterLink>
      </section>

      <section class="home-row">
        <div class="dc-card recent-panel">
          <div class="panel-head"><div><h2>最近使用</h2></div><RouterLink to="/profile">查看全部</RouterLink></div>
          <div class="recent-grid" v-if="recent.length">
            <RouterLink v-for="item in recent" :key="item.assetId" :to="`/datasets/${item.assetId}`" class="recent-item">
              <div><span v-if="item.layerCode" class="dc-chip">{{item.layerCode}}</span><b>{{ item.bizName }}</b><code>{{ item.tableName }}</code></div>
              <ArrowRight :size="17" />
            </RouterLink>
          </div>
          <div v-else class="dc-empty">暂无最近浏览，先从资产目录或搜索开始。</div>
        </div>
        <div class="dc-card overview-panel">
          <h2>资产概览</h2>
          <div class="mini-stats"><div><strong>{{ format(overview.tableCount) }}</strong><span>数据集</span></div><div><strong>{{ format(overview.columnCount) }}</strong><span>字段</span></div><div><strong>{{ format(overview.metricCount) }}</strong><span>指标</span></div><div><strong>{{ format(overview.codeTableCount) }}</strong><span>码表</span></div></div>
          <RouterLink class="overview-link" to="/overview">进入数据概览 <ArrowRight :size="16" /></RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, ArrowUpRight, BookOpenCheck, Boxes, Database, Hash, Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'

const router = useRouter(); const keyword = ref(''); const hot = ['贷款余额','企业风险','region_code','监管报送']
const overview = reactive({ tableCount: 0, columnCount: 0, metricCount: 0, codeTableCount: 0 })
const recent = ref<any[]>([])
const launchers = [
  { to:'/catalog', title:'资产目录', desc:'按业务主题浏览数据集与字段', icon:Database },
  { to:'/code-tables', title:'标准码值', desc:'查询标准码表、数据标准与引用', icon:Boxes },
  { to:'/word-roots', title:'词根索引', desc:'查看字段命名词根与规范用法', icon:Hash },
  { to:'/metrics', title:'指标与制度', desc:'查询指标口径与制度依据', icon:BookOpenCheck },
]
const previewRows = ref<any[]>([])
const previewOpen = ref(false)
const previewLoading = ref(false)
let previewTimer: number | undefined
let requestId = 0
const previewGroups = computed(() => [
  {type:'TABLE',label:'数据集'}, {type:'COLUMN',label:'字段'}, {type:'METRIC',label:'指标'},
  {type:'CODE_TABLE',label:'码表'},
].map(g => ({...g,items:previewRows.value.filter((v) => v.asset_type===g.type)})).filter(g=>g.items.length))

function submit(){ const q=keyword.value.trim(); if(q){previewOpen.value=false;router.push({name:'search',query:{q}})} }
function openPreview(item:any){
  previewOpen.value=false
  if(item.asset_type==='TABLE')router.push(`/datasets/${item.asset_id}`)
  else if(item.asset_type==='COLUMN')router.push(`/fields/${item.asset_id}`)
  else if(item.asset_type==='METRIC')router.push(`/metrics/${item.technical_name}`)
  else if(item.asset_type==='CODE_TABLE')router.push(`/code-tables/${item.technical_name}`)
  else submit()
}
watch(keyword,(value)=>{
  if(previewTimer!==undefined)window.clearTimeout(previewTimer)
  const q=value.trim(); const id=++requestId
  previewRows.value=[]
  if(!q){previewOpen.value=false;previewLoading.value=false;return}
  previewOpen.value=true;previewLoading.value=true
  previewTimer=window.setTimeout(async()=>{
    try{const v=await assetApi.search(q,6) as any[];if(id===requestId)previewRows.value=v}
    catch{if(id===requestId)previewRows.value=[]}
    finally{if(id===requestId)previewLoading.value=false}
  },200)
})
onBeforeUnmount(()=>{if(previewTimer!==undefined)window.clearTimeout(previewTimer)})
function quick(value:string){ keyword.value=value; submit() }
function format(v:number){ return Number(v||0).toLocaleString() }
onMounted(async()=>{
  try { Object.assign(overview, await assetApi.overview()) } catch {}
  try { recent.value = await activityApi.recent() as any[] } catch {
    try { recent.value = (await assetApi.tables({limit:4}) as any[]).slice(0,4) } catch {}
  }
})
</script>

<style scoped>
.hero{position:relative;min-height:340px;overflow:hidden;border:1px solid #d9ebf4;border-radius:26px;background:linear-gradient(135deg,#eef9fd 0%,#fbfdff 58%,#edf8fc 100%);padding:54px 58px;box-shadow:var(--dc-shadow-md)}.hero.hero-preview-open{overflow:visible}.hero-copy{position:relative;z-index:2;max-width:820px}.hero h1{font-size:42px;line-height:1.16;letter-spacing:-.04em;margin:12px 0 10px}.hero p{font-size:15px;color:var(--dc-text-2);margin:0}.hero-search{margin-top:30px;height:60px;display:flex;align-items:center;gap:10px;padding:6px 6px 6px 17px;background:#fff;border:1px solid #cfe4ef;border-radius:15px;box-shadow:0 18px 42px rgba(50,120,157,.12);color:#6b9db6}.hero-search input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--dc-text);font-size:15px}.hero-search button{height:48px;padding:0 27px;border:0;border-radius:11px;background:linear-gradient(135deg,#51add2,#72c8db);color:#fff;font-weight:700;cursor:pointer}.hot{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:12px;font-size:12px;color:#89a0af}.hot button{border:0;background:transparent;color:#4e8eab;cursor:pointer;padding:3px 5px}.hero-orbit{position:absolute;right:0;top:0;width:36%;height:100%}.orb{position:absolute;border-radius:50%;filter:blur(2px)}.orb-a{width:220px;height:220px;right:40px;top:34px;background:radial-gradient(circle at 35% 35%,rgba(123,207,226,.38),rgba(109,171,213,.04) 68%)}.orb-b{width:120px;height:120px;right:160px;bottom:22px;background:radial-gradient(circle,rgba(80,167,209,.22),transparent 70%)}.grid-dot{position:absolute;inset:0;background-image:radial-gradient(rgba(69,143,180,.15) 1px,transparent 1px);background-size:18px 18px;mask-image:linear-gradient(to left,#000,transparent)}.launch-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px;margin-top:20px}.launch-card{position:relative;min-height:116px;padding:18px 17px;display:flex;align-items:flex-start;gap:12px;border:1px solid var(--dc-border);border-radius:15px;background:#fff;box-shadow:0 8px 24px rgba(44,109,142,.04);transition:.18s}.launch-card:hover{transform:translateY(-2px);border-color:#bfdde9;box-shadow:0 14px 32px rgba(44,109,142,.08)}.launch-icon{flex:0 0 42px;height:42px;border-radius:12px;display:grid;place-items:center;background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.launch-card b{font-size:14px}.launch-card p{margin:7px 0 0;font-size:11px;line-height:1.55;color:var(--dc-text-2)}.launch-arrow{position:absolute;right:13px;top:13px;color:#9aafbc}.home-row{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(300px,.8fr);gap:18px;margin-top:22px}.recent-panel,.overview-panel{padding:22px}.panel-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px}.panel-head h2,.overview-panel h2{font-size:18px;margin:5px 0 0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}.recent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.recent-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px;border:1px solid #e7eff4;border-radius:11px}.recent-item div{min-width:0;display:grid;gap:5px}.recent-item b{font-size:13px}.recent-item code{font-size:10px;color:#718b9a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}.mini-stats div{padding:13px;border-radius:11px;background:#f7fbfd;border:1px solid #e5f0f5}.mini-stats strong{display:block;font-size:22px;color:#276b8e}.mini-stats span{font-size:11px;color:#8297a5}.overview-link{margin-top:14px;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dc-primary-strong)}@media(max-width:1200px){.launch-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.home-row{grid-template-columns:1fr}}@media(max-width:760px){.hero{padding:34px 24px;min-height:auto}.hero h1{font-size:32px}.hero-orbit{opacity:.45;width:45%}.launch-grid{grid-template-columns:1fr 1fr}.recent-grid{grid-template-columns:1fr}}@media(max-width:520px){.hero-search{height:54px}.hero-search button{height:42px;padding:0 16px}.launch-grid{grid-template-columns:1fr}}
.hero-search-wrap{position:relative}.hero-preview{position:absolute;top:calc(100% + 8px);left:0;right:0;z-index:12;max-height:310px;overflow:auto;padding:8px 10px;border:1px solid #cfe4ef;border-radius:12px;background:#fff;box-shadow:0 18px 42px rgba(50,120,157,.14)}.preview-group{padding:7px 0}.preview-group>b{display:block;padding:5px 8px;color:var(--dc-text-2);font-size:12px}.preview-group button{width:100%;display:flex;align-items:center;gap:10px;padding:9px 8px;border:0;border-radius:8px;background:transparent;text-align:left;color:var(--dc-text);cursor:pointer}.preview-group button:hover{background:#f2f9fc}.preview-group button span{flex:1;min-width:0;font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.preview-group button code{max-width:45%;font-size:12px;color:var(--dc-text-2);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.preview-hint{padding:16px;text-align:center;font-size:12px;color:var(--dc-text-2)}.preview-all{width:100%;padding:9px;border:0;border-top:1px solid var(--dc-border);background:transparent;color:var(--dc-primary-strong);cursor:pointer;font-size:12px}
</style>
