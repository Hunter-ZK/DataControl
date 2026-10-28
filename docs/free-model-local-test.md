# 可选免费模型开发测试（Windows）

第三方项目：[dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model)，固定版本 `v2.7.2`、源码提交 `e1b347aec9cc956eda70a766219f028a811078e2`。

此模式**只能用于本地模拟数据**。免费模型请求发送至 OpenCode/Kilo 等公共服务；第三方关于“免费不限量”的宣传不代表实际可用性和服务保证，可能有地区、429 限流、服务条款与数据隐私风险。该插件部分通道会仿照上游客户端请求格式；请遵守服务商条款，不要用它规避访问控制。**不要发送真实业务元数据、内部 SQL、个人数据、密钥、客户资料**。安装前应审查第三方源码。

首次，在关闭 DataControl 后，仓库根目录 PowerShell：

```powershell
git pull --ff-only
.\scripts\setup-free-model-test.ps1
```

脚本只从 GitHub 拉取并核验固定版本源码，不安装同名 npm 包。插件与本地配置都保存在 `.local`；只修改独立的 `dataagent-headless-free` Profile，保留原先的 Guard、只读 Agent3 MCP、生产 SQL 禁止执行。

启动 DataControl（无需另一个启动窗口，也无需重新启动服务切换模型）：

```powershell
.\start.bat
```

打开 **智能问数 → 对话窗口顶部「对话模型」→「免费模型测试」**，阅读第三方数据提示并确认。随时点击「DeepSeek 官方」即可切回；切换时自动新建会话，旧会话会保留在左侧历史。该模式选用 `our-free-model / kilo-auto/free`；不需要 DeepSeek API Key。若公共上游限制请求，测试不成功并非 DataControl 模型配置自动转为官方 DeepSeek。检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8910/health | Format-List
Get-Content .\.local\agent-gateway.err.log -Tail 40
```

`modelMode=free-test`、`provider=our-free-model` 表示已选测试配置；`ready=true` 只确认本地组件存在，不能证明第三方模型可用。

模型由页面逐次传给 Gateway，**无需通过 PowerShell 反复切换或重启**。原 `start-free-test.ps1` 已变为普通启动兼容入口，不再决定模型。首次安装第三方插件仍需要本地运行一次 `setup-free-model-test.ps1`；没有安装时 UI 会显示对应就绪错误。本选项不计入官方真实模型验收。

切换模型模式后请在智能问数页面新建会话。服务端会在免费模式的 sessionId 上加 `free-test:` 前缀，并拒绝跨模式恢复历史会话，避免把官方模型的上下文意外传给第三方。
