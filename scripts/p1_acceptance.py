from __future__ import annotations

import argparse
import sys

import httpx


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def get(client: httpx.Client, path: str, **params):
    response = client.get(path, params=params)
    response.raise_for_status()
    payload = response.json()
    expect(payload.get("code") == "OK", f"{path}: unexpected response envelope")
    return payload["data"]


def main() -> int:
    parser = argparse.ArgumentParser(description="DataControl Next-P1 live acceptance")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=30.0, trust_env=False) as client:
        short = get(client, "/search", q="贷款", limit=20)
        expect(short["total"] > 0, "2-character Chinese search returned zero results")

        multi = get(client, "/search", q="贷款 余额", limit=20)
        expect(multi["total"] > 0, "multi-token search returned zero results")
        expect(len(multi["facets"]["assetTypes"]) >= 2, "search facets are unexpectedly empty")

        metric_only = get(client, "/search", q="贷款 余额", asset_type="METRIC", limit=20)
        expect(metric_only["total"] > 0, "METRIC filter returned zero results")
        expect(
            metric_only["facets"]["assetTypes"] == multi["facets"]["assetTypes"],
            "asset-type facet did not exclude its own filter",
        )

        first_catalog_page = get(client, "/tables/page", offset=0, limit=20, status="ONLINE")
        later_catalog_page = get(client, "/tables/page", offset=240, limit=20, status="ONLINE")
        expect(first_catalog_page["total"] >= 260, "catalog total is below deterministic corpus size")
        expect(later_catalog_page["items"], "catalog cannot reach assets beyond old 200-row cutoff")

        graph = get(client, "/relations/graph/DS000004", depth=3, direction="both")
        node_ids = {node["assetId"] for node in graph["nodes"]}
        expect("DS000008" not in node_ids and "DS000009" not in node_ids, "both traversal crossed into sibling branch")
        expect(any(node.get("level", 0) < 0 for node in graph["nodes"]), "graph has no upstream levels")
        expect(any(node.get("level", 0) > 0 for node in graph["nodes"]), "graph has no downstream levels")
        expect(all(edge.get("evidence") in {"CONFIRMED", "INFERRED"} for edge in graph["edges"]), "relation evidence is missing")

        columns = get(client, "/columns", dataset_id="DS000004", limit=500)
        loan_balance = next(item for item in columns if item["columnName"] == "loan_balance")
        field_graph = get(
            client,
            f"/relations/columns/{loan_balance['assetId']}",
            depth=2,
            direction="both",
        )
        expect(field_graph["edges"], "field-level lineage returned no edges")
        expect(
            any(edge.get("transformation") for edge in field_graph["edges"]),
            "field lineage has no transformation evidence",
        )

        path = get(client, "/relations/path", source="DS000001", target="DS000006", max_depth=12)
        expect(path["found"] is True, "golden directed path DS000001 -> DS000006 was not found")
        expect(all(edge.get("taskName") for edge in path["edges"]), "path is missing task names")

    print("NEXT-P1 LIVE API ACCEPTANCE PASSED")
    print("Manual UI acceptance remains required for Search V2 / Relation Graph V2 visual fidelity.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, httpx.HTTPError, StopIteration) as exc:
        print(f"NEXT-P1 LIVE API ACCEPTANCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
