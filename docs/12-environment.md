# 12 · Environment

## Development baseline
- Python 3.13+ for current development; target compatibility baseline remains Python 3.14.
- Node is required only when Vue/dsh phases require it.
- MySQL 8 is the intended deployment database; SQLite demo mode remains available for self-contained local validation.
- Docker is not required.

## Supported developer operating systems

### Windows 10/11
Use PowerShell entry points:

```powershell
.\scripts\setup-dev.ps1
.\scripts\verify.ps1
.\scripts\start-dev.ps1
```

### macOS
Use Bash/Zsh entry points:

```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
bash scripts/start-dev.sh
```

Optionally run `chmod +x scripts/*.sh` once and invoke the scripts directly.

## Portability rules
1. Runtime Python code uses `pathlib` or platform-neutral APIs for filesystem paths.
2. Runtime application code must not depend on PowerShell, cmd.exe, Bash-only commands, drive-letter paths, or Unix-only paths.
3. Windows `.ps1` and macOS/Linux `.sh` scripts are equivalent thin wrappers; business logic remains in Python.
4. Text files use UTF-8 so Chinese content behaves consistently across systems.
5. CI runs generation/tests/search verification on Windows, macOS and Ubuntu.
6. Native dependencies introduced later must be checked on Apple Silicon and Windows before adoption.
