<template>
  <div class="dc-page home">
    <div class="dc-container">
      <section class="hero">
        <h1>找到数据，读懂口径，追溯来源</h1>
        <p>从业务名称、表名、字段、指标或标准编码开始。</p>
        <div class="search-area">
          <div class="hero-search">
            <Search :size="20"/>
            <input v-model="keyword" placeholder="例如：贷款余额、region_code、dwd_loan_snapshot"
              @keydown.enter="submit" @keydown.esc="previews=[]" aria-label="全局数据资产搜索"/>
            <button @click="submit">搜索</button>
          </div>
          <div v-if="keyword.trim()" class="suggestions">
            <div v-if="loading" class="suggest-empty">正在检索…</div>
            <RouterLink v-for="item in previews" :key="item.asset_id" :to="target(item)" class="suggestion">
              <span>{{typeLabel(item.asset_type)}}</span><b>{{item.title}}</b><code>{{item.technical_name}}</code>
            </RouterLink>
            <div v-if="!loading && !previews.length" class="suggest-empty">暂无预览结果，回车可完整检索。</div>
            <button class="all-results" @click="submit">查看完整检索结果</button>
          </div>
        </div>
        <div class="hot"><span>常用搜索</span><button v-for="x in hot" :key="x" @click="quick(x)">{{x}}</button></div>
      </section>
      <div class="continuation">
        <section class="dc-card panel">
          <div class="panel-head"><h2>最近浏览</h2><RouterLink to="/profile">查看全部</RouterLink></div>
          <div v-if="!loggedIn" class="dc-empty"><RouterLink to="/login">登录后查看最近浏览</RouterLink></div>
          <div v-else-if="!recent.length" class="dc-empty">暂无浏览记录，从资产目录开始探索。</div>
          <RouterLink v-for="item in recent.slice(0,5)" :key="item.assetId" :to="'/datasets/'+item.assetId" class="list-row">
            <LayerTag :layer="item.layerCode"/><span>{{item.bizName||item.assetId}}</span><code>{{item.tableName}}</code>
          </RouterLink>
        </section>
        <section class="dc-card panel">
          <div class="panel-head"><h2>我的收藏</h2><RouterLink to="/profile">查看全部</RouterLink></div>
          <div v-if="!loggedIn" class="dc-empty"><RouterLink to="/login">登录后查看我的收藏</RouterLink></div>
          <div v-else-if="!favorites.length" class="dc-empty">暂无收藏资产。</div>
          <RouterLink v-for="item in favorites.slice(0,5)" :key="item.assetId" :to="'/datasets/'+item.assetId" class="list-row">
            <LayerTag :layer="item.layerCode"/><span>{{item.bizName||item.assetId}}</span><code>{{item.tableName}}</code>
          </RouterLink>
        </section>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { activityApi, assetApi } from '@/api/client'
import LayerTag from '@/components/LayerTag.vue'
import { typeLabel } from '@/utils/labels'
const router=useRouter(),keyword=ref(''),previews=ref<any[]>([]),loading=ref(false),
  recent=ref<any[]>([]),favorites=ref<any[]>([])
