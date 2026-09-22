<template>
  <div class="relation-panel">
    <header class="panel-head">
      <div>
        <span class="dc-eyebrow">RELATION GUIDANCE</span>
        <h3>关系与血缘</h3>
        <p>从当前数据资产直接查看表级上下游与字段级血缘；复杂路径、影响分析和多层展开可进入完整关系工作区。</p>
      </div>
      <RouterLink class="open-workspace" :to="`/relations/${datasetId}`">
        <ExternalLink :size="14" />展开完整关系分析
      </RouterLink>
    </header>

    <div v-if="loading" class="dc-empty">正在加载关系与血缘…</div>
    <template v-else>
      <section class="summary-grid">
        <div><span>上游资产</span><strong>{{ upstreamCount }}</strong></div>
        <div><span>下游资产</span><strong>{{ downstreamCount }}</strong></div>
        <div><span>字段血缘</span><strong>{{ fieldEdgeCount }}</strong></div>
        <div><span>已确认关系</span><strong>{{ confirmedCount }}</strong></div>
      </section>

      <section class="mini-graph dc-card">
        <div class="graph-head">
          <div><b>表级血缘预览</b><span>2 层上下游</span></div>
          <div class="legend"><span><i class="solid" />已确认</span><span><i class="dashed" />推断</span></div>
        </div>
        <div v-if="!graph.nodes.length" class="dc-empty">当前数据集暂无表级血缘。</div>
        <div v-else class="graph-scroll">
          <div class="graph-stage" :style="{ width: `${graphWidth}px`, height: `${graphHeight}px` }">
            <svg class="edges" :width="graphWidth" :height="graphHeight" :viewBox="`0 0 ${graphWidth} ${graphHeight}`">
              <defs>
                <marker id="detail-arrow-confirmed" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2185ab" /></marker>
                <marker id="detail-arrow-inferred" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#8caab8" /></marker>
              </defs>
              <path
                v-for="edge in graph.edges"
                :key="edge.id"
                :d="edgePath(edge)"
                class="edge"
                :class="{ inferred: edge.evidence === 'INFERRED' }"
                :marker-end="edge.evidence === 'INFERRED' ? 'url(#detail-arrow-inferred)' : 'url(#detail-arrow-confirmed)'"
              />
            </svg>
            <div v-for="lane in lanes" :key="lane.level" class="lane-title" :style="{ left: `${lane.x}px` }">{{ laneTitle(lane.level) }}</div>
            <RouterLink
              v-for="node in graph.nodes"
              :key="node.assetId"
              :to="`/datasets/${node.assetId}`"
              class="graph-node"
              :class="{ center: node.isCenter }"
              :style="nodeStyle(node.assetId)"
            >
              <div><span class="layer-chip" :data-layer="node.layerCode">{{ node.layerCode || 'TABLE' }}</span><em v-if="node.isCenter">当前</em></div>
              <b>{{ node.name }}</b>
              <code>{{ node.tableName || node.assetId }}</code>
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="field-section">
        <div class="field-head">
          <div><b>字段级血缘</b><span>当前表相关字段关系事实</span></div>
          <RouterLink :to="{ name: 'relations', query: { mode: 'field' } }">进入字段血缘工作区 <ArrowRight :size="13" /></RouterLink>
        </div>
        <div v-if="fieldRows.length" class="field-list">
          <article v-for="edge in fieldRows" :key="edge.id">
            <span class="relation-type">{{ edge.relationType || 'DIRECT' }}</span>
            <RouterLink :to="`/fields/${edge.source}`"><code>{{ nodeLabel(edge.source) }}</code></RouterLink>
            <ArrowRight :size="13" />
            <RouterLink :to="`/fields/${edge.target}`"><code>{{ nodeLabel(edge.target) }}</code></RouterLink>
            <small>{{ edge.transformation || '直接映射' }}</small>
          </article>
        </div>
        <div v-else class="dc-empty compact">当前表暂无字段级血缘。</div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, ExternalLink } from 'lucide-vue-next'
