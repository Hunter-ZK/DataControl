from __future__ import annotations

from collections import defaultdict, deque
from operator import attrgetter
from typing import Callable, TypeVar

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.db.lineage_models import ColumnLineage
from backend.app.db.models import Column, Dataset, TableLineage

EdgeT = TypeVar("EdgeT")

_TABLE_SOURCE = attrgetter("src_asset_id")
_TABLE_TARGET = attrgetter("dst_asset_id")
_COLUMN_SOURCE = attrgetter("src_column_id")
_COLUMN_TARGET = attrgetter("dst_column_id")


class RelationService:
    def __init__(self, db: Session):
        self.db = db

    def _dataset_map(self, ids: set[str]) -> dict[str, Dataset]:
        if not ids:
            return {}
        rows = self.db.execute(select(Dataset).where(Dataset.asset_id.in_(ids))).scalars().all()
        return {row.asset_id: row for row in rows}

    def _column_map(self, ids: set[str]) -> dict[str, Column]:
        if not ids:
            return {}
        rows = self.db.execute(select(Column).where(Column.asset_id.in_(ids))).scalars().all()
        return {row.asset_id: row for row in rows}

    @staticmethod
    def _walk(
        center: str,
        edges: list[EdgeT],
        *,
        depth: int,
        direction: str,
        source: Callable[[EdgeT], str],
        target: Callable[[EdgeT], str],
    ) -> tuple[set[str], dict[int, EdgeT], dict[str, int]]:
        adjacency: dict[str, list[EdgeT]] = defaultdict(list)
        if direction == "downstream":
            for edge in edges:
                adjacency[source(edge)].append(edge)
            next_node = target
        else:
            for edge in edges:
                adjacency[target(edge)].append(edge)
            next_node = source

        nodes = {center}
        found_edges: dict[int, EdgeT] = {}
        distances = {center: 0}
        queue = deque([(center, 0)])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for edge in adjacency.get(current, []):
                found_edges[int(getattr(edge, "id"))] = edge
                other = next_node(edge)
                next_depth = current_depth + 1
                if distances.get(other, 10**9) <= next_depth:
                    continue
                distances[other] = next_depth
                nodes.add(other)
                queue.append((other, next_depth))
        return nodes, found_edges, distances

    @staticmethod
    def _merge_directional(
        center: str,
        upstream: tuple[set[str], dict[int, EdgeT], dict[str, int]],
        downstream: tuple[set[str], dict[int, EdgeT], dict[str, int]],
        *,
        max_nodes: int,
        source: Callable[[EdgeT], str],
        target: Callable[[EdgeT], str],
    ) -> tuple[set[str], dict[int, EdgeT], dict[str, int], bool]:
        up_nodes, up_edges, up_distance = upstream
        down_nodes, down_edges, down_distance = downstream
        candidates = [(0, 0, center)]
        candidates.extend((distance, 0, node) for node, distance in up_distance.items() if node != center)
        candidates.extend((distance, 1, node) for node, distance in down_distance.items() if node != center)
        candidates.sort(key=lambda value: (value[0], value[1], value[2]))

        selected: set[str] = set()
        levels: dict[str, int] = {}
        for distance, side, node in candidates:
            candidate_level = -distance if side == 0 else distance
            if node in selected:
                if abs(candidate_level) < abs(levels.get(node, candidate_level)):
                    levels[node] = candidate_level
                continue
            if len(selected) >= max_nodes:
                break
            selected.add(node)
            levels[node] = candidate_level
        selected.add(center)
        levels[center] = 0

        combined_edges = {**up_edges, **down_edges}
        kept_edges = {
            edge_id: edge
            for edge_id, edge in combined_edges.items()
            if source(edge) in selected and target(edge) in selected
        }
        return selected, kept_edges, levels, len(up_nodes | down_nodes) > len(selected)

    @classmethod
    def _directional_graph(
        cls,
        center: str,
        edges: list[EdgeT],
        *,
        depth: int,
        direction: str,
        max_nodes: int,
        source: Callable[[EdgeT], str],
        target: Callable[[EdgeT], str],
    ) -> tuple[set[str], dict[int, EdgeT], dict[str, int], bool]:
        if direction == "both":
            upstream = cls._walk(
                center,
                edges,
                depth=depth,
                direction="upstream",
                source=source,
                target=target,
            )
            downstream = cls._walk(
                center,
                edges,
                depth=depth,
                direction="downstream",
                source=source,
                target=target,
            )
            return cls._merge_directional(
                center,
                upstream,
                downstream,
                max_nodes=max_nodes,
                source=source,
                target=target,
            )

        nodes, found_edges, distances = cls._walk(
            center,
            edges,
            depth=depth,
            direction=direction,
            source=source,
            target=target,
        )
        ordered = sorted(nodes, key=lambda node: (distances.get(node, 0), node))
        selected = set(ordered[:max_nodes])
        selected.add(center)
        kept_edges = {
            edge_id: edge
            for edge_id, edge in found_edges.items()
            if source(edge) in selected and target(edge) in selected
        }
        sign = -1 if direction == "upstream" else 1
        levels = {node: sign * distances.get(node, 0) for node in selected}
        return selected, kept_edges, levels, len(nodes) > len(selected)

    @staticmethod
    def _table_node(
        dataset: Dataset | None,
        asset_id: str,
        *,
        center: str | None = None,
        level: int = 0,
    ) -> dict:
        return {
            "assetId": dataset.asset_id if dataset else asset_id,
            "name": dataset.biz_name if dataset else asset_id,
            "tableName": dataset.table_name if dataset else None,
            "layerCode": dataset.layer_code if dataset else None,
            "catalogCode": dataset.catalog_code if dataset else None,
            "status": dataset.status if dataset else None,
            "isCenter": asset_id == center,
            "level": level,
        }

    @staticmethod
    def _table_edge(edge: TableLineage) -> dict:
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
        edges = self.db.execute(select(TableLineage)).scalars().all()
        nodes, found_edges, levels, truncated = self._directional_graph(
            asset_id,
            edges,
            depth=depth,
            direction=direction,
            max_nodes=max_nodes,
            source=_TABLE_SOURCE,
            target=_TABLE_TARGET,
        )
        datasets = self._dataset_map(nodes)
        return {
            "centerAssetId": asset_id,
            "depth": depth,
            "direction": direction,
            "truncated": truncated,
            "nodes": [
                self._table_node(
                    datasets.get(node),
                    node,
                    center=asset_id,
                    level=levels.get(node, 0),
                )
                for node in sorted(nodes, key=lambda value: (levels.get(value, 0), value))
            ],
            "edges": [self._table_edge(edge) for edge in found_edges.values()],
        }

    def path(self, source: str, target: str, *, max_depth: int = 8) -> dict:
        if self.db.get(Dataset, source) is None or self.db.get(Dataset, target) is None:
            raise KeyError("source_or_target")
        max_depth = max(1, min(max_depth, 12))
        adjacency: dict[str, list[TableLineage]] = defaultdict(list)
        for edge in self.db.execute(select(TableLineage)).scalars().all():
            adjacency[edge.src_asset_id].append(edge)

        queue = deque([(source, [source], [])])
        visited_depth = {source: 0}
        found_nodes: list[str] | None = None
        found_edges: list[TableLineage] | None = None
        while queue:
            current, node_path, edge_path = queue.popleft()
            current_depth = len(edge_path)
            if current == target:
                found_nodes, found_edges = node_path, edge_path
                break
            if current_depth >= max_depth:
                continue
            for edge in adjacency.get(current, []):
                nxt = edge.dst_asset_id
                next_depth = current_depth + 1
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
            "nodes": [self._table_node(datasets.get(node), node) for node in found_nodes],
            "edges": [self._table_edge(edge) for edge in found_edges],
        }

    def impact(self, asset_id: str, *, depth: int = 3, max_nodes: int = 200) -> dict:
        graph = self.graph(asset_id, depth=depth, direction="downstream", max_nodes=max_nodes)
        impacted = [node for node in graph["nodes"] if node["assetId"] != asset_id]
        layer_counts: dict[str, int] = defaultdict(int)
        for node in impacted:
            layer_counts[node.get("layerCode") or "UNKNOWN"] += 1
        return {
            **graph,
            "impactCount": len(impacted),
            "impactByLayer": dict(layer_counts),
        }

    @staticmethod
    def _column_node(
        column: Column,
        dataset: Dataset | None,
        *,
        center: str | None = None,
        level: int = 0,
    ) -> dict:
        return {
            "assetId": column.asset_id,
            "datasetId": column.dataset_id,
            "columnName": column.column_name,
            "name": column.cn_name or column.column_name,
            "dataType": column.data_type,
            "tableName": dataset.table_name if dataset else None,
            "datasetName": dataset.biz_name if dataset else column.dataset_id,
            "layerCode": dataset.layer_code if dataset else None,
            "isCenter": column.asset_id == center,
            "level": level,
        }

    @staticmethod
    def _column_edge(edge: ColumnLineage) -> dict:
        return {
            "id": edge.id,
            "source": edge.src_column_id,
            "target": edge.dst_column_id,
            "sourceDatasetId": edge.src_dataset_id,
            "targetDatasetId": edge.dst_dataset_id,
            "transformation": edge.transformation,
            "taskName": edge.task_name,
            "evidence": edge.evidence,
            "relationType": edge.relation_type,
        }

    def column_graph(
        self,
        column_id: str,
        *,
        depth: int = 2,
        direction: str = "both",
        max_nodes: int = 120,
    ) -> dict:
        center = self.db.get(Column, column_id)
        if center is None:
            raise KeyError(column_id)
        depth = max(1, min(depth, 5))
        direction = direction if direction in {"upstream", "downstream", "both"} else "both"
        edges = self.db.execute(select(ColumnLineage)).scalars().all()
        nodes, found_edges, levels, truncated = self._directional_graph(
            column_id,
            edges,
            depth=depth,
            direction=direction,
            max_nodes=max_nodes,
            source=_COLUMN_SOURCE,
            target=_COLUMN_TARGET,
        )
        columns = self._column_map(nodes)
        datasets = self._dataset_map({column.dataset_id for column in columns.values()})
        return {
            "centerAssetId": column_id,
            "centerDatasetId": center.dataset_id,
            "depth": depth,
            "direction": direction,
            "truncated": truncated,
            "nodes": [
                self._column_node(
                    columns[node],
                    datasets.get(columns[node].dataset_id),
                    center=column_id,
                    level=levels.get(node, 0),
                )
                for node in sorted(nodes, key=lambda value: (levels.get(value, 0), value))
                if node in columns
            ],
            "edges": [self._column_edge(edge) for edge in found_edges.values()],
        }

    def table_field_lineage(self, dataset_id: str) -> dict:
        if self.db.get(Dataset, dataset_id) is None:
            raise KeyError(dataset_id)
        edges = self.db.execute(
            select(ColumnLineage).where(
                or_(
                    ColumnLineage.src_dataset_id == dataset_id,
                    ColumnLineage.dst_dataset_id == dataset_id,
                )
            )
        ).scalars().all()
        column_ids = {edge.src_column_id for edge in edges} | {edge.dst_column_id for edge in edges}
        columns = self._column_map(column_ids)
        datasets = self._dataset_map({column.dataset_id for column in columns.values()})
        return {
            "datasetId": dataset_id,
            "nodes": [
                self._column_node(column, datasets.get(column.dataset_id))
                for column in columns.values()
            ],
            "edges": [self._column_edge(edge) for edge in edges],
        }
