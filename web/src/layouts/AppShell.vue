<template>
  <div class="app-shell">
    <header class="top-shell">
      <RouterLink class="brand" to="/" aria-label="DataControl 首页">
        <span class="brand-mark">D</span>
        <span class="brand-copy"><b>DataControl</b><small>数据资产智能工作台</small></span>
      </RouterLink>

      <nav class="nav-capsule" aria-label="主导航">
        <RouterLink to="/" :class="{ active: route.name === 'home' }">首页</RouterLink>
        <RouterLink to="/catalog" :class="{ active: isDataActive }">数据资产</RouterLink>
        <RouterLink to="/relations" :class="{ active: isRelationActive }">关系分析</RouterLink>

        <details class="nav-group" :class="{ active: isStandardActive }">
          <summary>标准规范</summary>
          <div class="nav-menu">
            <RouterLink to="/code-tables"><span>标准与码值</span><small>标准定义、码表与引用</small></RouterLink>
            <RouterLink to="/word-roots"><span>词根索引</span><small>字段命名词根与规范</small></RouterLink>
            <RouterLink to="/metrics"><span>指标与制度</span><small>指标口径与制度依据</small></RouterLink>
          </div>
        </details>

        <RouterLink to="/overview" :class="{ active: route.name === 'overview' }">数据概览</RouterLink>
      </nav>

      <div class="top-actions">
        <button class="search-command" title="全局资产检索" @click="goSearch">
          <Search :size="16" />
          <span>搜索资产</span>
          <kbd>{{ shortcutLabel }}</kbd>
        </button>
        <button class="agent-action" title="回到首页问 DataAgent" @click="goAgent">
          <Sparkles :size="16" />
          <span>问 DataAgent</span>
        </button>
        <RouterLink to="/profile" class="avatar" title="个人中心">H</RouterLink>
      </div>
    </header>

    <main class="workspace">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { Search, Sparkles } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const shortcutLabel = navigator.userAgent.includes('Mac') ? '⌘K' : 'Ctrl K'

const isDataActive = computed(() =>
  route.path === '/catalog' || route.path.startsWith('/datasets/') || route.path.startsWith('/fields/'),
)
const isRelationActive = computed(() => route.path.startsWith('/relations'))
const isStandardActive = computed(() =>
  route.path.startsWith('/code-tables') ||
  route.path.startsWith('/standards') ||
  route.path.startsWith('/word-roots') ||
  route.path.startsWith('/metrics') ||
  route.path.startsWith('/stat-systems'),
)

function goSearch() {
  router.push({ name: 'search' })
}

function goAgent() {
  if (route.name === 'home') {
    document.querySelector<HTMLTextAreaElement>('#home-agent-input')?.focus()
    document.querySelector('#home-agent')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  router.push({ name: 'home', hash: '#home-agent' })
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
.app-shell{min-height:100vh;background:var(--dc-bg)}
.top-shell{
  position:sticky;top:0;z-index:40;height:70px;padding:0 24px;
  display:grid;grid-template-columns:minmax(180px,1fr) auto minmax(300px,1fr);
  align-items:center;gap:18px;background:rgba(255,255,255,.95);
  border-bottom:1px solid var(--dc-border);backdrop-filter:blur(18px)
}
.brand{display:flex;align-items:center;gap:10px;width:max-content}
.brand-mark{
  width:34px;height:34px;border-radius:10px;display:grid;place-items:center;
  background:#0a1019;color:#fff;font-weight:850;box-shadow:0 7px 18px rgba(10,16,25,.13)
}
.brand-copy{display:grid;line-height:1.12}
.brand-copy b{font-size:14px;color:#121721}
.brand-copy small{margin-top:4px;font-size:8px;color:#8c929b}

.nav-capsule{
  display:flex;align-items:center;gap:2px;padding:4px;
  border-radius:999px;background:#0b1018;box-shadow:0 10px 30px rgba(11,16,24,.12)
}
.nav-capsule>a,.nav-group>summary{
  min-height:34px;padding:0 15px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
  color:#a9b0ba;font-size:11px;font-weight:650;white-space:nowrap;cursor:pointer;
  list-style:none;transition:.15s ease
}
.nav-group>summary::-webkit-details-marker{display:none}
.nav-capsule>a:hover,.nav-group>summary:hover{color:#fff}
.nav-capsule>a.active,.nav-group.active>summary{
  background:#f4f4f2;color:#151a21;box-shadow:0 2px 8px rgba(0,0,0,.16)
}
.nav-group{position:relative}
.nav-group[open]>summary{background:#f4f4f2;color:#151a21}
.nav-menu{
  position:absolute;left:50%;top:calc(100% + 10px);transform:translateX(-50%);
  width:250px;padding:8px;border:1px solid #e1e3e7;border-radius:13px;background:#fff;
  box-shadow:0 20px 55px rgba(17,24,39,.16)
}
.nav-menu a{display:grid;gap:3px;padding:11px 12px;border-radius:9px}
.nav-menu a:hover{background:#f4f4f6}
.nav-menu span{font-size:12px;font-weight:700;color:#1b2028}
.nav-menu small{font-size:9px;color:#8b929b}

.top-actions{justify-self:end;display:flex;align-items:center;gap:8px}
.search-command,.agent-action{
  height:36px;border-radius:9px;display:flex;align-items:center;gap:7px;
  padding:0 11px;font-size:10px;font-weight:700;cursor:pointer
}
.search-command{border:1px solid #e0e2e5;background:#f8f8f7;color:#626a74}
.search-command kbd{
  margin-left:3px;padding:2px 5px;border-radius:5px;background:#fff;border:1px solid #e1e3e6;
  color:#989ea6;font-size:8px;font-weight:600
}
.agent-action{
  border:1px solid #dcd5ff;background:var(--dc-ai-soft);color:var(--dc-ai-strong)
}
.agent-action:hover{background:#e7e1ff}
.avatar{
  width:35px;height:35px;border-radius:50%;display:grid;place-items:center;
  background:#eceef1;color:#1e242d;font-size:12px;font-weight:850
}
.workspace{min-width:0}

@media(max-width:1120px){
  .top-shell{grid-template-columns:auto minmax(0,1fr) auto}
  .brand-copy{display:none}
  .nav-capsule{justify-self:center}
  .search-command span,.search-command kbd{display:none}
}
@media(max-width:820px){
  .top-shell{height:auto;min-height:66px;padding:10px 14px;grid-template-columns:auto 1fr auto}
  .nav-capsule{grid-row:2;grid-column:1/-1;justify-self:stretch;overflow:auto;justify-content:flex-start}
  .top-actions{grid-column:3}
  .agent-action span{display:none}
}
@media(max-width:520px){
  .search-command{display:none}
  .nav-capsule>a,.nav-group>summary{padding:0 12px}
}
</style>
