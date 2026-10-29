from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.assets import get_db
from backend.app.api.auth import get_current_user
from backend.app.agent.history import _sanitize_trace_value
from backend.app.core.config import ROOT
from backend.app.db.application_models import AgentConversation, AgentToolEvent, AgentTurn
from backend.app.db.models import ChangeLog, Column, Dataset, Metric, User

router = APIRouter(prefix="/api/v1/admin/workbench", tags=["admin-workbench"])


def require_admin_dev(user: User = Depends(get_current_user)) -> User:
    if os.getenv("DATACONTROL_ADMIN_WORKBENCH_ENABLED") != "1":
        raise HTTPException(404, "Developer workbench is disabled")
    if str(user.role).upper() != "ADMIN":
        raise HTTPException(403, "Administrator role required")
    return user


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return fallback


def _dataset_payload(row: Dataset) -> dict[str, Any]:
    return {
        "assetId": row.asset_id, "tableName": row.table_name, "bizName": row.biz_name,
        "workspaceCode": row.workspace_code, "layerCode": row.layer_code,
        "catalogCode": row.catalog_code, "status": row.status, "isCommon": row.is_common,
        "bizDefinition": row.biz_definition, "statCaliber": row.stat_caliber,
        "dataSourceDesc": row.data_source_desc, "grain": row.grain, "usageNotes": row.usage_notes,
        "techOwner": row.tech_owner, "bizOwner": row.biz_owner, "ownerDept": row.owner_dept,
        "updateFreq": row.update_freq, "scheduleDesc": row.schedule_desc, "scheduleNode": row.schedule_node,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "columnCount": len(row.columns),
    }


def _column_payload(row: Column) -> dict[str, Any]:
    return {
        "assetId": row.asset_id, "datasetId": row.dataset_id, "columnName": row.column_name,
        "ordinalNo": row.ordinal_no, "cnName": row.cn_name, "dataType": row.data_type,
        "bizDefinition": row.biz_definition, "unit": row.unit,
        "codeTableNo": row.code_table_no, "standardNo": row.standard_no,
    }


class DatasetMetadataPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    biz_name: str | None = Field(default=None, max_length=128)
    biz_definition: str | None = None
    stat_caliber: str | None = None
    data_source_desc: str | None = None
    grain: str | None = Field(default=None, max_length=200)
    usage_notes: str | None = None
    tech_owner: str | None = Field(default=None, max_length=64)
    biz_owner: str | None = Field(default=None, max_length=64)
    owner_dept: str | None = Field(default=None, max_length=128)
    update_freq: str | None = Field(default=None, max_length=16)
    schedule_desc: str | None = Field(default=None, max_length=300)
    schedule_node: str | None = Field(default=None, max_length=128)


class ColumnMetadataPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cn_name: str | None = Field(default=None, max_length=128)
    biz_definition: str | None = None
    unit: str | None = Field(default=None, max_length=32)
    code_table_no: str | None = Field(default=None, max_length=64)
    standard_no: str | None = Field(default=None, max_length=64)


class MetricMetadataPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_name: str | None = Field(default=None, max_length=128)
    aliases: str | None = Field(default=None, max_length=500)
    biz_definition: str | None = None
    stat_system_code: str | None = Field(default=None, max_length=64)
    aggregation: str | None = Field(default=None, max_length=16)
    measure_column: str | None = Field(default=None, max_length=128)
    time_field: str | None = Field(default=None, max_length=128)
    time_additivity: str | None = Field(default=None, max_length=16)
    caliber_desc: str | None = None
    valid_dimensions: str | None = Field(default=None, max_length=500)
    metric_kind: str | None = Field(default=None, max_length=16)
    numerator_metric_code: str | None = Field(default=None, max_length=64)
    denominator_metric_code: str | None = Field(default=None, max_length=64)
    formula: str | None = None
    time_grain: str | None = Field(default=None, max_length=16)
    latest_strategy: str | None = Field(default=None, max_length=32)
    mandatory_filters: str | None = None
    semantic_notes: str | None = None
    status: str | None = Field(default=None, max_length=16)


