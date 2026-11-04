const statuses: Record<string,string> = { ONLINE:'在用', VALID:'有效', OFFLINE:'已下线', DEPRECATED:'已废弃', DRAFT:'草稿' }
const assetTypes: Record<string,string> = { TABLE:'数据集', COLUMN:'字段', CODE_TABLE:'码表', DATA_STANDARD:'数据标准', WORD_ROOT:'词根', METRIC:'指标', STAT_SYSTEM:'统计制度' }
export function statusLabel(value?: string|null): string { if (!value) return '—'; return statuses[value.toUpperCase()] || value }
export function assetTypeLabel(value?: string|null): string { if (!value) return '资产'; return assetTypes[value.toUpperCase()] || value }
