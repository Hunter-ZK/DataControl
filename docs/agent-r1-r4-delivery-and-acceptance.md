# DataControl Agent + Portal F1–F4｜增量交付与验收说明

日期：2026-10-28  
实施分支：`feature/r0-r1-harness-autonomy-20261027`（PR #6 Draft，**未合并 main**）

## 原则与边界

遵循已确认的“Claude 方案 + 六项增强建议”：保持 Vue → Portal → Gateway → DeepSeek Harness → Agent3 MCP/Core 的单一 Agent 运行时；可信 SQL/治理规则由确定性代码生成或静态验证。生产数据库、生产 DDL/DML **均不执行**。离线模拟查询仅允许在独立评测程序中，不向 Agent 开放 sandbox_run。

## 本轮实际提交的功能

### F1 身份、Skill、质量基础
- 正式 Agent API 要求登录；Portal 的续接会话由服务端持有，浏览器不得传入任意 provider sessionId；取消请求按登录用户检查 run 所属会话。
- 2026-10-28 最新变更：可选公共免费模型已恢复，开发启动时自动尝试安装到独立的 `dataagent-headless-free` Profile，无需另设环境开关。仅在用户显式选择免费模式并确认后使用；官方 DeepSeek 仍为默认模型。第三方兼容性尚待 Mac/Windows 实机验收，不允许使用内部数据。
- MCP 清单改为 `agent/tool-catalog.json`，由 MCP Server、Gateway、Portal 共享，避免三处白名单漂移。
- 标准档与多步任务档采用分别安装的 dsh Headless Profile（`dataagent-headless` / `dataagent-headless-multi`）；每会话固定档位并保存在 SQLite，默认 120s/600s 超时。普通启动会校验 Profile 内容，缺失时触发配置重建。二者目前通过配置与提示词分离，尚非全部规划插件的严格独立装载。
- 新增八份数据资产、SQL 改写、澄清、结果、规划、ETL 与质量检查 Skill 文档；为主要界面加入设计变量。
- `scripts/agent_quality_gate.py --mode stub` 执行确定性工具协议测试；`--mode real` 以当前 P3 题库进行真实模型问数测评并与本地基线比较。真实模型首次基线必须在本机实际运行后建立，不能用 CI 通过代替。

### F2 资产发现与统一入口
- Portal 新增 `/api/v1/agent-assets/{asset_type}/{asset_id}`、`/references`、`/lineage` 只读事实接口；支持七类资产，结果由数据库实际记录产生。
- Agent3 新增 `search_assets`、`get_asset`、`find_references`、`get_lineage_summary`、`revise_query`。改写要求已有已校验的结构化语义计划，保留指标与必要过滤条件，不允许任意原始 SQL 片段。
- Gateway 仅把真实 MCP 结果中的 `assetId/assetType` 作为证据，前端渲染可点击资产引用，而不是让模型自由编造 URL。
- 首页统一输入框提供 **检索资产** 和 **问 DataAgent** 两个明确操作；检索联想与即时结果卡可跳转。最近会话支持准确打开。
- 外壳加入快捷命令搜索、分组导航、移动端导航抽屉、账号退出；服务异常标识不再完全静态。

### F3 对话与过程可视
- 智能问数新增三栏（历史／对话／依据及 SQL 检查器），右栏切换资产依据、静态校验、工具步骤；工具步骤来自真实 Gateway 事件，不模拟思维链。
- 增加复制、重新生成、建议追问与本地有用/有误标记；在真实完成结果中记录时长（毫秒）和工具调用次数，可在回答中展示。
- 移动端可打开被折叠的聊天历史；服务端历史与登录会话仍保持原有审计机制。

### F4 数仓开发草案与浏览器回归
- 新增四个 **仅生成草案** 的确定性工具：`check_naming`、`generate_ddl`、`generate_etl`、`generate_dq_checks`。校验命名、字段类型、显式映射、真实源字段和质量规则；拒绝未治理字段及危险标识符，返回 `execution_allowed=false`。自动推测复杂关联与生产调度**不在当前实现范围**。
- 新增对应工具单元测试、元数据 API 测试和 Playwright Chromium 浏览器回归。浏览器在 1440/1024/390 宽度生成首页截图，验证检索结果和已受保护的 Agent 入口。

