import { expect, test } from '@playwright/test'

test('approved homepage keeps original hero and removes duplicate module cards',async({page})=>{
  await page.goto('/')
  await expect(page.locator('.atlas-home .atlas-hero')).toBeVisible()
  await expect(page.locator('.atlas-hero .hero-art')).toBeAttached()
  await expect(page.locator('.quick-capabilities')).toHaveCount(0)
  await expect(page.locator('.recent-panel')).toHaveCount(2)
  await expect(page.locator('.overview-panel')).toHaveCount(0)
  await expect(page.locator('.topbar .command')).toHaveCount(0)
})

test('approved navigation shows six primary destinations, with tools accessible by secondary routes',async({page})=>{
  await page.goto('/')
  const nav=page.locator('.sidebar .nav-item')
  await expect(nav).toHaveCount(6)
  await expect(nav).toHaveText(['首页','资产目录','数据标准','词根索引','指标与制度','智能问数'])
  await expect(page.locator('.sidebar .sidebar-foot .account-trigger')).toBeVisible()
  await expect(page.locator('.sidebar .nav-item[href="/profile"]')).toHaveCount(0)
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
