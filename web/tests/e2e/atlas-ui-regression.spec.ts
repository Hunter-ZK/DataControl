import { expect, test } from '@playwright/test'

test('Atlas 2.1 homepage information architecture is preserved', async ({page}) => {
  await page.goto('/')
  await expect(page.locator('.atlas-home .atlas-hero')).toBeVisible()
  await expect(page.locator('.atlas-hero .hero-art')).toBeAttached()
  await expect(page.locator('.quick-capabilities .capability')).toHaveCount(4)
  await expect(page.locator('.naming-home-entry')).toHaveCount(0)
  await expect(page.locator('.workspace-heading')).toBeVisible()
})

test('Atlas navigation order stays stable when the naming workspace is added', async ({page}) => {
  await page.goto('/')
  const nav=page.locator('.nav-group').filter({has:page.locator('.nav-section', {hasText:'数据理解'})})
  await expect(nav.locator('.nav-item')).toHaveText([
    '业务指标', '数据标准', '标准码表', '统计制度', '词根索引',
  ])
  const work=page.locator('.nav-group').filter({has:page.locator('.nav-section',{hasText:'工作空间'})})
  await expect(work.locator('.nav-item')).toHaveText(['首页','智能问数','字段规范化命名'])
})

test('naming workbench uses Atlas-styled controls and not browser-native grey selects', async ({page}) => {
  await page.goto('/workbench/naming')
  await expect(page.locator('.naming-page .dc-page-head')).toBeVisible()
  await expect(page.locator('.file-zone')).toBeVisible()
  await page.getByRole('textbox',{name:'粘贴中文字段清单'}).fill('贷款余额')
  await page.getByRole('button',{name:'读取文本'}).click()
  await expect(page.locator('.source-summary .el-select')).toHaveCount(1)
  await page.getByRole('button',{name:/下一步：设置规则/}).click()
  await expect(page.locator('.rule-grid>div')).toHaveCount(4)
})
