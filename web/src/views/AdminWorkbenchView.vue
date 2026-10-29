<template>
  <div class="admin-workbench">
    <header class="page-head">
      <div>
        <div class="eyebrow"><Wrench :size="14" /> DEVELOPER WORKSPACE</div>
        <h1>开发管理工作台</h1>
        <p>面向 Agent 调优与数据资产维护。运行记录、实际生效规则和元数据修改集中在这里。</p>
      </div>
      <div class="head-tags">
        <el-tag type="success" effect="plain">本地开发环境</el-tag>
        <el-tag type="warning" effect="plain">管理员权限</el-tag>
      </div>
    </header>

    <div class="notice">
      <ShieldAlert :size="18" />
      <div>
        <b>调试数据可包含完整业务内容</b>
        <span>工具输入与输出会持久化供开发排查；认证密钥、密码、Token 等字段会脱敏。Harness 当前没有提供可靠的 Token 用量或完整原始模型请求报文，本页会明确显示缺失项，不生成模拟数据。</span>
      </div>
    </div>

    <nav class="workbench-tabs">
      <button :class="{ active: activeTab === 'debug' }" @click="activeTab = 'debug'"><Activity :size="17" /> Agent 运行调试 <span>{{ runTotal }}</span></button>
      <button :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'"><ShieldCheck :size="17" /> 规则与配置 <span>{{ ruleFiles.length }}</span></button>
      <button :class="{ active: activeTab === 'metadata' }" @click="activeTab = 'metadata'"><Database :size="17" /> 元数据管理 <span>{{ datasetTotal + metricTotal }}</span></button>
    </nav>

    <section v-if="activeTab === 'debug'" class="panel debug-panel">
      <div class="panel-heading">
        <div><h2>Agent 运行记录</h2><p>每次运行对应一个 Run ID。选择记录后查看真实输入、工具调用参数、完整工具返回和最终结果。</p></div>
        <el-button :icon="RefreshCw" @click="refreshDebug" :loading="runsLoading">刷新</el-button>
      </div>
      <div class="filter-row">
        <el-input v-model="runKeyword" clearable placeholder="搜索问题、会话或 Run ID" :prefix-icon="Search" @keydown.enter="loadRuns" />
        <el-select v-model="runStatus" @change="loadRuns">
          <el-option label="全部状态" value="all" />
          <el-option label="排队中" value="queued" />
          <el-option label="运行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
          <el-option label="已中断" value="interrupted" />
          <el-option label="已取消" value="cancelled" />
          <el-option label="超时" value="timeout" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="loadRuns">查询</el-button>
      </div>

      <div class="debug-layout">
        <aside class="run-list">
          <div class="list-caption">最近运行 <span>{{ runs.length }} / {{ runTotal }}</span></div>
          <button v-for="run in runs" :key="run.runId" class="run-item" :class="{ selected: selectedRunId === run.runId }" @click="selectRun(run)">
            <div class="run-item-top">
              <span class="status-dot" :class="statusClass(run.status)"></span>
              <b>{{ run.displayQuestion || run.conversationTitle }}</b>
            </div>
            <p>{{ run.conversationTitle }} · {{ run.modelMode }} · {{ run.taskTier }}</p>
            <div class="run-item-bottom">
              <span>{{ formatDate(run.createdAt) }}</span>
              <span>{{ run.toolEventCount }} 个事件</span>
            </div>
            <code>{{ run.runId }}</code>
          </button>
          <el-empty v-if="!runs.length && !runsLoading" description="没有匹配的运行记录" :image-size="76" />
        </aside>

        <main class="run-detail">
          <template v-if="runDetail">
            <div class="detail-heading">
              <div>
                <div class="detail-kicker">RUN DETAIL</div>
                <h3>{{ runDetail.displayQuestion || runDetail.conversationTitle }}</h3>
                <code>{{ runDetail.runId }}</code>
              </div>
              <div class="detail-actions">
                <el-tag :type="statusTag(runDetail.status)">{{ statusLabel(runDetail.status) }}</el-tag>
                <el-button text :icon="Copy" @click="copyText(formatJson(runDetail))">复制完整调试记录</el-button>
              </div>
            </div>
            <div class="stats-row">
              <div><span>模型模式</span><b>{{ runDetail.modelMode }}</b></div>
              <div><span>任务模式</span><b>{{ runDetail.taskTier }}</b></div>
              <div><span>工具事件</span><b>{{ runDetail.events.length }}</b></div>
              <div><span>Token 用量</span><b>未提供</b></div>
            </div>

            <div class="trace-limit-note">
              <Info :size="15" />
              <span>{{ runDetail.tracePayloadsAvailable ? '本次记录包含工具输入输出。' : '这是旧运行记录或当前运行尚未产生工具事件：历史记录只保存工具名称和状态，没有可回溯的完整参数。' }} {{ runDetail.tokenUsageNote }}</span>
            </div>

            <section class="detail-block">
              <div class="block-title"><MessageSquare :size="16" /> 实际提交给 Harness 的用户输入</div>
              <pre class="json-view">{{ runDetail.question }}</pre>
              <div v-if="runDetail.displayQuestion !== runDetail.question" class="sub-block">
                <label>前端展示的问题</label>
                <pre class="json-view">{{ runDetail.displayQuestion }}</pre>
              </div>
              <div v-if="runDetail.contextAsset" class="sub-block">
                <label>绑定的数据资产上下文</label>
                <pre class="json-view">{{ formatJson(runDetail.contextAsset) }}</pre>
              </div>
            </section>

            <section class="detail-block">
              <div class="block-title"><Workflow :size="16" /> 完整工具调用时间线 <span class="muted">{{ runDetail.events.length }} events</span></div>
              <div v-if="runDetail.events.length" class="event-list">
                <article v-for="event in runDetail.events" :key="event.sequence" class="event-card">
                  <button class="event-head" @click="toggleEvent(event.sequence)">
                    <span class="event-index">{{ String(event.sequence).padStart(2, '0') }}</span>
                    <span class="event-kind" :class="event.type">{{ event.type === 'tool_call' ? 'TOOL CALL' : 'TOOL RESULT' }}</span>
                    <b>{{ event.tool }}</b>
                    <span v-if="event.status" class="event-status">{{ event.status }}</span>
                    <span class="event-time">{{ formatDate(event.createdAt) }}</span>
                    <ChevronDown :size="16" :class="{ rotated: expandedEvents[event.sequence] }" />
                  </button>
                  <div v-if="expandedEvents[event.sequence]" class="event-body">
                    <div class="event-meta"><span>Call ID</span><code>{{ event.callId || '—' }}</code><span>状态</span><code>{{ event.status || '—' }}</code></div>
                    <div v-if="event.payload?.input !== undefined" class="payload-block">
                      <label>输入参数</label>
                      <pre class="json-view">{{ formatJson(event.payload.input) }}</pre>
                    </div>
                    <div v-if="event.payload?.output !== undefined" class="payload-block">
                      <label>完整工具返回</label>
                      <pre class="json-view">{{ formatJson(event.payload.output) }}</pre>
                    </div>
                    <pre v-if="event.payload && event.payload.input === undefined && event.payload.output === undefined" class="json-view">{{ formatJson(event.payload) }}</pre>
                    <div v-if="!event.payload" class="old-event">该事件没有保存输入输出载荷（可能是调试追踪增强前产生的记录）。</div>
                  </div>
                </article>
              </div>
              <el-empty v-else description="本次运行没有已保存的工具事件" :image-size="64" />
            </section>

            <section class="detail-block">
              <div class="block-title"><FileText :size="16" /> 最终结果与状态</div>
              <div v-if="runDetail.error" class="error-box"><AlertTriangle :size="16" /> {{ runDetail.error }}</div>
              <pre class="json-view">{{ formatJson(runDetail.result) }}</pre>
            </section>
            <section class="detail-block">
              <div class="block-title"><ShieldCheck :size="16" /> 本次运行时的规则快照 <span class="muted">{{ runDetail.debugContext?.files.length || 0 }} 个文件</span></div>
              <template v-if="runDetail.debugContext">
                <div class="trace-limit-note"><Info :size="15" /><span>快照时间：{{ formatDate(runDetail.debugContext.capturedAt) }}。这些文件内容在本轮任务预留时读取，便于比较调优前后的规则变化。</span></div>
                <div class="event-list">
                  <article v-for="file in runDetail.debugContext.files" :key="file.path" class="event-card">
                    <button class="event-head" @click="toggleSnapshotFile(file.path)">
                      <span class="event-index"><FileCode2 :size="14" /></span>
                      <span class="event-kind" :class="{ tool_result: file.exists }">{{ file.exists ? 'SNAPSHOT' : 'MISSING' }}</span>
                      <b>{{ file.category }}</b>
                      <span class="event-time">{{ file.path }}</span>
                      <ChevronDown :size="16" :class="{ rotated: expandedSnapshotFiles[file.path] }" />
                    </button>
                    <div v-if="expandedSnapshotFiles[file.path]" class="event-body">
                      <div v-if="file.sha256" class="hash-line"><span>SHA-256</span><code>{{ file.sha256 }}</code></div>
                      <pre class="code-view">{{ file.content || '本轮运行时未找到该文件。' }}</pre>
                    </div>
                  </article>
                </div>
              </template>
              <div v-else class="old-event">该运行记录早于规则快照功能，无法还原历史运行时的配置文件；请在“规则与配置”查看当前版本。</div>
            </section>
          </template>
          <el-empty v-else description="从左侧选择一条运行记录，查看执行细节" :image-size="100" />
        </main>
      </div>
    </section>

    <section v-else-if="activeTab === 'rules'" class="panel rules-panel">
      <div class="panel-heading">
        <div><h2>规则与配置检查器</h2><p>读取当前工作区和本地运行 Profile 的真实文件，不是人工整理的摘要。</p></div>
        <div class="rule-selects">
          <el-select v-model="ruleModelMode" @change="loadRules"><el-option label="DeepSeek 正式模型" value="deepseek" /><el-option label="免费模型测试" value="free-test" /></el-select>
          <el-select v-model="ruleTaskTier" @change="loadRules"><el-option label="标准任务" value="standard" /><el-option label="多步任务" value="multi" /></el-select>
          <el-button :icon="RefreshCw" @click="loadRules" :loading="rulesLoading">重新读取</el-button>
        </div>
      </div>
      <div class="profile-banner">
        <div><span>选择的 Profile</span><b>{{ rulesResult?.profile || '—' }}</b></div>
        <div><span>模型模式</span><b>{{ ruleModelMode }}</b></div>
        <div><span>任务模式</span><b>{{ ruleTaskTier }}</b></div>
      </div>
      <div class="rules-layout">
        <aside class="rule-files">
          <button v-for="file in ruleFiles" :key="file.path" :class="{ selected: selectedRulePath === file.path }" @click="selectedRulePath = file.path">
            <FileCode2 :size="16" />
            <span><b>{{ file.category }}</b><small>{{ file.path }}</small></span>
            <el-tag v-if="!file.exists" size="small" type="warning">缺失</el-tag>
            <el-tag v-else size="small" type="success">已读取</el-tag>
          </button>
        </aside>
        <main class="rule-content">
          <template v-if="selectedRule">
            <div class="rule-content-head">
              <div><h3>{{ selectedRule.category }}</h3><code>{{ selectedRule.path }}</code></div>
              <el-button :icon="Copy" @click="copyText(selectedRule.content)" :disabled="!selectedRule.exists">复制文件内容</el-button>
            </div>
            <div v-if="selectedRule.sha256" class="hash-line"><span>SHA-256</span><code>{{ selectedRule.sha256 }}</code></div>
            <div v-else class="missing-file">当前运行环境未找到该文件。它不会被标记为已生效。</div>
            <pre class="code-view">{{ selectedRule.content || '文件不存在或无法读取。' }}</pre>
          </template>
          <el-empty v-else description="请选择左侧规则文件" />
        </main>
      </div>
      <div class="trace-limit-note"><Info :size="15" /><span>{{ rulesResult?.notice || '这里显示实际文件内容。当前尚未把每次运行时的规则文件完整快照写入历史，因此历史运行和当前配置可能不同。' }}</span></div>
      <div v-if="rulesResult?.precedence?.length" class="precedence-note">
        <b>规则生效与覆盖关系</b>
        <ol><li v-for="item in rulesResult.precedence" :key="item">{{ item }}</li></ol>
      </div>
      <div class="rule-legend">
        <div><span class="legend-dot prompt"></span><b>Prompt / Profile</b><p>告诉模型如何判断、规划和表达；本身不等于代码级阻断。</p></div>
        <div><span class="legend-dot tools"></span><b>工具目录 / Schema</b><p>决定模型实际能调用哪些工具、每个工具接受什么参数。</p></div>
        <div><span class="legend-dot guard"></span><b>Guard / Core / Portal</b><p>代码校验、权限边界、SQL 安全与持久化约束。</p></div>
      </div>
    </section>

    <section v-else class="panel metadata-panel">
      <div class="panel-heading">
        <div><h2>{{ metadataEntity === 'datasets' ? '数据集与字段元数据' : '业务指标语义' }}</h2><p>修改后直接写入本地元数据数据库，并记录变更审计。</p></div>
        <div class="metadata-head-actions">
          <div class="entity-switch">
            <button :class="{ active: metadataEntity === 'datasets' }" @click="metadataEntity = 'datasets'">数据集 / 字段</button>
            <button :class="{ active: metadataEntity === 'metrics' }" @click="metadataEntity = 'metrics'">指标语义</button>
          </div>
          <el-button v-if="metadataEntity === 'datasets'" :icon="RefreshCw" @click="loadDatasets" :loading="datasetsLoading">刷新元数据</el-button>
          <el-button v-else :icon="RefreshCw" @click="loadMetrics" :loading="metricsLoading">刷新指标</el-button>
        </div>
      </div>
      <div v-if="metadataEntity === 'datasets'" class="metadata-layout">
        <aside class="dataset-list">
          <div class="filter-row dataset-filter">
            <el-input v-model="datasetKeyword" clearable placeholder="搜索数据集名称、表名" :prefix-icon="Search" @keydown.enter="loadDatasets" />
            <el-button :icon="Search" @click="loadDatasets" />
          </div>
          <div class="list-caption">数据集 <span>{{ datasetRows.length }} / {{ datasetTotal }}</span></div>
          <button v-for="dataset in datasetRows" :key="dataset.assetId" class="dataset-item" :class="{ selected: selectedDatasetId === dataset.assetId }" @click="selectDataset(dataset.assetId)">
            <Database :size="17" />
            <span><b>{{ dataset.bizName }}</b><small>{{ dataset.tableName }}</small><small>{{ dataset.layerCode }} · {{ dataset.columnCount }} 字段</small></span>
          </button>
          <el-empty v-if="!datasetRows.length && !datasetsLoading" description="没有找到数据集" :image-size="70" />
        </aside>
        <main class="metadata-editor">
          <template v-if="datasetDraft">
            <div class="detail-heading">
              <div><div class="detail-kicker">METADATA RECORD</div><h3>{{ datasetDraft.bizName }}</h3><code>{{ datasetDraft.tableName }}</code></div>
              <el-button type="primary" :icon="Save" :loading="savingMetadata" @click="saveMetadata">保存变更</el-button>
            </div>
            <div class="metadata-fields">
              <label>业务名称<el-input v-model="datasetDraft.bizName" /></label>
              <label>所属工作空间<el-input :model-value="datasetDraft.workspaceCode" disabled /></label>
              <label>业务定义<el-input v-model="datasetDraft.bizDefinition" type="textarea" :rows="3" /></label>
              <label>统计口径<el-input v-model="datasetDraft.statCaliber" type="textarea" :rows="3" /></label>
              <label>数据来源说明<el-input v-model="datasetDraft.dataSourceDesc" type="textarea" :rows="2" /></label>
              <label>数据粒度<el-input v-model="datasetDraft.grain" /></label>
              <label>使用注意事项<el-input v-model="datasetDraft.usageNotes" type="textarea" :rows="2" /></label>
              <label>技术负责人<el-input v-model="datasetDraft.techOwner" /></label>
              <label>业务负责人<el-input v-model="datasetDraft.bizOwner" /></label>
              <label>所属部门<el-input v-model="datasetDraft.ownerDept" /></label>
              <label>更新频率<el-input v-model="datasetDraft.updateFreq" /></label>
              <label>调度说明<el-input v-model="datasetDraft.scheduleDesc" /></label>
              <label>调度节点<el-input v-model="datasetDraft.scheduleNode" /></label>
            </div>
            <div class="columns-heading"><div><h3>字段元数据</h3><p>可编辑中文名称、业务定义、单位、码表编号和标准编号。</p></div><span>{{ columnDrafts.length }} 个字段</span></div>
            <el-table :data="columnDrafts" height="420" size="small" stripe>
              <el-table-column prop="ordinalNo" label="#" width="55" />
              <el-table-column prop="columnName" label="字段名" min-width="170">
                <template #default="scope"><code>{{ scope.row.columnName }}</code><small class="dtype">{{ scope.row.dataType }}</small></template>
              </el-table-column>
              <el-table-column label="中文名称" min-width="145"><template #default="scope"><el-input v-model="scope.row.cnName" size="small" /></template></el-table-column>
              <el-table-column label="业务定义" min-width="220"><template #default="scope"><el-input v-model="scope.row.bizDefinition" size="small" /></template></el-table-column>
              <el-table-column label="单位" width="100"><template #default="scope"><el-input v-model="scope.row.unit" size="small" /></template></el-table-column>
              <el-table-column label="码表编号" width="125"><template #default="scope"><el-input v-model="scope.row.codeTableNo" size="small" /></template></el-table-column>
              <el-table-column label="标准编号" width="125"><template #default="scope"><el-input v-model="scope.row.standardNo" size="small" /></template></el-table-column>
            </el-table>
            <div class="metadata-foot"><span>最近更新：{{ formatDate(datasetDraft.updatedAt) }}</span><span>每次实际变更都会写入变更日志。</span></div>
          </template>
          <el-empty v-else description="选择一个数据集以查看和编辑元数据" :image-size="100" />
        </main>
      </div>
      <div v-else class="metadata-layout metric-layout">
        <aside class="dataset-list">
          <div class="filter-row dataset-filter">
            <el-input v-model="metricKeyword" clearable placeholder="搜索指标名称、编码或来源表" :prefix-icon="Search" @keydown.enter="loadMetrics" />
            <el-button :icon="Search" @click="loadMetrics" />
          </div>
          <div class="list-caption">业务指标 <span>{{ metricRows.length }} / {{ metricTotal }}</span></div>
          <button v-for="metric in metricRows" :key="metric.metricCode" class="dataset-item" :class="{ selected: selectedMetricCode === metric.metricCode }" @click="selectMetric(metric)">
            <Activity :size="17" />
            <span><b>{{ metric.metricName }}</b><small>{{ metric.metricCode }}</small><small>{{ metric.sourceTableName || metric.sourceDatasetName }}</small></span>
          </button>
          <el-empty v-if="!metricRows.length && !metricsLoading" description="没有找到业务指标" :image-size="70" />
        </aside>
        <main class="metadata-editor">
          <template v-if="metricDraft">
            <div class="detail-heading">
              <div><div class="detail-kicker">METRIC SEMANTIC</div><h3>{{ metricDraft.metricName }}</h3><code>{{ metricDraft.metricCode }}</code></div>
              <el-button type="primary" :icon="Save" :loading="savingMetric" @click="saveMetric">保存指标</el-button>
            </div>
            <div class="trace-limit-note"><Info :size="15" /><span>指标语义会直接影响 Agent 的指标解析、维度选择和 SQL 生成。修改聚合方式、度量字段、时间字段或强制过滤条件前，请确认业务口径。</span></div>
            <div class="metadata-fields metric-fields">
              <label>指标名称<el-input v-model="metricDraft.metricName" /></label>
              <label>指标编码<el-input :model-value="metricDraft.metricCode" disabled /></label>
              <label>来源数据表<el-input :model-value="metricDraft.sourceTableName || ''" disabled /></label>
              <label>来源数据集 ID<el-input :model-value="metricDraft.sourceDatasetId" disabled /></label>
              <label>业务定义<el-input v-model="metricDraft.bizDefinition" type="textarea" :rows="3" /></label>
              <label>指标别名<el-input v-model="metricDraft.aliases" placeholder="多个别名以逗号分隔" /></label>
              <label>聚合方式<el-input v-model="metricDraft.aggregation" /></label>
              <label>度量字段<el-input v-model="metricDraft.measureColumn" /></label>
              <label>时间字段<el-input v-model="metricDraft.timeField" /></label>
              <label>时间可加性<el-input v-model="metricDraft.timeAdditivity" /></label>
              <label>统计口径<el-input v-model="metricDraft.caliberDesc" type="textarea" :rows="2" /></label>
              <label>有效维度<el-input v-model="metricDraft.validDimensions" placeholder="多个字段以逗号分隔" /></label>
              <label>指标类型<el-input v-model="metricDraft.metricKind" /></label>
              <label>分子指标编码<el-input v-model="metricDraft.numeratorMetricCode" /></label>
              <label>分母指标编码<el-input v-model="metricDraft.denominatorMetricCode" /></label>
              <label>计算公式<el-input v-model="metricDraft.formula" type="textarea" :rows="2" /></label>
              <label>时间粒度<el-input v-model="metricDraft.timeGrain" /></label>
              <label>最新值策略<el-input v-model="metricDraft.latestStrategy" /></label>
              <label>强制过滤条件（JSON）<el-input v-model="metricDraft.mandatoryFilters" type="textarea" :rows="3" /></label>
              <label>语义备注<el-input v-model="metricDraft.semanticNotes" type="textarea" :rows="3" /></label>
              <label>统计制度编号<el-input v-model="metricDraft.statSystemCode" /></label>
              <label>状态<el-input v-model="metricDraft.status" /></label>
            </div>
            <div class="metadata-foot"><span>来源数据集为只读关联，不允许在此处直接更换。</span><span>实际修改会写入变更日志。</span></div>
          </template>
          <el-empty v-else description="选择一个业务指标以查看和编辑语义" :image-size="100" />
        </main>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Activity, AlertTriangle, ChevronDown, Copy, Database, FileCode2, FileText, Info, MessageSquare,
  RefreshCw, Save, Search, ShieldAlert, ShieldCheck, Workflow, Wrench,
} from 'lucide-vue-next'
import {
  adminWorkbenchApi,
  type AdminColumnRecord,
  type AdminDatasetRecord,
  type AdminDatasetSummary,
  type AdminMetricRecord,
  type AdminRuleFile,
  type AdminRulesResult,
  type AdminRunDetail,
  type AdminRunSummary,
} from '@/api/client'

