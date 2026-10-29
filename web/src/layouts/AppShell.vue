<template>
  <div class="shell" :class="{ 'is-collapsed': navCollapsed }">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark"><Layers3 :size="21" :stroke-width="2.2"/></span>
        <span class="brand-copy"><b>DataControl</b><small>数据资产与智能工作台</small></span>
      </RouterLink>

      <button class="collapse-nav" :aria-label="navCollapsed ? '展开侧边栏' : '折叠侧边栏'" :title="navCollapsed ? '展开导航' : '收起导航'" @click="navCollapsed=!navCollapsed"><PanelLeftClose :size="16"/></button>
      <nav class="nav" aria-label="主导航">
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <div class="nav-section">{{ group.title }}</div>
          <RouterLink v-for="item in group.items" :key="item.to" :to="item.to"
            class="nav-item" :title="item.label">
            <AssetIcon v-if="'assetType' in item && item.assetType" :type="String(item.assetType)" :size="21" mode="inline"/>
            <component :is="item.icon" v-else :size="21" :stroke-width="1.9"/>
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-foot">
        <span class="status-dot" :class="{offline:serviceAvailable===false}" />
        <div><b>{{serviceAvailable===false?'服务异常':'本地数据服务'}}</b>
          <small>{{serviceAvailable===false?'请检查服务日志':'DataControl'}}</small></div>
      </div>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="top-left">
          <button class="icon-button mobile-menu" aria-label="展开导航" @click="mobileNavOpen=true"><Menu :size="18"/></button>
          <button v-if="route.name !== 'home'" class="icon-button" @click="router.back()"><ArrowLeft :size="18" /></button>
          <AssetIcon :type="breadcrumbType" :size="17" mode="inline"/>
          <span class="crumb">{{ route.meta.title || '工作台' }}</span>
        </div>
        <button class="command" aria-label="打开全局资产搜索" @click="commandOpen=true">
          <Search :size="17" /><span>搜索数据集、字段、指标、标准…</span><kbd>{{ isMac ? '⌘ K' : 'Ctrl K' }}</kbd>
        </button>
        <div class="top-actions">
          <RouterLink to="/agent" class="soft-action"><Sparkles :size="17" />智能问数</RouterLink>
          <a class="icon-button help-link" title="使用说明" aria-label="使用说明" href="https://github.com/Hunter-ZK/DataControl/blob/main/README.md" target="_blank" rel="noopener noreferrer"><CircleHelp :size="17"/></a>
          <el-dropdown>
            <button class="avatar user-trigger" aria-label="用户菜单">{{userInitial}}</button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main><RouterView /></main>
      <AssetAgentDrawer/>
    </div>
    <el-drawer v-model="mobileNavOpen" title="DataControl 导航" direction="ltr" size="min(300px,85vw)">
      <div class="mobile-links">
        <RouterLink v-for="item in [...primary,...secondary]" :key="item.to" :to="item.to" @click="mobileNavOpen=false">
          <AssetIcon v-if="'assetType' in item && item.assetType" :type="String(item.assetType)" :size="18" mode="inline"/>
          <component :is="item.icon" v-else :size="18"/>{{item.label}}
        </RouterLink>
      </div>
    </el-drawer>
    <el-dialog v-model="commandOpen" title="快速查找数据资产" width="min(620px,95vw)" class="command-dialog">
      <el-input v-model="commandQuery" autofocus placeholder="数据集、指标、字段或标准名称"
        @input="loadCommandSuggestions" @keydown.enter="openCommandSearch"/>
      <div v-if="availableAssetCommands.length" class="command-asset-actions">
        <div class="command-asset-heading">当前资产 · {{ activeAssetOperations?.label }}</div>
        <button v-for="item in availableAssetCommands" :key="item.id" @click="runAssetOperation(item.id)">
          <Sparkles v-if="item.group==='问 Agent'" :size="15"/>
          <FileText v-else :size="15"/>
          <span>{{item.label}}</span><small>{{item.group}}</small>
        </button>
      </div>
      <div class="command-results">
        <button v-for="item in commandSuggestions" :key="item.assetType+item.assetId"
          @click="chooseCommand(item)"><AssetIcon :type="item.assetType" :size="16" mode="inline"/><b>{{item.title}}</b><code>{{item.technicalName}}</code><small>{{item.assetType}}</small></button>
        <button v-if="commandQuery.trim()" @click="openCommandSearch">查看完整检索结果：{{commandQuery}}</button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { activeAssetOperations } from '@/composables/assetOperations'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, BarChart3, BookOpenCheck, Boxes, CircleGauge, CircleHelp, Database, FileText, Hash, Layers3, Menu, PanelLeftClose, Search, Sparkles, UserRound } from 'lucide-vue-next'
