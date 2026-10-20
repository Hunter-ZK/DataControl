<template>
  <section class="demo-report" aria-label="交互演示结果">
    <header class="report-intro">
      <div class="report-eyebrow"><Sparkles :size="15" /> DataAgent · 交互演示 <span>全部使用模拟数据</span></div>
      <div class="report-title-row">
        <div>
          <h2>{{ title }}</h2>
          <p>{{ description }}</p>
        </div>
        <button class="restart" type="button" @click="emit('reset')"><RotateCcw :size="15" /> 新问题</button>
      </div>
    </header>

    <div class="report-grid">
      <div class="report-primary">
        <template v-if="scenario === 'assets'">
          <div class="surface-head">
            <div><span class="overline">分析路径</span><h3>从业务概念定位数据集</h3></div>
            <span class="info-tag">3 个示例候选</span>
          </div>
          <div class="pathway" role="group" aria-label="贷款余额资产分析链路">
            <div class="pathway-node question-node"><small>业务需求</small><strong>贷款余额分析</strong></div>
            <span class="path-connector"><ArrowRight :size="19" /></span>
            <div class="pathway-node metric-node"><small>需要的指标</small><strong>期末贷款余额</strong></div>
            <span class="path-connector"><ArrowRight :size="19" /></span>
            <div class="pathway-node target-node"><small>候选数据集</small><strong>{{ selectedDataset.name }}</strong></div>
          </div>
          <div class="data-head"><strong>选择一张数据集，查看它有哪些字段</strong><span>点击下方任意卡片</span></div>
          <div class="dataset-choices">
            <button v-for="(dataset,index) in demoDatasets" :key="dataset.key" type="button"
              class="dataset-choice" :class="{selected:dataset.key===selectedKey}" :aria-pressed="dataset.key===selectedKey"
              @click="selectedKey=dataset.key;detailsTab='fields'">
              <div class="choice-top"><span class="layer" :data-layer="dataset.layer">{{ dataset.layer }}</span><span class="choice-rank">0{{ index+1 }}</span></div>
              <strong>{{ dataset.name }}</strong>
              <code>{{ dataset.table }}</code>
              <span class="choice-bottom">{{ dataset.grain }} <ArrowRight :size="14"/></span>
            </button>
          </div>
          <div class="analysis-hint"><Info :size="15" /> 推荐顺序仅为演示假设，并非仓内真实质量评级。</div>
        </template>

        <template v-else-if="scenario === 'trend'">
          <div class="surface-head">
            <div><span class="overline">趋势探索</span><h3>贷款余额月度变化</h3></div>
            <span class="info-tag">2026 年 4—9 月 · 模拟值</span>
          </div>
          <div class="trend-top">
            <div><small>当前选中月份余额</small><strong>{{ activePoint.value.toFixed(1) }}<span>亿元</span></strong></div>
            <div class="trend-delta"><small>环比上月</small><strong :class="activeDelta>=0?'positive':'negative'">{{ activeMonth === 0 ? '—' : (activeDelta >= 0 ? '+' : '') + activeDelta.toFixed(1) + '%' }}</strong></div>
          </div>
          <div class="bar-chart" role="group" aria-label="点击柱形查看贷款余额月份数据">
            <div class="chart-scale"><span>150</span><span>130</span><span>110</span><span>90</span></div>
            <div class="bar-grid">
              <div class="chart-gridline" v-for="i in 4" :key="i" :style="{top:(i-1)*33.333+'%'}"></div>
              <button v-for="(point,index) in demoTrend" :key="point.month" type="button"
                class="bar-column" :class="{active:activeMonth===index}"
                :aria-pressed="activeMonth===index"
                :aria-label="`${point.month}贷款余额${point.value}亿元`"
                @click="activeMonth=index">
                <span class="bar-value">{{ point.value }}</span>
                <span class="bar-shape" :style="{height:barHeight(point.value)+'%'}"></span>
                <span class="bar-label">{{ point.month.slice(5) }}月</span>
              </button>
            </div>
          </div>
          <div class="analysis-hint"><Info :size="15" /> 点击柱形，可查看月份、环比及下一步分析建议。</div>
        </template>

        <template v-else-if="scenario === 'sql'">
          <div class="surface-head">
            <div><span class="overline">语义规划</span><h3>先确定业务条件，再查看 SQL</h3></div>
            <span class="info-tag">未连接真实数仓</span>
          </div>
          <div class="sql-form">
            <label>机构<select v-model="sqlOrg"><option value="深圳分行">深圳分行</option><option value="广州分行">广州分行</option></select></label>
            <label>月份<select v-model="sqlMonth"><option value="202609">2026 年 9 月</option><option value="202608">2026 年 8 月</option><option value="202607">2026 年 7 月</option></select></label>
          </div>
          <div class="sql-semantic">
            <div><small>指标</small><strong>贷款余额</strong></div>
            <ArrowRight :size="17"/>
            <div><small>候选数据集</small><strong>企业贷款月度汇总</strong></div>
            <ArrowRight :size="17"/>
            <div><small>筛选条件</small><strong>{{ sqlOrg }} · {{ sqlMonth }}</strong></div>
          </div>
          <div class="code-editor">
            <div class="code-top"><div><span class="code-dot"></span><span class="code-dot"></span><span class="code-dot"></span><b>SQL 预览</b></div><button type="button" @click="copySql"><Copy :size="15"/> {{ copied ? '已复制' : '复制 SQL' }}</button></div>
            <pre><code>{{ mockSql }}</code></pre>
          </div>
          <div class="analysis-hint"><AlertCircle :size="15" /> 这是模板生成的演示 SQL：表名、字段、口径及语法均未在真实环境校验，不可直接执行。</div>
        </template>

        <template v-else>
          <div class="surface-head">
            <div><span class="overline">字段规范</span><h3>把中文含义拆解为可复用词根</h3></div>
            <span class="info-tag">示例命名方案</span>
          </div>
          <div class="naming-grid">
            <button v-for="part in namingParts" :key="part.code" type="button"
              class="naming-piece" :class="{active:selectedRoot===part.code}"
              @click="selectedRoot=part.code" :aria-pressed="selectedRoot===part.code">
              <small>{{ part.chinese }}</small><strong>{{ part.code }}</strong><span>{{ part.english }}</span>
            </button>
          </div>
          <div class="naming-result">
            <span>组合建议</span>
            <div><code>cust_risk_lvl</code><button type="button" @click="copyName"><Copy :size="15" /> {{ copied ? '已复制' : '复制' }}</button></div>
            <p>该命名是模拟的词根拼接结果，实际使用前需核对组织内部命名规范和已有字段。</p>
          </div>
          <div class="compare-head">替代写法对比</div>
          <div class="compare-list">
            <button v-for="item in nameAlternatives" :key="item.name" type="button"
              :class="{ selected:selectedName===item.name }" @click="selectedName=item.name">
              <code>{{ item.name }}</code><span>{{ item.desc }}</span><ChevronRight :size="15"/></button>
          </div>
        </template>
      </div>

      <aside class="report-inspector">
        <div class="inspector-head"><span class="inspector-dot"></span><strong>{{ inspectorTitle }}</strong><span>模拟</span></div>
        <template v-if="scenario==='assets'">
          <div class="inspector-title"><span class="layer" :data-layer="selectedDataset.layer">{{ selectedDataset.layer }}</span><h3>{{ selectedDataset.name }}</h3></div>
          <code class="inspector-tech">{{ selectedDataset.table }}</code>
          <p class="inspector-summary">{{ selectedDataset.summary }}</p>
          <div class="inspector-tabs">
            <button type="button" v-for="tab in detailTabs" :key="tab.key" :class="{active:detailsTab===tab.key}" @click="detailsTab=tab.key">{{ tab.label }}</button>
          </div>
          <div v-if="detailsTab==='fields'" class="fields-list">
            <div class="field-row" v-for="f in selectedDataset.fields" :key="f.name"><div><strong>{{ f.label }}</strong><code>{{ f.name }}</code></div><span>{{ f.type }}</span></div>
          </div>
          <div v-else-if="detailsTab==='definition'" class="inspector-info"><div><span>统计粒度</span><b>{{ selectedDataset.grain }}</b></div><div><span>更新频率</span><b>{{ selectedDataset.frequency }}</b></div><div><span>业务说明</span><b>{{ selectedDataset.summary }}</b></div></div>
          <div v-else class="inspector-info"><div><span>上游来源</span><b>{{ selectedDataset.source }}</b></div><div><span>关联指标</span><b>贷款余额（演示）</b></div><p>需接入真实血缘 API 才能核实上游依赖。</p></div>
          <div class="inspector-bottom"><button type="button" @click="emit('followup','帮我生成深圳分行2026年9月贷款余额的 SQL')">继续生成 SQL <ArrowRight :size="15"/></button><RouterLink :to="{name:'catalog',query:{keyword:'贷款'}}">查询真实资产目录 <ExternalLink :size="14"/></RouterLink></div>
        </template>

        <template v-else-if="scenario==='trend'">
          <h3>{{ activePoint.month }} 月度数据</h3>
          <div class="inspector-kpi">{{ activePoint.value.toFixed(1) }}<small>亿元</small></div>
          <div class="inspector-info">
            <div><span>统计对象</span><b>贷款余额（模拟）</b></div>
            <div><span>比较月份</span><b>{{ activeMonth===0?'无上月数据':demoTrend[activeMonth-1]?.month }}</b></div>
            <div><span>环比变动</span><b>{{ activeMonth===0?'—':(activeDelta>=0?'+':'')+activeDelta.toFixed(1)+'%' }}</b></div>
          </div>
          <p class="inspector-summary">图中的数字来自固定演示数组，并非数仓查询结果。可切换月份体验联动效果。</p>
          <div class="inspector-bottom"><button type="button" @click="emit('followup','帮我生成深圳分行2026年9月贷款余额的 SQL')">用这些指标生成 SQL <ArrowRight :size="15"/></button></div>
        </template>

        <template v-else-if="scenario==='sql'">
          <h3>查询条件</h3>
          <div class="inspector-info">
            <div><span>查询指标</span><b>贷款余额</b></div>
            <div><span>数据集</span><b>demo_ads_corp_loan_month</b></div>
            <div><span>机构</span><b>{{ sqlOrg }}</b></div>
            <div><span>月份</span><b>{{ sqlMonth }}</b></div>
          </div>
          <div class="sql-validation"><AlertCircle :size="16" /><div><b>尚未校验</b><p>正式运行需要检查字段是否存在、指标口径、权限及 SQL 方言。</p></div></div>
          <div class="inspector-bottom"><button type="button" @click="emit('followup','哪些数据集可以分析企业贷款余额？')">查看数据集选择过程 <ArrowRight :size="15"/></button></div>
        </template>

        <template v-else>
          <h3>{{ selectedRootInfo.chinese }} · {{ selectedRootInfo.english }}</h3>
          <div class="inspector-kpi root-kpi">{{ selectedRootInfo.code }}</div>
          <p class="inspector-summary">{{ selectedRootInfo.explanation }}</p>
          <div class="inspector-info"><div><span>当前对比</span><b>{{ selectedName }}</b></div><div><span>建议</span><b>{{ selectedNameDescription }}</b></div></div>
          <div class="sql-validation"><Info :size="16"/><div><b>仅为命名演示</b><p>未验证这些词根是否属于你们现有的规范词典，也未核对仓内是否有同名字段。</p></div></div>
          <div class="inspector-bottom"><RouterLink to="/word-roots">打开真实词根索引 <ExternalLink :size="14"/></RouterLink></div>
        </template>
      </aside>
    </div>
    <footer class="report-foot"><ShieldCheck :size="15" /> 当前处于交互演示模式；所有数据、字段及 SQL 为模拟示例，不会访问或执行生产数据。</footer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { AlertCircle, ArrowRight, ChevronRight, Copy, ExternalLink, Info, RotateCcw, ShieldCheck, Sparkles } from 'lucide-vue-next'
