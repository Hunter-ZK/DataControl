# 12 · Environment

## Current Portal baseline

- Python 3.13+
- Node.js 24+
- npm
- Windows 10/11 PowerShell or macOS Bash/Zsh

Portal backend and Vue frontend are verified in CI on Windows, macOS and Ubuntu.

## Embedded DataAgent baseline

The P3 migration source `Hunter-ZK/DataAgent-dsh` declares Python `>=3.14,<3.15`, plus its own Python and Node dependencies for Agent3 Core, MCP, dsh and the guard plugin.

This version difference is explicit technical work, not something setup scripts may hide. Until P3-B resolves it, the Agent runtime readiness flag remains closed.

The preferred migration outcome is:

```text
DataControl checkout
├── .venv/          Portal Python environment
├── web/            Vue dependencies
└── agent/          embedded DataAgent source/runtime assets
```

If isolated Agent Python 3.14 environment is retained, scripts may create a separate `.venv-agent`; the user must still start everything from the DataControl repository and must not clone `DataAgent-dsh` separately.

## Current quick start

### Windows

```powershell
.\scripts\setup-dev.ps1
.\scripts\verify.ps1
.\scripts\start-dev.ps1
```

### macOS

```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
bash scripts/start-dev.sh
```

Current scripts start Portal + Vue. P3-B will extend the same scripts to Agent components only after the embedded migration gate passes.

## Portability rules

- runtime paths use repository-relative or `pathlib`-style resolution;
- no product code may assume Windows drive letters or POSIX-only paths;
- PowerShell and Bash wrappers must offer equivalent setup/start/verify behavior;
- UTF-8 is the repository text baseline;
- CI remains cross-platform;
- a dependency requiring platform-specific native binaries must be validated on Windows and macOS before acceptance.
