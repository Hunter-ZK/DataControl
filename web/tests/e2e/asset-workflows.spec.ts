import { expect, test } from '@playwright/test'

test('naming workbench supports deterministic review without invented roots', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('datacontrol_token','test')
    localStorage.setItem('datacontrol_user',JSON.stringify({id:11,username:'qa'}))
  })
  await page.route('**/api/v1/workbench/naming/suggest', route => route.fulfill({json:{
    code:'OK',data:{engine:'deterministic-root-matcher-v1',notice:'规则预览',
      items:[{cnName:'贷款余额',suggestedName:'loan_bal',segments:[
        {cn:'贷款',root:'loan',source:'贷款'},{cn:'余额',root:'bal',source:'余额'}],
        source:'词根规则',issues:[],status:'待确认',existingCandidates:[]},
      {cnName:'未知字段',suggestedName:'',segments:[{cn:'未知字段',root:'',source:'missing'}],
        source:'人工待补充',issues:['缺少词根：未知字段'],status:'待确认',existingCandidates:[]}]}
  }}))
  await page.route('**/api/v1/workbench/naming/export',route=>route.fulfill({
    status:200,body:'spreadsheet fixture',headers:{'content-type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
  }))
  await page.goto('/workbench/naming')
  await expect(page.getByRole('heading',{name:'字段规范化命名'})).toBeVisible()
  await page.getByRole('textbox',{name:'粘贴中文字段清单'}).fill('贷款余额\n未知字段')
  await page.getByRole('button',{name:'读取文本'}).click()
  await page.getByRole('button',{name:/下一步：设置规则/}).click()
  await page.getByRole('button',{name:'生成命名建议'}).click()
  await expect(page.locator('.naming-table tbody tr')).toHaveCount(2)
  await expect(page.locator('.naming-table')).toContainText('未知字段 → 待补')
  await page.getByRole('button',{name:'批量确认无校验问题的行'}).click()
  await expect(page.getByText('已确认 1')).toBeVisible()
  await page.getByRole('button',{name:/查看导出/}).click()
  await expect(page.getByText('建议新增词根',{exact:true})).toBeVisible()
  const downloadPromise=page.waitForEvent('download')
  await page.getByRole('button',{name:'下载 Excel 成果'}).click()
  const download=await downloadPromise
  expect(download.suggestedFilename()).toBe('datacontrol_naming_results.xlsx')
})

test('asset Agent stays inside detail drawer and uses existing server stream', async ({ page }) => {
  await page.addInitScript(()=>{
    localStorage.setItem('datacontrol_token','test')
    localStorage.setItem('datacontrol_user',JSON.stringify({id:11,username:'qa'}))
  })
  await page.route('**/api/v1/code-tables/C-1', route=>route.fulfill({
    json:{code:'OK',data:{assetId:'CODE-1',codeTableNo:'C-1',name:'地区码表',
      status:'ONLINE',values:[{value:'44',name:'广东'}]}}
  }))
  await page.route('**/api/v1/agent-assets/references**',route=>route.fulfill({
    json:{code:'OK',data:{assetId:'CODE-1',total:0,status:'complete',references:[]}}
  }))
  await page.route('**/api/v1/agent/status**',route=>route.fulfill({json:{
    code:'OK',data:{ready:true,reason:'',provider:'deepseek',model:'official',mode:'production'}
  }}))
  await page.route('**/api/v1/agent/conversations', route=>route.fulfill({json:{
    code:'OK',data:{id:'server-test-1',title:'资产问答',messages:[],modelMode:'deepseek'}
  }}))
  await page.route('**/api/v1/agent/query/stream',route=>route.fulfill({
    status:200,contentType:'application/x-ndjson',
    body:JSON.stringify({type:'activity',event:{type:'tool_call',tool:'get_asset',callId:'c-1'}})+'\n'+
      JSON.stringify({type:'result',result:{answer:'地区码表包含登记码值广东。',sql:null,
        evidence:{assets:[{assetId:'CODE-1',assetType:'CODE_TABLE',title:'地区码表'}]},
        events:[{type:'tool_call',tool:'get_asset',callId:'c-1'}],sqlExecuted:false,hiddenReasoningExposed:false}})+'\n'
  }))
  await page.goto('/code-tables/C-1')
  await page.getByRole('button',{name:'问这个码表'}).click()
  await expect(page.locator('.dc-agent-drawer')).toBeVisible()
  await expect(page.locator('.dc-agent-drawer')).toContainText('地区码表')
  await page.locator('.dc-agent-drawer').getByRole('button',{name:'发送'}).click()
  await expect(page.locator('.dc-agent-drawer')).toContainText('地区码表包含登记码值广东。')
  await expect(page).toHaveURL(/\/code-tables\/C-1/)
  await page.locator('.dc-agent-drawer').getByRole('button',{name:/在完整对话中继续/}).click()
  await expect(page).toHaveURL(/\/agent\?conversationId=/)
})
