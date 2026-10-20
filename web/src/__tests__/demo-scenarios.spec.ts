import { describe, expect, it } from 'vitest'
import { classifyDemoQuestion, demoDatasets, demoSuggestions, demoTrend } from '@/components/demo/demoScenarios'

describe('on-demand DataAgent demo', () => {
  it('classifies the four supported user intents from the actual input', () => {
    expect(classifyDemoQuestion('哪些数据集可以分析企业贷款余额？')).toBe('assets')
    expect(classifyDemoQuestion('2026年4至9月贷款余额的趋势如何？')).toBe('trend')
    expect(classifyDemoQuestion('帮我生成深圳分行2026年9月贷款余额的 SQL')).toBe('sql')
    expect(classifyDemoQuestion('“客户风险等级”字段应该怎么规范命名？')).toBe('naming')
  })

  it('does not create an unrelated loan answer for unsupported questions', () => {
    expect(classifyDemoQuestion('如何查看存款余额的趋势？')).toBeNull()
    expect(classifyDemoQuestion('机构代码的上游表是哪张？')).toBeNull()
    expect(classifyDemoQuestion('帮我生成资产负债表 SQL')).toBeNull()
    expect(classifyDemoQuestion('')).toBeNull()
  })

  it('exposes supported examples and coherent interactive preview fields', () => {
    expect(demoSuggestions.map(s => classifyDemoQuestion(s.question))).toEqual(
      demoSuggestions.map(s => s.kind),
    )
    expect(demoDatasets).toHaveLength(3)
    expect(demoDatasets.every(table =>
      table.table.startsWith('demo_') && table.fields.length >= 4,
    )).toBe(true)
    expect(demoDatasets[0]!.fields.some(field => field.name === 'org_code')).toBe(true)
    expect(demoTrend).toHaveLength(6)
    expect(demoTrend.every(point => point.value > 0)).toBe(true)
  })
})
