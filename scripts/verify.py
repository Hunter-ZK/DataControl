from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

if not ((3, 13) <= sys.version_info[:2] < (3, 15)):
    raise SystemExit(f"DataControl verification requires Python 3.13 or 3.14; found {sys.version.split()[0]}")

python_steps = [
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    [sys.executable, "samples/generate_demo_data.py"],
    [sys.executable, "samples/enrich_p1_data.py"],
    [sys.executable, "samples/enrich_p3_reference.py"],
    [sys.executable, "samples/rebuild_search_index.py"],
    [sys.executable, "samples/generate_p3_question_bank.py"],
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "scripts/search_benchmark.py"],
]

for command in python_steps:
    print(">", " ".join(map(str, command)))
    subprocess.run(command, cwd=ROOT, check=True)

try:
    __import__("agent3")
    __import__("dataagent_gateway")
except ImportError as exc:
    raise SystemExit(
        "Embedded Agent package is not installed in .venv. Run scripts/setup-agent.sh or setup-agent.ps1 first."
    ) from exc

agent_steps = [
    [sys.executable, "agent/scripts/check_architecture.py"],
    [sys.executable, "-m", "pytest", "-q", "agent/tests"],
]
for command in agent_steps:
    print(">", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)

npm = shutil.which("npm")
if npm is None:
    raise SystemExit("npm is required for verification")

frontend_steps = [
    [npm, "run", "type-check"],
    [npm, "run", "test"],
    [npm, "run", "build"],
]
for command in frontend_steps:
    print(">", " ".join(command))
    subprocess.run(command, cwd=WEB, check=True)

guard = ROOT / "agent" / "guard-plugin"
subprocess.run([npm, "run", "build"], cwd=guard, check=True)
subprocess.run([npm, "test"], cwd=guard, check=True)

print("\nP3 MONOREPO VERIFICATION PASSED (shared Python runtime + Portal + Agent + frontend)")
