"""One entry point for deterministic CI checks and local real-model quality review.

The stub mode validates the tool contracts. The real mode invokes the live
question suite and records its empirical pass rate; neither executes production SQL.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".local"
BASELINE = REPORT_DIR / "agent-quality-baseline.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stub", "real"), default="stub")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--set-baseline", action="store_true")
    args = parser.parse_args()
    REPORT_DIR.mkdir(exist_ok=True)
    if args.mode == "stub":
        command = [sys.executable, "-m", "pytest", "-q",
                   "agent/tests/test_r2_r4_contracts.py",
                   "agent/tests/test_gateway_stream.py"]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        report = {
            "mode": "stub-contracts", "timestamp": datetime.now(UTC).isoformat(),
            "passed": completed.returncode == 0,
            "note": "Deterministic contract tests, not a live model accuracy result.",
        }
        (REPORT_DIR / "agent-quality-contracts.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(completed.returncode)
    command = [sys.executable, "scripts/p3_agent_question_suite.py",
               "--limit", str(max(1, args.limit))]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    source = REPORT_DIR / "p3-question-suite-report.json"
    if not source.exists():
        raise SystemExit("Real-model evaluation report not created; check the Agent service")
    report = json.loads(source.read_text(encoding="utf-8"))
    rate = float(report.get("passRate", 0))
    if args.set_baseline or not BASELINE.exists():
        BASELINE.write_text(json.dumps({
            "createdAt": datetime.now(UTC).isoformat(),
            "count": report["count"], "passRate": rate,
            "note": "Measured local real-model result, not a predefined pass guarantee",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    print(f"Real-model pass rate: {rate:.2%}; baseline {baseline['passRate']:.2%}")
    if rate + 0.02 < float(baseline["passRate"]):
        raise SystemExit("Real-model quality regression exceeds 2 percentage points")
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
