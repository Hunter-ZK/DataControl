<template>
  <div class="dc-page metric-page"><div class="dc-container">
    <button class="dc-back" @click="router.back()"><ArrowLeft :size="16" />返回</button>
    <div v-if="loading" class="dc-empty">正在加载指标语义模型…</div>
    <template v-else-if="metric">
      <section class="metric-head dc-card">
        <div>
          <div class="head-tags"><span class="type-pill">{{ kindLabel(metric.metricKind) }}</span><span class="status">● {{ metric.status === 'ONLINE' ? '在用' : metric.status }}</span><span class="policy"><ShieldCheck :size="13" />仅内部可信证据</span></div>
          <h1>{{ metric.name }}</h1>
          <code class="metric-code">{{ metric.metricCode }}</code>
          <p>{{ metric.definition || metric.caliber || '暂无指标定义。' }}</p>
        </div>
        <div class="head-actions">
          <RouterLink :to="`/datasets/${metric.source.assetId}`" class="soft-action"><Database :size="15" />查看来源资产</RouterLink>
          <button class="primary-action" @click="askMetric"><Sparkles :size="15" />用此指标提问</button>
        </div>
      </section>

      <div class="metric-layout">
        <main class="metric-main">
          <section class="formula-card dc-card">
            <div class="section-head"><div><span class="dc-eyebrow">SEMANTIC MODEL</span><h2>计算语义</h2></div><span class="kind-badge">{{ metric.metricKind }}</span></div>
            <div class="formula-grid">
              <div class="formula-main"><span>计算表达式</span><strong>{{ formulaText }}</strong><small v-if="metric.metricKind === 'BASE'">{{ metric.aggregation.toUpperCase() }} · {{ metric.measureColumn }}</small><small v-else>{{ dependencyText }}</small></div>
              <div><span>聚合方式</span><b>{{ metric.aggregation.toUpperCase() }}</b></div>
              <div><span>度量字段</span><code>{{ metric.measureColumn }}</code></div>
              <div><span>时间可加性</span><b :class="{ danger: metric.time.additivity === 'NON_ADDITIVE' }">{{ additivityLabel(metric.time.additivity) }}</b></div>
            </div>
          </section>

          <section class="dc-card source-card">
            <div class="section-head"><div><span class="dc-eyebrow">SOURCE & TIME</span><h2>数据来源与统计周期</h2></div></div>
            <RouterLink :to="`/datasets/${metric.source.assetId}`" class="source-row">
              <span class="layer-chip" :data-layer="metric.source.layerCode">{{ metric.source.layerCode || 'TABLE' }}</span>
              <div><b>{{ metric.source.name }}</b><code>{{ metric.source.tableName }}</code></div>
              <ArrowRight :size="16" />
            </RouterLink>
            <div class="time-grid">
              <div><span>时间字段</span><code>{{ metric.time.field }}</code></div>
              <div><span>时间粒度</span><b>{{ metric.time.grain || '未登记' }}</b></div>
              <div><span>最新期策略</span><b>{{ metric.time.latestStrategy }}</b><small>本期 / 当前 / 最新统一按该策略解析</small></div>
              <div><span>跨期规则</span><b>{{ additivityLabel(metric.time.additivity) }}</b><small v-if="metric.time.additivity === 'NON_ADDITIVE'">余额/快照类指标禁止跨期直接求和</small></div>
            </div>
          </section>

          <section class="dc-card dimension-card">
            <div class="section-head"><div><span class="dc-eyebrow">DIMENSIONS</span><h2>可用维度与码值</h2></div><span>{{ metric.validDimensions.length }} 个维度</span></div>
            <div class="dimension-list">
              <article v-for="dimension in metric.validDimensions" :key="dimension.name">
                <div><b>{{ dimension.label }}</b><code>{{ dimension.name }}</code></div>
                <span>{{ dimension.dataType || '—' }}</span>
                <RouterLink v-if="dimension.codeTableNo" :to="`/code-tables/${dimension.codeTableNo}`">{{ dimension.codeTableNo }}</RouterLink>
                <RouterLink v-else-if="dimension.standardNo" :to="`/standards/${dimension.standardNo}`">{{ dimension.standardNo }}</RouterLink>
                <em v-else>无关联码表</em>
              </article>
            </div>
          </section>

          <section class="dc-card governance-card">
            <div class="section-head"><div><span class="dc-eyebrow">GOVERNANCE</span><h2>口径约束</h2></div></div>
            <div v-if="metric.mandatoryFilters.length" class="filter-list">
              <article v-for="(filter,index) in metric.mandatoryFilters" :key="index"><span>必选过滤</span><code>{{ filterText(filter) }}</code></article>
            </div>
            <div v-else class="empty-inline">当前指标没有登记强制过滤条件。</div>
            <div class="caliber"><b>统计口径</b><p>{{ metric.caliber || '暂无补充口径。' }}</p></div>
            <div class="notes"><b>语义说明</b><p>{{ metric.semanticNotes || '暂无补充说明。' }}</p></div>
          </section>
        </main>

        <aside class="metric-side">
          <section class="dc-card side-card"><span class="dc-eyebrow">ALIASES</span><h3>同义词</h3><div class="tag-list"><span v-for="alias in metric.aliases" :key="alias">{{ alias }}</span><em v-if="!metric.aliases.length">未登记</em></div></section>
          <section class="dc-card side-card"><span class="dc-eyebrow">STATISTICAL SYSTEM</span><h3>治理归属</h3><dl><div><dt>统计制度</dt><dd>{{ metric.statSystemCode || '—' }}</dd></div><div><dt>Asset ID</dt><dd><code>{{ metric.assetId }}</code></dd></div><div><dt>研究策略</dt><dd>内部证据优先，不使用外部网络</dd></div></dl></section>
          <section class="dc-card yaml-card"><span class="dc-eyebrow">MODEL PREVIEW</span><h3>语义模型</h3><pre>{{ modelPreview }}</pre></section>
        </aside>
      </div>
    </template>
    <div v-else class="dc-empty">未找到指标语义模型。</div>
  </div></div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Database, ShieldCheck, Sparkles } from 'lucide-vue-next'