type WorkbenchTab = 'debug' | 'rules' | 'metadata'
const activeTab = ref<WorkbenchTab>('debug')

const runKeyword = ref('')
const runStatus = ref('all')
const runs = ref<AdminRunSummary[]>([])
const runTotal = ref(0)
const runsLoading = ref(false)
const selectedRunId = ref('')
const runDetail = ref<AdminRunDetail | null>(null)
const expandedEvents = ref<Record<number, boolean>>({})
const expandedSnapshotFiles = ref<Record<string, boolean>>({})

const ruleModelMode = ref<'deepseek' | 'free-test'>('deepseek')
const ruleTaskTier = ref<'standard' | 'multi'>('standard')
const rulesResult = ref<AdminRulesResult | null>(null)
const ruleFiles = ref<AdminRuleFile[]>([])
const selectedRulePath = ref('')
const rulesLoading = ref(false)
const selectedRule = computed(() => ruleFiles.value.find((item) => item.path === selectedRulePath.value) || null)

const metadataEntity = ref<'datasets' | 'metrics'>('datasets')
const metricKeyword = ref('')
const metricRows = ref<AdminMetricRecord[]>([])
const metricTotal = ref(0)
const metricsLoading = ref(false)
const selectedMetricCode = ref('')
const metricDraft = ref<AdminMetricRecord | null>(null)
const savingMetric = ref(false)

