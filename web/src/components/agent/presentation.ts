import type { AgentActivity, AgentValidation, AgentValidationIssue, AgentValidationState } from '@/api/client'
import type { AgentMessage, ProcessStep } from '@/components/agent/types'

export function validationState(item: AgentMessage): AgentValidationState {
  if (item.validationState) return item.validationState
  if (!item.sql) return 'not_applicable'
  if (!item.validation) return 'not_validated'
  return item.validation.valid ? 'passed' : 'failed'
}

export function validationIssues(validation?: AgentValidation | null): AgentValidationIssue[] {
  return validation?.issues || []
}

export function hasAdvisory(validation?: AgentValidation | null) {
  return validationIssues(validation).some((issue) => issue.blocking === false || issue.severity !== 'error')
}

export function validationTone(item: AgentMessage) {
  const state = validationState(item)
  if (state === 'failed') return 'danger'
  if (state === 'not_validated' || state === 'unknown') return 'pending'
  if (state === 'passed' && hasAdvisory(item.validation)) return 'warning'
  return 'success'
}

export function sqlStatusText(item: AgentMessage) {
  const state = validationState(item)
  if (state === 'failed') return '校验未通过 · 仅生成'
  if (state === 'not_validated') return '尚未校验 · 仅生成'
  if (state === 'unknown') return '校验状态未知 · 仅生成'
  if (state === 'passed' && hasAdvisory(item.validation)) return '校验通过 · 有提示 · 仅生成'
  return '静态校验通过 · 仅生成'
}

export function validationTitle(item: AgentMessage) {
  const state = validationState(item)
  if (state === 'failed') return 'SQL 静态校验未通过'
  if (state === 'not_validated') return 'SQL 尚未完成静态校验'
  if (state === 'unknown') return 'SQL 校验状态未知'
  if (hasAdvisory(item.validation)) return 'SQL 静态校验通过，但存在提示项'
  return 'SQL 静态校验通过'
}

export function validationDescription(item: AgentMessage) {
  const state = validationState(item)
  if (state === 'failed') return '存在阻断项，当前 SQL 不应作为可信结果直接使用。'
  if (state === 'not_validated') return '仅展示生成结果，不继承其他 SQL 的校验状态。'
  if (state === 'unknown') return '校验结果缺少可判定状态，请重新执行校验。'
  if (hasAdvisory(item.validation)) return '未发现阻断项，但仍需关注下方风险或规范提示。'
  return '未发现阻断项；DataControl 仍不会执行该 SQL。'
}

export function statementLabel(validation?: AgentValidation | null) {
  return validation?.statement_type || {
    query: 'QUERY',
    dml: 'DML',
    ddl: 'DDL',
    access_control: 'ACCESS',
    unknown: 'SQL',
  }[validation?.operation || 'unknown']
}

export function riskLabel(validation?: AgentValidation | null) {
  return {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '高危操作',
  }[validation?.risk_level || 'low']
}

export function showRisk(validation?: AgentValidation | null) {
  return !!validation?.risk_level && validation.risk_level !== 'low'
}

export function severityLabel(severity: AgentValidationIssue['severity']) {
  return { error: '阻断', warning: '提示', info: '说明' }[severity]
}

export function displaySql(item: AgentMessage) {
  return item.validation?.normalized_sql?.trim() || item.sql || ''
}

export function activityLabel(event: AgentActivity) {
  const labels: Record<string, string> = {
    plan_metric: '规划指标口径',
    resolve_metric: '解析指标',
    get_schema: '读取表结构',
    search_tables: '检索数据资产',
    get_semantic_model: '读取指标口径',
    compile_query: '生成可信 SQL',
    validate_sql: '静态校验 SQL',
    explain_sql: '解析 SQL',
    search_verified_sql: '检索可信 SQL',
  }
  return labels[event.tool || ''] || event.tool || 'Agent3 工具'
}

export function processSteps(events?: AgentActivity[]): ProcessStep[] {
  if (!events?.length) return []
  const results = new Map<string, AgentActivity>()
  for (const event of events) {
    if (event.type === 'tool_result' && event.callId) results.set(event.callId, event)
  }
  return events
    .filter((event) => event.type === 'tool_call' && event.callId)
    .slice(-12)
    .map((event) => {
      const result = event.callId ? results.get(event.callId) : undefined
      return {
        callId: event.callId || '',
        tool: event.tool || '',
        label: activityLabel(event),
        status: result ? (result.status === 'error' ? 'error' : 'done') : 'running',
      }
    })
}
