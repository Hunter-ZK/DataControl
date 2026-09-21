# 12 · Environment

## Development baseline

- Python `>=3.13,<3.15` for both Portal and embedded DataAgent;
- Node.js 24+;
- npm;
- Windows 10/11 PowerShell or macOS/Linux Bash/Zsh.

Portal and Agent run as separate processes and keep HTTP/MCP boundaries, but local development uses one repository-local `.venv`. A separate `.venv-agent` is no longer required.

## Embedded DataAgent baseline

The migrated DataAgent source originally came from a repository that pinned Python 3.14, but DataControl P3 has been adapted and tested against Python 3.13. The package metadata, setup scripts and CI therefore use the DataControl compatibility range `>=3.13,<3.15` rather than inheriting the source repository's historical interpreter pin.

MCP currently pulls `pyjwt[crypto]`, which makes `cryptography` a transitive runtime dependency. `cryptography` 49+ stopped publishing CPython macOS x86_64 wheels. DataControl therefore constrains the Agent runtime to `cryptography>=48.0.1,<49`, the newest compatible line with a universal2 wheel, and setup explicitly requires a binary wheel. This keeps Intel Macs self-contained and avoids requiring local Rust, pkg-config or Homebrew OpenSSL merely to install the Agent.

```text
DataControl checkout
├── .venv/          shared Portal + Agent Python environment
├── web/            Vue dependencies
├── agent/          embedded DataAgent source/runtime assets
└── .local/         generated dsh profiles, logs and acceptance evidence
```

The process boundary remains:

```text
Portal :8000
  -> Agent Gateway :8910
  -> dsh
  -> Agent3 MCP :8900
  -> Agent3 Core
  -> Portal read-only facts
```

Sharing `.venv` does not relax architecture boundaries; it only removes an unnecessary interpreter/version split.

## Quick start

### Windows

```powershell
.\scripts\setup-dev.ps1
$env:DEEPSEEK_API_KEY="..."
.\scripts\start-dev.ps1
```

### macOS / Linux

```bash
bash scripts/setup-dev.sh
export DEEPSEEK_API_KEY="..."
bash scripts/start-dev.sh
```

If only Agent dependencies are missing, `setup-agent` reuses the existing `.venv` and installs the embedded Agent package plus dsh/Guard/profile assets.

## Portability rules

- runtime paths use repository-relative or `pathlib`-style resolution;
- no product code may assume Windows drive letters or POSIX-only paths;
- PowerShell and Bash wrappers must offer equivalent setup/start/verify behavior;
- UTF-8 is the repository text baseline;
- CI remains cross-platform;
- a dependency requiring platform-specific native binaries must be validated on Windows and macOS before acceptance.