import { semanticApi, type SemanticMetric } from '@/api/client'

const route = useRoute()
const router = useRouter()
const metric = ref<SemanticMetric | null>(null)
const loading = ref(true)

const formulaText = computed(() => {
  if (!metric.value) return '—'
  if (metric.value.formula) return metric.value.formula
  return `${metric.value.aggregation.toUpperCase()}(${metric.value.measureColumn})`
})
const dependencyText = computed(() => {
  if (!metric.value) return ''
  const values = [metric.value.numeratorMetricCode, metric.value.denominatorMetricCode].filter(Boolean)
  return values.length ? `依赖：${values.join(' / ')}` : '派生指标'
})
const modelPreview = computed(() => {
  if (!metric.value) return ''
  const m = metric.value
  return [
    `metric: ${m.metricCode}`,
    `kind: ${m.metricKind}`,
    `aggregation: ${m.aggregation}`,
    `measure: ${m.measureColumn}`,
    m.formula ? `formula: ${m.formula}` : '',
    `source: ${m.source.tableName || m.source.assetId}`,
    `time_field: ${m.time.field}`,
    `time_grain: ${m.time.grain || 'unknown'}`,
    `latest: ${m.time.latestStrategy}`,
    `time_additivity: ${m.time.additivity}`,
    `dimensions: [${m.validDimensions.map((d) => d.name).join(', ')}]`,
    `research_policy: ${m.researchPolicy}`,
  ].filter(Boolean).join('\n')
})

function kindLabel(value: string) { return { BASE: '基础指标', RATIO: '比率指标', DERIVED: '派生指标' }[value] || value }
function additivityLabel(value: string) { return value === 'NON_ADDITIVE' ? '时间不可加' : '可加' }
function filterText(filter: Record<string, unknown>) { return `${String(filter.field || '')} ${String(filter.op || '=')} ${String(filter.label || filter.value || '')}`.trim() }
function askMetric() { if (!metric.value) return; router.push({ name: 'agent', query: { q: `请基于受治理指标“${metric.value.name}”（metric_id=${metric.value.metricCode}）回答我的问题，并严格遵守其时间、维度和必选过滤口径。` } }) }

onMounted(async () => {
  try { metric.value = await semanticApi.metric(String(route.params.code)) } finally { loading.value = false }
})
</script>

