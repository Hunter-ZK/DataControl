import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/layouts/AppShell.vue'
import HomeView from '@/views/HomeView.vue'
import SearchView from '@/views/SearchView.vue'
import CatalogView from '@/views/CatalogView.vue'
import DatasetDetailView from '@/views/DatasetDetailView.vue'
import FieldDetailView from '@/views/FieldDetailView.vue'
import CodeTableDetailView from '@/views/CodeTableDetailView.vue'
import DataStandardDetailView from '@/views/DataStandardDetailView.vue'
import ReferenceDetailView from '@/views/ReferenceDetailView.vue'
import OverviewView from '@/views/OverviewView.vue'
import ReferenceListView from '@/views/ReferenceListView.vue'
import ProfileView from '@/views/ProfileView.vue'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    {
      path: '/', component: AppShell, children: [
        { path: '', name: 'home', component: HomeView, meta: { title: '首页' } },
        { path: 'overview', name: 'overview', component: OverviewView, meta: { title: '数据概览' } },
        { path: 'catalog', name: 'catalog', component: CatalogView, meta: { title: '资产目录' } },
        { path: 'search', name: 'search', component: SearchView, meta: { title: '资产检索' } },
        { path: 'datasets/:id', name: 'dataset', component: DatasetDetailView, meta: { title: '数据集详情' } },
        { path: 'fields/:id', name: 'field', component: FieldDetailView, meta: { title: '字段详情' } },
        { path: 'code-tables', name: 'codeTables', component: ReferenceListView, props: { kind: 'code-tables' }, meta: { title: '标准码值' } },
        { path: 'code-tables/:no', name: 'codeTable', component: CodeTableDetailView, meta: { title: '码表详情' } },
        { path: 'standards', name: 'standards', component: ReferenceListView, props: { kind: 'data-standards' }, meta: { title: '数据标准' } },
        { path: 'standards/:no', name: 'standard', component: DataStandardDetailView, meta: { title: '数据标准详情' } },
        { path: 'word-roots', name: 'wordRoots', component: ReferenceListView, props: { kind: 'word-roots' }, meta: { title: '词根索引' } },
        { path: 'word-roots/:root', name: 'wordRoot', component: ReferenceDetailView, props: { kind: 'word-roots' }, meta: { title: '词根详情' } },
        { path: 'metrics', name: 'metrics', component: ReferenceListView, props: { kind: 'metrics' }, meta: { title: '指标与制度' } },
        { path: 'metrics/:code', name: 'metric', component: ReferenceDetailView, props: { kind: 'metrics' }, meta: { title: '指标详情' } },
        { path: 'stat-systems', name: 'statSystems', component: ReferenceListView, props: { kind: 'stat-systems' }, meta: { title: '统计制度' } },
        { path: 'stat-systems/:code', name: 'statSystem', component: ReferenceDetailView, props: { kind: 'stat-systems' }, meta: { title: '统计制度详情' } },
        { path: 'profile', name: 'profile', component: ProfileView, meta: { title: '个人中心' } },
      ],
    },
  ],
})

router.afterEach((to) => { document.title = `${String(to.meta.title || 'DataControl')} · DataControl` })
export default router
