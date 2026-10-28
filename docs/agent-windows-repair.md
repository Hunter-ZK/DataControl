# Windows Agent 未就绪：Profile 过期与修复说明

## 本次报错的原因

旧 `setup_dataagent.ps1` 通过 `dsh.cmd` 直接执行 `--dump-config`，在 PowerShell 5.1 的中文路径下可能产生乱码。报错 `patch: entry "tool-ralph" not found` 则表示正在应用的旧 Profile 包含新版 Harness 已移除的插件 ID。当前源码 `agent/dsh/profile/headless.patch.yml` 不再包含 `tool-ralph`；如果本地仍出现报错，首先检查 Git 分支和未同步的本地文件。

## 操作步骤（不删除 .local 或用户会话）

在 DataControl 仓库根目录打开 PowerShell：

```powershell
git status --short
git branch --show-current
git fetch origin
git switch feature/r0-r1-harness-autonomy-20261027
git pull --ff-only
.\start.bat repair
```

如果切换分支或拉取被本地改动阻止，请先妥善保存这些改动，**不要**使用 `git reset --hard` 或删除整个 `.local`。

`.\start.bat repair` 会先修复，再**直接启动**服务；无需在同一个服务运行期间再次执行 `.\start.bat`。启动完成后打开 `http://127.0.0.1:5173`。

启动器现会对比仓库原始 Profile 与本地生成的 Profile；不匹配时自动更新配置。遇到不可解析的旧插件条目时，旧 Profile 会备份到 `.local/dsh-home-v0.2.1-rc.3/profile-backups/`，再生成新 Profile。正常修复不重装 npm 依赖。

## “进程启动”与“Agent 可用”的区别

`Agent3 MCP` 在 `127.0.0.1:8900`，`DataAgent Gateway` 在 `127.0.0.1:8910`。Gateway 进程启动并不意味着模型可以回答：还要求安装并同步 Harness Profile、设置 `DEEPSEEK_API_KEY`、MCP 连通。

```powershell
Invoke-RestMethod http://127.0.0.1:8910/health | Format-List
Invoke-RestMethod http://127.0.0.1:8000/api/v1/agent/status | Format-List
Get-Content .\.local\agent-gateway.err.log -Tail 50
Get-Content .\.local\agent-mcp.err.log -Tail 50
Get-Content .\.local\dsh-profile-command.stderr.log -Tail 50
```

- 如果 8910 请求连接失败：Gateway 进程没有启动或已退出，检查启动终端报错和日志。
- 如果返回 `ready: false`、`apiKeyPresent: false`：配置 API Key 后**重启**进程。
- 如果 `profileReady: false`：执行 `.\start.bat repair`。
- 如果 `mcpReachable: false`：检查 8900 端口、Agent MCP 日志和 Portal 8000 健康状态。

**不要把密钥、原始业务问题或未脱敏日志直接上传到公开仓库。**

本次修复按要求不手动运行测试；GitHub Actions 如因提交自动触发，属于仓库原有 CI 行为。