import { demoDatasets, demoTrend, type DemoScenario } from './demoScenarios'

const props=defineProps<{scenario: DemoScenario; question: string}>()
const emit=defineEmits<{followup:[question:string];reset:[]}>()

const selectedKey=ref('ads')
const detailsTab=ref<'fields'|'definition'|'source'>('fields')
const detailTabs=[{key:'fields',label:'字段结构'},{key:'definition',label:'业务定义'},{key:'source',label:'数据来源'}] as const
const selectedDataset=computed(()=>demoDatasets.find(item=>item.key===selectedKey.value)||demoDatasets[0]!)
const activeMonth=ref(5)
const activePoint=computed(()=>demoTrend[activeMonth.value]!)
const activeDelta=computed(()=>{
  if(activeMonth.value===0)return 0
  const prev=demoTrend[activeMonth.value-1]!.value
  return (activePoint.value.value-prev)/prev*100
})
function barHeight(v:number){return Math.max(8,Math.min(100,(v-90)/65*100))}

const sqlOrg=ref('深圳分行')
const sqlMonth=ref('202609')
const mockSql=computed(()=>`-- 模拟 SQL，未进行真实校验
SELECT org_code, SUM(loan_balance) AS loan_balance
FROM demo_ads_corp_loan_month
WHERE stat_month = '${sqlMonth.value}'
  AND org_code = '${sqlOrg.value === '深圳分行' ? 'DEMO_SZ' : 'DEMO_GZ'}'
GROUP BY org_code;`)
const copied=ref(false)
async function copyText(value:string) {
  try {await navigator.clipboard.writeText(value);copied.value=true}
  catch {copied.value=false}
}
function copySql(){void copyText(mockSql.value)}
function copyName(){void copyText('cust_risk_lvl')}
watch([sqlOrg,sqlMonth],()=>{copied.value=false})