import { assetApi, type SearchSuggestion } from '@/api/client'
import AssetIcon from '@/components/AssetIcon.vue'
import AssetAgentDrawer from '@/components/AssetAgentDrawer.vue'

const router = useRouter()
const mobileNavOpen=ref(false)
const navCollapsed=ref(false)
const isMac=typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
const breadcrumbType=computed(():string => ({
  catalog:'TABLE',dataset:'TABLE',field:'COLUMN',search:'TABLE',
  codeTables:'CODE_TABLE',codeTable:'CODE_TABLE',standards:'STANDARD',standard:'STANDARD',
  wordRoots:'WORD_ROOT',wordRoot:'WORD_ROOT',metrics:'METRIC',metric:'METRIC',
  statSystems:'STAT_SYSTEM',statSystem:'STAT_SYSTEM',
} as Record<string,string>)[String(route.name)]||'CATALOG')
const commandOpen=ref(false)
const commandQuery=ref('')
const commandSuggestions=ref<SearchSuggestion[]>([])
const availableAssetCommands=computed(()=>activeAssetOperations.value?.path===route.fullPath
  ? activeAssetOperations.value.actions.filter(item=>item.label.toLowerCase().includes(commandQuery.value.trim().toLowerCase()))
  : [])
function runAssetOperation(id:string) {
  const current=activeAssetOperations.value
  commandOpen.value=false
  commandQuery.value=''
  if(current?.path===route.fullPath)current.execute(id)
}
const serviceAvailable=ref<boolean|null>(null)
let commandEpoch=0
const userInitial=computed(()=>{
  try {const u=JSON.parse(localStorage.getItem('datacontrol_user')||'{}') as {displayName?:string;username?:string};
    return (u.displayName||u.username||'U').slice(0,1).toUpperCase()}catch{return 'U'}
})
async function loadCommandSuggestions(){
  const q=commandQuery.value.trim(),epoch=++commandEpoch
  if(!q){commandSuggestions.value=[];return}
  try{const rows=await assetApi.suggest(q,7);if(epoch===commandEpoch)commandSuggestions.value=rows}
  catch{if(epoch===commandEpoch)commandSuggestions.value=[]}
}
function chooseCommand(item:SearchSuggestion){
  commandOpen.value=false
  const code=item.technicalName||item.assetId
  const names:Record<string,string>={TABLE:'dataset',COLUMN:'field',METRIC:'metric',CODE_TABLE:'codeTable',STANDARD:'standard',WORD_ROOT:'wordRoot',STAT_SYSTEM:'statSystem'}
  const key:Record<string,string>={TABLE:'id',COLUMN:'id',METRIC:'code',CODE_TABLE:'no',STANDARD:'no',WORD_ROOT:'root',STAT_SYSTEM:'code'}
  const name=names[item.assetType]
  if(!name){router.push({name:'search',query:{q:code}});return}
  router.push({name,params:{[key[item.assetType]]:item.assetType==='TABLE'||item.assetType==='COLUMN'?item.assetId:code}})
}
function openCommandSearch(){commandOpen.value=false;router.push({name:'search',query:{q:commandQuery.value.trim()}})}
function logout(){localStorage.removeItem('datacontrol_token');localStorage.removeItem('datacontrol_user');router.push({name:'login'})}

