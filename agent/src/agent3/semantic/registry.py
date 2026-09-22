from __future__ import annotations

from pathlib import Path
import re
import yaml

from agent3.contracts.authz import AuthzContext
from agent3.semantic.models import (
    Additivity,
    MandatoryFilter,
    MetricDefinition,
    MetricKind,
)

_NOISE = re.compile(
    r"(?:请|帮我|帮忙|查询|查一下|看一下|统计|生成|给我|一下|多少|是多少|情况|数据|指标|本期|当期|当前|现在|最新(?:一期)?|期末|本月|当月|最近一期|最近|今年|本年|上期|上月|上年)",
    re.IGNORECASE,
)
_SPACE = re.compile(r"[\s_\-—，,。；;：:（）()]+")


def _normalize(value: str) -> str:
    folded = value.strip().casefold()
    folded = _NOISE.sub("", folded)
    return _SPACE.sub("", folded)


class SemanticRegistry:
    def __init__(self, metrics: tuple[MetricDefinition, ...]) -> None:
        self._metrics = {metric.id: metric for metric in metrics}

    def get(self, authz: AuthzContext, metric_id: str) -> MetricDefinition | None:
        _ = authz
        return self._metrics.get(metric_id)

    @staticmethod
    def _score(metric: MetricDefinition, phrase: str) -> int:
        folded = phrase.strip().casefold()
        normalized = _normalize(phrase)
        if not normalized and not folded:
            return 0
        terms = tuple(x for x in (metric.id, metric.name, *metric.aliases) if x)
        if any(folded == term.casefold() for term in terms):
            return 20_000
        best = 0
        for term in terms:
            norm_term = _normalize(term)
            if not norm_term:
                continue
            if normalized == norm_term:
                best = max(best, 10_000 + len(norm_term))
            elif norm_term in normalized:
                best = max(best, 1_000 + len(norm_term))
            elif normalized and normalized in norm_term:
                best = max(best, 100 + len(normalized))
        return best

    def candidates(
        self,
        authz: AuthzContext,
        phrase: str,
        *,
        limit: int = 5,
    ) -> tuple[tuple[int, MetricDefinition], ...]:
        _ = authz
        rows = [
            (self._score(metric, phrase), metric)
            for metric in self._metrics.values()
        ]
        rows = [item for item in rows if item[0] > 0]
        rows.sort(key=lambda item: (-item[0], item[1].name, item[1].id))
        return tuple(rows[: max(1, limit)])

    def resolve(self, authz: AuthzContext, phrase: str) -> MetricDefinition | None:
        candidates = self.candidates(authz, phrase, limit=2)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0][1]
        if candidates[0][0] == candidates[1][0]:
            return None
        return candidates[0][1]

    def all(self, authz: AuthzContext) -> tuple[MetricDefinition, ...]:
        _ = authz
        return tuple(self._metrics.values())

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SemanticRegistry":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        metrics: list[MetricDefinition] = []
        for raw in payload.get("metrics", []):
            additivity = raw.get("additivity") or {}
            metrics.append(MetricDefinition(
                id=raw["id"],
                name=raw["name"],
                aliases=tuple(raw.get("aliases", [])),
                aggregation=raw["aggregation"],
                measure=raw["measure"],
                source_entity=raw["source_entity"],
                mandatory_filters=tuple(
                    MandatoryFilter(field=i["field"], op=i["op"], value=i["value"])
                    for i in raw.get("mandatory_filters", [])
                ),
                additivity_time=Additivity(additivity.get("time", Additivity.ADDITIVE.value)),
                grain=tuple(raw.get("grain", [])),
                valid_dimensions=tuple(raw.get("valid_dimensions", [])),
                time_field=raw.get("time_field", "dt"),
                owner=raw.get("owner", ""),
                caveats=raw.get("caveats", ""),
                kind=MetricKind(raw.get("kind", MetricKind.BASE.value)),
                numerator_metric_id=raw.get("numerator_metric_id", ""),
                denominator_metric_id=raw.get("denominator_metric_id", ""),
                formula=raw.get("formula", ""),
                time_grain=raw.get("time_grain", ""),
                latest_strategy=raw.get("latest_strategy", "MAX"),
            ))
        return cls(tuple(metrics))
