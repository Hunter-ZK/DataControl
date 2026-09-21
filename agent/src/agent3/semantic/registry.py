from __future__ import annotations

from pathlib import Path
import re
import yaml

from agent3.contracts.authz import AuthzContext
from agent3.semantic.models import Additivity, MandatoryFilter, MetricDefinition

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

    def resolve(self, authz: AuthzContext, phrase: str) -> MetricDefinition | None:
        _ = authz
        folded = phrase.strip().casefold()
        normalized = _normalize(phrase)
        exact: list[MetricDefinition] = []
        scored: list[tuple[int, MetricDefinition]] = []
        for metric in self._metrics.values():
            terms = tuple(x for x in (metric.id, metric.name, *metric.aliases) if x)
            if any(folded == term.casefold() for term in terms):
                exact.append(metric)
                continue
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
            if best:
                scored.append((best, metric))
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1 or not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return None
        return scored[0][1]

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
                id=raw["id"], name=raw["name"], aliases=tuple(raw.get("aliases", [])),
                aggregation=raw["aggregation"], measure=raw["measure"], source_entity=raw["source_entity"],
                mandatory_filters=tuple(MandatoryFilter(field=i["field"], op=i["op"], value=i["value"]) for i in raw.get("mandatory_filters", [])),
                additivity_time=Additivity(additivity.get("time", Additivity.ADDITIVE.value)),
                grain=tuple(raw.get("grain", [])), valid_dimensions=tuple(raw.get("valid_dimensions", [])),
                time_field=raw.get("time_field", "dt"), owner=raw.get("owner", ""), caveats=raw.get("caveats", ""),
            ))
        return cls(tuple(metrics))