const datasetKeyword = ref('')
const datasetRows = ref<AdminDatasetSummary[]>([])
const datasetTotal = ref(0)
const datasetsLoading = ref(false)
const selectedDatasetId = ref('')
const datasetDraft = ref<AdminDatasetRecord | null>(null)
const columnDrafts = ref<AdminColumnRecord[]>([])
const savingMetadata = ref(false)
let pollHandle: number | undefined

function messageOf(error: unknown) {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    if (response?.data?.detail) return String(response.data.detail)
  }
  return error instanceof Error ? error.message : '请求失败，请检查服务端日志。'
}
function formatJson(value: unknown) {
  if (value === undefined || value === null) return value === null ? 'null' : '（无数据）'
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}
function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
function statusLabel(status: string) {
  return ({ queued: '排队中', running: '运行中', cancel_requested: '取消请求中', completed: '已完成',
    failed: '失败', interrupted: '已中断', cancelled: '已取消', timeout: '超时' } as Record<string, string>)[status] || status
}
function statusClass(status: string) {
  return ({ queued: 'pending', running: 'running', completed: 'done', failed: 'failed',
    interrupted: 'failed', cancelled: 'muted', timeout: 'failed' } as Record<string, string>)[status] || 'muted'
}
function statusTag(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'running' || status === 'queued' || status === 'cancel_requested') return 'warning'
  if (status === 'failed' || status === 'timeout' || status === 'interrupted') return 'danger'
  return 'info'
}
async function copyText(text: string) {
  try { await navigator.clipboard.writeText(text); ElMessage.success('已复制') }
  catch { ElMessage.warning('复制失败，请手动选择内容。') }
}
async function loadRuns() {
  runsLoading.value = true
  try {
    const result = await adminWorkbenchApi.runs(runKeyword.value, runStatus.value, 100)
    runs.value = result.items
    runTotal.value = result.total
    if (!runs.value.length) {
      selectedRunId.value = ''
      runDetail.value = null
    } else if (!selectedRunId.value || !runs.value.some((item) => item.runId === selectedRunId.value)) {
      await selectRun(runs.value[0])
    }
  } catch (error) { ElMessage.error('读取 Agent 运行记录失败：' + messageOf(error)) }
  finally { runsLoading.value = false }
}
async function selectRun(run: AdminRunSummary) {
  selectedRunId.value = run.runId
  try { runDetail.value = await adminWorkbenchApi.run(run.runId) }
  catch (error) { runDetail.value = null; ElMessage.error('读取运行详情失败：' + messageOf(error)) }
}
function toggleEvent(sequence: number) {
  expandedEvents.value = { ...expandedEvents.value, [sequence]: !expandedEvents.value[sequence] }
}
function toggleSnapshotFile(path: string) {
  expandedSnapshotFiles.value = { ...expandedSnapshotFiles.value, [path]: !expandedSnapshotFiles.value[path] }
}
async function refreshDebug() {
  await loadRuns()
  if (selectedRunId.value) await selectRun(runs.value.find((item) => item.runId === selectedRunId.value) || runs.value[0])
}
async function loadRules() {
  rulesLoading.value = true
  try {
    rulesResult.value = await adminWorkbenchApi.rules(ruleModelMode.value, ruleTaskTier.value)
    ruleFiles.value = rulesResult.value.files
    if (!ruleFiles.value.some((item) => item.path === selectedRulePath.value)) {
      const active = ruleFiles.value.find((item) => item.category === '运行时实际生成配置' && item.exists)
      selectedRulePath.value = active?.path || ruleFiles.value[0]?.path || ''
    }
  } catch (error) { ElMessage.error('读取 Agent 规则失败：' + messageOf(error)) }
  finally { rulesLoading.value = false }
}
async function loadMetrics() {
  metricsLoading.value = true
  try {
    const result = await adminWorkbenchApi.metrics(metricKeyword.value, 200)
    metricRows.value = result.items
    metricTotal.value = result.total
    if (!selectedMetricCode.value && metricRows.value.length) selectMetric(metricRows.value[0])
    else if (selectedMetricCode.value && !metricRows.value.some((item) => item.metricCode === selectedMetricCode.value) && metricRows.value.length) {
      selectMetric(metricRows.value[0])
    }
  } catch (error) { ElMessage.error('读取业务指标失败：' + messageOf(error)) }
  finally { metricsLoading.value = false }
}
function selectMetric(metric: AdminMetricRecord) {
  selectedMetricCode.value = metric.metricCode
  metricDraft.value = { ...metric }
}
async function saveMetric() {
  const draft = metricDraft.value
  if (!draft || savingMetric.value) return
  savingMetric.value = true
  try {
    const updated = await adminWorkbenchApi.updateMetric(draft.metricCode, {
      metric_name: draft.metricName, aliases: draft.aliases ?? null,
      biz_definition: draft.bizDefinition ?? null, stat_system_code: draft.statSystemCode ?? null,
      aggregation: draft.aggregation, measure_column: draft.measureColumn, time_field: draft.timeField,
      time_additivity: draft.timeAdditivity, caliber_desc: draft.caliberDesc ?? null,
      valid_dimensions: draft.validDimensions ?? null, metric_kind: draft.metricKind,
      numerator_metric_code: draft.numeratorMetricCode ?? null,
      denominator_metric_code: draft.denominatorMetricCode ?? null, formula: draft.formula ?? null,
      time_grain: draft.timeGrain ?? null, latest_strategy: draft.latestStrategy,
      mandatory_filters: draft.mandatoryFilters ?? null, semantic_notes: draft.semanticNotes ?? null,
      status: draft.status,
    })
    metricDraft.value = updated
    await loadMetrics()
    ElMessage.success('指标语义已保存，实际变更已写入审计日志。')
  } catch (error) { ElMessage.error('保存指标语义失败：' + messageOf(error)) }
  finally { savingMetric.value = false }
}
async function loadDatasets() {
  datasetsLoading.value = true
  try {
    const result = await adminWorkbenchApi.datasets(datasetKeyword.value, 150)
    datasetRows.value = result.items
    datasetTotal.value = result.total
    if (!selectedDatasetId.value && datasetRows.value.length) await selectDataset(datasetRows.value[0].assetId)
    else if (selectedDatasetId.value && !datasetRows.value.some((item) => item.assetId === selectedDatasetId.value) && datasetRows.value.length) await selectDataset(datasetRows.value[0].assetId)
  } catch (error) { ElMessage.error('读取元数据失败：' + messageOf(error)) }
  finally { datasetsLoading.value = false }
}
async function selectDataset(assetId: string) {
  selectedDatasetId.value = assetId
  try {
    const detail = await adminWorkbenchApi.dataset(assetId)
    datasetDraft.value = { ...detail.dataset }
    columnDrafts.value = detail.columns.map((item) => ({ ...item }))
  } catch (error) { datasetDraft.value = null; columnDrafts.value = []; ElMessage.error('读取数据集详情失败：' + messageOf(error)) }
}
async function saveMetadata() {
  const draft = datasetDraft.value
  if (!draft || savingMetadata.value) return
  savingMetadata.value = true
  try {
    await adminWorkbenchApi.updateDataset(draft.assetId, {
      biz_name: draft.bizName, biz_definition: draft.bizDefinition ?? null,
      stat_caliber: draft.statCaliber ?? null, data_source_desc: draft.dataSourceDesc ?? null,
      grain: draft.grain ?? null, usage_notes: draft.usageNotes ?? null,
      tech_owner: draft.techOwner ?? null, biz_owner: draft.bizOwner ?? null,
      owner_dept: draft.ownerDept ?? null, update_freq: draft.updateFreq ?? null,
      schedule_desc: draft.scheduleDesc ?? null, schedule_node: draft.scheduleNode ?? null,
    })
    for (const column of columnDrafts.value) {
      await adminWorkbenchApi.updateColumn(column.assetId, {
        cn_name: column.cnName ?? null, biz_definition: column.bizDefinition ?? null,
        unit: column.unit ?? null, code_table_no: column.codeTableNo ?? null,
        standard_no: column.standardNo ?? null,
      })
    }
    await loadDatasets()
    await selectDataset(draft.assetId)
    ElMessage.success('元数据已保存，实际变更已写入审计日志。')
  } catch (error) { ElMessage.error('保存元数据失败：' + messageOf(error)) }
  finally { savingMetadata.value = false }
}
async function refreshSelectedRun() {
  if (!selectedRunId.value) return
  const current = runs.value.find((item) => item.runId === selectedRunId.value)
  if (current && (['queued', 'running', 'cancel_requested'].includes(current.status)
      || runDetail.value?.status !== current.status)) await selectRun(current)
}
onMounted(async () => {
  await Promise.all([loadRuns(), loadRules(), loadDatasets(), loadMetrics()])
  pollHandle = window.setInterval(async () => {
    if (activeTab.value === 'debug') {
      await loadRuns()
      await refreshSelectedRun()
    }
  }, 3000)
})
onBeforeUnmount(() => { if (pollHandle !== undefined) window.clearInterval(pollHandle) })
</script>

