# DataControl 本地 DeepSeek（llama.cpp）接入与验收

新增模型模式：local-deepseek。现有 DeepSeek 官方（deepseek）及公共免费测试（free-test）仍保留。

## 调用链

Vue Agent → Portal :8000 → Gateway :8910 → dsh dataagent-headless-local → llm-pi-ai OpenAI Chat Completions → llama.cpp :9931/v1/chat/completions；工具调用继续经过 Agent3 MCP :8900、Guard 和可信 SQL 静态校验。没有单独绕开 Harness 做普通聊天。

## Windows 验收

1. 在同一 Windows 电脑启动 llama.cpp llama-server，仅监听 127.0.0.1:9931；确认 Invoke-RestMethod http://127.0.0.1:9931/v1/models 能返回 data[].id。
2. 若只有一个模型 ID，DataControl 自动选择；如果有多个，先设置 PowerShell 环境变量 $env:DATACONTROL_LOCAL_MODEL_ID 为实际返回的完整 ID，不按文件名猜测。
3. 在仓库根目录：

    git fetch origin
    git switch feature/local-deepseek-llamacpp-20261030
    git pull --ff-only
    .\.venv\Scripts\python.exe -m dataagent_gateway.local_provider probe
    .\scripts\setup-local-model.ps1
    .\start.bat

4. 另开 PowerShell 检查健康状态：

    Invoke-RestMethod 'http://127.0.0.1:8910/health?modelMode=local-deepseek&taskTier=standard' | Select-Object ready,provider,model,profile,reason

期望 ready=True，provider=local-llama，model 与 /v1/models id 一致，profile=dataagent-headless-local。多步任务同样可指定 taskTier=multi。
5. 浏览器进入 http://127.0.0.1:5173/agent，新建会话、选择“本地 DeepSeek”。先用简单文本问题确认模型能回答，再用业务问题检查工具调用：请通过元数据工具查找贷款余额指标及所属数据集与真实字段，能生成 SQL 时进行静态校验，不要执行 SQL。
6. 用管理员账号访问 /admin，在运行 Trace 中查看 modelMode=local-deepseek、本轮 tool_call/tool_result、真实字段依据、静态 SQL 校验；在规则中心选择本地模式查看当前 Profile。

## 验收边界

- 模型可用：/v1/models 正常、local Profile ready、普通问答有回复。
- Agent 可用：真实 MCP 工具调用已执行，工具返回与资产元数据一致，SQL 只生成和校验，不执行生产 SQL。7B Distill-Qwen 不保证稳定 Tool Calling；若无工具调用，应明确标记模型服务可用但 Agent 能力未通过。
- 不能从 CI 或一次聊天成功推断 CPU 7B 可以稳定完成多步 Agent 任务。真实本机模型响应时间和工具调用质量必须实际测试。

## 配置项

| 环境变量 | 默认值 | 含义 |
| --- | --- | --- |
| DATACONTROL_LOCAL_MODEL_BASE_URL | http://127.0.0.1:9931/v1 | 仅允许本机环回 HTTP /v1 URL |
| DATACONTROL_LOCAL_MODEL_ID | 自动发现单一 id | 多模型时指定准确 ID |
| DATACONTROL_AGENT_RUN_TIMEOUT_LOCAL | 900 秒（标准）/ 1200 秒（多步） | 整次 Agent 运行超时，可手动延长 |
| DATACONTROL_LOCAL_CONTEXT_WINDOW | 8192 | 声明上下文窗口，不应超过实际 llama-server 设置 |
| DATACONTROL_LOCAL_MAX_TOKENS | 2048 | 每次输出 Token 上限，CPU 环境应谨慎提高 |
| DATACONTROL_LOCAL_MODEL_API_KEY | local-no-key-required | 满足 dsh Provider 字段要求，不是真正密钥 |

修改上述配置后，在同一个 PowerShell 会话重新执行 setup-local-model.ps1，再启动 DataControl。运行入口脚本会在本机服务可用时尝试自动同步本地 Profile；若同步失败不会影响官方 Provider。

## 实现与安全

本地 Profile 配置保存在 .local/dsh-home-v0.2.1-rc.3/profiles/dataagent-headless-local 与 -multi；由 agent/src/dataagent_gateway/local_provider.py 基于原 Headless Profile 派生，保留 MCP 和 Guard，使用 dsh llm-pi-ai 的 openai-completions 协议，兼容参数 supportsDeveloperRole=false 与 maxTokensField=max_tokens。
模型 ID 变化后需重新生成 Profile；本地会话使用 local-deepseek:<hash>:<sessionId> 前缀，禁止跨 Provider 续接。Gateway 限制同一时刻最多一项本地 CPU 模型任务。
模型离线、Profile 旧版本或 dsh 适配不兼容时，查看 /health 的 reason、.local/local-model-profile.stderr.log 和管理员运行 Trace。
无鉴权的 9931 必须只监听本机，不要对局域网或公网开放。不要执行生产 SQL/DDL，也不要将本地模式改写成不经 MCP/Guard 的裸模型请求。

## 本地工具调用单独诊断

在 llama.cpp 已启动且模型加载完成时，可运行：

    .\.venv\Scripts\python.exe -m dataagent_gateway.local_provider tool-probe

脚本向本机 /v1/chat/completions 发送合成的工具调用示例（无真实业务数据），检测返回中是否包含结构化 tool_calls。若 toolCallingObserved=false，说明接口能回答不代表 Agent 具备可靠的工具调用能力。测试可能在 CPU 上耗时较久，单次成功也不保证复杂任务稳定。按 llama.cpp 官方 Function Calling 指南，确认启动了 --jinja，并为 DeepSeek R1 Distill Qwen 7B 使用正确的工具调用模板（可能需要 --chat-template-file）。
