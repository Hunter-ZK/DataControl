# R1-B｜服务端会话、运行状态和审计（2026-10-28）

## 目标和边界

DataControl 仍采用 Vue → Portal FastAPI → Agent Gateway → DeepSeek Harness → Agent3 MCP/Core 的单仓库架构。**Portal 记录会话和运行事实；Gateway 执行模型调用。**不新增 LangGraph、Redis、第二套 Agent 服务，也不执行生产 SQL。当前只在模拟数据/本机环境验收；官方 DeepSeek 真模型和第三方公共模型的实际质量需要独立人工验证。

## 数据对象与数据库

- `sys_agent_conversation`：用户、标题、模型模式、置顶、Provider session ID、有限旧历史、资产上下文、时间戳。
- `sys_agent_turn`：唯一 run ID、conversation ID、内部请求文本、用户界面原始问题、模型模式、状态、脱敏结果和时间。
- `sys_agent_tool_event`：按执行顺序的白名单工具名、Call ID 和状态；不记录原始参数、工具返回、隐藏思维。
- 迁移：`20261028_0005_agent_history.py`；正常 Windows `start.bat` 已在服务启动前执行 `alembic upgrade head`。旧浏览器历史在用户确认导入前保持不变。

## 状态机

```text
queued → running → completed
                 → failed | timeout | cancelled | interrupted
queued/running → cancel_requested → cancelled
                                  → completed（完成与取消竞态，按实际终止事件）
                                  → interrupted（失联，结果不确定）
```

服务端只在观察到最终 `result` 时记录 completed；仅收到取消请求不算 cancelled。异常结束将清除 Provider session ID，避免恢复不完整上下文；用户刷新或 Portal 重启时，遗留运行标记为 interrupted。Gateway 采用进程内任务登记并限制同时运行 4 个任务，本机单实例开发是第一阶段边界；不宣称已经实现跨机器任务恢复或后台断线续跑。

`runId` 是跨重复请求的幂等键。相同用户/会话/问题的已终止请求可返回缓存结果；运行中重复则返回 409；同一 ID 变更请求内容返回 409。数据库对同一会话未终止回合设置唯一部分索引。每用户最多 2 个运行中的回合，且不会越权恢复其他用户的历史。

## API

- `GET /api/v1/agent/conversations`：当前登录用户的会话列表与历史。
- `POST /api/v1/agent/conversations`：创建固定模型模式会话。
- `POST /api/v1/agent/conversations/import`：用户明确同意后导入本地旧会话，剔除旧工具事件参数。
- `GET/PATCH/DELETE /api/v1/agent/conversations/{id}`：详情、重命名/置顶、删除（执行中不可删除）。
- `POST /api/v1/agent/query/stream`：原有 NDJSON 基础上可选携带 `conversationId` 和 `displayQuestion`；有会话 ID 时必须登录，服务端拥有会话 ID / 模型模式 / 续接 session ID 的最终控制权。无会话 ID 的旧用法保持本地浏览器历史。
- `GET /api/v1/agent/runs/{runId}`：有权限用户读取本轮状态。
- `POST /api/v1/agent/query/{runId}/cancel`：取消请求；返回 `cancelled: true` 表示取消信号已下发，不代表最终终止。

## 旧数据兼容与用户体验

对话历史继续以 `localStorage` 作浏览器侧缓存；登录后同步服务端历史，旧本地记录仅经确认才上传，取消时不删除本地历史。保存时限制最多 40 段会话、每段最近 80 条消息；服务端原始回合仍保留（后续可单独设计保留期和脱敏政策）。免费测试模式与官方模式严格隔离，第三方公共模型始终要求本次页面明确确认；不得提交真实公司数据。

## 验收与限制

1. Windows 最新 HEAD：正常 `start.bat` 自动升级到迁移版本 0005，不要求重新安装 npm。
2. 使用真实 DeepSeek：至少一次完整 `resolve_metric → get_schema → compile_query → validate_sql`，检查返回的 SQL 校验依据和 `sqlExecuted=false`。
3. 登录用户：发送→刷新→历史恢复；重复 runId 不重复启动；不同用户不能读取/取消他人的运行。
4. 停止请求：等待服务端 terminal `cancelled`；失败不能误显示停止；异常断流不能伪装 completed。
5. 未登录用户：仍使用本地历史；旧本地历史确认后导入，取消则原样保留；官方/免费模式上下文不交叉。
6. 自动化：Python、Vue、CI stub E2E、跨平台 CI 全绿；外部真实模型验收不由 CI 代替。

**尚未实现：**跨进程/跨机器中断恢复、后台常驻执行、推送通知、运行级 Token/成本统计、长期审计保留政策、全量 R1-C 真实模型准确率评测。这些不是本次完成声明。
