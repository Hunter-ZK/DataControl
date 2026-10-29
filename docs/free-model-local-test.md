# dsh-our-free-model｜默认提供的开发测试模型

Upstream: https://github.com/Ebony-Vinyl/dsh-our-free-model

DataControl installs the pinned plugin in an **isolated profile automatically**
when setting up or starting the local Agent. There is no extra environment
variable or manual install command. The model appears beside official DeepSeek
in the Intelligent Q&A model selector, but **official DeepSeek remains the
default for new conversations**.

Selecting the public model requires a one-time confirmation for that session.
The app then sends selected free-test questions with a consent flag; it does
not ask again for each turn of the same conversation. The public-mode warning
remains visible throughout the session. Different model modes never share
provider session handles.

**Privacy boundary:** upstream may relay prompts and tool output to public
providers; do not use real business metadata, non-public SQL, customer data,
secrets, or personal information. The model selector is not a data-loss
prevention control. Free-test mode must only be used with a synthetic/local
dataset; actual production tenant authorization is not implemented.

The upstream documentation advertises dsh 0.1.5–0.1.7-rc.2 while DataControl
pins dsh 0.2.1-rc.3; compatibility **has not been proved**. If the pinned
plugin cannot be installed, the start process reports an explicit warning
and the free-test status remains not-ready. Official DeepSeek and the
metadata catalog continue to run.

The bundled installer clones the reviewed v2.7.2 release and checks its pinned
commit before using the local source. It does **not** install the unrelated
npm registry package. Normal boot can reuse the ready marker without
reinstalling. For troubleshooting only:

- macOS/Linux: `bash scripts/setup-free-model-test.sh`
- Windows PowerShell: `.\scripts\setup-free-model-test.ps1`

No production SQL or DDL is executed by either model.
