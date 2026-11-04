<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">D</span>
        <span class="brand-copy"><b>DataControl</b></span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <template v-for="item in primary" :key="item.label">
          <RouterLink
            v-if="!item.disabled"
            :to="item.to"
            class="nav-item"
            :class="{ 'nav-item-active': isActive(item) }"
          >
            <component :is="item.icon" :size="18" stroke-width="1.8" />
            <span>{{ item.label }}</span>
          </RouterLink>
          <button v-else class="nav-item nav-disabled" type="button" disabled title="P3 阶段开放">
            <component :is="item.icon" :size="18" stroke-width="1.8" />
            <span>{{ item.label }}</span>
            <small>即将上线</small>
          </button>
        </template>
      </nav>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="top-left">
          <nav class="breadcrumbs" aria-label="当前位置">
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.label">
              <RouterLink v-if="crumb.to && index < breadcrumbs.length - 1" :to="crumb.to">{{ crumb.label }}</RouterLink>
              <span v-else class="crumb">{{ crumb.label }}</span>
              <span v-if="index < breadcrumbs.length - 1" class="crumb-separator">/</span>
            </template>
          </nav>
        </div>
        <button v-if="route.name !== 'home'" class="command" type="button" @click="openCommand">
          <Search :size="17" /><span>搜索数据资产…</span><kbd>{{ shortcutLabel }}</kbd>
        </button>
        <div class="top-actions">
          <div class="account-wrap">
            <button class="avatar" type="button" aria-label="账户菜单" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen">H</button>
            <div v-if="userMenuOpen" class="account-menu">
              <RouterLink to="/profile" @click="userMenuOpen = false"><UserRound :size="15" />个人中心</RouterLink>
              <button type="button" @click="logout"><LogOut :size="15" />退出登录</button>
            </div>
          </div>
        </div>
      </header>
      <main><RouterView /></main>
    </div>
  </div>

  <div v-if="commandOpen" class="command-backdrop" @click.self="closeCommand">
    <section class="command-panel" role="dialog" aria-modal="true" aria-label="全局搜索">
      <div class="command-input">
        <Search :size="18" />
        <input
          ref="commandInput"
          v-model="commandQuery"
          autofocus
          placeholder="搜索数据集、字段、指标、码表…"
          @keydown.enter="submitCommand"
          @keydown.arrow-down.prevent="moveCommandSelection(1)"
          @keydown.arrow-up.prevent="moveCommandSelection(-1)"
          @keydown.esc="closeCommand"
        />
        <kbd>Esc</kbd>
      </div>
      <div class="command-results">
        <div v-if="searching" class="command-empty">正在搜索…</div>
        <button v-for="(item,index) in commandResults" :key="item.asset_id" class="command-result" :class="{selected:index===selectedCommandIndex}" type="button" @mouseenter="selectedCommandIndex=index" @click="openResult(item)">
          <span class="dc-chip">{{ assetTypeLabel(item.asset_type) }}</span>
          <span class="command-result-copy">
            <b>{{ item.title }}</b>
            <code>{{ item.technical_name }}</code>
          </span>
          <ArrowRight :size="16" />
        </button>
        <div v-if="commandQuery.trim() && !searching && !commandResults.length" class="command-empty">没有找到匹配资产，按 Enter 查看完整检索页。</div>
        <div v-if="!commandQuery.trim()" class="command-empty">输入关键词，快速定位数据资产。</div>
      </div>
      <div class="command-foot"><span>↑ ↓ 选择 · Enter 打开 · Esc 关闭</span><button type="button" @click="openFullSearch">查看全部结果 <ArrowRight :size="12"/></button></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ArrowRight, BarChart3, BookOpenCheck, Boxes, CircleGauge, Database, LogOut, Search, Sparkles, UserRound } from 'lucide-vue-next'
import { assetApi } from '@/api/client'
import { assetTypeLabel } from '@/utils/labels'

const router = useRouter()
const route = useRoute()
const primary = [
  { to: '/', label: '首页', icon: CircleGauge, matches: ['/'] },
  { to: '/catalog', label: '资产目录', icon: Database, matches: ['/catalog', '/datasets', '/fields'] },
  { to: '/standards', label: '数据标准', icon: Boxes, matches: ['/standards', '/code-tables', '/word-roots'] },
  { to: '/metrics', label: '指标与制度', icon: BookOpenCheck, matches: ['/metrics', '/stat-systems'] },
  { to: '#', label: '智能问数', icon: Sparkles, matches: ['__disabled__'] as string[], disabled: true },
  { to: '/overview', label: '数据概览', icon: BarChart3, matches: ['/overview'] },
]
const userMenuOpen = ref(false)
const commandOpen = ref(false)
const commandQuery = ref('')
const commandResults = ref<any[]>([])
const selectedCommandIndex = ref(0)
const searching = ref(false)
const commandInput = ref<HTMLInputElement | null>(null)
const isMac = ref(false)
let searchTimer: number | undefined

