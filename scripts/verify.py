from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

python_steps = [
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    [sys.executable, "samples/generate_demo_data.py"],
    [sys.executable, "samples/enrich_p1_data.py"],
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "scripts/search_benchmark.py"],
]
for cmd in python_steps:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

npm = shutil.which("npm")
if npm is None:
    raise SystemExit("npm is required for P2 verification")
for args in ([npm, "run", "type-check"], [npm, "run", "test"], [npm, "run", "build"]):
    print(">", " ".join(args))
    subprocess.run(args, cwd=WEB, check=True)

print("\nP2 VERIFICATION PASSED")