const namingParts=[
  {chinese:'客户',english:'customer',code:'cust',explanation:'演示中 customer 缩写为 cust。实际标准请以组织词根库为准。'},
  {chinese:'风险',english:'risk',code:'risk',explanation:'risk 可以表示风险语义。需和具体风险类型及分类口径核对。'},
  {chinese:'等级',english:'level',code:'lvl',explanation:'演示中 level 缩写为 lvl，是否允许这种缩写应由内部规范决定。'},
]
const selectedRoot=ref('cust')
const selectedRootInfo=computed(()=>namingParts.find(x=>x.code===selectedRoot.value)||namingParts[0]!)
const nameAlternatives=[
  {name:'cust_risk_lvl',desc:'较简洁、拆解明确的演示建议'},
  {name:'customer_risk_level',desc:'语义完整，但可能不符合缩写约定'},
  {name:'risk_lvl',desc:'缺失客户主体，容易产生歧义'},
]
const selectedName=ref('cust_risk_lvl')
const selectedNameDescription=computed(()=>nameAlternatives.find(x=>x.name===selectedName.value)?.desc||'')

const title=computed(()=>({
  assets:'找到适合贷款余额分析的数据集',
  trend:'查看贷款余额的月度变化',
  sql:'把业务要求转换成 SQL',
  naming:'为“客户风险等级”设计字段名',
})[props.scenario])
const description=computed(()=>({
  assets:'比较候选数据集的统计粒度，再查看字段结构和来源。',
  trend:'选择图表月份，查看对应余额和环比变化。',
  sql:'修改机构和月份，观察业务条件如何实时映射到 SQL。',
  naming:'点击词根和备选字段，理解命名建议与选择依据。',
})[props.scenario])
const inspectorTitle=computed(()=>({
  assets:'数据集详情',trend:'选中月份',sql:'SQL 解释',naming:'词根说明',
})[props.scenario])