const shortcutLabel = computed(() => isMac.value ? '⌘ K' : 'Ctrl K')
const pageContextTitle = ref('')
provide('dataControlPageTitle', pageContextTitle)
watch(() => route.path, () => { pageContextTitle.value = '' })
const breadcrumbs = computed(() => {
  const path = route.path
  const title = String(route.meta.title || 'DataControl')
  if (path.startsWith('/datasets/')) return [{ label: '资产目录', to: '/catalog' }, { label: pageContextTitle.value || title }]
  if (path.startsWith('/fields/')) return [{ label: '资产目录', to: '/catalog' }, { label: title }]
  if (path.startsWith('/code-tables')) return [{ label: '数据标准', to: '/standards' }, { label: pageContextTitle.value || '码表' }]
  if (path.startsWith('/standards')) return pageContextTitle.value ? [{ label: '数据标准', to: '/standards' }, { label: pageContextTitle.value }] : [{ label: '数据标准' }]
  if (path.startsWith('/word-roots')) return [{ label: '数据标准', to: '/standards' }, { label: pageContextTitle.value || '词根' }]
  if (path.startsWith('/metrics')) return pageContextTitle.value ? [{ label: '指标与制度', to: '/metrics' }, { label: pageContextTitle.value }] : [{ label: '指标与制度', to: '/metrics' }, { label: '指标' }]
  if (path.startsWith('/stat-systems')) return [{ label: '指标与制度', to: '/metrics' }, { label: pageContextTitle.value || '统计制度' }]
  return [{ label: title }]
})

function isActive(item: typeof primary[number]) {
  return item.matches.includes(route.path) || item.matches.some((path) => path !== '/' && route.path.startsWith(path + '/'))
}
function openCommand() {
  userMenuOpen.value = false
  commandOpen.value = true
  nextTick(() => commandInput.value?.focus())
}
function closeCommand() {
  commandOpen.value = false
  commandQuery.value = ''
  commandResults.value = []
}
function openResult(item: any) {
  const q = commandQuery.value.trim()
  closeCommand()
  if (item.asset_type === 'TABLE') router.push(`/datasets/${item.asset_id}`)
  else if (item.asset_type === 'COLUMN') router.push(`/fields/${item.asset_id}`)
  else if (item.asset_type === 'CODE_TABLE') router.push(`/code-tables/${item.technical_name}`)
  else if (item.asset_type === 'DATA_STANDARD') router.push(`/standards/${item.technical_name}`)
  else if (item.asset_type === 'WORD_ROOT') router.push(`/word-roots/${item.technical_name}`)
  else if (item.asset_type === 'METRIC') router.push(`/metrics/${item.technical_name}`)
  else if (item.asset_type === 'STAT_SYSTEM') router.push(`/stat-systems/${item.technical_name}`)
  else router.push({ name: 'search', query: { q } })
}
function moveCommandSelection(delta: number) {
  const count = commandResults.value.length
  if (!count) return
  selectedCommandIndex.value = Math.max(0, Math.min(count - 1, selectedCommandIndex.value + delta))
}
function openFullSearch() {
  const q = commandQuery.value.trim()
  if (!q) return
  closeCommand()
  router.push({ name: 'search', query: { q } })
}
function submitCommand() {
  if (commandResults.value.length) {
    openResult(commandResults.value[selectedCommandIndex.value] || commandResults.value[0])
    return
  }
  openFullSearch()
}
function logout() {
  localStorage.removeItem('datacontrol_token')
  localStorage.removeItem('datacontrol_user')
  userMenuOpen.value = false
  router.push('/login')
}
function shortcut(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openCommand()
  }
  if (event.key === 'Escape') {
    closeCommand()
    userMenuOpen.value = false
  }
}
watch(commandQuery, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer)
  selectedCommandIndex.value = 0
  const query = value.trim()
  if (!query) {
    commandResults.value = []
    searching.value = false
    return
  }
  searchTimer = window.setTimeout(async () => {
    searching.value = true
    try {
      commandResults.value = await assetApi.search(query, 6) as any[]
    } catch {
      commandResults.value = []
    } finally {
      searching.value = false
    }
  }, 180)
})
onMounted(() => {
  isMac.value = /Mac|iPhone|iPad/.test(navigator.platform)
  window.addEventListener('keydown', shortcut)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', shortcut)
  if (searchTimer) window.clearTimeout(searchTimer)
})
</script>

