import { describe, expect, it } from 'vitest'
import { renderAgentMarkdown } from '@/components/agent/markdown'

describe('renderAgentMarkdown', () => {
  it('renders structured markdown for long-form agent answers', () => {
    const html = renderAgentMarkdown(
      '## 结论\n\n**贷款余额**使用以下口径。\n\n1. 先确认指标\n2. 再确认期间\n\n| 字段 | 含义 |\n| --- | --- |\n| loan_balance | 贷款余额 |',
      '结论',
    )
    expect(html).toContain('<strong>贷款余额</strong>')
    expect(html).toContain('<ol>')
    expect(html).toContain('<table>')
    expect(html).not.toContain('<h2>结论</h2>')
  })

  it('does not trust raw html or unsafe link protocols', () => {
    const html = renderAgentMarkdown('<script>alert(1)</script>\n\n[bad](javascript:alert(1))')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('href="javascript:')
    expect(html).toContain('&lt;script&gt;')
  })
})
