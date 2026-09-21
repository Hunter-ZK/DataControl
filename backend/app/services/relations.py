from __future__ import annotations

from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Dataset, TableLineage


class RelationService:
    def __init__(self, db: Session):
        self.db = db

    def _all_edges(self) -> list[TableLineage]:
        return self.db.execute(select(TableLineage)).scalars().all()

    def _dataset_map(self, ids: set[str]) -> dict[str, Dataset]:
        if not ids:
            return {}
        rows = self.db.execute(select(Dataset).where(Dataset.asset_id.in_(ids))).scalars().all()
        return {x.asset_id: x for x in rows}

    @staticmethod
    def _node_payload(ds: Dataset | None, asset_id: str, center: str | None = None) -> dict:
        if ds is None:
            return {
                "assetId": asset_id,
                "name": asset_id,
                "tableName": None,
                "layerCode": None,
                "catalogCode": None,
                "status": None,
                "isCenter": asset_id == center,
            }
        return {
            "assetId": ds.asset_id,
            "name": ds.biz_name,
            "tableName": ds.table_name,
            "layerCode": ds.layer_code,
            "catalogCode": ds.catalog_code,
            "status": ds.status,
            "isCenter": ds.asset_id == center,
        }

    @staticmethod
    def _edge_payload(edge: TableLineage) -> dict:
        return {
            "id": edge.id,
            "source": edge.src_asset_id,
            "target": edge.dst_asset_id,
            "taskName": edge.task_name,
            "evidence": edge.evidence,
        }

    def graph(
        self,
        asset_id: str,
        *,
        depth: int = 2,
        direction: str = "both",
        max_nodes: int = 120,
    ) -> dict:
        if self.db.get(Dataset, asset_id) is None:
            raise KeyError(asset_id)

        depth = max(1, min(depth, 5))
        direction = direction if direction in {"upstream", "downstream", "both"} else "both"
        all_edges = self._all_edges()
        upstream: dict[str, list[TableLineage]] = defaultdict(list)
        downstream: dict[str, list[TableLineage]] = defaultdict(list)
        for edge in all_edges:
            downstream[edge.src_asset_id].append(edge)
            upstream[edge.dst_asset_id].append(edge)

        seen_nodes = {asset_id}
        seen_edges: dict[int, TableLineage] = {}
        queue = deque([(asset_id, 0)])
        truncated = False

        while queue:
            current, level = queue.popleft()
            if level >= depth:
                continue
            candidates: list[TableLineage] = []
            if direction in {"downstream", "both"}:
                candidates.extend(downstream.get(current, []))
            if direction in {"upstream", "both"}:
                candidates.extend(upstream.get(current, []))
            for edge in candidates:
                seen_edges[edge.id] = edge
                other = edge.dst_asset_id if edge.src_asset_id == current else edge.src_asset_id
                if other in seen_nodes:
                    continue
                if len(seen_nodes) >= max_nodes:
                    truncated = True
                    continue
                seen_nodes.add(other)
                queue.append((other, level + 1))

        datasets = self._dataset_map(seen_nodes)
        return {
            "centerAssetId": asset_id,
            "depth": depth,
            "direction": direction,
            "truncated": truncated,
            "nodes": [self._node_payload(datasets.get(x), x, asset_id) for x in seen_nodes],
            "edges": [self._edge_payload(x) for x in seen_edges.values()],
        }

    def path(self, source: str, target: str, *, max_depth: int = 8) -> dict:
        if self.db.get(Dataset, source) is None or self.db.get(Dataset, target) is None:
            raise KeyError("source_or_target")
        max_depth = max(1, min(max_depth, 12))
        edges = self._all_edges()
        adjacency: dict[str, list[TableLineage]] = defaultdict(list)
        for edge in edges:
            adjacency[edge.src_asset_id].append(edge)

        queue = deque([(source, [source], [])])
        visited_depth = {source: 0}
        found_nodes: list[str] | None = None
        found_edges: list[TableLineage] | None = None

        while queue:
            current, node_path, edge_path = queue.popleft()
            depth = len(edge_path)
            if current == target:
                found_nodes, found_edges = node_path, edge_path
                break
            if depth >= max_depth:
                continue
            for edge in adjacency.get(current, []):
                nxt = edge.dst_asset_id
                next_depth = depth + 1
                if visited_depth.get(nxt, 10**9) <= next_depth:
                    continue
                visited_depth[nxt] = next_depth
                queue.append((nxt, node_path + [nxt], edge_path + [edge]))

        if found_nodes is None or found_edges is None:
            return {"found": False, "source": source, "target": target, "nodes": [], "edges": []}

        datasets = self._dataset_map(set(found_nodes))
        return {
            "found": True,
            "source": source,
            "target": target,
            "hopCount": len(found_edges),
            "nodes": [self._node_payload(datasets.get(x), x) for x in found_nodes],
            "edges": [self._edge_payload(x) for x in found_edges],
        }

    def impact(self, asset_id: str, *, depth: int = 3, max_nodes: int = 200) -> dict:
        graph = self.graph(asset_id, depth=depth, direction="downstream", max_nodes=max_nodes)
        impacted = [x for x in graph["nodes"] if x["assetId"] != asset_id]
        layer_counts: dict[str, int] = defaultdict(int)
        for node in impacted:
            layer_counts[node.get("layerCode") or "UNKNOWN"] += 1
        return {
            **graph,
            "impactCount": len(impacted),
            "impactByLayer": dict(layer_counts),
        }
