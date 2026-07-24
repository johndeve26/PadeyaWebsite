"""Production readiness API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CheckStatus = Literal["pass", "fail", "warn", "skip"]


class ReadinessCheckPublic(BaseModel):
    id: str
    category: str
    name: str
    status: CheckStatus
    message: str
    fix: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AIReadinessSummaryPublic(BaseModel):
    status: Literal["PASS", "WARN", "FAIL"]
    templates_seeded: bool
    feature_routes_present: bool
    provider_status: str
    kill_switch_active: bool
    blocked_keys_status: str
    quarantined_keys_status: str
    spend_cap_status: str
    message: str


class ProductionReadinessPublic(BaseModel):
    verdict: str
    summary: str
    checks: list[ReadinessCheckPublic]
    ai_readiness: AIReadinessSummaryPublic | None = None
