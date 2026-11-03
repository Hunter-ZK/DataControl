const statusMap: Record<string, string> = {
  ONLINE: '在用', VALID: '有效', OFFLINE: '已下线',
  DEPRECATED: '已废弃', DRAFT: '草稿', DISABLED: '已停用',
}
const typeMap: Record<string, string> = {
  TABLE: '数据集', COLUMN: '字段', METRIC: '指标',
  CODE_TABLE: '码表', STANDARD: '数据标准',
  WORD_ROOT: '词根', STAT_SYSTEM: '统计制度',
}
export function statusLabel(value?: string | null) {
  if (!value) return '—'
  return statusMap[value] || value
}
export function typeLabel(value?: string | null) {
  if (!value) return '—'
  return typeMap[value] || value
}
