import { describe, it, expect } from 'vitest'
import { createDdlDraft, createSelectDraft, createCaseDraft, makeCsv } from '@/utils/assetExport'

const fields = [
  { columnName: 'loan_amt', dataType: 'DECIMAL(20,2)', ordinalNo: 2 },
  { columnName: 'stat_dt', dataType: 'STRING', ordinalNo: 1 },
]
describe('asset export safety', () => {
  it('preserves field order and labels incomplete SQL drafts', () => {
    const sql = createDdlDraft('dws_loan', fields, true)
    expect(sql).toContain('CREATE TABLE dws_loan')
    expect(sql.indexOf('stat_dt')).toBeLessThan(sql.indexOf('loan_amt'))
    expect(sql).toContain('未包含分区')
    expect(createSelectDraft('dws_loan', fields, true)).toContain('人工补充')
  })
  it('rejects incomplete metadata and dangerous identifiers', () => {
    expect(() => createDdlDraft('dws_loan', fields, false)).toThrow('未完整加载')
    expect(() => createDdlDraft('loan;DROP', fields, true)).toThrow('标识符')
    expect(() => createDdlDraft('dws_loan', [{ columnName: 'foo', dataType: 'ARRAY<STRING>' }], true)).toThrow('不支持')
  })
  it('escapes literals and spreadsheet formulas', () => {
    expect(createCaseDraft([{ value: "O'H", name: "王'某" }])).toContain("O''H")
    expect(createCaseDraft([{ value: "O'H", name: "王'某" }])).toContain("王''某")
    expect(makeCsv([['字段'], ['=1+1']])).toContain("'=1+1")
    expect(makeCsv([['名称'], ['贷款,"余额"']])).toContain('""余额""')
  })
})
