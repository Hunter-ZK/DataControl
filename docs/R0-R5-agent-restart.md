# DataControl R0–R5 实施与验收基线（2026-10-27）

来源：用户已确认的产品需求、Claude《DataControl 后续优化方案》及当前源码校验。本文区分**已提交**和**尚未开发**，不以 CI 桩模型测试代替真实大模型验收。

## 已确认的方向

- 元数据门户和 DataAgent 双核心；用户共用统一入口，不强制在检索与聊天之间作选择。
- 优先 Agent 真实能力，再优化 UI 和资产检索，真实 DataWorks 数据接入与血缘扩展暂缓。
- 当前本地开发，以模拟数据验证；生产 SQL/DDL 不执行，真实执行仅在用户后续批准独立模拟沙箱时讨论。
- 不恢复 10 月 20 日实验原型；不擅自合并历史 Draft PR。
- 采用既有 Agent3 MCP + Gateway + DeepSeek Harness 组合，Agent 开放式规划但受治理工具边界约束。

## R0 · 运行时基线与正确性

1. 固定在 `feature/next-p2-semantic-planning` 的代码树上创建新开发分支，不直接修改 main。
2. 升级 dsh `0.1.6-alpha.2` → `0.2.1-rc.3`，独立 `DSH_HOME` 并支持旧版回退；开放 Headless Goal / Todo / 子 Agent / Workflow / compaction / Plan Mode 组件。
3. 修复路由复用时详情不更新、引用详情回退错误项、检索错误引号提示；保存端到端与构建证据。
4. P0 完成标志：GitHub CI 全绿 + 本地 DeepSeek 真模型调用和对话续接通过。前者不代表后者。

## R1 · Agent 真实可用（未开发）

- 流式事件、取消、数据库会话存储、请求并发限制和运行审计；SDK 替代每问 CLI 单进程须先比较性能与兼容性。
- 基于既有 Question Bank 验收可信 SQL、澄清准确率及任务耗时；不可无基线承诺 3 秒首反馈。

## R2 · 资产发现 + 可信 SQL（未开发）

- `search_assets` / `get_asset` / 可信血缘摘要；受治理 SQL 修订；统一搜索入口的快速通道；实体卡跳转。
- 含歧义追问和上下文延续，但不虚构字段/码值。

## R3 · 前端产品化（未开发）

- 统一输入框 + 联想 + 搜索结果卡 + 对话；保留独立检索页面；围绕真实任务重整导航和详情跳转。

## R4 · 大规模检索（未开发）

- FTS 性能优化、同义词/词根、完整筛选与实际语料压力测试；性能指标从真实基线定义。

## R5 · 数仓开发辅助（未开发）

- DDL/加工 SQL/数据质量校验的受治理工具与 Skills；多步骤任务规划、测试样本和人工确认。
- 模拟数据库执行须先单独设计隔离与审批，绝不可连到生产数仓。

## 本地验收（Windows）

1. `git fetch origin`，`git switch feature/r0-r1-harness-autonomy-20261027`。
2. `powershell -ExecutionPolicy Bypass -File .\\scripts\\setup-dev.ps1`（首次）和 `powershell -ExecutionPolicy Bypass -File .\\scripts\\setup-agent.ps1`。
3. 在**本机终端进程环境**中设置真实 `DEEPSEEK_API_KEY`，运行 `powershell -ExecutionPolicy Bypass -File .\\scripts\\start-dev.ps1`。
4. 打开 `http://127.0.0.1:5173`；用 Agent 页面提问“本期贷款余额，生成并校验 SQL，不执行”，再在同一会话追问“按地区统计”。
5. 新终端执行 `.\\.venv\\Scripts\\python.exe scripts\\p3_agent_acceptance.py`，核对输出及 `.local/p3-agent-acceptance.json`。真实模型失败时留存 `.local/agent-gateway.err.log`、`.local/agent-mcp.err.log`，不要提交密钥。
6. 启动 CLI 的 `--dump-config` 核对开启的自主规划插件、Shell/Web 与执行权限仍受限。
