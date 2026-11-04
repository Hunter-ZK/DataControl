<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">D</span>
        <span class="brand-copy"><b>DataControl</b></span>
      </RouterLink>

      <nav class="nav">
        <template v-for="item in primary" :key="item.label">
          <RouterLink v-if="!item.disabled" :to="item.to" class="nav-item" :class="{ 'nav-item-active': isActive(item) }">
            <component :is="item.icon" :size="18" stroke-width="1.8" />
            <span>{{ item.label }}</span>
          </RouterLink>
          <button v-else type="button" class="nav-item nav-disabled" disabled title="P3 阶段开放">
            <component :is="item.icon" :size="18" stroke-width="1.8" />
            <span>{{ item.label }}</span>
            <small>即将上线</small>
          </button>
        </template>
      </nav>

      <div class="sidebar-foot">
        <span class="status-dot" />
        <div><b>服务正常</b></div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="top-left">
          <nav class="breadcrumbs" aria-label="当前位置">
            <template v-for="(item, i) in breadcrumbs" :key="item.label">
              <RouterLink v-if="item.to && i !== breadcrumbs.length - 1" :to="item.to">{{ item.label }}</RouterLink>
              <span v-else class="crumb">{{ item.label }}</span>
              <span v-if="i !== breadcrumbs.length - 1" class="breadcrumb-divider">/</span>
            </template>
          </nav>
        </div>
        <button v-if="route.name !== 'home'" type="button" class="command" @click="openCommand">
          <Search :size="17" /><span>搜索数据资产…</span><kbd>{{ shortcut }}</kbd>
        </button>
        <div class="top-actions">
          <div class="account-wrap">
            <button type="button" class="avatar" aria-label="账户菜单" :aria-expanded="accountOpen" @click="accountOpen=!accountOpen">H</button>
            <div v-if="accountOpen" class="account-menu">
              <RouterLink to="/profile" @click="accountOpen=false"><UserRound :size="15" />个人中心</RouterLink>
              <button type="button" @click="logout"><LogOut :size="15" />退出登录</button>
            </div>
          </div>
        </div>
      </header>
      <main><RouterView /></main>
    </div>
  </div>

  <div v-if="commandOpen" class="search-overlay" @click.self="closeCommand">
    <section class="search-dialog" role="dialog" aria-modal="true" aria-label="全局资产搜索">
      <div class="search-dialog-input">
        <Search :size="18" />
        <input ref="commandInput" v-model="commandQuery" placeholder="搜索数据集、字段、指标、码表…" @keydown.enter="submitCommand" @keydown.arrow-down.prevent="moveSelection(1)" @keydown.arrow-up.prevent="moveSelection(-1)" @keydown.esc="closeCommand" />
        <kbd>Esc</kbd>
      </div>
      <div class="search-dialog-list">
        <div v-if="searching" class="search-dialog-hint">正在搜索…</div>
        <button v-for="(item, index) in commandResults" :key="item.asset_id" type="button" class="search-dialog-result" :class="{ selected: index===selectedIndex }" @mouseenter="selectedIndex=index" @click="openResult(item)">
          <span class="dc-chip">{{ assetTypeLabel(item.asset_type) }}</span>
          <span class="search-dialog-result-text"><b>{{ item.title }}</b><code>{{ item.technical_name }}</code></span>
          <ArrowRight :size="15" />
        </button>
        <div v-if="!searching && !commandResults.length" class="search-dialog-hint">{{commandQuery.trim() ? '没有匹配的建议，可查看完整检索结果' : '输入关键词，查找数据资产'}}</div>
      </div>
      <div class="search-dialog-footer">
        <span>↑ ↓ 选择 · Enter 打开 · Esc 关闭</span>
        <button type="button" :disabled="!commandQuery.trim()" @click="openFullSearch">查看全部结果</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ArrowRight, BarChart3, BookOpenCheck, Boxes, CircleGauge, Database, LogOut, Search, Sparkles, UserRound } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import { assetTypeLabel } from '@/utils/labels'

type NavItem = { to: string; label: string; icon: any; matches: string[]; disabled?: boolean }
const router = useRouter()
const route = useRoute()
const primary: NavItem[] = [
  { to: '/', label: '首页', icon: CircleGauge, matches: ['/'] },
  { to: '/catalog', label: '资产目录', icon: Database, matches: ['/catalog','/datasets','/fields'] },
  { to: '/standards', label: '数据标准', icon: Boxes, matches: ['/standards','/code-tables','/word-roots'] },
  { to: '/metrics', label: '指标与制度', icon: BookOpenCheck, matches: ['/metrics','/stat-systems'] },
  { to: '#', label: '智能问数', icon: Sparkles, matches: [], disabled: true },
  { to: '/overview', label: '数据概览', icon: BarChart3, matches: ['/overview'] },
]
const accountOpen = ref(false)
const commandOpen = ref(false)
const commandQuery = ref('')
const commandResults = ref<any[]>([])
const selectedIndex = ref(0)
const searching = ref(false)
const commandInput = ref<HTMLInputElement | null>(null)
const isMac = ref(false)
const shortcut = computed(() => isMac.value ? '⌘ K' : 'Ctrl K')
const breadcrumbs = computed(() => {
  const path = route.path
  const title = String(route.meta.title || 'DataControl')
  if (path.startsWith('/datasets/') || path.startsWith('/fields/')) return [{label:'资产目录',to:'/catalog'},{label:title}]
  if (path.startsWith('/code-tables/') || path.startsWith('/standards/')) return [{label:'数据标准',to:'/standards'},{label:title}]
  if (path.startsWith('/word-roots/')) return [{label:'数据标准',to:'/standards'},{label:title}]
  if (path.startsWith('/metrics/') || path.startsWith('/stat-systems/')) return [{label:'指标与制度',to:'/metrics'},{label:title}]
  return [{label:title}]
})
let timer: number | undefined
let requestId = 0

