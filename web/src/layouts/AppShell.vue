<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">D</span>
        <span class="brand-copy"><b>DataControl</b><small>数据资产门户</small></span>
      </RouterLink>

      <nav class="nav">
        <RouterLink
          v-for="item in primary"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isNavActive(item) }"
          :data-tip="item.desc"
        >
          <component :is="item.icon" :size="18" stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>

        <div class="nav-divider" />

        <RouterLink
          v-for="item in reference"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isNavActive(item) }"
          :data-tip="item.desc"
        >
          <component :is="item.icon" :size="18" stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>

        <div class="nav-divider" />

        <RouterLink
          v-for="item in secondary"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isNavActive(item) }"
          :data-tip="item.desc"
        >
          <component :is="item.icon" :size="18" stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <span class="status-dot" />
        <div><b>服务正常</b><small>本地开发环境</small></div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="top-left">
          <button v-if="route.name !== 'home'" class="icon-button" title="返回上一页" @click="goBack()">
            <ArrowLeft :size="18" />
          </button>
          <span class="crumb">{{ route.meta.title || 'DataControl' }}</span>
        </div>

        <button v-if="route.name !== 'home'" class="command" title="打开全局资产检索" @click="goSearch">
          <Search :size="17" />
          <span>搜索数据集、字段、指标、标准…</span>
          <kbd>{{ shortcutLabel }}</kbd>
        </button>

        <div class="top-actions" :class="{ 'home-actions': route.name === 'home' }">
          <RouterLink v-if="route.name !== 'home'" to="/agent" class="soft-action" title="进入智能问数">
            <Sparkles :size="17" />智能问数
          </RouterLink>
          <RouterLink to="/profile" class="avatar" title="个人中心">H</RouterLink>
        </div>
      </header>
      <main><RouterView /></main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  BarChart3,
  BookOpenCheck,
  Boxes,
  CircleGauge,
  Database,
  GitFork,
  Hash,
  Search,
  Sparkles,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const shortcutLabel = navigator.userAgent.includes('Mac') ? '⌘ K' : 'Ctrl K'

const primary = [
  { to: '/', label: '首页', desc: '搜索入口、最近使用和轻量资产概览', icon: CircleGauge },
  { to: '/catalog', label: '数据资产', desc: '按业务主题浏览数据集与字段', icon: Database },
  { to: '/relations', label: '关系分析', desc: '查看上下游血缘、影响分析和关系路径', icon: GitFork },
]

const reference = [
  { to: '/code-tables', label: '标准与码值', desc: '查询码表、数据标准及引用关系', icon: Boxes },
  { to: '/word-roots', label: '词根索引', desc: '查看字段命名词根和规范用法', icon: Hash },
  { to: '/metrics', label: '指标与制度', desc: '查询指标口径、计算规则和制度依据', icon: BookOpenCheck },
]

const secondary = [
  { to: '/overview', label: '数据概览', desc: '查看资产规模、分层分布和近期变化', icon: BarChart3 },
]

function isNavActive(item: { to: string }) {
  const path = route.path
  if (item.to === '/') return route.name === 'home'
  if (item.to === '/catalog') return path === '/catalog' || path.startsWith('/datasets/') || path.startsWith('/fields/')
  if (item.to === '/code-tables') return path.startsWith('/code-tables') || path.startsWith('/standards')
  if (item.to === '/metrics') return path.startsWith('/metrics') || path.startsWith('/stat-systems')
  return path === item.to || path.startsWith(`${item.to}/`)
}

function fallbackRoute() {
  const name = String(route.name || '')
  if (name === 'dataset' || name === 'field') return { name: 'catalog' }
  if (name === 'codeTable') return { name: 'codeTables' }
  if (name === 'standard') return { name: 'standards' }
  if (name === 'wordRoot') return { name: 'wordRoots' }
  if (name === 'metric') return { name: 'metrics' }
  if (name === 'statSystem') return { name: 'statSystems' }
  return { name: 'home' }
}

function goBack() {
  const previous = window.history.state?.back
  if (typeof previous === 'string' && previous.startsWith('/')) {
    router.back()
    return
  }
  router.push(fallbackRoute())
}

function goSearch() {
  router.push({ name: 'search' })
}

function shortcut(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    goSearch()
  }
}

