export type DemoScenario = 'assets' | 'trend' | 'sql' | 'naming'

export interface DemoSuggestion {
  label: string
  question: string
  kind: DemoScenario
}

export const demoSuggestions: DemoSuggestion[] = [
  { label: '找数据集', question: '哪些数据集可以分析企业贷款余额？', kind: 'assets' },
  { label: '分析趋势', question: '2026年4至9月贷款余额的趋势如何？', kind: 'trend' },
  { label: '生成 SQL', question: '帮我生成深圳分行2026年9月贷款余额的 SQL', kind: 'sql' },
  { label: '规范命名', question: '“客户风险等级”字段应该怎么规范命名？', kind: 'naming' },
]

/**
 * Narrow, predictable demo routing. Unsupported domains never receive a
 * made-up loan or customer-risk answer. Production Agent uses a separate path.
 */
export function classifyDemoQuestion(question: string): DemoScenario | null {
  const text = question.replace(/\s+/g, '').toLowerCase()
  if (!text) return null
  if (/客户风险等级/.test(text) && /(字段|命名|词根|规范|缩写|名称|取名|叫什么)/.test(text)) return 'naming'
  if (/(贷款|loan)/.test(text)) {
    if (/(sql|写.*查询|生成.*查询语句|查询语句|查询脚本)/.test(text)) return 'sql'
    if (/(趋势|走势|变化|增长|波动|月度分析)/.test(text)) return 'trend'
    if (/(数据集|哪些表|什么表|资产|来源|从哪里|在哪|找表|分析|推荐|贷款余额)/.test(text)) return 'assets'
  }
  return null
}

export interface DemoDataset {
  key: string
  name: string
  table: string
  layer: string
  summary: string
  grain: string
  frequency: string
  source: string
  fields: { name: string; label: string; type: string }[]
}

export const demoDatasets: DemoDataset[] = [
  {
    key: 'ads', name: '企业贷款月度汇总', table: 'demo_ads_corp_loan_month',
    layer: 'ADS', grain: '月份 × 机构 × 客户类型', frequency: '每月',
    source: '贷款主题汇总、机构维度',
    summary: '面向余额分析的汇总数据集；适合按机构和月份统计，演示中作为优先候选。',
    fields: [
      { name: 'stat_month', label: '统计月份', type: 'STRING' },
      { name: 'org_code', label: '机构代码', type: 'STRING' },
      { name: 'customer_type', label: '客户类型', type: 'STRING' },
      { name: 'loan_balance', label: '贷款余额', type: 'DECIMAL(20,2)' },
    ],
  },
  {
    key: 'dws', name: '贷款余额主题汇总', table: 'demo_dws_loan_balance',
    layer: 'DWS', grain: '月份 × 机构 × 贷款类型', frequency: '每月',
    source: '贷款合同明细、机构维度',
    summary: '提供可复用的贷款主题汇总，适合多口径分析，但仍需确认客户类型过滤规则。',
    fields: [
      { name: 'stat_month', label: '统计月份', type: 'STRING' },
      { name: 'org_code', label: '机构代码', type: 'STRING' },
      { name: 'loan_type', label: '贷款类别', type: 'STRING' },
      { name: 'balance_amt', label: '余额金额', type: 'DECIMAL(20,2)' },
    ],
  },
  {
    key: 'dwd', name: '贷款合同明细', table: 'demo_dwd_loan_contract',
    layer: 'DWD', grain: '单笔合同', frequency: '每日',
    source: '贷款业务源系统',
    summary: '保留合同级细节，适合穿透核查；做月末余额统计需要额外聚合与口径校验。',
    fields: [
      { name: 'contract_id', label: '贷款合同编号', type: 'STRING' },
      { name: 'org_code', label: '机构代码', type: 'STRING' },
      { name: 'customer_id', label: '客户编号', type: 'STRING' },
      { name: 'contract_balance', label: '合同余额', type: 'DECIMAL(20,2)' },
    ],
  },
]

export const demoTrend = [
  { month: '2026-04', value: 125.2 },
  { month: '2026-05', value: 129.8 },
  { month: '2026-06', value: 128.4 },
  { month: '2026-07', value: 136.9 },
  { month: '2026-08', value: 141.7 },
  { month: '2026-09', value: 146.8 },
]