<style scoped>
.metric-page{background:#eef6fa;min-height:100%}.metric-head{padding:25px 27px;display:flex;justify-content:space-between;align-items:center;gap:22px}.head-tags{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.type-pill{padding:4px 8px;border-radius:999px;background:#dff1f8;color:#176f94;font-size:9px;font-weight:800}.status{font-size:10px;color:#237759}.policy{display:flex;align-items:center;gap:4px;padding:4px 7px;border-radius:999px;background:#e9f5ef;color:#2e725d;font-size:9px}.metric-head h1{font-size:30px;margin:9px 0 5px;color:#153f54}.metric-code{font-size:12px;color:#2b718f}.metric-head p{font-size:12px;line-height:1.65;color:#587484;max-width:760px;margin:8px 0 0}.head-actions{display:flex;gap:8px}.soft-action,.primary-action{display:flex;align-items:center;gap:6px;padding:9px 11px;border-radius:9px;font-size:10px;font-weight:700;white-space:nowrap}.soft-action{background:#edf7fb;color:#236f8f}.primary-action{border:0;background:#177da7;color:#fff;cursor:pointer}.metric-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:15px;margin-top:15px;align-items:start}.metric-main,.metric-side{display:grid;gap:14px}.formula-card,.source-card,.dimension-card,.governance-card,.side-card,.yaml-card{padding:18px}.section-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}.section-head h2{font-size:17px;margin:4px 0 0;color:#214c61}.section-head>span{font-size:9px;color:#738b97}.kind-badge{padding:4px 7px;border-radius:6px;background:#e9f4f8;color:#27718f;font-weight:800}.formula-grid{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:9px}.formula-grid>div{padding:13px;border:1px solid #dbe7ec;border-radius:9px;background:#fbfdfe}.formula-grid span,.time-grid span{display:block;font-size:9px;color:#778e9a;margin-bottom:5px}.formula-main strong{display:block;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;color:#165f80;overflow-wrap:anywhere}.formula-grid b,.formula-grid code{font-size:11px}.formula-grid small{display:block;font-size:8px;color:#78909c;margin-top:5px}.danger{color:#a45d18}.source-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:9px;align-items:center;padding:12px;border:1px solid #d9e7ed;border-radius:9px;background:#f8fcfd;color:#2c566a}.source-row div{min-width:0}.source-row b,.source-row code{display:block}.source-row b{font-size:11px}.source-row code{font-size:9px;color:#708894;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.layer-chip{padding:3px 6px;border-radius:5px;background:#e4f2f8;color:#176f94;font-size:8px;font-weight:800}.time-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:10px}.time-grid>div{padding:11px;border:1px solid #e0e9ed;border-radius:8px}.time-grid b,.time-grid code{font-size:10px}.time-grid small{display:block;font-size:8px;color:#7b919c;margin-top:4px;line-height:1.45}.dimension-list{display:grid}.dimension-list article{display:grid;grid-template-columns:minmax(0,1fr) 90px 130px;gap:10px;align-items:center;padding:10px 4px;border-top:1px solid #edf2f4}.dimension-list article:first-child{border-top:0}.dimension-list b,.dimension-list code{display:block}.dimension-list b{font-size:11px}.dimension-list code{font-size:9px;color:#718b98;margin-top:2px}.dimension-list>article>span,.dimension-list a,.dimension-list em{font-size:9px;color:#587989;font-style:normal}.dimension-list a{color:#167397}.filter-list{display:grid;gap:7px}.filter-list article{display:grid;grid-template-columns:80px 1fr;gap:9px;padding:9px 10px;border-radius:8px;background:#f1f8fb}.filter-list span{font-size:9px;color:#6e8794}.filter-list code{font-size:10px;color:#255f79}.empty-inline{font-size:10px;color:#7b909b;padding:8px 0}.caliber,.notes{margin-top:10px;padding:11px 12px;border:1px solid #e0e9ed;border-radius:9px}.caliber b,.notes b{font-size:10px;color:#285f78}.caliber p,.notes p{font-size:10px;line-height:1.6;color:#657f8d;margin:5px 0 0}.side-card h3,.yaml-card h3{font-size:15px;margin:5px 0 11px;color:#214b60}.tag-list{display:flex;flex-wrap:wrap;gap:6px}.tag-list span{padding:5px 7px;border-radius:999px;background:#edf6f9;color:#3c7187;font-size:9px}.tag-list em{font-size:9px;color:#8497a0;font-style:normal}.side-card dl{display:grid;gap:11px;margin:0}.side-card dl div{display:grid;gap:3px}.side-card dt{font-size:8px;color:#81939d}.side-card dd{margin:0;font-size:10px;color:#345d70;line-height:1.5}.yaml-card pre{margin:0;padding:12px;border-radius:8px;background:#122a39;color:#d6edf7;overflow:auto;font-size:9px;line-height:1.6}.dc-back{margin-bottom:12px}@media(max-width:1100px){.metric-layout{grid-template-columns:1fr}.metric-side{grid-template-columns:1fr 1fr}.yaml-card{grid-column:1/-1}.formula-grid{grid-template-columns:1fr 1fr}.time-grid{grid-template-columns:1fr 1fr}}@media(max-width:720px){.metric-head{align-items:flex-start;flex-direction:column}.head-actions{width:100%}.soft-action,.primary-action{flex:1;justify-content:center}.metric-side{grid-template-columns:1fr}.yaml-card{grid-column:auto}.formula-grid,.time-grid{grid-template-columns:1fr}.dimension-list article{grid-template-columns:1fr}.dimension-list article>*{justify-self:start}}
</style>
