<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink to="/" class="brand" aria-label="DataControl 首页">
        <span class="brand-mark">D</span><b>DataControl <small>数据资产平台</small></b>
      </RouterLink>
      <nav class="navigation" aria-label="主导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to"
          class="nav-item" :class="{active:activeSection(item.to)}">
          <component :is="item.icon" :size="18"/><span>{{item.label}}</span>
        </RouterLink>
        <button class="nav-item disabled" disabled title="智能问数将在 P3 接入" aria-label="智能问数，即将上线">
          <Sparkles :size="18"/><span>智能问数</span><small>即将上线</small>
        </button>
      </nav>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <div class="top-left">
          <button class="mobile-menu" aria-label="打开导航" @click="mobileOpen=!mobileOpen"><Menu :size="20"/></button>
          <nav class="breadcrumbs" aria-label="面包屑">
            <RouterLink v-if="parentCrumb" :to="parentCrumb.to">{{parentCrumb.label}}</RouterLink>
            <ChevronRight v-if="parentCrumb" :size="14"/>
            <span>{{ String(route.meta.title || '首页') }}</span>
          </nav>
        </div>
        <button v-if="route.name !== 'home'" class="command-trigger" @click="openCommand">
          <Search :size="16"/><span>{{route.name==='search' && route.query.q ? '检索：'+String(route.query.q) : '搜索数据集、字段、指标、码表…'}}</span>
          <kbd>{{shortcutLabel}} K</kbd>
        </button>
        <div class="account">
          <button class="avatar" aria-label="账户菜单" :aria-expanded="accountOpen" @click="accountOpen=!accountOpen">
            <UserRound :size="18"/>
          </button>
          <div v-if="accountOpen" class="account-menu">
            <RouterLink to="/profile" @click="accountOpen=false">个人中心</RouterLink>
            <RouterLink v-if="!loggedIn" to="/login" @click="accountOpen=false">登录</RouterLink>
            <button v-else @click="logout">退出登录</button>
          </div>
        </div>
      </header>
      <nav v-if="mobileOpen" class="mobile-links" aria-label="移动端导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" @click="mobileOpen=false">{{item.label}}</RouterLink>
        <RouterLink to="/profile" @click="mobileOpen=false">个人中心</RouterLink>
      </nav>
      <main class="main"><RouterView /></main>
    </div>
    <div v-if="commandOpen" class="command-overlay" @click.self="closeCommand" @keydown.esc="closeCommand">
      <section class="command-dialog" role="dialog" aria-modal="true" aria-label="全局资产搜索">
        <div class="command-input">
          <Search :size="18"/>
          <input ref="commandInput" v-model="commandKeyword" placeholder="搜索数据集、字段、指标、码表…"
            @keydown.enter.prevent="submitCommand" @keydown.down.prevent="moveSelection(1)"
            @keydown.up.prevent="moveSelection(-1)" @keydown.esc.prevent="closeCommand"/>
          <button aria-label="关闭搜索" @click="closeCommand"><X :size="17"/></button>
        </div>
        <div class="command-results">
          <p v-if="commandBusy">正在检索…</p>
          <p v-else-if="commandKeyword.trim() && !previews.length">没有找到匹配资产。回车可打开完整检索。</p>
          <p v-else-if="!commandKeyword.trim()">输入关键词，可直接定位数据资产。</p>
          <button v-for="(item,i) in previews" :key="item.asset_id" class="command-item"
            :class="{selected:i===selectedIndex}" @click="openItem(item)">
            <span class="type">{{typeLabel(item.asset_type)}}</span>
            <span class="item-name">{{item.title}}<small>{{item.technical_name}}</small></span>
            <ArrowUpRight :size="15"/>
          </button>
        </div>
        <div class="command-footer"><span>↑ ↓ 选择　Enter 打开　Esc 关闭</span><button @click="submitFullSearch">查看全部结果</button></div>
      </section>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, BarChart3, BookOpenCheck, ChevronRight, CircleGauge, Database, Menu, Search, Sparkles, UserRound, X } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import { typeLabel } from '@/utils/labels'