## 一次验收建议

在 Windows PowerShell：

```powershell
cd 'D:\学习\DataAgent\DataControl'
git status --short
git switch feature/r0-r1-harness-autonomy-20261027
git pull --ff-only
.\start.bat
```

在另一终端执行：

```powershell
.\.venv\Scripts\python.exe scripts\agent_quality_gate.py --mode stub
.\.venv\Scripts\python.exe scripts\p3_agent_acceptance.py
.\.venv\Scripts\python.exe scripts\agent_quality_gate.py --mode real --limit 12 --set-baseline
```

**不要提供任何 API Key 给他人或第三方测试服务。** 真实模型验收涉及官方 API 成本；`--set-baseline` 首轮测得的是实际分数，不是 100% 通过声明。

按产品动作验收：
1. 未登录点击智能问数，必须跳转登录，登录后返回；匿名直接 POST /agent/query 应被拒绝。
2. 首页输入“贷款余额”，点击“检索资产”：直接显示资产结果；点击“问 DataAgent”：打开正式问数，不自动猜测路由。
3. 搜索结果中的指标/字段/数据集卡可以准确进入详情；在 Agent 回答内点击引用应与真实数据库 ID 对应。
4. 依次问“本期各地区贷款余额，生成 SQL”“改成同比”“只看广东省”，核对指标、时间与过滤条件有没有漂移；如证据不足应明确澄清而非虚构。
5. 分别试用停止、异常中断、刷新、切换会话、不同用户读取历史；运行状态必须与服务端一致。
   在新会话中切换“标准问数 / 多步任务”，检查状态与不同 Profile 的启动，已发送过消息的会话应禁止直接切换档位；旧会话刷新后保留档位。
6. 测试命名、DDL/ETL/数据质量规则草案：可复制 SQL、解释依据，**不运行 SQL**；缺少真实字段或未确认业务连接必须明确拒绝或追问。
7. 浏览器 1440、1024、390px 下检验首页、导航、问数历史与检查器，特别注意小屏入口能否使用。

## 刻意未宣称完成的项目

这些涉及更大的架构或环境条件，不能仅凭源码有入口就算验收通过：
- 标准/多步 dsh Profile 已物理分离，但规划插件和 Skill 集合的严格分档白名单、工具调用上限和跨进程任务恢复仍未完成；
- Portal → Gateway → MCP 逐用户动态 AuthzContext 和数据权限下传。当前只完成 Portal 会话归属，MCP 仍为本地开发 PoC 身份；不能视为生产多租户权限隔离；
- `MAX_PT` 分区策略和受治理维表自动连接的完整确定性能力、SQL 常用库检索覆盖率、正式第二模型提供方；
- 基于真实模型 SQL 的 DuckDB 结果集对照，以及跨类别准确率统计，尚需专门完善 Golden 数据和评估转换规则；
- 完整 Stylelint 零硬编码、Pinia 全局重构、自动 OpenAPI 类型生成、全部旧界面重设计、全量移动端 UX 确认；
- 正式 Token 计费统计和 Guard 集中审计、服务端持久化用户反馈；
- 官方 DeepSeek 本机验收结果、外部模型可用性与响应时间 P50/P95：必须使用本机运行证据，不用 GitHub Stub CI 冒充。

提交说明中的“F1–F4 已实现”仅针对上述实际落地的子能力；不足项需另行验收/跟进。

## CI 门禁

GitHub Actions 对相同最终 HEAD 同时检查：Python（Win/macOS/Ubuntu）、前端（Win/macOS/Ubuntu）、Agent（Win/macOS/Ubuntu）、Stub E2E、Chromium Playwright。只有相关任务全部完成且成功后，才能写“CI 全绿”。如果仍 pending/failed，以 GitHub 真实状态为准。Draft PR 不自动合并。