const loggedIn=ref(Boolean(localStorage.getItem('datacontrol_token')))
const hot=['贷款余额','企业风险','region_code','监管报送']
let timer:ReturnType<typeof setTimeout>|undefined,seq=0
watch(keyword,()=>{
  if(timer)clearTimeout(timer)
  const q=keyword.value.trim(),id=++seq
  previews.value=[]
  if(!q){loading.value=false;return}
  loading.value=true
  timer=setTimeout(async()=>{
    try{const result=await assetApi.searchPage({q,limit:6});if(id===seq)previews.value=result.items}
    catch{if(id===seq)previews.value=[]}
    finally{if(id===seq)loading.value=false}
  },220)
})
function submit(){const q=keyword.value.trim();if(q)router.push({name:'search',query:{q}})}
function quick(q:string){keyword.value=q;submit()}
function target(item:any){
  const value=encodeURIComponent(item.asset_type==='TABLE'||item.asset_type==='COLUMN'?item.asset_id:item.technical_name)
  if(item.asset_type==='TABLE')return '/datasets/'+value
  if(item.asset_type==='COLUMN')return '/fields/'+value
  if(item.asset_type==='METRIC')return '/metrics/'+value
  if(item.asset_type==='CODE_TABLE')return '/code-tables/'+value
  return '/search?q='+encodeURIComponent(keyword.value)
}
onMounted(async()=>{
  if(!loggedIn.value)return
  const results=await Promise.allSettled([activityApi.recent(),activityApi.favorites()])
  if(results[0].status==='fulfilled')recent.value=results[0].value as any[]
  if(results[1].status==='fulfilled')favorites.value=results[1].value as any[]
})
onBeforeUnmount(()=>{if(timer)clearTimeout(timer)})
</script>
<style scoped>
.home{min-height:100%}.hero{max-width:850px;margin:0 auto;text-align:center;padding:clamp(30px,9vh,100px) 0 40px}
.hero h1{font-size:clamp(24px,3vw,34px);margin:0;color:var(--dc-text);letter-spacing:-.02em}
.hero p{font-size:14px;color:var(--dc-text-2);margin:12px 0 0}
.search-area{position:relative;margin-top:25px;text-align:left;z-index:4}
.hero-search{height:52px;display:flex;align-items:center;gap:12px;padding:5px 6px 5px 15px;background:white;border:1px solid #b9d8e8;border-radius:8px;box-shadow:0 5px 20px rgba(25,102,146,.08);color:var(--dc-primary-strong)}
.hero-search input{flex:1;min-width:0;outline:0;border:0;font-size:14px;color:var(--dc-text)}
.hero-search button{padding:0 22px;height:40px;background:var(--dc-primary);border:0;border-radius:6px;color:#fff}
.suggestions{position:absolute;top:58px;left:0;right:0;padding:7px;border:1px solid var(--dc-border-strong);border-radius:8px;background:#fff;box-shadow:0 16px 35px rgba(28,73,104,.15);max-height:330px;overflow:auto}
.suggestion{display:flex;align-items:center;gap:12px;padding:10px;border-radius:6px;font-size:13px}
.suggestion:hover{background:#eff7fb}.suggestion span{color:var(--dc-primary-strong);font-size:12px;width:40px;flex:0 0 auto}
.suggestion b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.suggestion code{font-size:12px;color:var(--dc-text-2);margin-left:auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.suggest-empty{padding:12px;color:var(--dc-text-2);font-size:13px}
.all-results{border:0;background:#f2f8fb;color:var(--dc-primary-strong);width:100%;text-align:center;padding:9px}
.hot{display:flex;justify-content:center;gap:8px;align-items:center;margin-top:14px;font-size:12px;color:var(--dc-text-2);flex-wrap:wrap}
.hot button{border:1px solid var(--dc-border);border-radius:5px;background:#fff;padding:5px 10px;color:var(--dc-primary-strong)}
.continuation{display:grid;grid-template-columns:1fr 1fr;gap:14px;max-width:1040px;margin:0 auto}
.panel{padding:15px;min-width:0}.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.panel-head h2{font-size:15px;margin:0}.panel-head a{font-size:12px;color:var(--dc-primary-strong)}
.list-row{display:flex;align-items:center;gap:9px;min-height:41px;border-bottom:1px solid #eff2f6;font-size:13px}
.list-row:hover{background:#f7fbfd}.list-row span:not(.layer){overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.list-row code{font-size:11px;color:var(--dc-text-2);margin-left:auto;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
@media(max-width:820px){.hero{padding-top:38px}.continuation{grid-template-columns:1fr}.suggestion code,.list-row code{display:none}}
</style>
