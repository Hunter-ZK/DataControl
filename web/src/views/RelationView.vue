<template>
  <div class="dc-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16"/>返回</button>
    <section class="dc-page-head"><div><span class="dc-eyebrow">LINEAGE & IMPACT</span><h1 class="dc-title">关系指引</h1><p class="dc-subtitle">从当前数据集展开上下游、查询路径并评估下游影响范围。</p></div></section>

    <section class="dc-card relation-toolbar">
      <div><span>中心资产</span><el-input v-model="assetId" placeholder="例如 DS000001" @keyup.enter="loadGraph"/></div>
      <div><span>展开层级</span><el-select v-model="depth" @change="loadGraph"><el-option v-for="x in [1,2,3,4,5]" :key="x" :label="`${x} 层`" :value="x"/></el-select></div>
      <div><span>方向</span><el-select v-model="direction" @change="loadGraph"><el-option label="上下游" value="both"/><el-option label="仅上游" value="upstream"/><el-option label="仅下游" value="downstream"/></el-select></div>
      <el-button type="primary" @click="loadGraph"><RefreshCw :size="15"/>重新加载</el-button>
    </section>

    <section class="dc-card graph-panel">
      <div class="panel-head"><div><b>{{ graph.nodes.length }} 个节点 · {{ graph.edges.length }} 条关系</b><span v-if="graph.truncated" class="warn">节点过多，已截断展示</span></div><RouterLink v-if="assetId" :to="`/datasets/${assetId}`">查看中心资产</RouterLink></div>
      <div v-if="loading" class="dc-empty">正在加载关系图…</div>
      <div v-else-if="graph.nodes.length===0" class="dc-empty">输入一个数据集 Asset ID 开始查看关系。</div>
      <div v-else class="lineage-lanes">
        <div v-for="lane in lanes" :key="lane.level" class="lane" :class="{center:lane.level===0}">
          <div class="lane-title">{{ laneTitle(lane.level) }}</div>
          <div class="lane-nodes">
            <RouterLink v-for="node in lane.nodes" :key="node.assetId" :to="`/datasets/${node.assetId}`" class="node-card" :class="{current:node.isCenter}">
              <div><span class="dc-chip">{{node.layerCode||'TABLE'}}</span><span class="node-status">{{node.status||'—'}}</span></div>
              <b>{{node.name}}</b><code class="dc-tech">{{node.tableName||node.assetId}}</code><small>{{node.catalogCode||'未分类'}}</small>
            </RouterLink>
          </div>
        </div>
      </div>
    </section>

    <div class="analysis-grid">
      <section class="dc-card impact-panel">
        <span class="dc-eyebrow">IMPACT</span><h2>影响分析</h2>
        <p>从中心资产向下游展开，统计潜在受影响资产。CONFIRMED 与 INFERRED 关系均展示，但不会被解释为绝对影响事实。</p>
        <div class="impact-stat"><strong>{{ impact.impactCount || 0 }}</strong><span>潜在受影响资产</span></div>
        <div class="layer-tags"><span v-for="(count,key) in impact.impactByLayer||{}" :key="key"><b>{{key}}</b>{{count}}</span></div>
        <el-button @click="loadImpact">重新计算 {{depth}} 层影响</el-button>
      </section>

      <section class="dc-card path-panel">
        <span class="dc-eyebrow">PATH FINDER</span><h2>路径查询</h2><p>沿确认的数据加工方向查找从源表到目标表的一条最短路径。</p>
        <div class="path-form"><el-input v-model="pathSource" placeholder="源 Asset ID"/><ArrowRight :size="18"/><el-input v-model="pathTarget" placeholder="目标 Asset ID"/><el-button type="primary" @click="findPath">查找</el-button></div>
        <div v-if="pathResult && !pathResult.found" class="dc-empty compact">在限定层级内未找到路径。</div>
        <div v-else-if="pathResult?.found" class="path-result">
          <span>{{pathResult.hopCount}} 跳</span>
          <template v-for="(node,index) in pathResult.nodes" :key="node.assetId"><RouterLink :to="`/datasets/${node.assetId}`">{{node.name}}</RouterLink><ArrowRight v-if="Number(index)<pathResult.nodes.length-1" :size="14"/></template>
        </div>
      </section>
    </div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, RefreshCw } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { relationApi, type RelationGraph, type RelationNode } from '@/api/client'

