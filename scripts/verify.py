from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
steps = [
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    [sys.executable, "samples/generate_demo_data.py"],
    [sys.executable, "samples/enrich_p1_data.py"],
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "scripts/search_benchmark.py"],
]
for cmd in steps:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)
print("\nP1 VERIFICATION PASSED")