const route = useRoute()
const primary = [
  { to: '/', label: '首页', icon: CircleGauge },
  { to: '/catalog', label: '资产目录', icon: Database, assetType: 'TABLE' },
  { to: '/search', label: '资产检索', icon: Search },
  { to: '/code-tables', label: '标准码表', icon: Boxes, assetType: 'CODE_TABLE' },
  { to: '/word-roots', label: '词根索引', icon: Hash, assetType: 'WORD_ROOT' },
  { to: '/metrics', label: '业务指标', icon: BookOpenCheck, assetType: 'METRIC' },
  { to: '/agent', label: '智能问数', icon: Sparkles },
  { to: '/workbench/naming', label: '字段规范化命名', icon: FileText },
  { to: '/standards', label: '数据标准', icon: BookOpenCheck, assetType: 'STANDARD' },
  { to: '/stat-systems', label: '统计制度', icon: FileText, assetType: 'STAT_SYSTEM' },
]
const secondary = [
  { to: '/overview', label: '数据概览', icon: BarChart3 },
  { to: '/profile', label: '个人中心', icon: UserRound },
]
const navGroups = [
  { title: '工作空间', items: [primary[0], primary[6], primary[7]] },
  { title: '数据发现', items: [primary[2], primary[1]] },
  { title: '数据理解', items: [primary[5], primary[9], primary[3], primary[8], primary[4]] },
  { title: '其他', items: secondary },
]

function shortcut(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); commandOpen.value=true
  }
}
onMounted(async() => {
  window.addEventListener('keydown', shortcut)
  try { const response=await fetch('/health');serviceAvailable.value=response.ok } catch {serviceAvailable.value=false}
})
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>

