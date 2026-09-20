from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.search.engine import SearchEngine

queries = ["贷款余额", "dwd_loan", "region_code", "企业风险", "存款余额", "监管报送"]
engine = SearchEngine()
timings = []
for query in queries:
    for _ in range(30):
        started = time.perf_counter()
        engine.search(query, 20)
        timings.append((time.perf_counter() - started) * 1000)

ordered = sorted(timings)
print({
    "queries": len(timings),
    "p50_ms": round(statistics.median(timings), 3),
    "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 3),
    "max_ms": round(max(timings), 3),
})
