from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
steps = [
    [sys.executable, "samples/generate_demo_data.py"],
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "scripts/search_benchmark.py"],
]
for cmd in steps:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)
print("\nP0 CORE VERIFICATION PASSED")
