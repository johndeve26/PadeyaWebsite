"""Pydantic schemas for Admin Runtime Settings API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RuntimeSettingUpsertRequest(BaseModel):
    """PUT body. For secrets: omit/blank keeps existing; clear=true removes override."""

    value: Any | None = None
    secret_value: Any | None = None  # FE alias — treated as value when set
    clear: bool = False
    reason: str | None = Field(default=None, max_length=500)

    def resolved_value(self) -> Any | None:
        if self.secret_value is not None and str(self.secret_value).strip() != "":
            return self.secret_value
        return self.value


class RuntimeSettingPublic(BaseModel):
    key: str
    category: str
    label: str
    description: str
    type: str
    is_secret: bool
    editable: bool
    source: str
    status: str | None = None
    restart_required: bool = False
    value: Any | None = None
    configured: bool | None = None
    last_four: str | None = None
    first_four: str | None = None
    masked_value: str | None = None
    managed_by: str | None = None
    specialist_route: str | None = None
    env_var: str | None = None
    required_for_feature: str | None = None
    sensitive_level: str | None = None
    validation_schema_json: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class RuntimeSettingsListResponse(BaseModel):
    categories: list[Any]
    settings: dict[str, list[dict[str, Any]]] | list[dict[str, Any]] | None = None
    registry_count: int | None = None
    system: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class RuntimeSettingsCategoryResponse(BaseModel):
    category: str
    label: str | None = None
    specialist_href: str | None = None
    settings: list[dict[str, Any]]

    model_config = {"extra": "allow"}


class RuntimeSettingsStatusResponse(BaseModel):
    environment: str
    app_version: str
    build_sha: str
    last_boot_time: str
    redis: str
    configured: dict[str, Any]
    providers: dict[str, Any]
    category_states: dict[str, Any]
    status_enums: list[str]


class RuntimeSettingsAuditResponse(BaseModel):
    items: list[dict[str, Any]]


class RuntimeSettingsTestResponse(BaseModel):
    ok: bool
    category: str
    status: str
    message: str | None = None
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