<style scoped>
.shell{min-height:100vh;display:grid;grid-template-columns:var(--dc-sidebar) minmax(0,1fr)}.sidebar{position:sticky;top:0;height:100vh;padding:20px 14px 16px;background:linear-gradient(180deg,#f2f9fd 0%,#edf6fb 100%);border-right:1px solid #dcebf4;display:flex;flex-direction:column;z-index:20}.brand{height:52px;padding:4px 8px;display:flex;align-items:center;gap:10px}.brand-mark{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#78c8df,#459ec9);color:#fff;font-weight:800;box-shadow:0 8px 20px rgba(68,155,198,.2)}.brand-copy{display:grid;line-height:1.15}.brand-copy b{font-size:15px}.nav{margin-top:16px;display:grid;gap:4px}.nav-item{width:100%;display:flex;align-items:center;gap:11px;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:#58798c;font-size:13px;text-align:left;transition:.16s ease;cursor:pointer}.nav-item:hover{background:rgba(255,255,255,.72);color:#2a708f}.nav-item-active{background:#fff;color:#227da7;font-weight:700;box-shadow:0 6px 18px rgba(49,117,151,.07)}.nav-disabled{cursor:not-allowed;opacity:.72}.nav-disabled small{margin-left:auto;font-size:12px;color:#8ba0af}.workspace{min-width:0}.topbar{position:sticky;top:0;height:var(--dc-topbar);padding:0 24px;display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.86);border-bottom:1px solid var(--dc-border);backdrop-filter:blur(18px);z-index:15}.top-left{display:flex;align-items:center;gap:9px;min-width:160px}.breadcrumbs{display:flex;align-items:center;gap:9px;min-width:0;font-size:13px}.breadcrumbs a{color:#7a93a3}.breadcrumbs a:hover{color:var(--dc-primary-strong)}.crumb{font-size:13px;font-weight:700;white-space:nowrap}.crumb-separator{color:#b1c0c9}.command{margin-left:auto;width:min(430px,38vw);height:38px;border:1px solid #d8e8f1;border-radius:11px;background:#fafdff;color:#7c92a1;display:flex;align-items:center;gap:9px;padding:0 12px;cursor:pointer}.command span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.command kbd,.command-input kbd{margin-left:auto;padding:2px 6px;border-radius:6px;background:#fff;border:1px solid #dce8ef;color:#78909e;font-size:12px}.top-actions{display:flex;align-items:center;gap:9px}.account-wrap{position:relative}.avatar{width:34px;height:34px;border:0;border-radius:50%;display:grid;place-items:center;background:#dff1f8;color:#2d7898;font-weight:800;cursor:pointer}.account-menu{position:absolute;right:0;top:42px;min-width:150px;padding:6px;background:#fff;border:1px solid var(--dc-border);border-radius:11px;box-shadow:var(--dc-shadow-md);display:grid;gap:3px}.account-menu a,.account-menu button{display:flex;align-items:center;gap:8px;padding:9px 10px;border:0;border-radius:7px;background:transparent;color:var(--dc-text-2);font-size:12px;text-align:left;cursor:pointer}.account-menu a:hover,.account-menu button:hover{background:var(--dc-primary-soft);color:var(--dc-primary-strong)}.command-backdrop{position:fixed;inset:0;z-index:100;background:rgba(23,48,64,.28);display:flex;justify-content:center;align-items:flex-start;padding:13vh 20px 20px}.command-panel{width:min(620px,100%);max-height:70vh;overflow:hidden;background:#fff;border:1px solid var(--dc-border);border-radius:16px;box-shadow:0 24px 70px rgba(26,65,88,.2)}.command-input{height:58px;display:flex;align-items:center;gap:11px;padding:0 17px;border-bottom:1px solid var(--dc-border);color:#79a1b5}.command-input input{flex:1;min-width:0;border:0;outline:0;color:var(--dc-text);font-size:14px}.command-results{max-height:calc(70vh - 100px);overflow:auto;padding:8px}.command-result{width:100%;display:flex;align-items:center;gap:11px;padding:11px 12px;border:0;border-radius:9px;background:transparent;text-align:left;cursor:pointer;color:var(--dc-text-2)}.command-result:hover,.command-result.selected{background:#f2f9fc}.command-result-copy{min-width:0;flex:1;display:grid;gap:4px}.command-result-copy b{font-size:13px;color:var(--dc-text)}.command-result-copy code{font-size:12px;color:var(--dc-text-3);overflow:hidden;text-overflow:ellipsis}.command-empty{padding:24px;text-align:center;color:var(--dc-text-3);font-size:12px}.command-foot{display:flex;justify-content:space-between;align-items:center;padding:9px 14px;border-top:1px solid var(--dc-border);color:var(--dc-text-3);font-size:12px}.command-foot button{display:flex;align-items:center;gap:5px;border:0;background:transparent;color:var(--dc-primary-strong);font-size:12px;cursor:pointer}@media(max-width:1080px){.shell{grid-template-columns:78px minmax(0,1fr)}.sidebar{padding:18px 10px}.brand-copy,.nav-item span,.nav-disabled small{display:none}.brand{justify-content:center;padding:0}.nav-item{justify-content:center;padding:11px}.top-left{min-width:auto}.command{width:min(420px,48vw)}}@media(max-width:820px){.shell{display:block}.sidebar{display:none}.topbar{padding:0 14px}.command{width:auto;flex:1}}@media(max-width:560px){.command span,.command kbd{display:none}.command{flex:0 0 40px;padding:0;justify-content:center}.crumb{max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.breadcrumbs{gap:5px}}
</style>
