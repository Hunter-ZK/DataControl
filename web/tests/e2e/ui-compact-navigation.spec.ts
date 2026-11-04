import {expect,test} from '@playwright/test'

const mock={code:'OK',data:{query:'贷款余额',total:1,offset:0,limit:8,items:[{assetId:'DS-1',assetType:'TABLE',title:'贷款余额',technicalName:'dws_loan_balance',snippet:'模拟数据集',score:100,titleHighlight:'',technicalNameHighlight:''}],facets:{assetTypes:{TABLE:1},layers:{},catalogs:{},statuses:{}}}}

test('global query is editable in the top bar and search filters open on demand',async({page})=>{
  await page.route('**/api/v1/catalogs',route=>route.fulfill({json:{code:'OK',data:[]}}))
  await page.route('**/api/v1/search**',route=>route.fulfill({json:mock}))
  await page.goto('/search?q=贷款余额')
  const input=page.getByRole('textbox',{name:'全局资产搜索'})
  await expect(input).toHaveValue('贷款余额')
  await expect(page.locator('.search-hero')).toHaveCount(0)
  await page.getByRole('button',{name:'高级筛选'}).click()
  await expect(page.getByRole('heading',{name:'高级筛选与常用筛选'})).toBeVisible()
})

test('field deep link resolves to its dataset and opens the in-context drawer',async({page})=>{
  await page.route('**/api/v1/columns/F-1',route=>route.fulfill({json:{code:'OK',data:{assetId:'F-1',datasetId:'DS-1',columnName:'loan_bal',cnName:'贷款余额',dataType:'DECIMAL(20,2)'}}}))
  await page.route('**/api/v1/tables/DS-1',route=>route.fulfill({json:{code:'OK',data:{assetId:'DS-1',bizName:'贷款余额日快照',tableName:'dws_loan_balance',layerCode:'DWS',status:'ONLINE',catalogCode:'CREDIT'}}}))
  await page.route('**/api/v1/tables/DS-1/columns/complete',route=>route.fulfill({json:{code:'OK',data:{assetId:'DS-1',total:1,complete:true,items:[{assetId:'F-1',datasetId:'DS-1',columnName:'loan_bal',cnName:'贷款余额',dataType:'DECIMAL(20,2)',ordinalNo:1}]}}}))
  await page.goto('/fields/F-1')
  await expect(page).toHaveURL(/\/datasets\/DS-1\?tab=columns&fieldId=F-1/)
  await expect(page.getByRole('heading',{name:'字段详情'})).toBeVisible()
  await expect(page.getByText('loan_bal').first()).toBeVisible()
})

test('mobile top bar retains an actionable search entry',async({page})=>{
  await page.setViewportSize({width:390,height:780})
  await page.goto('/search')
  await page.getByRole('button',{name:'打开全局资产搜索'}).click()
  await expect(page.getByRole('dialog',{name:'快速查找数据资产'})).toBeVisible()
})