<style scoped>
.metadata-head-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.entity-switch{display:flex;gap:3px;padding:4px;border:1px solid var(--dc-border);border-radius:9px;background:#f5f8fd}
.entity-switch button{border:0;border-radius:6px;padding:7px 10px;background:transparent;color:var(--dc-text-2);font-size:12px;font-weight:650;cursor:pointer}
.entity-switch button.active{background:#fff;color:var(--dc-primary);box-shadow:0 2px 7px #284f8b12}
.precedence-note{padding:13px 20px;border-top:1px solid var(--dc-border);background:#fafcff;color:var(--dc-text-2);font-size:12px}
.precedence-note b{font-size:12px}
.precedence-note ol{margin:8px 0 0;padding-left:20px;display:grid;gap:5px;line-height:1.65;color:var(--dc-text-3)}
.metric-fields label:nth-child(5),.metric-fields label:nth-child(11),.metric-fields label:nth-child(16),.metric-fields label:nth-child(19),.metric-fields label:nth-child(20){grid-column:span 2}
.admin-workbench{max-width:1600px;margin:0 auto;padding:28px 30px 42px;color:var(--dc-text);display:grid;gap:18px}
.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}
.eyebrow{display:flex;align-items:center;gap:7px;color:var(--dc-primary);font-size:11px;font-weight:800;letter-spacing:.12em}
.page-head h1{font-size:26px;line-height:1.25;margin:9px 0 7px;color:var(--dc-text);letter-spacing:-.025em}
.page-head p,.panel-heading p{font-size:13px;line-height:1.7;color:var(--dc-text-3);margin:0}
.head-tags{display:flex;gap:8px;flex-wrap:wrap}
.notice{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border:1px solid #f1dcae;border-radius:12px;background:#fffaf0;color:#8a6323}
.notice>svg{flex:none;margin-top:2px}.notice div{display:grid;gap:4px}.notice b{font-size:13px}.notice span{font-size:12px;line-height:1.65}
.workbench-tabs{display:flex;gap:6px;padding:5px;border:1px solid var(--dc-border);background:#f5f8fd;border-radius:12px;width:max-content;max-width:100%;flex-wrap:wrap}
.workbench-tabs button{display:flex;align-items:center;gap:8px;padding:10px 13px;border:0;border-radius:8px;background:transparent;color:var(--dc-text-2);font-size:13px;font-weight:650;cursor:pointer}
.workbench-tabs button span{display:grid;place-items:center;min-width:22px;height:21px;padding:0 5px;border-radius:6px;background:#e8eef8;color:#58719a;font-size:11px}
.workbench-tabs button.active{background:#fff;color:var(--dc-primary);box-shadow:0 2px 8px #284f8b12}
.workbench-tabs button.active span{background:var(--dc-primary-soft);color:var(--dc-primary)}
.panel{min-width:0;border:1px solid var(--dc-border);border-radius:15px;background:#fff;box-shadow:0 8px 25px #284f8b07;overflow:hidden}
.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 22px;border-bottom:1px solid var(--dc-border)}
.panel-heading h2{font-size:17px;margin:0 0 5px;color:var(--dc-text)}
.filter-row{display:flex;gap:9px;align-items:center;padding:15px 20px;border-bottom:1px solid var(--dc-border)}
.filter-row .el-input{max-width:440px}.filter-row .el-select{width:155px}
.debug-layout{display:grid;grid-template-columns:minmax(270px,350px) minmax(0,1fr);min-height:680px}
.run-list{min-width:0;border-right:1px solid var(--dc-border);background:#f9fbff;max-height:calc(100vh - 310px);min-height:560px;overflow:auto}
.list-caption{display:flex;justify-content:space-between;padding:13px 15px;color:var(--dc-text-2);font-size:12px;font-weight:750;border-bottom:1px solid var(--dc-border)}
.list-caption span{color:var(--dc-text-3);font-weight:500}
.run-item,.dataset-item{width:100%;display:grid;gap:8px;padding:14px 15px;border:0;border-bottom:1px solid #e9eef7;background:transparent;text-align:left;color:var(--dc-text);cursor:pointer}
.run-item:hover,.dataset-item:hover{background:#f1f6ff}.run-item.selected,.dataset-item.selected{background:#eaf2ff;box-shadow:inset 3px 0 var(--dc-primary)}
.run-item-top{display:flex;align-items:flex-start;gap:8px}.run-item-top b{font-size:12px;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.status-dot{width:8px;height:8px;flex:none;border-radius:50%;margin-top:5px;background:#a1aec1}.status-dot.done{background:#16a179}.status-dot.running{background:#3478e8;box-shadow:0 0 0 4px #3478e81c}.status-dot.failed{background:#d84b58}.status-dot.pending{background:#d69b32}.status-dot.muted{background:#9ca9b9}
.run-item p{margin:0;font-size:11px;color:var(--dc-text-3)}.run-item-bottom{display:flex;justify-content:space-between;gap:6px;font-size:10px;color:var(--dc-text-3)}
.run-item code,.detail-heading code,.rule-content-head code{font-size:10px;color:#7184a2;overflow-wrap:anywhere}
.run-detail{min-width:0;padding:20px 22px;overflow:hidden}
.detail-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding-bottom:17px;border-bottom:1px solid var(--dc-border)}
.detail-kicker{font-size:10px;letter-spacing:.1em;font-weight:800;color:var(--dc-primary);margin-bottom:5px}
.detail-heading h3{font-size:16px;line-height:1.55;margin:0 0 6px;overflow-wrap:anywhere}
.detail-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.stats-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:15px 0}
.stats-row>div{display:grid;gap:5px;padding:11px 12px;border:1px solid var(--dc-border);border-radius:9px;background:#fbfcff}
.stats-row span{font-size:11px;color:var(--dc-text-3)}.stats-row b{font-size:13px;color:var(--dc-text)}
.trace-limit-note{display:flex;align-items:flex-start;gap:8px;padding:11px 12px;margin:0 0 16px;border-radius:9px;background:#f3f7ff;color:#5a7196;font-size:12px;line-height:1.6}
.trace-limit-note svg{flex:none;margin-top:2px}
.detail-block{margin-top:18px}.block-title{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:750;margin-bottom:10px}.block-title .muted{font-size:11px;color:var(--dc-text-3);font-weight:500;margin-left:auto}
.json-view,.code-view{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;padding:13px 14px;border:1px solid #dfe7f4;border-radius:9px;background:#f7f9fd;color:#2d456a;font:12px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace}
.sub-block,.payload-block{display:grid;gap:7px;margin-top:12px}.sub-block label,.payload-block label{font-size:11px;font-weight:750;color:var(--dc-text-2)}
.event-list{display:grid;gap:8px}.event-card{border:1px solid var(--dc-border);border-radius:10px;overflow:hidden;background:#fff}
.event-head{display:flex;align-items:center;gap:9px;width:100%;padding:11px 12px;border:0;background:#fbfcff;color:var(--dc-text);text-align:left;cursor:pointer}
.event-index{display:grid;place-items:center;flex:none;width:27px;height:27px;border-radius:7px;background:#e9f1ff;color:#356fd1;font-size:11px;font-weight:800}
.event-kind{font-size:9px;letter-spacing:.04em;font-weight:850;color:#2869d0;background:#eaf2ff;padding:5px 6px;border-radius:5px;white-space:nowrap}.event-kind.tool_result{color:#087b65;background:#e4f7ef}
.event-head b{font-size:12px;overflow-wrap:anywhere}.event-status{font-size:10px;color:var(--dc-text-3)}.event-time{margin-left:auto;font-size:10px;color:var(--dc-text-3);white-space:nowrap}.event-head>svg{flex:none;color:var(--dc-text-3);transition:transform .15s}.event-head>svg.rotated{transform:rotate(180deg)}
.event-body{padding:13px;border-top:1px solid var(--dc-border);display:grid;gap:10px}.event-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:11px;color:var(--dc-text-3)}.event-meta code{color:var(--dc-text-2);font-size:10px}
.old-event{font-size:12px;color:#8b6a2d;padding:10px;background:#fff9ec;border-radius:7px}
.error-box{display:flex;gap:8px;align-items:flex-start;padding:11px;margin-bottom:10px;border:1px solid #f1c9cd;border-radius:8px;background:#fff4f4;color:#b33a44;font-size:12px}
.rule-selects{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.rule-selects .el-select{width:150px}
.profile-banner{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:15px 20px;border-bottom:1px solid var(--dc-border);background:#f9fbff}
.profile-banner>div{display:grid;gap:5px}.profile-banner span{font-size:11px;color:var(--dc-text-3)}.profile-banner b{font-size:13px;color:var(--dc-text)}
.rules-layout{display:grid;grid-template-columns:minmax(240px,320px) minmax(0,1fr);min-height:590px}
.rule-files{border-right:1px solid var(--dc-border);background:#fafcff;max-height:720px;overflow:auto}
.rule-files button{width:100%;display:flex;align-items:flex-start;gap:9px;padding:13px 12px;border:0;border-bottom:1px solid #e8eef7;background:transparent;text-align:left;color:var(--dc-text-2);cursor:pointer}
.rule-files button.selected{background:#eaf2ff;color:var(--dc-primary);box-shadow:inset 3px 0 var(--dc-primary)}
.rule-files button>svg{flex:none;margin-top:2px}.rule-files button>span{flex:1;min-width:0;display:grid;gap:5px}.rule-files b{font-size:11px}.rule-files small{font-size:10px;color:var(--dc-text-3);overflow-wrap:anywhere}
.rule-content{min-width:0;padding:18px}.rule-content-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.rule-content-head h3{font-size:15px;margin:0 0 6px}.hash-line{display:flex;align-items:flex-start;gap:10px;margin:12px 0;font-size:10px;color:var(--dc-text-3)}.hash-line code{overflow-wrap:anywhere;color:#58729a}
.code-view{max-height:680px;background:#101d35;color:#d9e5fa;border-color:#223452;white-space:pre;overflow:auto;font-size:11px}
.missing-file{padding:10px;margin:12px 0;background:#fff8e9;border-radius:7px;color:#946c24;font-size:12px}
.rule-legend{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:15px 20px;border-top:1px solid var(--dc-border);background:#fafcff}
.rule-legend>div{position:relative;padding-left:14px}.rule-legend b{font-size:12px}.rule-legend p{font-size:11px;line-height:1.6;color:var(--dc-text-3);margin:5px 0 0}.legend-dot{position:absolute;left:0;top:3px;width:7px;height:7px;border-radius:50%}.legend-dot.prompt{background:#7b61d1}.legend-dot.tools{background:#2f86bb}.legend-dot.guard{background:#139879}
.metadata-layout{display:grid;grid-template-columns:minmax(260px,330px) minmax(0,1fr);min-height:700px}
.dataset-list{border-right:1px solid var(--dc-border);background:#f9fbff;max-height:calc(100vh - 260px);overflow:auto}.dataset-filter{padding:12px;border-bottom:1px solid var(--dc-border)}.dataset-filter .el-input{min-width:0}
.dataset-item{display:flex;align-items:flex-start;gap:10px}.dataset-item>svg{flex:none;margin-top:2px;color:var(--dc-primary)}.dataset-item>span{display:grid;gap:5px;min-width:0}.dataset-item b{font-size:12px}.dataset-item small{font-size:10px;color:var(--dc-text-3);overflow-wrap:anywhere}
.metadata-editor{padding:20px;min-width:0;overflow:hidden}.metadata-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px 16px;padding:18px 0}
.metadata-fields label{display:grid;gap:6px;font-size:11px;font-weight:700;color:var(--dc-text-2)}.metadata-fields label:nth-child(3),.metadata-fields label:nth-child(4),.metadata-fields label:nth-child(5),.metadata-fields label:nth-child(7){grid-column:span 2}
.columns-heading{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin:13px 0 11px}.columns-heading h3{font-size:15px;margin:0 0 4px}.columns-heading p{font-size:11px;color:var(--dc-text-3);margin:0}.columns-heading>span{font-size:11px;color:var(--dc-text-3)}
.dtype{display:block;font-size:10px;color:var(--dc-text-3);margin-top:3px}.metadata-foot{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;padding-top:12px;font-size:10px;color:var(--dc-text-3)}
@media(max-width:1050px){.debug-layout,.rules-layout,.metadata-layout{grid-template-columns:260px minmax(0,1fr)}.run-detail,.metadata-editor{padding:15px}.rule-content{padding:14px}.event-time{display:none}}
@media(max-width:760px){.admin-workbench{padding:17px 12px 28px}.page-head{display:grid}.page-head h1{font-size:22px}.panel-heading{align-items:flex-start;padding:15px;flex-wrap:wrap}.debug-layout,.rules-layout,.metadata-layout{grid-template-columns:1fr}.run-list,.rule-files,.dataset-list{max-height:300px;min-height:0;border-right:0;border-bottom:1px solid var(--dc-border)}.run-detail,.metadata-editor,.rule-content{padding:14px}.filter-row{padding:12px;flex-wrap:wrap}.filter-row .el-input{max-width:none;flex:1 1 100%}.filter-row .el-select{flex:1}.stats-row{grid-template-columns:repeat(2,minmax(0,1fr))}.profile-banner,.rule-legend{grid-template-columns:1fr}.rule-selects{width:100%}.rule-selects .el-select{flex:1;min-width:120px}.metadata-fields{grid-template-columns:1fr}.metadata-fields label:nth-child(n){grid-column:auto}.detail-heading{display:grid}.detail-actions{justify-content:flex-start}.workbench-tabs{width:100%}.workbench-tabs button{flex:1;justify-content:center;padding:10px 7px;font-size:12px}.workbench-tabs button svg{display:none}}
</style>