@router.get("/metadata/datasets")
def list_metadata_datasets(
    keyword: str | None = None,
    limit: int = Query(100, ge=1, le=300),
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    stmt = select(Dataset).options(selectinload(Dataset.columns))
    count_stmt = select(func.count(Dataset.asset_id))
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        predicate = or_(Dataset.table_name.ilike(term), Dataset.biz_name.ilike(term),
                        Dataset.biz_definition.ilike(term), Dataset.asset_id.ilike(term))
        stmt = stmt.where(predicate)
        count_stmt = count_stmt.where(predicate)
    rows = db.execute(stmt.order_by(Dataset.table_name).limit(limit)).scalars().all()
    total = db.scalar(count_stmt) or 0
    return {"code": "OK", "data": {"items": [_dataset_payload(row) for row in rows], "total": total}}


@router.get("/metadata/datasets/{asset_id}")
def get_metadata_dataset(
    asset_id: str,
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(Dataset).options(selectinload(Dataset.columns)).where(Dataset.asset_id == asset_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Dataset not found")
    columns = sorted(row.columns, key=lambda item: (item.ordinal_no, item.column_name))
    return {"code": "OK", "data": {"dataset": _dataset_payload(row),
                                    "columns": [_column_payload(item) for item in columns]}}


@router.patch("/metadata/datasets/{asset_id}")
def update_metadata_dataset(
    asset_id: str,
    body: DatasetMetadataPatch,
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(Dataset).options(selectinload(Dataset.columns)).where(Dataset.asset_id == asset_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Dataset not found")
    values = body.model_dump(exclude_unset=True)
    if "biz_name" in values and (values["biz_name"] is None or not values["biz_name"].strip()):
        raise HTTPException(422, "Business name cannot be empty")
    changes: dict[str, dict[str, Any]] = {}
    for key, value in values.items():
        old = getattr(row, key)
        if old != value:
            changes[key] = {"before": old, "after": value}
            setattr(row, key, value)
    if changes:
        row.updated_at = datetime.utcnow()
        db.add(ChangeLog(dataset_id=row.asset_id, change_type="ADMIN_EDIT",
                         content=_json({"entity": "dataset", "changes": changes}),
                         changed_by=user.username))
        db.commit()
        db.refresh(row)
    return {"code": "OK", "data": _dataset_payload(row)}


@router.patch("/metadata/columns/{asset_id}")
def update_metadata_column(
    asset_id: str,
    body: ColumnMetadataPatch,
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    row = db.get(Column, asset_id)
    if row is None:
        raise HTTPException(404, "Column not found")
    values = body.model_dump(exclude_unset=True)
    changes: dict[str, dict[str, Any]] = {}
    for key, value in values.items():
        old = getattr(row, key)
        if old != value:
            changes[key] = {"before": old, "after": value}
            setattr(row, key, value)
    if changes:
        parent_dataset = db.get(Dataset, row.dataset_id)
        if parent_dataset is not None:
            parent_dataset.updated_at = datetime.utcnow()
        db.add(ChangeLog(dataset_id=row.dataset_id, change_type="COLUMN_EDIT",
                         content=_json({"entity": "column", "assetId": row.asset_id,
                                        "columnName": row.column_name, "changes": changes}),
                         changed_by=user.username))
        db.commit()
        db.refresh(row)
    return {"code": "OK", "data": _column_payload(row)}


def _metric_payload(row: Metric, source: Dataset | None = None) -> dict[str, Any]:
    return {
        "assetId": row.asset_id, "metricCode": row.metric_code, "metricName": row.metric_name,
        "aliases": row.aliases, "bizDefinition": row.biz_definition,
        "sourceDatasetId": row.source_dataset_id,
        "sourceDatasetName": source.biz_name if source else row.source_dataset_id,
        "sourceTableName": source.table_name if source else None,
        "statSystemCode": row.stat_system_code, "aggregation": row.aggregation,
        "measureColumn": row.measure_column, "timeField": row.time_field,
        "timeAdditivity": row.time_additivity, "caliberDesc": row.caliber_desc,
        "validDimensions": row.valid_dimensions, "metricKind": row.metric_kind,
        "numeratorMetricCode": row.numerator_metric_code,
        "denominatorMetricCode": row.denominator_metric_code, "formula": row.formula,
        "timeGrain": row.time_grain, "latestStrategy": row.latest_strategy,
        "mandatoryFilters": row.mandatory_filters, "semanticNotes": row.semantic_notes,
        "status": row.status,
    }


@router.get("/metadata/metrics")
def list_metadata_metrics(
    keyword: str | None = None,
    limit: int = Query(100, ge=1, le=300),
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    stmt = select(Metric, Dataset).join(Dataset, Dataset.asset_id == Metric.source_dataset_id)
    count_stmt = select(func.count(Metric.asset_id)).join(
        Dataset, Dataset.asset_id == Metric.source_dataset_id
    )
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        predicate = or_(Metric.metric_code.ilike(term), Metric.metric_name.ilike(term),
                        Metric.biz_definition.ilike(term), Dataset.table_name.ilike(term))
        stmt = stmt.where(predicate)
        count_stmt = count_stmt.where(predicate)
    rows = db.execute(stmt.order_by(Metric.metric_name).limit(limit)).all()
    total = db.scalar(count_stmt) or 0
    return {"code": "OK", "data": {"items": [_metric_payload(metric, source) for metric, source in rows],
                                    "total": total}}


@router.patch("/metadata/metrics/{metric_code}")
def update_metadata_metric(
    metric_code: str,
    body: MetricMetadataPatch,
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    row = db.execute(select(Metric).where(Metric.metric_code == metric_code)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Metric not found")
    values = body.model_dump(exclude_unset=True)
    if values.get("mandatory_filters"):
        try:
            json.loads(values["mandatory_filters"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "Mandatory filters must be valid JSON") from exc
    if "metric_name" in values and (values["metric_name"] is None or not values["metric_name"].strip()):
        raise HTTPException(422, "Metric name cannot be empty")
    changes: dict[str, dict[str, Any]] = {}
    for key, value in values.items():
        old = getattr(row, key)
        if old != value:
            changes[key] = {"before": old, "after": value}
            setattr(row, key, value)
    if changes:
        db.add(ChangeLog(dataset_id=row.source_dataset_id, change_type="METRIC_EDIT",
                         content=_json({"entity": "metric", "metricCode": row.metric_code,
                                        "changes": changes}), changed_by=user.username))
        db.commit()
        db.refresh(row)
    source = db.get(Dataset, row.source_dataset_id)
    return {"code": "OK", "data": _metric_payload(row, source)}


@router.get("/runs")
def list_agent_runs(
    keyword: str | None = None,
    status: str | None = None,
    limit: int = Query(80, ge=1, le=300),
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    stmt = select(AgentTurn, AgentConversation).join(
        AgentConversation, AgentConversation.id == AgentTurn.conversation_id
    ).order_by(AgentTurn.created_at.desc())
    count_stmt = select(func.count(AgentTurn.id)).join(
        AgentConversation, AgentConversation.id == AgentTurn.conversation_id
    )
    if status and status != "all":
        stmt = stmt.where(AgentTurn.status == status)
        count_stmt = count_stmt.where(AgentTurn.status == status)
    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        predicate = or_(AgentTurn.question.ilike(term), AgentTurn.display_question.ilike(term),
                        AgentConversation.title.ilike(term), AgentTurn.id.ilike(term))
        stmt = stmt.where(predicate)
        count_stmt = count_stmt.where(predicate)
    rows = db.execute(stmt.limit(limit)).all()
    total = db.scalar(count_stmt) or 0
    ids = [turn.id for turn, _ in rows]
    counts: dict[str, int] = {}
    if ids:
        count_rows = db.execute(
            select(AgentToolEvent.turn_id, func.count(AgentToolEvent.id))
            .where(AgentToolEvent.turn_id.in_(ids)).group_by(AgentToolEvent.turn_id)
        ).all()
        counts = {str(run_id): int(count) for run_id, count in count_rows}
    items = []
    for turn, conv in rows:
        result = _decode(turn.result_json, {})
        items.append({
            "runId": turn.id, "conversationId": conv.id, "conversationTitle": conv.title,
            "userId": conv.user_id, "modelMode": turn.model_mode, "taskTier": conv.task_tier,
            "question": turn.question, "displayQuestion": turn.display_question or turn.question,
            "status": turn.status, "createdAt": turn.created_at.isoformat() if turn.created_at else None,
            "finishedAt": turn.finished_at.isoformat() if turn.finished_at else None,
            "error": turn.error, "toolEventCount": counts.get(turn.id, 0),
            "durationMs": result.get("durationMs"),
        })
    return {"code": "OK", "data": {"items": items, "total": total}}


@router.get("/runs/{run_id}")
def get_agent_run(
    run_id: str,
    user: User = Depends(require_admin_dev),
    db: Session = Depends(get_db),
):
    turn = db.get(AgentTurn, run_id)
    if turn is None:
        raise HTTPException(404, "Agent run not found")
    conv = db.get(AgentConversation, turn.conversation_id)
    if conv is None:
        raise HTTPException(404, "Agent conversation not found")
    rows = db.execute(
        select(AgentToolEvent).where(AgentToolEvent.turn_id == run_id)
        .order_by(AgentToolEvent.sequence)
    ).scalars().all()
    events = []
    for row in rows:
        events.append({
            "sequence": row.sequence, "type": row.event_type, "callId": row.call_id,
            "tool": row.tool, "status": row.status,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "payload": _decode(row.payload_json, None),
        })
    result = _decode(turn.result_json, None)
    return {"code": "OK", "data": {
        "runId": turn.id, "conversationId": conv.id, "conversationTitle": conv.title,
        "userId": conv.user_id, "modelMode": turn.model_mode, "taskTier": conv.task_tier,
        "question": turn.question, "displayQuestion": turn.display_question or turn.question,
        "contextAsset": _decode(conv.context_asset_json, None),
        "status": turn.status, "createdAt": turn.created_at.isoformat() if turn.created_at else None,
        "finishedAt": turn.finished_at.isoformat() if turn.finished_at else None,
        "error": turn.error, "events": events, "result": result,
        "debugContext": _decode(turn.debug_context_json, None),
        "toolEventCount": len(events), "durationMs": result.get("durationMs") if isinstance(result, dict) else None,
        "tracePayloadsAvailable": any(item["payload"] is not None for item in events),
        "tokenUsage": None, "tokenUsageNote": "当前 Harness 事件流未提供可靠的 token 统计。",
    }}


def _file_record(category: str, display_path: str, path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        content = _sanitize_trace_value(raw)
        exists = True
    except (OSError, UnicodeError):
        content, exists, digest = "", False, None
    return {"category": category, "path": display_path, "exists": exists,
            "sha256": digest, "content": content}


@router.get("/rules")
def get_effective_rules(
    modelMode: Literal["deepseek", "free-test"] = "deepseek",
    taskTier: Literal["standard", "multi"] = "standard",
    user: User = Depends(require_admin_dev),
):
    if modelMode == "free-test":
        profile = "dataagent-headless-free"
    elif taskTier == "multi":
        profile = "dataagent-headless-multi"
    else:
        profile = os.getenv("DATACONTROL_DSH_PROFILE", "dataagent-headless")
    dsh_home = Path(os.getenv("DSH_HOME", str(ROOT / ".local" / "dsh-home-v0.2.1-rc.3"))).resolve()
    agent_root = ROOT / "agent"
    overlay = "headless-multi.patch.yml" if taskTier == "multi" else "headless.patch.yml"
    files = [
        _file_record("系统提示词 / Profile", f"agent/dsh/profile/{overlay}",
                     agent_root / "dsh" / "profile" / overlay),
        _file_record("Agent query preset / system instructions", "agent/dsh/presets/dataagent-query/agent.cordis.yml",
                     agent_root / "dsh" / "presets" / "dataagent-query" / "agent.cordis.yml"),
        _file_record("Profile 基础配置", "agent/dsh/profile/cordis.patch.yml",
                     agent_root / "dsh" / "profile" / "cordis.patch.yml"),
        _file_record("运行时实际生成配置", f".local/profiles/{profile}/cordis.patch.yml",
                     dsh_home / "profiles" / profile / "cordis.patch.yml"),
        _file_record("可用 MCP 工具目录", "agent/tool-catalog.json", agent_root / "tool-catalog.json"),
        _file_record("Guard 执行入口", "agent/guard-plugin/src/index.ts",
                     agent_root / "guard-plugin" / "src" / "index.ts"),
        _file_record("Guard 硬规则", "agent/guard-plugin/src/policy.ts",
                     agent_root / "guard-plugin" / "src" / "policy.ts"),
        _file_record("MCP 工具参数定义", "agent/src/agent3/adapters/mcp/tools.py",
                     agent_root / "src" / "agent3" / "adapters" / "mcp" / "tools.py"),
        _file_record("确定性业务规则与 SQL 边界", "agent/src/agent3/services/core.py",
                     agent_root / "src" / "agent3" / "services" / "core.py"),
        _file_record("数仓开发草案规则", "agent/src/agent3/services/development.py",
                     agent_root / "src" / "agent3" / "services" / "development.py"),
        _file_record("Harness 调用与事件解析", "agent/src/dataagent_gateway/runner.py",
                     agent_root / "src" / "dataagent_gateway" / "runner.py"),
        _file_record("Portal 事件过滤与安全策略", "backend/app/agent/history.py",
                     ROOT / "backend" / "app" / "agent" / "history.py"),
        _file_record("Portal API 执行边界", "backend/app/api/agent.py",
                     ROOT / "backend" / "app" / "api" / "agent.py"),
    ]
    return {"code": "OK", "data": {
        "profile": profile, "modelMode": modelMode, "taskTier": taskTier,
        "files": files,
        "precedence": [
            "运行时生成的 cordis.patch.yml 是当前 Harness profile 的实际配置；",
            "headless.patch.yml / headless-multi.patch.yml 是项目维护的 Profile 源配置，启动脚本负责同步；",
            "tool-catalog.json 与 MCP tools.py 限定暴露的工具及参数；",
            "Guard、Agent3 Core 和 Portal API 代码执行确定性拦截、业务验证与安全边界。",
        ],
        "notice": "文件内容来自当前工作区。历史运行尚未保存完整配置快照；若配置已变更，当前内容不一定等于历史运行时版本。",
    }}
