# DataControl｜macOS 安装与人工验收（不运行自动化测试）

适用分支：`feature/r0-r1-harness-autonomy-20261027`  
系统：Apple Silicon 或 Intel macOS；Python 3.13/3.14、Node.js 24+、Git  
验证对象：数据资产服务 Portal + 官方 DeepSeek DataAgent（标准问数/多步任务）

## 1. 准备开发环境

打开 macOS 的**终端 Terminal**。如未安装 Homebrew，先通过 [Homebrew 官网](https://brew.sh/) 安装；然后运行：

```bash
brew install python@3.14 node@24 git
export PATH="$(brew --prefix node@24)/bin:$PATH"
python3.14 --version
node --version
npm --version
git --version
```

上述 `PATH` 仅影响**当前终端**。如果之后新开终端提示 Node 版本太低，可以重新执行 `export PATH=...`；经确认后再将其写入 `~/.zshrc`。

## 2. 获取代码

首次克隆（私有仓库需要有权限的 GitHub 账号登录）：

```bash
git clone --branch feature/r0-r1-harness-autonomy-20261027 https://github.com/Hunter-ZK/DataControl.git
cd DataControl
```

已经存在本地仓库：

```bash
cd /你自己的路径/DataControl
git status --short
git fetch origin
git switch feature/r0-r1-harness-autonomy-20261027
git pull --ff-only
```

**注意：** 如果 `git status --short` 显示本地未提交变更，先检查并备份，勿执行 `git reset --hard`、`git clean -fd` 或直接覆盖本地修改。首次切换分支时也可能需要使用 `git switch --track origin/feature/r0-r1-harness-autonomy-20261027`。

## 3. 安装与配置

首次使用，单独执行：

```bash
bash start.sh setup
```

脚本安装 Portal、前端、Agent、固定版本 Harness 和两个独立的 dsh Headless Profile，并生成本地模拟元数据与语义模型。包安装阶段需要联网；本地数据库放在 `.local/`，不会提交到 GitHub。

需要调用官方 DeepSeek 时，在项目根目录创建 `.env`：

```bash
nano .env
```

文件内填写一行（用你自己的真实密钥替换占位符）：

```dotenv
DEEPSEEK_API_KEY=请替换为自己的密钥
```

保存后执行：

```bash
chmod 600 .env
```

`.env` 已被 Git 忽略。macOS 启动脚本会**安全读取此项环境变量**，无需 `source .env`，也不应将密钥发给任何人。已在当前终端导出的 `DEEPSEEK_API_KEY` 优先于文件内容。更改密钥后需要重新启动服务。

## 4. 日常启动、停止与修复

在项目根目录启动：

```bash
bash start.sh
```

保持此终端处于运行状态，在浏览器访问：

- 页面：http://127.0.0.1:5173
- Portal：http://127.0.0.1:8000/health
- Agent Gateway：http://127.0.0.1:8910/health

测试账号可使用登录页面展示的 `demo` / `admin`。这是**本地开发演示账号**，不能当作生产认证验收。

正常停止：在启动终端按 **Control+C**。如果服务异常残留，另开终端执行 `bash start.sh stop`；脚本只会停止能够确认属于 DataControl 的服务，不会强行杀掉未知占用端口的进程。

安装不完整或模型 Profile 失效：

```bash
bash start.sh repair
```

`repair` 会修复 Agent 依赖并随后启动，保留本地 SQLite 数据和原有 dsh 会话（损坏/不完整 Profile 将备份至 `.local/dsh-home-v0.2.1-rc.3/profile-backups/`）。

升级分支后，日常 `bash start.sh` 会自动对照三个 Profile 的配置文件，仅在配置变化时重建 Profile；还会执行 Alembic 数据库结构迁移，**不重置演示数据**。

## 5. 手工验收：建议按场景完成

| 场景 | 操作 | 预期 |
|---|---|---|
| 首页统一入口 | 输入“贷款余额”，点击“检索资产” | 在首页下方出现真实模拟数据集/字段/指标结果，不会误进聊天 |
| DataAgent 入口 | 同样输入，点击“问 DataAgent” | 打开智能问数页面，输入的问题被带入；未登录应转到登录 |
| 资产跳转 | 点击某个搜索结果或 Agent 引用资产 | 进入正确的数据集、字段或指标详情 |
| 标准问数 | 选择“标准问数”，询问“本期各地区贷款余额，生成并校验 SQL” | 使用官方模型和受治理 MCP 工具；显示可解释 SQL、来源和静态验证结果，**不执行 SQL** |
| 连续修改 | 继续输入“改成同比”，再输入“只看广东省” | 不擅自更换指标；沿用有依据的业务口径，无法确定时澄清 |
| 多步任务 | 新建会话后选“多步任务”，让它分析一个已有数据集的口径/字段并提出校验步骤 | 使用独立 multi Profile；工具步骤可见；无编造运行结果 |
| 执行过程 | 打开右侧检查器，切换“数据依据 / SQL 校验 / 执行步骤” | 只展示真实证据和工具活动，不泄露模型隐藏推理 |
| 任务停止 | 发送较复杂请求，在执行中点击停止 | 以服务端取消确认为准，不把浏览器中断误报为任务完成 |
| 历史与恢复 | 完成会话后刷新页面，重新打开历史 | 原回答和档位保留；结束状态如实展示 |
| 账号隔离 | 用 demo 创建会话并退出，换 admin 登录 | 不得显示 demo 的会话或旧浏览器缓存；切回 demo 能找到其历史 |
| 旧版历史迁移 | 首次发现旧本地历史 | 明确询问归属，经确认才导入；不擅自附加旧 Session ID |
| 数仓开发辅助 | 请求生成某表 DDL/ETL 和非空/唯一性检验 SQL | 只生成经过字段核对的草案，缺少字段/业务规则必须说明，**不部署、不执行** |
| Mac 窄屏 | 缩小浏览器窗口 | 导航仍可打开，能访问历史会话和搜索入口 |

注意：如果没有配置官方 DeepSeek API Key，可以先检查首页检索、资产详情、认证与本地浏览器页面。也可以在“智能问数”中主动选择“免费模型测试”，应用会在启动时自动尝试安装该独立 Profile，无需手动设置环境变量。首次切换时会出现一次隐私提醒；第三方网关可能记录问题或工具信息，只能使用公开模拟数据。插件与固定版 dsh 的兼容性未经实机确认，若显示未就绪可检查日志。**免费模式不能作为官方 DeepSeek 质量验收。**

## 6. Mac 的运行状态与故障定位

可以在另一个终端查看：

```bash
curl -s 'http://127.0.0.1:8910/health?taskTier=standard'
curl -s 'http://127.0.0.1:8910/health?taskTier=multi'
tail -n 60 .local/agent-gateway.err.log
tail -n 60 .local/agent-mcp.err.log
tail -n 60 .local/backend.err.log
```

关注健康信息里的 `ready` 和 `reason`。即使健康 HTTP 请求返回 200，也要确认实际的 `ready=true`。不要将带有 API Key 的环境信息或配置截图公开分享。

- **`python3.14` 不存在：** 检查 Homebrew 的 Python 安装，或通过 `PYTHON_BIN` 指定受支持的 Python。
- **Node 版本不符合要求：** 重新执行 `export PATH="$(brew --prefix node@24)/bin:$PATH"`。
- **端口已被占用：** 使用 `lsof -nP -iTCP:8000 -sTCP:LISTEN` 等确认占用进程；必要时执行 `bash start.sh stop`，不要盲目 kill。
- **Gateway `ready=false`：** 先检查密钥、Profile 配置、MCP 和错误日志；需要时 `bash start.sh repair`。
- **安装提示 `cryptography` 版本或 wheel：** 使用兼容的 Python 与官方构建包；项目将依赖固定为可安装预编译 wheel 的版本，不建议手动修改依赖锁定。
- **升级后历史/字段异常：** 确认是否执行到 Alembic migration 步骤。必要时先备份 `.local/datacontrol.db`，再重新启动。

## 7. 验收定位

此轮主要进行**本机产品与交互验收**，不要求先运行自动化测试，也不代表真实模型质量已达到验收指标。公开免费模型通道已停用；不要输入真实内部业务数据到本地模拟环境或第三方服务。

GitHub PR #6 保持 Draft，代码仍位于开发分支，未经用户确认不合并 main。
