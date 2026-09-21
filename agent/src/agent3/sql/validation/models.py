from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueAction(StrEnum):
    AUTO_FIX = "auto_fix"
    CONTEXT_REQUIRED = "context_required"
    HUMAN_REVIEW = "human_review"
    BLOCK = "block"
    ADVISORY = "advisory"
    IGNORE = "ignore"


class SQLOperation(StrEnum):
    QUERY = "query"
    DML = "dml"
    DDL = "ddl"
    ACCESS_CONTROL = "access_control"
    UNKNOWN = "unknown"


class SQLRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: Severity
    message: str
    suggestion: str | None = None
    metadata: dict[str, Any] | None = None
    action: IssueAction = IssueAction.BLOCK
    auto_fixable: bool = False

    @property
    def blocking(self) -> bool:
        return self.action in {
            IssueAction.AUTO_FIX,
            IssueAction.CONTEXT_REQUIRED,
            IssueAction.HUMAN_REVIEW,
            IssueAction.BLOCK,
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["action"] = self.action.value
        data["blocking"] = self.blocking
        return data


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    dialect: str
    issues: tuple[ValidationIssue, ...]
    normalized_sql: str | None = None
    statement_type: str | None = None
    operation: SQLOperation = SQLOperation.UNKNOWN
    risk_level: SQLRiskLevel = SQLRiskLevel.LOW
    execution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "dialect": self.dialect,
            "issues": [issue.to_dict() for issue in self.issues],
            "normalized_sql": self.normalized_sql,
            "statement_type": self.statement_type,
            "operation": self.operation.value,
            "risk_level": self.risk_level.value,
            # DataControl validates and generates SQL only. Runtime execution is
            # deliberately outside this product boundary, even for SELECT.
            "execution_allowed": self.execution_allowed,
        }
