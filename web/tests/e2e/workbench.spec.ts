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
    await expect(page.getByRole('button', { name: '向 DataAgent 提问' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath(`homepage-${width}.png`), fullPage: true })
  })
}

test('mobile navigation exposes asset discovery and protected Agent', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 780 })
  await page.goto('/')
  await page.getByRole('button', { name: '展开导航' }).click()
  await expect(page.getByRole('link', { name: '智能问数' }).first()).toBeVisible()
})

test('asset search separates result records and switches detail density', async ({ page }) => {
  await page.route('**/api/v1/catalogs', async route => {
    await route.fulfill({ json: { code:'OK',data:[] } })
  })
  await page.route('**/api/v1/search**', async route => {
    await route.fulfill({ json: route.request().url().includes('/suggest')
      ? {code:'OK',data:[]} : queryData })
  })
  await page.goto('/search?q=贷款余额')
  await expect(page.getByRole('heading', { name: '贷款余额汇总' })).toBeVisible()
  await expect(page.locator('.result-group')).toHaveCount(1)
  await expect(page.locator('.asset-definition')).toHaveCount(1)
  await page.getByRole('button', { name: '精简' }).click()
  await expect(page.locator('.asset-definition')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '贷款余额汇总' })).toBeVisible()
  await page.getByRole('button', { name: '详细' }).click()
  await expect(page.locator('.asset-definition')).toHaveCount(1)
})

test('word-root dictionary retains searchable rows without card layout', async ({ page }) => {
  await page.route('**/api/v1/word-roots**', async route => {
    await route.fulfill({ json: {code:'OK',data:[
      {assetId:'W-1',root:'BAL',cnName:'余额',enFull:'Balance',synonyms:'存量余额',status:'ONLINE'},
      {assetId:'W-2',root:'AMT',cnName:'金额',enFull:'Amount',synonyms:'',status:'ONLINE'}
    ]} })
  })
  await page.goto('/word-roots')
  await expect(page.locator('.dictionary-table tbody tr')).toHaveCount(2)
  await page.getByRole('button', { name: 'B', exact:true }).click()
  await expect(page.locator('.dictionary-table tbody tr')).toHaveCount(1)
  await expect(page.getByRole('link', { name: 'BAL' })).toBeVisible()
})

test('asset quick preview opens lightweight hover and a pinnable dialog without navigation', async ({ page }) => {
  await page.route('**/api/v1/catalogs', async route=>route.fulfill({json:{code:'OK',data:[]}}))
  await page.route('**/api/v1/tables/DS000004', async route=>route.fulfill({json:{code:'OK',data:{
    assetId:'DS000004',bizName:'贷款余额汇总',tableName:'stat_prod.dws_loan_region_month',
    layerCode:'DWS',description:'按月汇总的模拟贷款余额数据集'
  }}}))
  await page.route('**/api/v1/search**', async route=>route.fulfill({json:route.request().url().includes('/suggest')
    ? {code:'OK',data:[]} : queryData}))
  await page.goto('/search?q=贷款余额')
  const button=page.getByRole('button',{name:'快捷预览资产'})
  await button.hover()
  await expect(page.locator('.dc-asset-preview-popper')).toContainText('贷款余额汇总')
  await button.click()
  const dialog=page.getByRole('dialog',{name:'资产快捷预览'})
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('贷款余额汇总')
  await expect(page).toHaveURL(/\/search\?q=/)
})

test('search presets can be named, restored and deleted in this browser', async ({ page }) => {
  await page.route('**/api/v1/catalogs', async route=>route.fulfill({json:{code:'OK',data:[]}}))
  await page.route('**/api/v1/search**', async route=>route.fulfill({json:route.request().url().includes('/suggest')
    ? {code:'OK',data:[]} : queryData}))
  await page.goto('/search?q=贷款余额')
  await page.getByRole('button',{name:'保存筛选',exact:true}).click()
  await page.locator('.el-message-box input').fill('贷款常用查询')
  await page.locator('.el-message-box__btns .el-button--primary').click()
  await expect(page.getByRole('button',{name:'应用：贷款常用查询'})).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button',{name:'应用：贷款常用查询'})).toBeVisible()
  await page.getByRole('button',{name:'应用：贷款常用查询'}).click()
  await expect(page.getByRole('heading',{name:'贷款余额汇总'})).toBeVisible()
  await page.getByRole('button',{name:'删除筛选：贷款常用查询'}).click()
  await page.locator('.el-message-box__btns .el-button--primary').click()
  await expect(page.getByRole('button',{name:'应用：贷款常用查询'})).toHaveCount(0)
})