const route=useRoute(); const router=useRouter(); const assetId=ref(String(route.params.id||route.query.id||'DS000001')); const depth=ref(2); const direction=ref('both'); const loading=ref(false); const graph=reactive<RelationGraph>({centerAssetId:'',depth:2,direction:'both',truncated:false,nodes:[],edges:[]}); const impact=reactive<any>({impactCount:0,impactByLayer:{}}); const pathSource=ref(assetId.value); const pathTarget=ref(''); const pathResult=ref<any|null>(null)
const levelMap=computed(()=>{
  const levels=new Map<string,number>(); if(!graph.centerAssetId)return levels; levels.set(graph.centerAssetId,0)
  for(let pass=0;pass<depth.value;pass++){
    let changed=false
    for(const edge of graph.edges){const s=levels.get(edge.source);const t=levels.get(edge.target);if(s!==undefined&&s>=0&&t===undefined){levels.set(edge.target,s+1);changed=true}if(t!==undefined&&t<=0&&s===undefined){levels.set(edge.source,t-1);changed=true}}
    if(!changed)break
  }
  return levels
})
const lanes=computed(()=>{
  const groups=new Map<number,RelationNode[]>(); for(const node of graph.nodes){const level=levelMap.value.get(node.assetId)??0;const list=groups.get(level)||[];list.push(node);groups.set(level,list)}
  return [...groups.entries()].sort((a,b)=>a[0]-b[0]).map(([level,nodes])=>({level,nodes}))
})
function laneTitle(level:number){if(level===0)return '当前资产';return level<0?`上游 ${Math.abs(level)} 层`:`下游 ${level} 层`}
async function loadGraph(){if(!assetId.value.trim())return;loading.value=true;try{Object.assign(graph,await relationApi.graph(assetId.value.trim(),{depth:depth.value,direction:direction.value}));pathSource.value=assetId.value.trim();await loadImpact();await router.replace({name:'relations',params:{id:assetId.value.trim()}})}catch{ElMessage.error('关系加载失败，请确认 Asset ID 是否存在')}finally{loading.value=false}}
async function loadImpact(){if(!assetId.value.trim())return;try{Object.assign(impact,await relationApi.impact(assetId.value.trim(),{depth:depth.value}))}catch{impact.impactCount=0;impact.impactByLayer={}}}
async function findPath(){if(!pathSource.value.trim()||!pathTarget.value.trim())return;try{pathResult.value=await relationApi.path(pathSource.value.trim(),pathTarget.value.trim(),12)}catch{ElMessage.error('路径查询失败')}}
watch(()=>route.params.id,(v)=>{if(typeof v==='string'&&v!==assetId.value){assetId.value=v;loadGraph()}})
onMounted(loadGraph)
</script>

<style scoped>
.relation-toolbar{padding:15px 18px;display:grid;grid-template-columns:minmax(220px,1.5fr) 150px 160px auto;gap:12px;align-items:end}.relation-toolbar>div{display:grid;gap:6px}.relation-toolbar span{font-size:10px;color:var(--dc-text-3)}.relation-toolbar :deep(.el-button>span){display:flex;align-items:center;gap:6px}.graph-panel{margin-top:16px;padding:0 18px 20px;overflow:hidden}.panel-head{min-height:58px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf2f5}.panel-head>div{display:flex;gap:10px;align-items:center}.panel-head b{font-size:12px}.panel-head a{font-size:11px;color:var(--dc-primary-strong)}.warn{font-size:10px;color:#b7791f}.lineage-lanes{display:flex;gap:12px;overflow:auto;padding:18px 2px 4px;min-height:300px}.lane{flex:1 0 220px;min-width:220px}.lane.center{flex-basis:250px}.lane-title{height:32px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#7892a1;text-transform:uppercase;letter-spacing:.08em}.lane-nodes{display:grid;gap:10px}.node-card{display:grid;gap:7px;padding:13px;border:1px solid var(--dc-border);border-radius:11px;background:#fff;box-shadow:0 6px 18px rgba(48,108,138,.04)}.node-card:hover{border-color:#b9dce9;box-shadow:0 10px 26px rgba(48,108,138,.08)}.node-card.current{border-color:#7cc6df;background:linear-gradient(135deg,#eef9fd,#fff);box-shadow:0 10px 30px rgba(60,145,181,.11)}.node-card>div{display:flex;justify-content:space-between;align-items:center}.node-status{font-size:9px;color:#7d97a6}.node-card b{font-size:12px}.node-card code{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.node-card small{font-size:9px;color:var(--dc-text-3)}.analysis-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:16px;margin-top:16px}.impact-panel,.path-panel{padding:22px}.impact-panel h2,.path-panel h2{font-size:18px;margin:6px 0 8px}.impact-panel p,.path-panel p{font-size:11px;line-height:1.7;color:var(--dc-text-2)}.impact-stat{display:flex;align-items:baseline;gap:8px;margin:18px 0}.impact-stat strong{font-size:34px;color:#27789b}.impact-stat span{font-size:11px;color:var(--dc-text-3)}.layer-tags{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:15px}.layer-tags span{padding:6px 9px;border-radius:999px;background:#f2f8fb;font-size:10px;color:#698596}.layer-tags b{margin-right:5px;color:#2f718f}.path-form{display:grid;grid-template-columns:1fr auto 1fr auto;gap:8px;align-items:center;margin-top:18px}.path-result{margin-top:17px;padding:13px;border-radius:10px;background:#f5fafc;display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:11px}.path-result>span{padding:4px 7px;border-radius:999px;background:#dff2f8;color:#2e7896}.path-result a{color:#285f7a;font-weight:700}.compact{padding:18px 0}@media(max-width:1000px){.relation-toolbar{grid-template-columns:1fr 1fr}.analysis-grid{grid-template-columns:1fr}}@media(max-width:680px){.relation-toolbar{grid-template-columns:1fr}.path-form{grid-template-columns:1fr}.path-form>svg{transform:rotate(90deg);justify-self:center}.lineage-lanes{min-height:0}}
</style>
