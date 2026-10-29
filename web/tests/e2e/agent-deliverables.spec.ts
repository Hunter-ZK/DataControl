import { expect, test } from '@playwright/test'

test('long task outputs open in a separate real-results workspace', async ({ page }) => {
  const fixture = {
    id:'chat-ui-artifacts',serverId:'srv-ui-artifacts',title:'DWS 查询方案',
    sessionId:null,modelMode:'deepseek',taskTier:'multi',pinned:false,
    createdAt:1700000000000,updatedAt:1700000000000,
    messages:[
      {role:'user',text:'请生成 DWS 月度汇总 SQL'},
      {role:'assistant',text:'已生成用于人工审核的 SQL 草案，不执行生产任务。',
        sql:"SELECT region_code, SUM(loan_balance) AS balance FROM dw.dws_loan WHERE dt = '${dt}' GROUP BY region_code",
        validationState:'passed',validation:{valid:true,operation:'query',issues:[]},
        evidence:{assets:[{assetId:'DS1',assetType:'TABLE',title:'贷款汇总',technicalName:'dw.dws_loan'}]},
        events:[{type:'tool_call',callId:'t1',tool:'compile_query'},
          {type:'tool_result',callId:'t1',tool:'compile_query',status:'success'}],
        durationMs:1200,toolCallCount:1},
    ],
  }
  await page.addInitScript((conversation) => {
    localStorage.setItem('datacontrol_token','fixture-token')
    localStorage.setItem('datacontrol_user',JSON.stringify({id:11,username:'tester'}))
    localStorage.setItem('datacontrol_agent_conversations_v1_user_11',JSON.stringify([conversation]))
    localStorage.setItem('datacontrol_agent_active_conversation_v1_user_11',conversation.id)
  },fixture)
  await page.route('**/api/v1/agent/status**',async route=>route.fulfill({json:{code:'OK',data:{
    ready:true,mode:'test',source:'fixture',provider:'test',model:'test',gatewayUrl:'',sqlExecutionEnabled:false
  }}}))
  await page.route('**/api/v1/agent/conversations',async route=>route.fulfill({json:{code:'OK',data:[]}}))
  await page.goto('/agent')
  await expect(page.getByRole('button',{name:/成果工作区/}).first()).toBeVisible()
  await page.getByRole('button',{name:/成果工作区/}).first().click()
  const workspace=page.getByRole('region',{name:'Agent 独立成果工作区'})
  await expect(workspace.getByRole('heading',{name:'任务成果工作区'})).toBeVisible()
  await expect(workspace).toContainText('1 份 SQL')
  await workspace.getByRole('button',{name:'SQL 草案'}).click()
  await expect(workspace).toContainText('SELECT region_code')
  await workspace.getByRole('button',{name:'依据'}).click()
  await expect(workspace).toContainText('贷款汇总')
  await workspace.getByRole('button',{name:'任务记录'}).click()
  await expect(workspace).toContainText('编译语义查询')
  await workspace.getByRole('button',{name:'关闭成果工作区'}).click()
  await expect(workspace).toHaveCount(0)
})