function isActive(item: NavItem) {
  return item.matches.includes(route.path) || item.matches.some((x) => x !== '/' && route.path.startsWith(x + '/'))
}
function openCommand() {
  accountOpen.value = false
  commandOpen.value = true
  nextTick(() => commandInput.value?.focus())
}
function closeCommand() {
  commandOpen.value = false
  commandQuery.value = ''
  commandResults.value = []
}
function moveSelection(step: number) {
  if (!commandResults.value.length) return
  selectedIndex.value = Math.max(0, Math.min(commandResults.value.length - 1, selectedIndex.value + step))
}
function openResult(item: any) {
  const q = commandQuery.value.trim()
  closeCommand()
  const type = item.asset_type
  if (type === 'TABLE') router.push(`/datasets/${item.asset_id}`)
  else if (type === 'COLUMN') router.push(`/fields/${item.asset_id}`)
  else if (type === 'CODE_TABLE') router.push(`/code-tables/${item.technical_name}`)
  else if (type === 'DATA_STANDARD') router.push(`/standards/${item.technical_name}`)
  else if (type === 'WORD_ROOT') router.push(`/word-roots/${item.technical_name}`)
  else if (type === 'METRIC') router.push(`/metrics/${item.technical_name}`)
  else if (type === 'STAT_SYSTEM') router.push(`/stat-systems/${item.technical_name}`)
  else router.push({name:'search',query:{q}})
}
function openFullSearch() {
  const q = commandQuery.value.trim()
  if (!q) return
  closeCommand()
  router.push({name:'search',query:{q}})
}
function submitCommand() {
  if (commandResults.value.length) openResult(commandResults.value[selectedIndex.value] || commandResults.value[0])
  else openFullSearch()
}
function logout() {
  accountOpen.value = false
  localStorage.removeItem('datacontrol_token')
  localStorage.removeItem('datacontrol_user')
  router.push('/login')
}
function keydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openCommand()
  }
  if (event.key === 'Escape') { closeCommand(); accountOpen.value = false }
}
watch(commandQuery, (v) => {
  if (timer !== undefined) window.clearTimeout(timer)
  const q = v.trim()
  const id = ++requestId
  commandResults.value = []
  selectedIndex.value = 0
  if (!q) { searching.value = false; return }
  searching.value = true
  timer = window.setTimeout(async () => {
    try { const results = await assetApi.search(q, 6) as any[]; if (id === requestId) commandResults.value = results }
    catch { if (id === requestId) commandResults.value = [] }
    finally { if (id === requestId) searching.value = false }
  }, 200)
})
watch(() => route.path, () => { accountOpen.value = false })
onMounted(() => {
  isMac.value = /Mac|iPad|iPhone/.test(navigator.platform)
  window.addEventListener('keydown', keydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', keydown)
  if (timer !== undefined) window.clearTimeout(timer)
})
</script>

<style scoped>
.shell{min-height:100vh;display:grid;grid-template-columns:var(--dc-sidebar) minmax(0,1fr)}.sidebar{position:sticky;top:0;height:100vh;padding:20px 14px 16px;background:linear-gradient(180deg,#f2f9fd 0%,#edf6fb 100%);border-right:1px solid #dcebf4;display:flex;flex-direction:column;z-index:20}.brand{height:52px;padding:4px 8px;display:flex;align-items:center;gap:10px}.brand-mark{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#78c8df,#459ec9);color:#fff;font-weight:800;box-shadow:0 8px 20px rgba(68,155,198,.2)}.brand-copy{display:grid;line-height:1.15}.brand-copy b{font-size:15px}.nav{margin-top:16px;display:grid;gap:4px}.nav-item{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:10px;color:#58798c;font-size:13px;transition:.16s ease}.nav-item:hover{background:rgba(255,255,255,.72);color:#2a708f}.nav-item.router-link-exact-active,.nav-item-active{background:#fff;color:#227da7;font-weight:700;box-shadow:0 6px 18px rgba(49,117,151,.07)}.nav-divider{height:1px;background:#d7e8f1;margin:10px 8px}.sidebar-foot{margin-top:auto;padding:12px;display:flex;gap:9px;align-items:center;border-top:1px solid #d8e9f2}.status-dot{width:8px;height:8px;border-radius:50%;background:#43a87e;box-shadow:0 0 0 4px rgba(67,168,126,.1)}.sidebar-foot div{display:grid}.sidebar-foot b{font-size:12px}.sidebar-foot small{font-size:12px;color:#5b6b7a;margin-top:2px}.workspace{min-width:0}.topbar{position:sticky;top:0;height:var(--dc-topbar);padding:0 24px;display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.86);border-bottom:1px solid var(--dc-border);backdrop-filter:blur(18px);z-index:15}.top-left{display:flex;align-items:center;gap:9px;min-width:160px}.crumb{font-size:13px;font-weight:700}.breadcrumbs{display:flex;align-items:center;gap:8px;min-width:0;font-size:13px;white-space:nowrap}.breadcrumbs a{color:var(--dc-text-2)}.breadcrumbs a:hover{color:var(--dc-primary-strong)}.breadcrumb-divider{color:var(--dc-text-3)}.icon-button{width:32px;height:32px;border:1px solid var(--dc-border);background:#fff;border-radius:9px;color:#55798d;display:grid;place-items:center;cursor:pointer}.command{margin-left:auto;width:min(430px,38vw);height:38px;border:1px solid #d8e8f1;border-radius:11px;background:#fafdff;color:#7c92a1;display:flex;align-items:center;gap:9px;padding:0 12px;cursor:pointer}.command span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.command kbd{margin-left:auto;padding:2px 6px;border-radius:6px;background:#fff;border:1px solid #dce8ef;color:#78909e}.top-actions{display:flex;align-items:center;gap:9px}.soft-action{display:flex;align-items:center;gap:6px;font-size:12px;color:#2d7696;background:#eef8fc;padding:8px 11px;border-radius:9px}.avatar{width:34px;height:34px;border-radius:50%;border:0;display:grid;place-items:center;background:#dff1f8;color:#2d7898;font-weight:800;cursor:pointer}.account-wrap{position:relative}.account-menu{position:absolute;right:0;top:42px;min-width:150px;padding:6px;display:grid;gap:3px;background:#fff;border:1px solid var(--dc-border);border-radius:11px;box-shadow:var(--dc-shadow-md);z-index:30}.account-menu a,.account-menu button{display:flex;align-items:center;gap:9px;padding:9px 10px;text-align:left;color:var(--dc-text-2);font-size:12px;border:0;border-radius:7px;background:none;cursor:pointer}.account-menu a:hover,.account-menu button:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.nav-disabled{width:100%;border:0;background:none;text-align:left;opacity:.72;cursor:not-allowed}.nav-disabled small{margin-left:auto;font-size:12px;color:var(--dc-text-2)}.search-overlay{position:fixed;inset:0;z-index:100;background:rgba(23,48,64,.28);display:flex;justify-content:center;align-items:flex-start;padding:13vh 20px 20px}.search-dialog{width:min(610px,100%);max-height:72vh;overflow:hidden;background:#fff;border:1px solid var(--dc-border);border-radius:14px;box-shadow:0 24px 65px rgba(26,65,88,.18)}.search-dialog-input{height:56px;display:flex;align-items:center;gap:11px;padding:0 16px;color:var(--dc-primary-strong);border-bottom:1px solid var(--dc-border)}.search-dialog-input input{min-width:0;flex:1;border:0;outline:0;color:var(--dc-text);font-size:14px}.search-dialog-input kbd{padding:3px 6px;border:1px solid var(--dc-border);border-radius:6px;font-size:12px;color:var(--dc-text-2)}.search-dialog-list{max-height:calc(72vh - 103px);overflow:auto;padding:7px}.search-dialog-result{width:100%;display:flex;align-items:center;gap:11px;text-align:left;padding:10px 12px;border:0;border-radius:9px;background:transparent;color:var(--dc-text-2);cursor:pointer}.search-dialog-result:hover,.search-dialog-result.selected{background:#f1f9fd}.search-dialog-result-text{min-width:0;flex:1;display:grid;gap:3px}.search-dialog-result-text b{font-size:13px;color:var(--dc-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.search-dialog-result-text code{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.search-dialog-hint{padding:21px;text-align:center;font-size:12px;color:var(--dc-text-2)}.search-dialog-footer{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-top:1px solid var(--dc-border);font-size:12px;color:var(--dc-text-2)}.search-dialog-footer button{border:0;background:transparent;color:var(--dc-primary-strong);cursor:pointer}.search-dialog-footer button:disabled{opacity:.5;cursor:not-allowed}@media(max-width:1080px){.shell{grid-template-columns:78px minmax(0,1fr)}.sidebar{padding:18px 10px}.brand-copy,.nav-item span,.nav-disabled small,.sidebar-foot div{display:none}.brand{justify-content:center;padding:0}.nav-item{justify-content:center;padding:11px}.sidebar-foot{justify-content:center}.top-left{min-width:auto}.command{width:min(420px,48vw)}}@media(max-width:820px){.shell{display:block}.sidebar{display:none}.topbar{padding:0 14px}.command{width:auto;flex:1}.top-actions .soft-action{display:none}}@media(max-width:560px){.command span,.command kbd{display:none}.command{flex:0 0 40px;padding:0;justify-content:center}.crumb{max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
</style>