import { relationApi, type RelationEdge, type RelationGraph, type RelationNode, type TableFieldLineage } from '@/api/client'

const props = defineProps<{ datasetId: string }>()
const loading = ref(true)
const graph = reactive<RelationGraph>({ centerAssetId: '', depth: 2, direction: 'both', truncated: false, nodes: [], edges: [] })
const fields = reactive<TableFieldLineage>({ datasetId: '', nodes: [], edges: [] })
const nodeW = 150
const nodeH = 68
const laneW = 182
const laneGap = 28

const upstreamCount = computed(() => graph.nodes.filter((node) => Number(node.level || 0) < 0).length)
const downstreamCount = computed(() => graph.nodes.filter((node) => Number(node.level || 0) > 0).length)
const fieldEdgeCount = computed(() => fields.edges.length)
const confirmedCount = computed(() => graph.edges.filter((edge) => edge.evidence !== 'INFERRED').length)
const fieldRows = computed(() => fields.edges.slice(0, 8))
const levelValues = computed(() => Array.from(new Set(graph.nodes.map((node) => Number(node.level || 0)))).sort((a, b) => a - b))
const lanes = computed(() => levelValues.value.map((level, index) => ({ level, x: 28 + index * (laneW + laneGap) })))
const positionMap = computed(() => {
  const map = new Map<string, { x: number; y: number }>()
  for (const [laneIndex, level] of levelValues.value.entries()) {
    const nodes = graph.nodes.filter((node) => Number(node.level || 0) === level)
    nodes.forEach((node, index) => map.set(node.assetId, { x: 28 + laneIndex * (laneW + laneGap), y: 48 + index * (nodeH + 24) }))
  }
  return map
})
const maxLaneNodes = computed(() => Math.max(1, ...levelValues.value.map((level) => graph.nodes.filter((node) => Number(node.level || 0) === level).length)))
const graphWidth = computed(() => Math.max(720, 56 + levelValues.value.length * (laneW + laneGap)))
const graphHeight = computed(() => Math.max(260, 82 + maxLaneNodes.value * (nodeH + 24)))
const fieldNodeMap = computed(() => new Map(fields.nodes.map((node) => [node.assetId, node])))

