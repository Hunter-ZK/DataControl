export interface ExportColumn {
  columnName: string
  dataType: string
  ordinalNo?: number
  cnName?: string | null
  bizDefinition?: string | null
  standardNo?: string | null
  codeTableNo?: string | null
}

const identifier = /^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$/
const fieldType = /^[A-Za-z][A-Za-z0-9_]*(?:\(\d+(?:\s*,\s*\d+)?\))?$/
export function safeIdentifier(value: string): string {
  if (!identifier.test(value)) throw new Error('元数据标识符不符合安全规则，已停止生成 SQL。')
  return value
}
function checkedColumns(columns: ExportColumn[], complete: boolean): ExportColumn[] {
  if (!complete || columns.length === 0) throw new Error('字段尚未完整加载，不能生成完整资产导出。')
  const seen = new Set<string>()
  return [...columns].sort((a, b) => (a.ordinalNo || 0) - (b.ordinalNo || 0)).map(column => {
    safeIdentifier(column.columnName)
    if (!fieldType.test(column.dataType.trim())) throw new Error('不支持字段类型：' + column.dataType)
    if (seen.has(column.columnName.toLowerCase())) throw new Error('存在重名字段：' + column.columnName)
    seen.add(column.columnName.toLowerCase())
    return column
  })
}
export function createDdlDraft(tableName: string, columns: ExportColumn[], complete: boolean): string {
  safeIdentifier(tableName)
  const fields = checkedColumns(columns, complete)
  return [
    '-- 元数据草案：未包含分区、生命周期、存储及权限配置，未校验目标 SQL 方言。',
    '-- 仅用于预览与人工复核；不得直接部署生产表。',
    'CREATE TABLE ' + tableName + ' (',
    fields.map(c => '  ' + c.columnName + ' ' + c.dataType).join(',\n'),
    ');',
  ].join('\n')
}
export function createSelectDraft(tableName: string, columns: ExportColumn[], complete: boolean): string {
  safeIdentifier(tableName)
  const fields = checkedColumns(columns, complete)
  return [
    '-- 查询草案：未登记可验证的分区或期次条件，使用前需人工补充。',
    'SELECT',
    fields.map(c => '  ' + c.columnName).join(',\n'),
    'FROM ' + tableName + ';',
  ].join('\n')
}
export function createCaseDraft(values: Array<{ value: string | number; name?: string }>): string {
  if (!values.length) throw new Error('当前码表没有码值。')
  const escape = (v: unknown) => String(v ?? '').replace(/'/g, "''")
  return ['-- 请将 source_column 替换为真实字段，并核对 SQL 方言与码值类型。',
    'CASE source_column', ...values.map(row => "  WHEN '" + escape(row.value) + "' THEN '" + escape(row.name) + "'"),
    '  ELSE NULL', 'END'].join('\n')
}
export function makeCsv(rows: unknown[][]): string {
  function cell(value: unknown): string {
    let text = String(value ?? '')
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text
    return '"' + text.replace(/"/g, '""') + '"'
  }
  return '\uFEFF' + rows.map(row => row.map(cell).join(',')).join('\r\n') + '\r\n'
}
