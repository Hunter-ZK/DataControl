# Optional dsh-our-free-model development test mode

This is **not** the official DataControl model, and never participates in
production acceptance. The third-party plugin may relay questions and tool
results to OpenCode/Kilo public gateways. **Never send real internal metadata,
SQL, customer details or credentials.** The browser asks permission on every
turn and the Portal/Gateway require an explicit environment opt-in.

Upstream: https://github.com/Ebony-Vinyl/dsh-our-free-model

The upstream README advertises compatibility with dsh 0.1.5–0.1.7-rc.2,
whereas DataControl pins dsh 0.2.1-rc.3. Compatibility with DataControl is
**unverified**; keep the feature off if setup/config validation fails.

## Windows

Install official DataControl first, then (opt-in):

```powershell
.\scripts\setup-free-model-test.ps1
$env:DATACONTROL_ENABLE_FREE_TEST='1'
.\start.bat
```

## macOS / Linux

Install DataControl first, then:

```bash
bash scripts/setup-free-model-test.sh
DATACONTROL_ENABLE_FREE_TEST=1 bash start.sh
```

The installer reads only a pinned upstream git commit/release, does not use
an unrelated npm package of the same name, and creates a **separate**
`dataagent-headless-free` profile. The official `dataagent-headless`
profile remains unchanged. No auto-install during ordinary startup.

In Intelligent Q&A, create a new conversation, choose **免费模型测试**, and
acknowledge the public-provider warning on **each** turn. If the profile is
unavailable, status will show why. Only use demo/synthetic prompts.

The security opt-in is a developer operational control, not automated
classification of prompt content; it does **not** guarantee that arbitrary
metadata available to MCP is synthetic. For sensitive environments leave the
mode disabled. Switching back to official DeepSeek creates a separate session.