function laneTitle(level: number) { return level === 0 ? '当前资产' : level < 0 ? `上游 ${Math.abs(level)} 层` : `下游 ${level} 层` }
function nodeStyle(id: string) { const pos = positionMap.value.get(id) || { x: 0, y: 0 }; return { left: `${pos.x}px`, top: `${pos.y}px`, width: `${nodeW}px`, height: `${nodeH}px` } }
function edgePath(edge: RelationEdge) { const source = positionMap.value.get(edge.source); const target = positionMap.value.get(edge.target); if (!source || !target) return ''; const x1 = source.x + nodeW; const y1 = source.y + nodeH / 2; const x2 = target.x; const y2 = target.y + nodeH / 2; const mid = (x1 + x2) / 2; return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}` }
function nodeLabel(id: string) { const node = fieldNodeMap.value.get(id) as RelationNode | undefined; return node ? `${node.datasetName || node.datasetId}.${node.columnName || node.name}` : id }

onMounted(async () => {
  loading.value = true
  try {
    const [tableGraph, fieldLineage] = await Promise.all([
      relationApi.graph(props.datasetId, { depth: 2, direction: 'both' }),
      relationApi.tableFields(props.datasetId),
    ])
    Object.assign(graph, tableGraph)
    Object.assign(fields, fieldLineage)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.relation-panel{display:grid;gap:14px}.panel-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.panel-head h3{font-size:18px;margin:5px 0 7px;color:#214c61}.panel-head p{max-width:720px;font-size:11px;line-height:1.65;color:var(--dc-text-2);margin:0}.open-workspace{display:flex;align-items:center;gap:6px;padding:8px 10px;border-radius:8px;background:#e9f6fa;color:#176f93;font-size:10px;font-weight:700;white-space:nowrap}.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.summary-grid>div{padding:12px 14px;border:1px solid #dbe9ef;border-radius:10px;background:#f8fcfd}.summary-grid span{display:block;font-size:9px;color:#748d99}.summary-grid strong{display:block;font-size:22px;color:#255f79;margin-top:4px}.mini-graph{overflow:hidden}.graph-head{height:44px;display:flex;align-items:center;justify-content:space-between;padding:0 12px;border-bottom:1px solid #e5edf1}.graph-head>div:first-child{display:flex;gap:9px;align-items:center}.graph-head b{font-size:11px;color:#2a5367}.graph-head span,.legend{font-size:9px;color:#738d99}.legend{display:flex;gap:10px}.legend span{display:flex;align-items:center;gap:4px}.legend i{width:18px;border-top:1.5px solid #2185ab}.legend i.dashed{border-top-style:dashed;border-color:#8caab8}.graph-scroll{overflow:auto;min-height:280px}.graph-stage{position:relative}.edges{position:absolute;inset:0;z-index:1}.edge{fill:none;stroke:#2185ab;stroke-width:1.5}.edge.inferred{stroke:#8caab8;stroke-dasharray:5 5}.lane-title{position:absolute;top:16px;width:150px;text-align:center;font-size:8px;font-weight:800;color:#718994}.graph-node{position:absolute;z-index:2;padding:8px 9px;border:1px solid #c9dce5;border-radius:8px;background:#fff;box-shadow:0 4px 11px rgba(49,100,124,.07);display:grid;align-content:center;gap:4px;color:#284f63}.graph-node.center{border:2px solid #2186ad;background:#f1fbfe}.graph-node>div{display:flex;align-items:center;justify-content:space-between}.graph-node em{font-size:8px;font-style:normal;color:#14799e}.graph-node b{font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.graph-node code{font-size:8px;color:#728b97;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.layer-chip{padding:2px 5px;border-radius:4px;background:#edf3f6;color:#486575;font-size:7px;font-weight:800}.layer-chip[data-layer="ODS"]{background:#eeeafd;color:#4f3fa8}.layer-chip[data-layer="DWD"]{background:#e2f4f1;color:#0d6f68}.layer-chip[data-layer="DWS"]{background:#e3f1f8;color:#126b93}.layer-chip[data-layer="ADS"]{background:#fff3da;color:#83570a}.layer-chip[data-layer="DIM"]{background:#edf1f4;color:#44596a}.field-section{border:1px solid #dce8ed;border-radius:10px;overflow:hidden}.field-head{display:flex;justify-content:space-between;align-items:center;padding:11px 13px;background:#f8fbfc;border-bottom:1px solid #e6eef1}.field-head>div{display:flex;gap:8px;align-items:center}.field-head b{font-size:11px}.field-head span{font-size:9px;color:#78909b}.field-head a{display:flex;align-items:center;gap:4px;font-size:9px;color:#176f92}.field-list{display:grid}.field-list article{display:grid;grid-template-columns:90px minmax(0,1fr) auto minmax(0,1fr) minmax(120px,1fr);gap:8px;align-items:center;padding:9px 12px;border-bottom:1px solid #edf2f4}.field-list article:last-child{border-bottom:0}.field-list code{font-size:9px;color:#315d71}.field-list small{font-size:8px;color:#718a96;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.relation-type{font-size:8px;font-weight:800;color:#147a9f}.compact{padding:16px}@media(max-width:900px){.summary-grid{grid-template-columns:1fr 1fr}.panel-head{flex-direction:column}.field-list article{grid-template-columns:80px minmax(0,1fr) auto minmax(0,1fr)}.field-list small{grid-column:2/-1}}@media(max-width:620px){.summary-grid{grid-template-columns:1fr 1fr}.field-list article{grid-template-columns:1fr}.field-list article svg{display:none}}
</style>