const route = useRoute()
const router = useRouter()
const navItems = [
  {to:'/', label:'首页',icon:CircleGauge},
  {to:'/catalog',label:'资产目录',icon:Database},
  {to:'/standards',label:'数据标准',icon:BookOpenCheck},
  {to:'/metrics',label:'指标与制度',icon:BookOpenCheck},
  {to:'/overview',label:'数据概览',icon:BarChart3},
]
const commandOpen=ref(false),accountOpen=ref(false),mobileOpen=ref(false)
const loggedIn=ref(Boolean(localStorage.getItem('datacontrol_token')))
const commandKeyword=ref(''),previews=ref<any[]>([]),commandBusy=ref(false),selectedIndex=ref(0)
const commandInput=ref<HTMLInputElement|null>(null)
const shortcutLabel=ref('Ctrl')
let timer: ReturnType<typeof setTimeout> | undefined
let requestId=0
function activeSection(path:string){
  if (path==='/standards') return ['/standards','/code-tables','/word-roots'].some(x=>route.path.startsWith(x))
  if (path==='/metrics') return ['/metrics','/stat-systems'].some(x=>route.path.startsWith(x))
  return path==='/' ? route.path==='/' : route.path.startsWith(path)
}
const parentCrumb=computed(()=>{
  if (route.path.startsWith('/datasets/') || route.path.startsWith('/fields/')) return {label:'资产目录',to:'/catalog'}
  if (['/code-tables','/word-roots','/standards'].some(x=>route.path.startsWith(x)) && route.path.split('/').filter(Boolean).length>1) return {label:'数据标准',to:'/standards'}
  if (['/metrics','/stat-systems'].some(x=>route.path.startsWith(x)) && route.path.split('/').filter(Boolean).length>1) return {label:'指标与制度',to:'/metrics'}
  return null
})
function openCommand(){commandOpen.value=true;accountOpen.value=false;nextTick(()=>commandInput.value?.focus())}
function closeCommand(){commandOpen.value=false;commandKeyword.value='';previews.value=[];requestId++}
function itemUrl(item:any){
  if(item.asset_type==='TABLE')return '/datasets/'+encodeURIComponent(item.asset_id)
  if(item.asset_type==='COLUMN')return '/fields/'+encodeURIComponent(item.asset_id)
  if(item.asset_type==='METRIC')return '/metrics/'+encodeURIComponent(item.technical_name)
  if(item.asset_type==='CODE_TABLE')return '/code-tables/'+encodeURIComponent(item.technical_name)
  return '/search?q='+encodeURIComponent(commandKeyword.value)
}
function openItem(item:any){const url=itemUrl(item);closeCommand();router.push(url)}
function moveSelection(delta:number){selectedIndex.value=Math.min(previews.value.length-1,Math.max(0,selectedIndex.value+delta))}
function submitFullSearch(){const q=commandKeyword.value.trim();if(!q)return;closeCommand();router.push({name:'search',query:{q}})}
function submitCommand(){if(previews.value.length && selectedIndex.value>=0)openItem(previews.value[selectedIndex.value]);else submitFullSearch()}
watch(commandKeyword,()=>{
  if(timer)clearTimeout(timer)
  const q=commandKeyword.value.trim(),index=++requestId
  previews.value=[];selectedIndex.value=0
  if(!q){commandBusy.value=false;return}
  commandBusy.value=true
  timer=setTimeout(async()=>{
    try{const result=await assetApi.searchPage({q,limit:6});if(index===requestId)previews.value=result.items}
    catch{if(index===requestId)previews.value=[]}
    finally{if(index===requestId)commandBusy.value=false}
  },220)
})
function logout(){localStorage.removeItem('datacontrol_token');localStorage.removeItem('datacontrol_user');loggedIn.value=false;accountOpen.value=false;router.push('/login')}
function shortcut(e:KeyboardEvent){
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand()}
  if(e.key==='Escape'){closeCommand();accountOpen.value=false;mobileOpen.value=false}
}
watch(()=>route.fullPath,()=>{mobileOpen.value=false;accountOpen.value=false})
onMounted(()=>{shortcutLabel.value=/Mac|iPhone|iPad/.test(navigator.platform)?'⌘':'Ctrl';window.addEventListener('keydown',shortcut)})
onBeforeUnmount(()=>{window.removeEventListener('keydown',shortcut);if(timer)clearTimeout(timer)})
</script>
<style scoped>
.shell{height:100dvh;display:grid;grid-template-columns:var(--dc-sidebar) minmax(0,1fr);overflow:hidden}
.sidebar{height:100dvh;border-right:1px solid var(--dc-border);padding:14px 10px;background:#f3f8fc;display:flex;flex-direction:column;min-width:0}
.brand{height:48px;display:flex;align-items:center;gap:9px;padding:4px 9px;white-space:nowrap}
.brand-mark{display:grid;place-items:center;width:31px;height:31px;border-radius:8px;background:#1677b3;color:#fff;font-weight:800}
.brand b{font-size:14px}.brand small{display:block;font-weight:400;color:var(--dc-text-2);font-size:12px;margin-top:2px}
.navigation{display:grid;gap:4px;margin-top:14px}
.nav-item{border:0;background:transparent;text-align:left;display:flex;align-items:center;gap:12px;width:100%;min-height:38px;padding:8px 12px;border-radius:6px;color:#425e72;font-size:13px}
.nav-item:hover,.nav-item.active{background:#fff;color:var(--dc-primary-strong)}
.nav-item.active{font-weight:700;box-shadow:inset 3px 0 0 var(--dc-primary)}
.nav-item.disabled{opacity:.58}.nav-item small{margin-left:auto;font-size:11px}
.workspace{min-width:0;display:flex;flex-direction:column;height:100dvh}
.topbar{height:var(--dc-topbar);flex:0 0 var(--dc-topbar);background:#fff;border-bottom:1px solid var(--dc-border);display:flex;align-items:center;gap:12px;padding:0 18px;position:relative;z-index:20}
.top-left{display:flex;align-items:center;min-width:0}.breadcrumbs{display:flex;align-items:center;gap:6px;min-width:0;white-space:nowrap;font-size:13px;font-weight:650}.breadcrumbs a{color:var(--dc-primary-strong)}.breadcrumbs span{overflow:hidden;text-overflow:ellipsis}
.command-trigger{display:flex;align-items:center;gap:9px;width:min(430px,43vw);height:34px;padding:0 10px;margin-left:auto;border:1px solid var(--dc-border-strong);border-radius:6px;background:#f9fcfd;color:#587285;text-align:left;font-size:12px}
.command-trigger span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.command-trigger kbd{margin-left:auto;border:1px solid #dce6ed;border-radius:4px;background:#fff;padding:2px 5px;white-space:nowrap}
.account{position:relative}.avatar{width:33px;height:33px;display:grid;place-items:center;background:#e8f4fa;border:1px solid #cfe3ed;border-radius:50%;color:var(--dc-primary-strong)}
.account-menu{position:absolute;right:0;top:42px;min-width:140px;background:#fff;border:1px solid var(--dc-border);box-shadow:var(--dc-shadow-md);border-radius:8px;padding:6px;display:grid;gap:2px}
.account-menu a,.account-menu button{border:0;background:transparent;text-align:left;padding:9px;color:var(--dc-text);font-size:13px;border-radius:4px}.account-menu a:hover,.account-menu button:hover{background:var(--dc-primary-soft)}
.main{min-height:0;overflow:auto;flex:1;scrollbar-gutter:stable}
.mobile-menu,.mobile-links{display:none}
.command-overlay{position:fixed;inset:0;z-index:90;background:rgba(24,53,74,.33);display:flex;align-items:flex-start;justify-content:center;padding:14vh 16px 0}
.command-dialog{width:min(620px,100%);max-height:75vh;display:flex;flex-direction:column;background:#fff;border:1px solid var(--dc-border);border-radius:10px;box-shadow:0 20px 80px rgba(15,46,66,.22);overflow:hidden}
.command-input{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--dc-border)}
.command-input input{flex:1;min-width:0;border:0;outline:0;font-size:15px}.command-input button{border:0;background:transparent;color:var(--dc-text-2)}
.command-results{min-height:90px;overflow:auto;padding:8px}.command-results>p{color:var(--dc-text-2);font-size:13px;padding:10px}
.command-item{border:0;display:flex;align-items:center;gap:11px;width:100%;text-align:left;background:#fff;border-radius:6px;padding:10px}
.command-item:hover,.command-item.selected{background:#eff7fb}.command-item .type{font-size:12px;color:var(--dc-primary-strong);min-width:43px}
.item-name{flex:1;min-width:0;font-weight:650;font-size:13px;overflow:hidden;text-overflow:ellipsis}.item-name small{display:block;font-size:12px;font-weight:400;color:var(--dc-text-2);overflow:hidden;text-overflow:ellipsis}
.command-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 16px;border-top:1px solid var(--dc-border);font-size:12px;color:var(--dc-text-2)}
.command-footer button{background:none;border:0;color:var(--dc-primary-strong)}
@media(max-width:1080px){.shell{grid-template-columns:56px minmax(0,1fr)}.sidebar{padding:10px 6px}.brand{justify-content:center;padding:0}.brand b,.nav-item span,.nav-item small{display:none}.nav-item{justify-content:center;padding:10px}.command-trigger{width:min(430px,48vw)}}
@media(max-width:820px){.shell{display:block;height:auto;min-height:100dvh;overflow:visible}.sidebar{display:none}.workspace{height:auto;min-height:100dvh}.topbar{position:sticky;top:0}.main{overflow:visible}.mobile-menu{display:grid;place-items:center;border:0;background:none;padding:3px;margin-right:7px}.mobile-links{display:grid;position:fixed;top:52px;left:0;right:0;z-index:19;padding:12px;background:#fff;box-shadow:var(--dc-shadow-md);gap:7px}.mobile-links a{padding:8px;border-radius:6px;background:#f6f9fc}}
@media(max-width:560px){.topbar{padding:0 12px}.command-trigger{width:34px;justify-content:center;margin-left:auto}.command-trigger span,.command-trigger kbd{display:none}.breadcrumbs{font-size:12px}}
</style>
