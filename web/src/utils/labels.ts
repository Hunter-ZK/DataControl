/** Presentation-only labels; technical values remain unchanged in API payloads and URLs. */
export const STATUS_LABELS: Readonly<Record<string,string>> = {
  ONLINE:'在用', ACTIVE:'在用', EFFECTIVE:'有效', VALID:'有效',
  OFFLINE:'已下线', DISABLED:'已下线', DEPRECATED:'已下线', DRAFT:'草稿',
}
export function statusLabel(value: unknown): string {
  const key=String(value ?? '').trim()
  return STATUS_LABELS[key.toUpperCase()] ?? key
}
export const ASSET_TYPE_LABELS: Readonly<Record<string,string>> = {
  TABLE:'数据集', COLUMN:'字段', CODE_TABLE:'码表', STANDARD:'数据标准',
  WORD_ROOT:'词根', METRIC:'指标', STAT_SYSTEM:'统计制度',
}
export function assetTypeLabel(value: unknown): string {
  const key=String(value ?? '').trim()
  return ASSET_TYPE_LABELS[key.toUpperCase()] ?? key
}
