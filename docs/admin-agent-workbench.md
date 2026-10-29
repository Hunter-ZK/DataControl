# DataControl 管理员工作台

## 入口与权限

- 前端路由：`/admin`
- 仅允许 `ADMIN` 或 `DEVELOPER` 角色访问。
- 后端接口统一位于 `/api/v1/admin`，独立检查数据库中的用户角色；仅隐藏前端菜单不构成权限控制。
- 页面包含 Agent 运行调试、Prompt 与规则中心、元数据管理三个区域。

## Agent 详细 Trace

Gateway 在运行期间读取 dsh 的 JSONL stdout 事件，并将运行起始上下文、工具调用、工具结果、状态、最终回答、非 JSON stdout 和 stderr 诊断信息作为开发 Trace 发送给 Portal。Portal 对内容进行凭据脱敏和大小限制后，保存至 `sys_agent_debug_event`。

- `DATACONTROL_AGENT_DEBUG_CAPTURE` 默认为 `1`；设为 `0` 可关闭详细 Trace 捕获。
- 单次运行最多保存 500 条详细事件；单条事件内容限制约 100 KB，超限会标记截断。
- API Key、密码、认证凭据、Bearer Token 和匹配到的密钥格式会脱敏。
- 隐藏思维链与中间 Assistant 推理文本不采集。
- 只展示 Harness 实际发出的事件。若 Harness 没有暴露底层 Provider HTTP 请求体、完整模型输入 token、token 用量或计费数据，页面会说明该边界，不会伪造数据。
- 已有历史运行只有工具摘要，不能从旧摘要恢复当时没有持久化的原始参数与返回值。

## Prompt / 规则中心

配置中心由本地 Gateway 读取以下内容，并为文件计算 SHA-256：

- 标准任务和多步任务 Profile 源文件；
- 当前 `DSH_HOME/profiles/<profile>/cordis.patch.yml` 实际配置与安装包清单；
- Agent3 MCP 工具目录；
- Guard 策略源代码及插件接入代码；
- 仓库内 Skills。

页面将源配置与运行时 Profile 分开显示。配置文件存在并不自动证明它已被 Harness 成功加载，因此还应核对健康状态、实际 Profile 路径和文件哈希。

## 元数据管理

当前区域使用真实数据库统计数据集、字段、指标、码表、码值、数据标准、词根和统计制度数量，并检查部分业务定义字段的缺失情况。卡片链接到已有目录/检索/详情页面。

目前这些元数据实体的 API 主要支持查询和详情，尚无统一的维护写入 API。因此页面不会假装提供保存/编辑能力；后续需要按实体补充字段校验、变更审计、权限控制与导入回滚。

## 数据库迁移

新增 Alembic 迁移 `20261029_0008`，创建 `sys_agent_debug_event`。开发环境需执行：

```powershell
python -m alembic upgrade head
```

确保运行 Portal 的用户数据库已完成迁移后，再使用管理员工作台。

## 安全边界

本页面面向受控的开发调试环境。详细 Trace 可能包含业务问题、SQL 和元数据返回值；不要把管理员账号、Gateway 调试接口或包含 Trace 的数据库暴露到不可信网络。生产部署应关闭详细采集，并依据组织的数据留存要求决定是否保留历史 Trace。
