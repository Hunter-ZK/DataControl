from __future__ import annotations

import json
from datetime import datetime
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.agent.runtime import EmbeddedAgentGateway
from backend.app.agent import history
from backend.app.api.assets import get_db
from backend.app.api.auth import get_current_user
from backend.app.db.application_models import AgentConversation, AgentDebugEvent, AgentToolEvent, AgentTurn
from backend.app.db.models import (
    CodeTable, CodeValue, Column, DataStandard, Dataset, Metric,
    StatisticalSystem, User, WordRoot,
)
from backend.app.db.session import SessionLocal

router = APIRouter(prefix="/api/v1/admin", tags=["admin-workbench"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if str(user.role or "").upper() not in {"ADMIN", "DEVELOPER"}:
        raise HTTPException(403, "Administrator role is required")
    return user


def _decode(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {"unparsed": raw}


def _iso(value: datetime | None):
    return value.isoformat(timespec="seconds") if value else None


def _duration_ms(start: datetime | None, end: datetime | None):
    if not start:
        return None
    return max(0, int(((end or datetime.utcnow()) - start).total_seconds() * 1000))


@router.get("/metadata/overview")
def metadata_overview(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Real metadata inventory and completeness counts; no synthetic values."""
    def count(model):
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    def missing(model, column):
        return int(db.scalar(
            select(func.count()).select_from(model).where(
                or_(column.is_(None), column == "")
            )
        ) or 0)
    return {
        "code": "OK",
        "data": {
            "counts": {
                "datasets": count(Dataset),
                "columns": count(Column),
                "metrics": count(Metric),
                "codeTables": count(CodeTable),
                "codeValues": count(CodeValue),
                "standards": count(DataStandard),
                "wordRoots": count(WordRoot),
                "statSystems": count(StatisticalSystem),
            },
            "quality": {
                "datasetsMissingDefinition": missing(Dataset, Dataset.biz_definition),
                "columnsMissingChineseName": missing(Column, Column.cn_name),
                "columnsMissingDefinition": missing(Column, Column.biz_definition),
                "metricsMissingDefinition": missing(Metric, Metric.biz_definition),
                "metricsMissingMeasureColumn": missing(Metric, Metric.measure_column),
            },
        },
    }


@router.get("/agent/runs")
def list_agent_runs(
    limit: int = Query(50, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    _admin: User = Depends(require_admin),
):
    with SessionLocal() as db:
        stmt = (
            select(AgentTurn, AgentConversation)
            .join(AgentConversation, AgentConversation.id == AgentTurn.conversation_id)
            .order_by(AgentTurn.created_at.desc(), AgentTurn.id.desc())
            .limit(limit)
        )
        if status and status != "all":
            stmt = stmt.where(AgentTurn.status == status)
        if keyword and keyword.strip():
            like = "%" + keyword.strip()[:200] + "%"
            stmt = stmt.where(or_(
                AgentTurn.question.like(like),
                AgentTurn.display_question.like(like),
                AgentConversation.title.like(like),
            ))
        rows = db.execute(stmt).all()
        output = []
        for turn, conv in rows:
            debug_count = int(db.scalar(
                select(func.count()).select_from(AgentDebugEvent)
                .where(AgentDebugEvent.turn_id == turn.id)
            ) or 0)
            tool_count = int(db.scalar(
                select(func.count()).select_from(AgentToolEvent)
                .where(AgentToolEvent.turn_id == turn.id, AgentToolEvent.event_type == "tool_call")
            ) or 0)
            output.append({
                "runId": turn.id,
                "conversationId": conv.id,
                "conversationTitle": conv.title,
                "userId": conv.user_id,
                "displayQuestion": turn.display_question or turn.question,
                "status": turn.status,
                "modelMode": turn.model_mode,
                "taskTier": conv.task_tier,
                "createdAt": _iso(turn.created_at),
                "finishedAt": _iso(turn.finished_at),
                "durationMs": _duration_ms(turn.created_at, turn.finished_at),
                "debugEventCount": debug_count,
                "toolCallCount": tool_count,
                "debugCaptureAvailable": debug_count > 0,
                "error": turn.error,
            })
        return {"code": "OK", "data": output}


@router.get("/agent/runs/{run_id}")
def get_agent_run(
    run_id: UUID,
    _admin: User = Depends(require_admin),
):
    with SessionLocal() as db:
        turn = db.get(AgentTurn, str(run_id))
        if turn is None:
            raise HTTPException(404, "Agent run not found")
        conv = db.get(AgentConversation, turn.conversation_id)
        debug_rows = db.execute(
            select(AgentDebugEvent).where(AgentDebugEvent.turn_id == turn.id)
            .order_by(AgentDebugEvent.sequence)
        ).scalars().all()
        tool_rows = db.execute(
            select(AgentToolEvent).where(AgentToolEvent.turn_id == turn.id)
            .order_by(AgentToolEvent.sequence)
        ).scalars().all()
        return {
            "code": "OK",
            "data": {
                "run": {
                    "runId": turn.id,
                    "conversationId": turn.conversation_id,
                    "conversationTitle": conv.title if conv else None,
                    "userId": conv.user_id if conv else None,
                    "displayQuestion": turn.display_question or turn.question,
                    "promptSentToHarness": turn.question,
                    "status": turn.status,
                    "modelMode": turn.model_mode,
                    "taskTier": conv.task_tier if conv else "standard",
                    "createdAt": _iso(turn.created_at),
                    "finishedAt": _iso(turn.finished_at),
                    "durationMs": _duration_ms(turn.created_at, turn.finished_at),
                    "error": turn.error,
                    "result": history.public_answer(_decode(turn.result_json) or {}),
                },
                "debugCaptureAvailable": bool(debug_rows),
                "debugEvents": [
                    {
                        "sequence": row.sequence,
                        "eventType": row.event_type,
                        "source": row.source,
                        "createdAt": _iso(row.created_at),
                        "payload": _decode(row.payload_json),
                    }
                    for row in debug_rows
                ],
                "toolEvents": [
                    {
                        "sequence": row.sequence,
                        "eventType": row.event_type,
                        "callId": row.call_id,
                        "tool": row.tool,
                        "status": row.status,
                        "createdAt": _iso(row.created_at),
                    }
                    for row in tool_rows
                ],
                "limitations": [] if debug_rows else [
                    "该运行没有详细 Trace 记录（可能发生在调试采集启用前）。",
                    "普通工具调用摘要不包含历史工具参数与完整返回值，无法从摘要反向还原。",
                ],
            },
        }


@router.get("/agent/config")
async def agent_debug_config(
    modelMode: Literal["deepseek", "free-test", "local-deepseek"] = "deepseek",
    taskTier: Literal["standard", "multi", "quick"] = "standard",
    _admin: User = Depends(require_admin),
):
    runtime = EmbeddedAgentGateway()
    try:
        async with httpx.AsyncClient(timeout=8.0, trust_env=False) as client:
            response = await client.get(
                f"{runtime.gateway_url}/v1/debug/config",
                params={"modelMode": modelMode, "taskTier": taskTier},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            503,
            "Agent Gateway configuration endpoint is unavailable; restart the Gateway with the updated code.",
        ) from exc
    return {"code": "OK", "data": payload}
