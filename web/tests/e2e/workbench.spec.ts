import { expect, test } from '@playwright/test'

const queryData = {
  code: 'OK',
  data: {
    query: '贷款余额', total: 1, offset: 0, limit: 8,
    items: [{ assetId: 'DS000004', assetType: 'TABLE', title: '贷款余额汇总',
      technicalName: 'stat_prod.dws_loan_region_month', snippet: '模拟数据集',
      score: 100, titleHighlight: '', technicalNameHighlight: '' }],
    facets: { assetTypes: { TABLE: 1 }, layers: {}, catalogs: {}, statuses: {} },
  },
}

test('unified search keeps asset search and Agent Q&A as explicit choices', async ({ page }) => {
  await page.route('**/api/v1/search**', async route => {
    const url = route.request().url()
    await route.fulfill({
      json: url.includes('/suggest') ? { code: 'OK', data: [] } : queryData,
    })
  })
  await page.goto('/')
  const input = page.getByRole('textbox', { name: '数据资产检索与 DataAgent 统一入口' })
  await input.fill('贷款余额')
  await page.getByRole('button', { name: '检索资产' }).click()
  await expect(page.getByText('贷款余额汇总')).toBeVisible()
  await expect(page).toHaveURL(/\/$/)
  await page.getByRole('button', { name: '向 DataAgent 提问' }).click()
  // The Agent route is protected, so anonymous users are sent to login.
  await expect(page).toHaveURL(/\/login\?redirect=/)
})

for (const width of [1440, 1024, 390]) {
  test(`homepage renders at ${width}px without unusable input`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 850 })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /数据触手可及/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '检索资产' })).toBeVisible()
    await expect(page.getByRole('button', { name: '问 DataAgent' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath(`homepage-${width}.png`), fullPage: true })
  })
}

test('mobile navigation exposes asset discovery and protected Agent', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 780 })
  await page.goto('/')
  await page.getByRole('button', { name: '展开导航' }).click()
  await expect(page.getByRole('link', { name: '智能问数' }).first()).toBeVisible()
})