<style scoped>
.shell{min-height:100vh;display:grid;grid-template-columns:var(--dc-sidebar) minmax(0,1fr)}.sidebar{position:sticky;top:0;height:100vh;padding:20px 14px 16px;background:linear-gradient(180deg,#f2f9fd 0%,#edf6fb 100%);border-right:1px solid #dcebf4;display:flex;flex-direction:column;z-index:20}.brand{height:52px;padding:4px 8px;display:flex;align-items:center;gap:10px}.brand-mark{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#78c8df,#459ec9);color:#fff;font-weight:800;box-shadow:0 8px 20px rgba(68,155,198,.2)}.brand-copy{display:grid;line-height:1.15}.brand-copy b{font-size:15px}.brand-copy small{font-size:12px;letter-spacing:.13em;margin-top:4px;color:#7c9aab}.nav{margin-top:16px;display:grid;gap:4px}.nav-item{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:10px;color:#58798c;font-size:13px;transition:.16s ease}.nav-item:hover{background:rgba(255,255,255,.72);color:#2a708f}.nav-item.router-link-exact-active{background:#fff;color:#227da7;font-weight:700;box-shadow:0 6px 18px rgba(49,117,151,.07)}.nav-divider{height:1px;background:#d7e8f1;margin:10px 8px}.sidebar-foot{margin-top:auto;padding:12px;display:flex;gap:9px;align-items:center;border-top:1px solid #d8e9f2}.status-dot{width:8px;height:8px;border-radius:50%;background:#43a87e;box-shadow:0 0 0 4px rgba(67,168,126,.1)}.sidebar-foot div{display:grid}.sidebar-foot b{font-size:11px}.sidebar-foot small{font-size:12px;color:#86a0af;margin-top:2px}.workspace{min-width:0}.topbar{position:sticky;top:0;height:var(--dc-topbar);padding:0 24px;display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.86);border-bottom:1px solid var(--dc-border);backdrop-filter:blur(18px);z-index:15}.top-left{display:flex;align-items:center;gap:9px;min-width:160px}.crumb{font-size:13px;font-weight:700}.icon-button{width:32px;height:32px;border:1px solid var(--dc-border);background:#fff;border-radius:9px;color:#55798d;display:grid;place-items:center;cursor:pointer}.command{margin-left:auto;width:min(430px,38vw);height:38px;border:1px solid #d8e8f1;border-radius:11px;background:#fafdff;color:#7c92a1;display:flex;align-items:center;gap:9px;padding:0 12px;cursor:pointer}.command span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.command kbd{margin-left:auto;padding:2px 6px;border-radius:6px;background:#fff;border:1px solid #dce8ef;color:#78909e}.top-actions{display:flex;align-items:center;gap:9px}.soft-action{display:flex;align-items:center;gap:6px;font-size:12px;color:#2d7696;background:#eef8fc;padding:8px 11px;border-radius:9px}.avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#dff1f8;color:#2d7898;font-weight:800}@media(max-width:1080px){.shell{grid-template-columns:78px minmax(0,1fr)}.sidebar{padding:18px 10px}.brand-copy,.nav-item span,.sidebar-foot div{display:none}.brand{justify-content:center;padding:0}.nav-item{justify-content:center;padding:11px}.sidebar-foot{justify-content:center}.top-left{min-width:auto}.command{width:min(420px,48vw)}}@media(max-width:820px){.shell{display:block}.sidebar{display:none}.topbar{padding:0 14px}.command{width:auto;flex:1}.top-actions .soft-action{display:none}}@media(max-width:560px){.command span,.command kbd{display:none}.command{flex:0 0 40px;padding:0;justify-content:center}.crumb{max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
 .nav-section {font-size:12px;color:var(--dc-text-3);padding:12px 10px 3px;font-weight:700;letter-spacing:.03em;}
 .mobile-menu{display:none;}
 .status-dot.offline{background:var(--dc-danger);}
 .user-trigger{border:0;cursor:pointer;}
 .mobile-links{display:grid;gap:5px;}
 .mobile-links a{display:flex;align-items:center;gap:12px;padding:11px;border-radius:9px;color:var(--dc-text);}
 .mobile-links a.router-link-active{background:var(--dc-primary-soft);color:var(--dc-primary);}
 .command-asset-actions{border:1px solid var(--dc-border);border-radius:11px;background:var(--dc-surface-soft);margin-top:12px;padding:9px;max-height:320px;overflow:auto}.command-asset-heading{font-size:12px;font-weight:700;color:var(--dc-text-2);padding:5px 10px 9px}.command-asset-actions button{width:100%;display:flex;align-items:center;gap:10px;background:transparent;border:0;border-radius:8px;padding:10px;text-align:left;color:var(--dc-text);font-size:13px;cursor:pointer}.command-asset-actions button:hover{background:var(--dc-surface);color:var(--dc-primary)}.command-asset-actions button small{margin-left:auto;color:var(--dc-text-3)}
 .command-results{display:grid;gap:4px;max-height:340px;overflow:auto;margin-top:12px;}
 .command-results button{display:flex;align-items:center;gap:9px;padding:12px 8px;border:0;border-radius:7px;background:white;color:var(--dc-text);text-align:left;cursor:pointer;}
 .command-results button:hover{background:var(--dc-primary-soft);}
 .command-results button code{color:var(--dc-text-2);font-size:12px;}
 .command-results button small{margin-left:auto;color:var(--dc-text-3);font-size:12px;}
 @media(max-width:820px){.mobile-menu{display:grid;}}
 .shell.is-collapsed{grid-template-columns:76px minmax(0,1fr)}
 .shell.is-collapsed .sidebar{padding-left:10px;padding-right:10px}
 .shell.is-collapsed .brand-copy,.shell.is-collapsed .nav-item span,.shell.is-collapsed .sidebar-foot div,.shell.is-collapsed .nav-section{display:none}
 .shell.is-collapsed .brand,.shell.is-collapsed .nav-item,.shell.is-collapsed .sidebar-foot{justify-content:center}
 .collapse-nav{align-self:flex-end;border:1px solid var(--dc-border);border-radius:8px;background:#fff;color:var(--dc-primary);display:grid;place-items:center;width:28px;height:28px;cursor:pointer}
 .shell.is-collapsed .collapse-nav{align-self:center;transform:rotate(180deg)}
 .sidebar{background:#f8fbff;border-right-color:var(--dc-border)}
 .nav-item.router-link-exact-active{background:var(--dc-primary-soft);color:var(--dc-primary);box-shadow:none}
 .nav-item.router-link-exact-active:before{content:'';position:absolute;left:0;width:3px;height:22px;background:var(--dc-primary);border-radius:3px}
 .nav-item{position:relative}
 .command{background:#f8fbff;border-color:var(--dc-border)}
 .help-link{display:grid;flex:none}
 .soft-action{background:var(--dc-primary-soft);color:var(--dc-primary)}
 .brand-mark{background:linear-gradient(140deg,#2563eb,#60a5fa);box-shadow:0 2px 9px rgba(37,99,235,.12)}
 .topbar{background:rgba(255,255,255,.96);backdrop-filter:blur(12px)}
 @media(max-width:820px){.collapse-nav{display:none}.shell.is-collapsed{display:block}}
 
/* Atlas shell refinements: quiet canvas, clear focus, consistent icon rhythm. */
.shell{background:var(--dc-bg)}
.sidebar{background:#fff;border-right:1px solid var(--dc-border);padding:20px 12px 16px}
.brand{gap:11px;padding:0 12px;height:54px}
.brand-mark{width:37px;height:37px;border-radius:11px;background:#2563eb;box-shadow:0 5px 12px rgba(37,99,235,.14)}
.brand-copy b{color:#1b3353;font-size:16px;letter-spacing:-.025em}
.brand-copy small{font-size:12px;letter-spacing:0;margin-top:4px;color:#8b9db3}
.nav{display:block;margin-top:18px}
.nav-group{margin-bottom:12px}
.nav-section{font-size:12px;color:#94a3b7;padding:9px 13px 6px;letter-spacing:.035em;font-weight:680}
.nav-item{min-height:41px;border-radius:9px;margin:2px 0;gap:12px;color:#5a708e;padding:9px 12px;font-size:13px;font-weight:560}
.nav-item:hover{background:#f5f8fe;color:#245cce}
.nav-item.router-link-exact-active{background:#edf4ff;color:#1f59d6;box-shadow:inset 3px 0 #2563eb;font-weight:710}
.nav-item.router-link-exact-active:before{display:none}
.collapse-nav{margin:8px 0 1px;align-self:flex-end;border:0;background:transparent;color:#8ca0b9}
.collapse-nav:hover{background:#f0f5fd;color:#2563eb}
.sidebar-foot{border-top:1px solid var(--dc-border);margin:0 6px;padding:16px 6px}
.topbar{background:rgba(255,255,255,.97);height:64px;padding:0 26px;border-bottom:1px solid var(--dc-border)}
.top-left{min-width:188px;gap:10px}
.crumb{font-size:13px;color:#233954}
.command{height:38px;border-radius:9px;background:#f7f9fd;border-color:var(--dc-border);color:#7f90a9}
.command:hover{border-color:#c0d3f4;background:#fff}
.soft-action{font-size:12px;font-weight:700;border-radius:8px;padding:9px 12px}
.avatar{background:#e7f0ff;color:#235ac7}
.shell.is-collapsed .nav-section{display:none}
.shell.is-collapsed .nav-group{margin-bottom:12px}
.shell.is-collapsed .nav-item{justify-content:center}
@media(max-width:1080px){.nav-section{display:none}.nav-group{margin-bottom:13px}}
@media(max-width:820px){.top-left{min-width:0}}

/* Visual hierarchy: active navigation is a vivid anchored rail, not a pale text row. */
.shell{background:transparent}
.sidebar{background:linear-gradient(180deg,#fdfefe 0%,#f7fbff 100%);border-right:1px solid #d6e5f6;box-shadow:4px 0 26px rgba(38,83,153,.035)}
.brand{height:67px}
.brand-mark{width:46px;height:46px;border-radius:14px;background:linear-gradient(145deg,#2767eb,#4aa1fa);box-shadow:0 9px 24px rgba(37,99,235,.23)}
.brand-copy b{font-size:19px;color:#14294d}
.brand-copy small{font-size:12px;color:#8496ae}
.nav-section{font-size:12px;font-weight:790;color:#92a0b5;padding:15px 14px 7px}
.nav-item{min-height:49px;padding:12px 14px;font-size:14px;font-weight:590;border-radius:11px;gap:13px}
.nav-item:hover{background:#eaf3ff}
.nav-item.router-link-exact-active{background:linear-gradient(95deg,#e7f1ff,#f1f7ff);color:#195bd0;box-shadow:inset 4px 0 #3274ed,0 4px 13px rgba(42,93,172,.08)}
.topbar{background:rgba(255,255,255,.96);border-bottom:1px solid #d4e2f4;box-shadow:0 3px 15px rgba(30,75,153,.045)}
.command{border:1px solid #d4e1f4;background:#f1f6fe;height:42px;border-radius:11px}
.command:hover{background:white;border-color:#a7c5f5}
.soft-action{background:linear-gradient(105deg,#2767ec,#4485f2);color:white!important;border:0;border-radius:9px;padding:11px 15px;font-size:13px;box-shadow:0 6px 17px rgba(37,99,235,.17)}
.soft-action:hover{filter:brightness(1.045)}
.crumb{font-size:14px;font-weight:680}
.sidebar-foot{background:rgba(240,246,255,.67);border-radius:10px}

.nav{overflow-y:auto;scrollbar-width:thin;scrollbar-color:#d0dff4 transparent;min-height:0}.sidebar{min-height:0}.mobile-links a{font-size:14px}.command-results button{font-size:14px}.command-results code{font-size:12px}
</style>
