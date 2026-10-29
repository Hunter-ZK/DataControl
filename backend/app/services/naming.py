"""Deterministic naming assistance. Unknown terms are never invented as governed roots."""
from __future__ import annotations
import re
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db.models import Column, WordRoot

_SPLIT = re.compile(r"[,，;；|/、]+")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED = {"select", "from", "where", "group", "order", "table", "date", "user", "index", "by", "desc"}

def _root_terms(db: Session) -> dict[str, tuple[str, str]]:
    terms: dict[str, tuple[str, str]] = {}
    for root in db.execute(select(WordRoot).order_by(WordRoot.root_en)).scalars():
        if root.status not in ("EFFECTIVE", "VALID", "ONLINE"):
            continue
        abbr = root.root_en.strip().lower()
        if not _IDENTIFIER.fullmatch(abbr):
            continue
        names = [root.cn_name] + _SPLIT.split(root.synonyms or "")
        for term in names:
            name = (term or "").strip()
            if not name:
                continue
            if name in terms and terms[name][0] != abbr:
                terms[name] = ("", "ambiguous")
            elif name not in terms:
                terms[name] = (abbr, root.cn_name)
    return terms

def _segment(value: str, terms: dict[str, tuple[str, str]]):
    parts: list[dict[str, str]] = []
    i = 0
    sorted_terms = sorted(terms, key=lambda v: (-len(v), v))
    while i < len(value):
        if value[i].isspace() or value[i] in "_-":
            i += 1
            continue
        found = next((s for s in sorted_terms if value.startswith(s, i)), None)
        if found:
            abbr, original = terms[found]
            parts.append({"cn": found, "root": abbr, "source": original})
            i += len(found)
        else:
            start = i
            i += 1
            while i < len(value) and value[i] not in "_- " and not any(value.startswith(t, i) for t in sorted_terms):
                i += 1
            parts.append({"cn": value[start:i], "root": "", "source": "missing"})
    return parts

def suggest_names(db: Session, names: list[str], *, max_length: int = 64) -> list[dict]:
    if max_length < 8 or max_length > 128:
        raise ValueError("invalid maximum length")
    terms = _root_terms(db)
    unique_names = {name.strip() for name in names if name.strip()}
    existing: dict[str, set[str]] = {}
    for offset in range(0, len(unique_names), 200):
        subset = sorted(unique_names)[offset:offset+200]
        for cn, en in db.execute(select(Column.cn_name, Column.column_name).where(Column.cn_name.in_(subset))):
            if cn and en:
                existing.setdefault(cn, set()).add(en)
    result = []
    for raw in names:
        name = raw.strip()
        segments = _segment(name, terms)
        already = sorted(existing.get(name, set()))
        unknown = [p["cn"] for p in segments if not p["root"]]
        possible = "_".join(p["root"] for p in segments if p["root"])
        source = "已有字段复用" if len(already) == 1 else "词根规则" if not unknown else "人工待补充"
        proposed = already[0] if len(already) == 1 else possible if not unknown else ""
        issues: list[str] = []
        if not name:
            issues.append("中文名称为空")
        if len(already) > 1:
            issues.append("同名字段已有多个不同英文名，请人工确定")
            proposed = ""
        if unknown:
            issues.append("缺少词根：" + "、".join(dict.fromkeys(unknown)))
        if proposed and (not _IDENTIFIER.fullmatch(proposed.lower()) or proposed.lower() in _RESERVED):
            issues.append("命名格式或保留字冲突")
        if proposed and len(proposed) > max_length:
            issues.append(f"超过长度上限 {max_length}")
        result.append({
            "cnName": name, "suggestedName": proposed, "segments": segments,
            "source": source, "issues": issues, "status": "待确认",
            "existingCandidates": already,
        })
    duplicate = Counter(item["suggestedName"].lower() for item in result if item["suggestedName"])
    for item in result:
        if item["suggestedName"] and duplicate[item["suggestedName"].lower()] > 1:
            item["issues"].append("本批次存在重名英文名")
    return result
