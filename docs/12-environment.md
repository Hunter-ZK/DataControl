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

The virtual environment interpreter is `.venv\Scripts\python.exe`.

### macOS
Use Bash/Zsh entry points:

```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
bash scripts/start-dev.sh
```

The virtual environment interpreter is `.venv/bin/python`.

Optionally run `chmod +x scripts/*.sh` once and invoke the scripts directly.

## Portability rules
1. Runtime Python code must use `pathlib` or other platform-neutral APIs for filesystem paths.
2. Runtime application code must not depend on PowerShell, cmd.exe, Bash-only commands, drive-letter paths, or Unix-only paths.
3. Windows `.ps1` and macOS/Linux `.sh` scripts are equivalent developer entry points; business logic stays in Python so the scripts remain thin wrappers.
4. Text files are UTF-8. Do not rely on Windows legacy code pages for Chinese content.
5. Local host and application URLs remain `127.0.0.1` and are OS-independent.
6. Release CI must run backend generation/tests/search verification on Windows and macOS; Ubuntu is retained as an additional portability guard.

## Apple Silicon
No x86-only runtime dependency is currently required by the P0/P1 foundation. Dependencies added later, especially search/native or dsh/Node packages, must be checked on both Apple Silicon and Windows before adoption.