onMounted(() => window.addEventListener('keydown', shortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>

<style scoped>
.shell{min-height:100vh;display:grid;grid-template-columns:var(--dc-sidebar) minmax(0,1fr)}
.sidebar{position:sticky;top:0;height:100vh;padding:20px 14px 16px;background:#fff;border-right:1px solid var(--dc-border);display:flex;flex-direction:column;z-index:20;overflow:visible}
.brand{height:52px;padding:4px 8px;display:flex;align-items:center;gap:10px}
.brand-mark{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:#0b1320;color:#fff;font-weight:800;box-shadow:0 8px 20px rgba(11,19,32,.12)}
.brand-copy{display:grid;line-height:1.15}
.brand-copy b{font-size:15px}
.brand-copy small{font-size:9px;margin-top:4px;color:#8a9098}
.nav{margin-top:16px;display:grid;gap:4px;overflow:visible}
.nav-item{position:relative;display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:9px;color:#626a74;font-size:13px;transition:.16s ease}
.nav-item:hover{background:#f3f4f6;color:#151a22}
.nav-item.active,.nav-item.router-link-exact-active{background:#0b1320;color:#fff;font-weight:700;box-shadow:0 7px 18px rgba(11,19,32,.12)}
.nav-divider{height:1px;background:#eceef0;margin:9px 8px}
.nav-item::after{content:attr(data-tip);position:absolute;left:calc(100% + 12px);top:50%;transform:translateY(-50%) translateX(-4px);width:max-content;max-width:250px;padding:8px 10px;border-radius:8px;background:#0b1320;color:#fff;font-size:11px;font-weight:400;line-height:1.5;white-space:normal;box-shadow:0 10px 28px rgba(20,55,72,.18);opacity:0;visibility:hidden;pointer-events:none;transition:.15s ease;z-index:100}
.nav-item:hover::after{opacity:1;visibility:visible;transform:translateY(-50%) translateX(0)}
.sidebar-foot{margin-top:auto;padding:12px;display:flex;gap:9px;align-items:center;border-top:1px solid #eceef0}
.status-dot{width:8px;height:8px;border-radius:50%;background:#43a87e;box-shadow:0 0 0 4px rgba(67,168,126,.1)}
.sidebar-foot div{display:grid}
.sidebar-foot b{font-size:11px}
.sidebar-foot small{font-size:9px;color:#86a0af;margin-top:2px}
.workspace{min-width:0}
.topbar{position:sticky;top:0;height:var(--dc-topbar);padding:0 24px;display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.94);border-bottom:1px solid var(--dc-border);backdrop-filter:blur(18px);z-index:15}
.top-left{display:flex;align-items:center;gap:9px;min-width:160px}
.crumb{font-size:13px;font-weight:700}
.icon-button{width:32px;height:32px;border:1px solid var(--dc-border);background:#fff;border-radius:8px;color:#616975;display:grid;place-items:center;cursor:pointer}
.command{margin-left:auto;width:min(430px,38vw);height:38px;border:1px solid #e0e3e6;border-radius:10px;background:#f7f7f5;color:#777f89;display:flex;align-items:center;gap:9px;padding:0 12px;cursor:pointer}
.command span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.command kbd{margin-left:auto;padding:2px 6px;border-radius:6px;background:#fff;border:1px solid #dce8ef;color:#78909e;font-size:10px}
.top-actions{display:flex;align-items:center;gap:9px}
.top-actions.home-actions{margin-left:auto}
.soft-action{display:flex;align-items:center;gap:6px;font-size:12px;color:#fff;background:#0b1320;padding:8px 11px;border-radius:9px}
.avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#eceef1;color:#202630;font-weight:800}
@media(max-width:1080px){
  .shell{grid-template-columns:78px minmax(0,1fr)}
  .sidebar{padding:18px 10px}
  .brand-copy,.nav-item span,.sidebar-foot div{display:none}
  .brand{justify-content:center;padding:0}
  .nav-item{justify-content:center;padding:11px}
  .nav-item::after{left:calc(100% + 10px)}
  .sidebar-foot{justify-content:center}
  .top-left{min-width:auto}
  .command{width:min(420px,48vw)}
}
@media(max-width:820px){
  .shell{display:block}
  .sidebar{display:none}
  .topbar{padding:0 14px}
  .command{width:auto;flex:1}
  .top-actions .soft-action{display:none}
}
@media(max-width:560px){
  .command span,.command kbd{display:none}
  .command{flex:0 0 40px;padding:0;justify-content:center}
  .crumb{max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
}
</style>
