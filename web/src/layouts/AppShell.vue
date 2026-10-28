<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">D</span>
        <span class="brand-copy"><b>DataControl</b><small>DATA ASSET PORTAL</small></span>
      </RouterLink>

      <nav class="nav">
        <span class="nav-section">工作台</span>
        <RouterLink v-for="item in primary" :key="item.to" :to="item.to" class="nav-item">
          <component :is="item.icon" :size="18" stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>
        <div class="nav-divider" />
        <span class="nav-section">个人与统计</span>
        <RouterLink v-for="item in secondary" :key="item.to" :to="item.to" class="nav-item">
          <component :is="item.icon" :size="18" stroke-width="1.8" />
          <span>{{ item.label }}</span>
        </RouterLink>
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
          <span class="crumb">{{ route.meta.title || 'DataControl' }}</span>
        </div>
        <button class="command" @click="commandOpen=true">
          <Search :size="17" /><span>搜索数据集、字段、指标、标准…</span><kbd>⌘ K</kbd>
        </button>
        <div class="top-actions">
          <RouterLink to="/agent" class="soft-action"><Sparkles :size="17" />智能问数</RouterLink>
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
    </div>
    <el-drawer v-model="mobileNavOpen" title="DataControl 导航" direction="ltr" size="min(300px,85vw)">
      <div class="mobile-links">
        <RouterLink v-for="item in [...primary,...secondary]" :key="item.to" :to="item.to" @click="mobileNavOpen=false">
          <component :is="item.icon" :size="18"/>{{item.label}}
        </RouterLink>
      </div>
    </el-drawer>
    <el-dialog v-model="commandOpen" title="快速查找数据资产" width="min(620px,95vw)" class="command-dialog">
      <el-input v-model="commandQuery" autofocus placeholder="数据集、指标、字段或标准名称"
        @input="loadCommandSuggestions" @keydown.enter="openCommandSearch"/>
      <div class="command-results">
        <button v-for="item in commandSuggestions" :key="item.assetType+item.assetId"
          @click="chooseCommand(item)"><b>{{item.title}}</b><code>{{item.technicalName}}</code><small>{{item.assetType}}</small></button>
        <button v-if="commandQuery.trim()" @click="openCommandSearch">查看完整检索结果：{{commandQuery}}</button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, BarChart3, BookOpenCheck, Boxes, CircleGauge, Database, Hash, Menu, Search, Sparkles, UserRound } from 'lucide-vue-next'
import { assetApi, type SearchSuggestion } from '@/api/client'

const router = useRouter()
const mobileNavOpen=ref(false)
const commandOpen=ref(false)
const commandQuery=ref('')
const commandSuggestions=ref<SearchSuggestion[]>([])
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
  { to: '/catalog', label: '资产目录', icon: Database },
  { to: '/search', label: '资产检索', icon: Search },
  { to: '/code-tables', label: '标准码值', icon: Boxes },
  { to: '/word-roots', label: '词根索引', icon: Hash },
  { to: '/metrics', label: '指标与制度', icon: BookOpenCheck },
  { to: '/agent', label: '智能问数', icon: Sparkles },
]
const secondary = [
  { to: '/overview', label: '数据概览', icon: BarChart3 },
  { to: '/profile', label: '个人中心', icon: UserRound },
]

function goSearch() { router.push({ name: 'search' }) }
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
 .command-results{display:grid;gap:4px;max-height:340px;overflow:auto;margin-top:12px;}
 .command-results button{display:flex;align-items:center;gap:9px;padding:12px 8px;border:0;border-radius:7px;background:white;color:var(--dc-text);text-align:left;cursor:pointer;}
 .command-results button:hover{background:var(--dc-primary-soft);}
 .command-results button code{color:var(--dc-text-2);font-size:12px;}
 .command-results button small{margin-left:auto;color:var(--dc-text-3);font-size:12px;}
 @media(max-width:820px){.mobile-menu{display:grid;}}
</style>