watch(()=>props.scenario,()=>{
  selectedKey.value='ads';detailsTab.value='fields';activeMonth.value=5
  selectedRoot.value='cust';selectedName.value='cust_risk_lvl';copied.value=false
})
</script>

<style scoped>
.demo-report{border:1px solid #e6e3ef;border-radius:20px;background:#fff;box-shadow:0 16px 50px rgba(22,20,48,.065);overflow:hidden}
.report-intro{padding:28px 30px 22px}
.report-eyebrow{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:800;color:#6654ce}
.report-eyebrow span{margin-left:8px;border-radius:999px;background:#f2effd;color:#7563ac;font-size:10px;padding:4px 8px}
.report-title-row{display:flex;justify-content:space-between;align-items:flex-end;gap:16px}
.report-title-row h2{margin:14px 0 6px;color:#171829;font-size:27px;letter-spacing:-.04em}
.report-title-row p{margin:0;font-size:13px;color:#747889}
.restart{display:flex;align-items:center;gap:6px;padding:9px 12px;background:#f7f7f9;border:1px solid #e5e6ec;border-radius:9px;color:#434854;font-size:12px;cursor:pointer}
.report-grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(300px,.75fr);gap:0;border-top:1px solid #eceaf2}
.report-primary{padding:28px 28px 24px;min-width:0;background:#fff}
.report-inspector{background:#f9f9fc;border-left:1px solid #e9e8ef;padding:25px 22px;display:flex;flex-direction:column;min-width:0}
.surface-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:22px}
.surface-head h3{margin:6px 0 0;color:#262638;font-size:18px}
.overline{font-size:10px;font-weight:800;letter-spacing:.06em;color:#7a6aa6}
.info-tag{white-space:nowrap;padding:6px 9px;background:#f4f2fc;color:#7564b6;border-radius:7px;font-size:10px}
.pathway{border:1px solid #24253a;background:radial-gradient(ellipse at 60% 20%,#242044 0%,#121525 67%);border-radius:16px;padding:32px 22px;display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:192px;color:white}
.pathway-node{min-height:92px;min-width:0;flex:1;display:flex;flex-direction:column;justify-content:center;gap:11px;padding:14px;border:1px solid #42445f;border-radius:12px;background:rgba(255,255,255,.05)}
.pathway-node small{font-size:10px;color:#a8a8c3}
.pathway-node strong{font-size:14px;line-height:1.4}
.metric-node{border-color:#8c79ed;background:rgba(124,103,242,.14)}
.target-node{border-color:#7e6fd1}
.path-connector{color:#a293ea;flex:0 0 auto}
.data-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:24px 0 13px}
.data-head strong{font-size:14px}.data-head span{color:#8a8d9b;font-size:11px}
.dataset-choices{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.dataset-choice{display:flex;flex-direction:column;gap:7px;text-align:left;padding:15px;border:1px solid #e6e4ec;background:#fff;border-radius:12px;cursor:pointer;transition:.16s;min-height:160px;min-width:0}
.dataset-choice:hover{border-color:#b5a7f5;transform:translateY(-2px)}
.dataset-choice.selected{border-color:#7a67e8;background:#faf9ff;box-shadow:0 0 0 2px rgba(124,103,242,.1)}
.choice-top{display:flex;align-items:center;justify-content:space-between}
.choice-rank{font-size:11px;color:#999aaa}.layer{font-size:10px;font-weight:800;background:#eeeafa;color:#684ece;border-radius:5px;padding:4px 7px}
.layer[data-layer="DWD"]{background:#e9f5f2;color:#247366}.layer[data-layer="DWS"]{background:#edf0fb;color:#5673a4}
.dataset-choice strong{font-size:13px;color:#2a2938}
.dataset-choice code{font-size:10px;color:#798094;overflow-wrap:anywhere}
.choice-bottom{display:flex;align-items:center;justify-content:space-between;margin-top:auto;font-size:10px;color:#6d677f}
.analysis-hint{display:flex;align-items:flex-start;gap:7px;margin-top:18px;color:#777d8b;font-size:11px;line-height:1.6}.analysis-hint svg{flex-shrink:0;color:#8872e8}
.inspector-head{display:flex;gap:8px;align-items:center;color:#63647a;font-size:12px;font-weight:750}
.inspector-head span:last-child{margin-left:auto;font-size:10px;color:#9b9cad}
.inspector-dot{width:8px;height:8px;border-radius:50%;background:#8068eb;box-shadow:0 0 0 4px #ede8ff}
.inspector-title{display:flex;align-items:center;gap:8px;margin-top:25px}.inspector-title h3{margin:0;font-size:18px;color:#26263a}
.inspector-tech{display:block;margin-top:9px;color:#838899;font-size:11px;overflow-wrap:anywhere}
.inspector-summary{color:#6e7281;font-size:12px;line-height:1.8;margin:19px 0}
.inspector-tabs{display:flex;gap:4px;border-bottom:1px solid #e5e4ee;margin-bottom:12px}
.inspector-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:10px;font-size:11px;color:#75798b;cursor:pointer;white-space:nowrap}
.inspector-tabs button.active{border-color:#8068eb;color:#6450d2;font-weight:750}
.field-row{padding:10px 0;display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #e9e8f0}
.field-row>div{min-width:0;display:grid;gap:5px}
.field-row strong{font-size:12px}.field-row code{font-size:11px;color:#6f7290;overflow-wrap:anywhere}
.field-row>span{white-space:nowrap;font-size:10px;color:#818696}
.inspector-info{display:grid;gap:0;margin-top:16px}
.inspector-info>div{display:grid;gap:5px;border-bottom:1px solid #e7e6ee;padding:12px 0}
.inspector-info span{font-size:11px;color:#8b8e9d}.inspector-info b{font-size:12px;line-height:1.55;color:#333448;font-weight:650}
.inspector-info p{font-size:11px;color:#8a889a}
.inspector-bottom{margin-top:auto;padding-top:22px;display:grid;gap:10px}
.inspector-bottom button,.inspector-bottom a{width:100%;display:flex;justify-content:center;gap:9px;align-items:center;padding:12px 10px;border-radius:10px;border:1px solid #e4e1f2;background:#fff;color:#6051c0;font-size:12px;font-weight:700;cursor:pointer}
.inspector-bottom button{background:#6d57e3;color:white;border-color:#6d57e3}
.report-foot{padding:14px 26px;display:flex;align-items:center;gap:9px;border-top:1px solid #eceaf1;color:#8c8b9b;font-size:11px;background:#fff}
.trend-top{display:flex;gap:48px;align-items:flex-end;margin-bottom:24px}.trend-top>div{display:grid;gap:5px}
.trend-top small{font-size:11px;color:#8f92a0}
.trend-top strong{font-size:40px;letter-spacing:-.045em;color:#1d1d30}.trend-top strong span{font-size:13px;margin-left:7px;color:#7d8091;font-weight:500}
.trend-top .trend-delta strong{font-size:19px}.trend-delta .positive{color:#248968}.trend-delta .negative{color:#c25656}
.bar-chart{display:grid;grid-template-columns:35px 1fr;gap:8px;background:#141529;border-radius:16px;padding:28px 22px 20px;min-height:285px}
.chart-scale{display:flex;flex-direction:column;justify-content:space-between;padding-bottom:20px;font-size:10px;color:#666e89}
.bar-grid{position:relative;display:flex;justify-content:space-around;align-items:stretch;gap:7px;padding:0 0 10px}
.chart-gridline{position:absolute;height:1px;background:#34334b;left:0;right:0;pointer-events:none}
.bar-column{position:relative;z-index:1;flex:1;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;border:0;background:transparent;color:#9d9db3;cursor:pointer;padding:0}
.bar-shape{display:block;width:57%;max-width:48px;min-height:15px;border-radius:7px 7px 0 0;background:linear-gradient(180deg,#6254a8,#343356);transition:height .24s}
.bar-column.active .bar-shape{background:linear-gradient(180deg,#ad95ff,#7565e2);box-shadow:0 0 30px rgba(129,102,246,.3)}
.bar-value{font-size:10px;color:#dedaf2;opacity:0;margin-bottom:7px}.bar-column.active .bar-value,.bar-column:hover .bar-value{opacity:1}
.bar-label{margin-top:9px;font-size:11px;color:#a7a7bf}.bar-column.active .bar-label{color:#fff}
.inspector-kpi{font-size:38px;font-weight:750;color:#2b284a;margin-top:24px}
.inspector-kpi small{font-size:13px;color:#8a8b99;margin-left:8px}
.sql-form{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.sql-form label{display:grid;gap:8px;color:#7b7f8e;font-size:11px}
.sql-form select{min-height:42px;padding:0 12px;border:1px solid #dddbe8;border-radius:9px;color:#302e45;background:white;outline-color:#8c76eb}
.sql-semantic{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:22px 0}
.sql-semantic>div{display:grid;flex:1;min-width:0;gap:7px;border:1px solid #e6e3f0;border-radius:10px;padding:13px}
.sql-semantic small{font-size:10px;color:#838296}.sql-semantic strong{font-size:12px;color:#302d45}
.sql-semantic>svg{color:#8a76dc;flex:0 0 auto}
.code-editor{background:#131626;border-radius:13px;overflow:hidden;color:#eceaf6}
.code-top{padding:12px 16px;border-bottom:1px solid #303349;display:flex;align-items:center;justify-content:space-between}
.code-top>div{display:flex;align-items:center;gap:5px}.code-top b{margin-left:11px;font-size:11px;font-weight:600;color:#b0aac9}
.code-dot{width:7px;height:7px;border-radius:50%;background:#756f8a}.code-dot:first-child{background:#e57b87}.code-dot:nth-child(2){background:#e2b06c}.code-dot:nth-child(3){background:#7fbca9}
.code-top button{border:0;background:transparent;color:#c5b9ff;display:flex;gap:6px;align-items:center;cursor:pointer;font-size:11px}
.code-editor pre{margin:0;padding:22px;overflow:auto;font-size:12px;line-height:1.85}
.sql-validation{display:flex;gap:11px;padding:15px;border-radius:10px;background:#f7f0e4;color:#956c32;margin-top:25px}
.sql-validation b{font-size:12px}.sql-validation p{margin:6px 0 0;font-size:11px;line-height:1.6}
.naming-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.naming-piece{display:grid;gap:9px;text-align:left;border:1px solid #e6e2ef;background:#fff;padding:18px;border-radius:12px;cursor:pointer}
.naming-piece.active{border-color:#8d78e7;background:#f8f5ff;box-shadow:0 0 0 2px #f0ebff}
.naming-piece small{color:#88899e;font-size:12px}.naming-piece strong{font-size:25px;color:#292542}.naming-piece span{font-size:11px;color:#9c96ad}
.naming-result{border:1px solid #e4defa;background:linear-gradient(115deg,#f4f0ff,#fdfcff);border-radius:14px;margin-top:22px;padding:21px}
.naming-result>span{font-size:11px;color:#7864c7}
.naming-result>div{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:8px}
.naming-result code{font-size:25px;font-weight:750;color:#45349c;overflow-wrap:anywhere}
.naming-result button{display:flex;gap:6px;align-items:center;border:1px solid #e3dcff;background:#fff;color:#6e58d5;border-radius:7px;padding:8px;font-size:11px;cursor:pointer}
.naming-result p{font-size:11px;color:#898297;margin:13px 0 0}
.compare-head{margin:24px 0 10px;font-size:13px;font-weight:700}
.compare-list{display:grid;gap:7px}
.compare-list button{display:flex;align-items:center;gap:10px;border:1px solid #e6e4ed;border-radius:9px;padding:12px;background:#fff;text-align:left;cursor:pointer}
.compare-list button.selected{border-color:#8b77e7;background:#faf8ff}
.compare-list code{font-size:12px;color:#433782;font-weight:700}.compare-list span{margin-left:auto;font-size:11px;color:#828497}
.compare-list svg{color:#888295}
.root-kpi{font-family:Consolas,monospace;font-size:34px}
@media(max-width:1180px){.report-grid{grid-template-columns:1fr}.report-inspector{border-left:0;border-top:1px solid #e9e8ef}}
@media(max-width:750px){.report-intro{padding:22px}.report-title-row{align-items:flex-start;flex-direction:column}.report-primary{padding:20px}.dataset-choices{grid-template-columns:1fr}.pathway{flex-direction:column}.pathway-node{width:100%}.path-connector{transform:rotate(90deg)}.sql-form{grid-template-columns:1fr}.sql-semantic{flex-direction:column}.sql-semantic>div{width:100%}.sql-semantic>svg{transform:rotate(90deg)}.naming-grid{grid-template-columns:1fr}.compare-list button{flex-wrap:wrap}.compare-list span{margin-left:0}.report-foot{padding:12px 18px}}
</style>
