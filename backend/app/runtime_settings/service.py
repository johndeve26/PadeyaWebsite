"""RuntimeSettingsService — resolve, mutate, status, cache, audit.

Resolution order for optional settings (never raises on missing):
1. DB ``runtime_settings`` override (when session available + valid)
2. Environment / Settings fallback
3. Registry code default
4. Unconfigured / None for secrets

Boot-critical Class A stays on ``get_settings()`` / ``.env`` only — never
queried from this table at app import or factory time.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import Settings, get_settings
from app.core.encryption import encrypt_secret, secret_first4, secret_last4, format_secret_fingerprint, secret_fingerprint_parts
from app.runtime_settings.models import RuntimeSetting
from app.runtime_settings.registry import (
    CLASS_A_BLOCKLIST,
    DEFINITIONS_BY_CATEGORY,
    DEFINITIONS_BY_KEY,
    FINGERPRINT_DISPLAY_PLAIN_KEYS,
    RUNTIME_SETTING_DEFINITIONS,
    RuntimeSettingDefinition,
    bytes_to_admin_mb,
    get_definition,
    is_class_a_key,
    is_patch_allowlisted,
    registry_public_meta,
    setting_shows_fingerprint,
    validate_value,
)

logger = logging.getLogger("padeya.runtime_settings")

# Process boot time — set at import of this module (no DB).
PROCESS_STARTED_AT: datetime = datetime.now(UTC)

StatusState = str  # missing|disabled|needs_configuration|using_env_fallback|using_db_override

_cache_lock = Lock()
_value_cache: dict[str, tuple[int, Any]] = {}
_cache_generation = 0
_CACHE_TTL_SECONDS = 30.0


def invalidate_runtime_settings_cache() -> None:
    global _cache_generation
    with _cache_lock:
        _value_cache.clear()
        _cache_generation += 1


def _env_explicitly_set(env_var: str) -> bool:
    return bool(env_var) and env_var in os.environ


def _settings_value(settings: Settings, defn: RuntimeSettingDefinition) -> Any:
    return getattr(settings, defn.settings_attr, defn.default)


def _mask_non_secret(value: Any, *, admin_unit: str | None = None) -> str | None:
    if value is None:
        return None
    if admin_unit == "mb":
        mb = bytes_to_admin_mb(value)
        if mb is None:
            return None
        return f"{mb} MB"
    text = str(value)
    if len(text) <= 24:
        return text
    return text[:12] + "…" + text[-4:]


def _secret_masked(
    *,
    configured: bool,
    first_four: str | None = None,
    last_four: str | None = None,
) -> str:
    if not configured:
        return "Not configured"
    formatted = format_secret_fingerprint(first_four, last_four)
    return formatted or "Configured"


def _audit(
    db: Session,
    *,
    action: str,
    actor_user_id: UUID | None,
    category: str | None,
    key: str | None,
    details: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    payload = {
        "category": category,
        "key": key,
        "action": action,
        **details,
    }
    write_audit_log(
        db,
        action=action,
        actor_user_id=actor_user_id,
        resource_type="runtime_setting",
        resource_id=key,
        details=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


class RuntimeSettingsService:
    """DB-backed optional settings resolver with in-memory cache."""

    def get_runtime_setting(
        self,
        key: str,
        *,
        db: Session | None = None,
        settings: Settings | None = None,
    ) -> Any:
        """Resolve a non-secret (or typed) value. Never raises on missing optional keys."""
        try:
            return self._resolve(key, db=db, settings=settings, want_secret=False)
        except Exception:  # noqa: BLE001 — degrade to default
            logger.exception("runtime setting resolve failed key=%s", key)
            defn = get_definition(key)
            return defn.default if defn else None

    def get_runtime_secret(
        self,
        key: str,
        *,
        db: Session | None = None,
        settings: Settings | None = None,
    ) -> str | None:
        """Decrypt secret for internal use only — never return from admin APIs."""
        try:
            val = self._resolve(key, db=db, settings=settings, want_secret=True)
            if val is None:
                return None
            text = str(val).strip()
            return text or None
        except Exception:  # noqa: BLE001
            logger.exception("runtime secret resolve failed key=%s", key)
            return None

    def _resolve(
        self,
        key: str,
        *,
        db: Session | None,
        settings: Settings | None,
        want_secret: bool,
    ) -> Any:
        if is_class_a_key(key):
            # Boot-critical: Settings only — never from runtime_settings table.
            s = settings or get_settings()
            defn = get_definition(key)
            attr = defn.settings_attr if defn else key
            return getattr(s, attr, None)

        defn = get_definition(key)
        if defn is None:
            return None

        # Specialist-managed keys are not stored in runtime_settings.
        if defn.managed_by in {"email_provider_settings", "push_provider_settings"}:
            if want_secret and db is not None:
                return self._specialist_secret_plain(defn, db)
            if db is not None and not defn.is_secret:
                specialist_val = self._specialist_plain(defn, db)
                if specialist_val is not None:
                    return specialist_val
            s = settings or get_settings()
            return _settings_value(s, defn)

        if defn.managed_by == "env_only" or not defn.editable:
            s = settings or get_settings()
            return _settings_value(s, defn)

        gen = _cache_generation
        cache_key = f"{key}:{'s' if want_secret else 'p'}"
        with _cache_lock:
            hit = _value_cache.get(cache_key)
            if hit and hit[0] == gen:
                return hit[1]

        value, _source = self._resolve_with_source(
            defn, db=db, settings=settings, want_secret=want_secret
        )
        with _cache_lock:
            if _cache_generation == gen:
                _value_cache[cache_key] = (gen, value)
        return value

    def _resolve_with_source(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings | None,
        want_secret: bool,
    ) -> tuple[Any, str]:
        s = settings or get_settings()
        row = None
        if db is not None and defn.managed_by == "runtime_settings":
            try:
                row = db.scalar(
                    select(RuntimeSetting).where(RuntimeSetting.key == defn.key)
                )
            except Exception:  # noqa: BLE001 — table may be missing mid-migrate
                logger.debug("runtime_settings table unavailable for key=%s", defn.key)
                row = None

        if row is not None:
            if defn.is_secret:
                if want_secret and row.value_encrypted:
                    from app.core.encryption import decrypt_secret

                    try:
                        return decrypt_secret(row.value_encrypted), "db"
                    except Exception:  # noqa: BLE001
                        logger.error("Failed to decrypt runtime secret key=%s", defn.key)
                elif not want_secret:
                    return None, "db"
            elif row.value_plain is not None:
                return row.value_plain, "db"

        env_val = _settings_value(s, defn)
        if _env_explicitly_set(defn.env_var):
            return env_val, "env"
        # Settings always has a value (default or env) — treat as env when equal
        # to registry default → "default", else "env".
        if env_val == defn.default:
            return env_val, "default"
        return env_val, "env"

    def _specialist_plain(
        self, defn: RuntimeSettingDefinition, db: Session
    ) -> Any | None:
        """Non-secret values owned by specialist tables (e.g. smtp_port)."""
        if defn.managed_by == "email_provider_settings":
            from app.email.settings_service import get_active_provider_settings

            row = get_active_provider_settings(db)
            if row is None:
                return None
            if defn.key == "smtp_port" and row.smtp_port is not None:
                return int(row.smtp_port)
        return None

    def _specialist_secret_plain(
        self, defn: RuntimeSettingDefinition, db: Session
    ) -> str | None:
        if defn.managed_by == "email_provider_settings":
            from app.email.settings_service import (
                decrypt_smtp_password,
                decrypt_smtp_username,
                get_active_provider_settings,
            )

            row = get_active_provider_settings(db)
            if row is None:
                return None
            if defn.key == "smtp_password":
                return decrypt_smtp_password(row) or None
            if defn.key == "smtp_username":
                return decrypt_smtp_username(row) or None
        if defn.managed_by == "push_provider_settings":
            from app.notifications.settings_service import (
                decrypt_vapid_private,
                get_active_push_settings,
            )

            row = get_active_push_settings(db)
            if row is None:
                return None
            if defn.key == "vapid_private_key":
                try:
                    return decrypt_vapid_private(row) or None
                except Exception:  # noqa: BLE001
                    return None
        return None

    def resolve_source(
        self,
        key: str,
        *,
        db: Session | None = None,
        settings: Settings | None = None,
    ) -> str:
        defn = get_definition(key)
        if defn is None:
            return "missing"
        _, source = self._resolve_with_source(
            defn, db=db, settings=settings, want_secret=False
        )
        return source

    def status_state_for(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings | None = None,
    ) -> StatusState:
        s = settings or get_settings()
        if defn.is_secret or defn.managed_by == "env_only":
            configured = self._is_configured(defn, db=db, settings=s)
            if not configured:
                return "needs_configuration" if defn.required_for_feature else "missing"
        source = self.resolve_source(defn.key, db=db, settings=s)
        if source == "db":
            return "using_db_override"
        if source == "env":
            return "using_env_fallback"
        if defn.value_type == "boolean":
            val = self.get_runtime_setting(defn.key, db=db, settings=s)
            if val is False and defn.required_for_feature:
                return "disabled"
        return "using_env_fallback" if source == "default" else source

    def _is_configured(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings,
    ) -> bool:
        if defn.managed_by == "email_provider_settings":
            from app.email.settings_service import get_active_provider_settings

            if db is None:
                env_v = _settings_value(settings, defn)
                return bool(str(env_v or "").strip())
            row = get_active_provider_settings(db)
            if row is None:
                return False
            if defn.key == "smtp_password":
                return bool(row.smtp_password_encrypted)
            if defn.key == "smtp_username":
                return bool(row.smtp_username_encrypted)
            return False
        if defn.managed_by == "push_provider_settings":
            from app.notifications.settings_service import get_active_push_settings

            if db is None:
                return False
            row = get_active_push_settings(db)
            return bool(
                row and getattr(row, "vapid_private_key_encrypted", None)
            )
        if defn.managed_by == "runtime_settings" and db is not None:
            row = db.scalar(
                select(RuntimeSetting).where(RuntimeSetting.key == defn.key)
            )
            if row is not None:
                if defn.is_secret:
                    return bool(row.value_encrypted)
                return row.value_plain is not None
        val = _settings_value(settings, defn)
        if defn.is_secret or defn.value_type == "secret":
            return bool(str(val or "").strip())
        return val is not None and val != ""

    def _fingerprint_for(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings,
    ) -> tuple[str | None, str | None]:
        if defn.managed_by == "email_provider_settings" and db is not None:
            from app.email.settings_service import get_active_provider_settings

            row = get_active_provider_settings(db)
            if row is None:
                return None, None
            if defn.key == "smtp_password":
                return row.smtp_password_first4, row.smtp_password_last4
            if defn.key == "smtp_username":
                return row.smtp_username_first4, row.smtp_username_last4
        if defn.managed_by == "push_provider_settings" and db is not None:
            from app.notifications.settings_service import get_active_push_settings

            row = get_active_push_settings(db)
            if row is not None:
                return getattr(row, "vapid_private_first4", None), getattr(
                    row, "vapid_private_last4", None
                )
        if defn.managed_by == "runtime_settings" and db is not None:
            row = db.scalar(
                select(RuntimeSetting).where(RuntimeSetting.key == defn.key)
            )
            if row is not None:
                if defn.is_secret and (row.first_four or row.last_four):
                    return row.first_four, row.last_four
                if not defn.is_secret and defn.key in FINGERPRINT_DISPLAY_PLAIN_KEYS:
                    plain = row.value_plain
                    if plain is not None and str(plain).strip():
                        return secret_fingerprint_parts(str(plain))
        raw = _settings_value(settings, defn)
        if raw:
            return secret_fingerprint_parts(str(raw))
        return None, None

    def _last_four_for(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings,
    ) -> str | None:
        _first, last = self._fingerprint_for(defn, db=db, settings=settings)
        return last

    def serialize_setting(
        self,
        defn: RuntimeSettingDefinition,
        *,
        db: Session | None,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        s = settings or get_settings()
        source = self.resolve_source(defn.key, db=db, settings=s)
        state = self.status_state_for(defn, db=db, settings=s)
        meta = registry_public_meta(defn)
        base: dict[str, Any] = {
            **meta,
            "source": source,
            "status": state,
            "restart_required": defn.restart_required,
        }
        if setting_shows_fingerprint(defn):
            configured = self._is_configured(defn, db=db, settings=s)
            first4, last4 = (
                self._fingerprint_for(defn, db=db, settings=s) if configured else (None, None)
            )
            base.update(
                {
                    "configured": configured,
                    "first_four": first4,
                    "last_four": last4,
                    "masked_value": _secret_masked(
                        configured=configured,
                        first_four=first4,
                        last_four=last4,
                    ),
                    "value": None,
                }
            )
            return base

        value = self.get_runtime_setting(defn.key, db=db, settings=s)
        if defn.admin_unit == "mb":
            value = bytes_to_admin_mb(value)
        base.update(
            {
                "value": value,
                "configured": value is not None and value != "",
                "masked_value": None,
                "last_four": None,
                "admin_unit": defn.admin_unit,
            }
        )
        return base

    def list_all(
        self, db: Session, *, settings: Settings | None = None
    ) -> dict[str, Any]:
        from app.runtime_settings.registry import CATEGORIES

        s = settings or get_settings()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for defn in RUNTIME_SETTING_DEFINITIONS:
            grouped.setdefault(defn.category, []).append(
                self.serialize_setting(defn, db=db, settings=s)
            )
        testable = frozenset(
            {"email", "push", "ai", "payments", "storage", "integrations"}
        )
        category_cards: list[dict[str, Any]] = []
        for cat in CATEGORIES:
            defs = DEFINITIONS_BY_CATEGORY.get(cat, [])
            if not defs and cat not in {"system-status"}:
                continue
            specialist = None
            if cat == "email":
                specialist = "/admin/email/settings"
            elif cat == "push":
                specialist = "/admin/push/settings"
            sources = {
                self.resolve_source(d.key, db=db, settings=s) for d in defs
            }
            source = (
                "db"
                if "db" in sources
                else ("env" if "env" in sources else "default")
            )
            category_cards.append(
                {
                    "category": cat,
                    "label": cat.replace("-", " ").title(),
                    "setting_count": len(defs),
                    "testable": cat in testable,
                    "specialist_href": specialist,
                    "source": source,
                    "configured": True,
                    "status": (
                        "db_override"
                        if source == "db"
                        else ("env_fallback" if source == "env" else "configured")
                    ),
                }
            )
        status = self.system_status(
            db, actor_user_id=None, record_view_audit=False
        )
        return {
            "categories": category_cards,
            "settings": grouped,
            "registry_count": len(RUNTIME_SETTING_DEFINITIONS),
            "system": {
                "version": status.get("app_version"),
                "build_sha": status.get("build_sha"),
                "last_boot_at": status.get("last_boot_time"),
                "app_env": status.get("environment"),
                "items": [
                    {"key": k, "configured": v}
                    for k, v in (status.get("configured") or {}).items()
                    if isinstance(v, bool)
                ],
            },
        }

    def list_category(
        self, db: Session, category: str, *, settings: Settings | None = None
    ) -> dict[str, Any]:
        s = settings or get_settings()
        defs = DEFINITIONS_BY_CATEGORY.get(category, [])
        specialist = None
        if category == "email":
            specialist = "/admin/email/settings"
        elif category == "push":
            specialist = "/admin/push/settings"
        return {
            "category": category,
            "label": category.replace("-", " ").title(),
            "specialist_href": specialist,
            "settings": [
                self.serialize_setting(d, db=db, settings=s) for d in defs
            ],
        }

    def upsert(
        self,
        db: Session,
        *,
        category: str,
        key: str,
        value: Any = None,
        clear_secret: bool = False,
        actor_user_id: UUID | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if is_class_a_key(key) or key in CLASS_A_BLOCKLIST:
            _audit(
                db,
                action="runtime_setting_validation_failed",
                actor_user_id=actor_user_id,
                category=category,
                key=key,
                details={"reason": "class_a_blocked", "old_source": None, "new_source": None},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
            raise PermissionError(f"Boot-critical key is not editable: {key}")

        defn = get_definition(key)
        if defn is None or defn.category != category:
            _audit(
                db,
                action="runtime_setting_validation_failed",
                actor_user_id=actor_user_id,
                category=category,
                key=key,
                details={"reason": "unknown_or_category_mismatch"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
            raise LookupError(f"Unknown setting {category}/{key}")

        if not is_patch_allowlisted(key) or not defn.editable:
            _audit(
                db,
                action="runtime_setting_validation_failed",
                actor_user_id=actor_user_id,
                category=category,
                key=key,
                details={"reason": "not_editable"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
            raise PermissionError(f"Setting is not editable: {key}")

        old_source = self.resolve_source(key, db=db)

        # Specialist delegation — no duplicate secret storage
        if defn.managed_by == "email_provider_settings":
            return self._upsert_email_specialist(
                db,
                defn=defn,
                value=value,
                clear_secret=clear_secret,
                actor_user_id=actor_user_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                old_source=old_source,
                commit=commit,
            )
        if defn.managed_by == "push_provider_settings":
            return self._upsert_push_specialist(
                db,
                defn=defn,
                value=value,
                clear_secret=clear_secret,
                actor_user_id=actor_user_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                old_source=old_source,
                commit=commit,
            )
        if defn.managed_by != "runtime_settings":
            raise PermissionError(f"Setting is env-only: {key}")

        try:
            if defn.is_secret:
                if clear_secret:
                    return self.clear_override(
                        db,
                        category=category,
                        key=key,
                        actor_user_id=actor_user_id,
                        reason=reason,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        commit=commit,
                    )
                if value is None or str(value).strip() == "":
                    # blank/omit = keep existing
                    return self.serialize_setting(defn, db=db)
                plain = validate_value(defn, value)
            else:
                if value is None:
                    raise ValueError("value is required")
                plain = validate_value(defn, value)
            if key == "paystack_mode" and str(plain).lower() == "live":
                live_secret = (
                    self.get_runtime_secret("paystack_live_secret_key", db=db) or ""
                ).strip()
                if not live_secret:
                    raise ValueError(
                        "Set Paystack live secret key (sk_live_…) before switching mode to Live."
                    )
        except ValueError as exc:
            _audit(
                db,
                action="runtime_setting_validation_failed",
                actor_user_id=actor_user_id,
                category=category,
                key=key,
                details={"reason": str(exc)[:200]},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
            raise

        row = db.scalar(select(RuntimeSetting).where(RuntimeSetting.key == key))
        if row is None:
            row = RuntimeSetting(key=key, category=category)
            db.add(row)

        row.category = category
        row.value_type = defn.value_type
        row.is_secret = defn.is_secret
        row.is_editable = defn.editable
        row.is_required_for_runtime = False  # never Class A
        row.description = defn.description
        row.validation_schema_json = defn.validation_schema_json
        row.source = "db"
        row.updated_by_admin_id = actor_user_id

        old_masked = None
        new_masked = None
        if defn.is_secret:
            old_masked = _secret_masked(
                configured=bool(row.value_encrypted),
                first_four=row.first_four,
                last_four=row.last_four,
            )
            plain_text = str(plain)
            row.value_encrypted = encrypt_secret(plain_text)
            row.first_four = secret_first4(plain_text)
            row.last_four = secret_last4(plain_text)
            row.value_plain = None
            new_masked = _secret_masked(
                configured=True,
                first_four=row.first_four,
                last_four=row.last_four,
            )
            action = "runtime_secret_replaced"
        else:
            old_masked = _mask_non_secret(row.value_plain, admin_unit=defn.admin_unit)
            row.value_plain = plain
            row.value_encrypted = None
            if setting_shows_fingerprint(defn) and plain is not None and str(plain).strip():
                f4, l4 = secret_fingerprint_parts(str(plain))
                row.first_four = f4
                row.last_four = l4
                new_masked = _secret_masked(
                    configured=True, first_four=f4, last_four=l4
                )
            else:
                row.first_four = None
                row.last_four = None
                new_masked = _mask_non_secret(plain, admin_unit=defn.admin_unit)
            action = "runtime_setting_updated"

        db.flush()
        invalidate_runtime_settings_cache()
        _audit(
            db,
            action=action,
            actor_user_id=actor_user_id,
            category=category,
            key=key,
            details={
                "old_source": old_source,
                "new_source": "db",
                "old_value_masked": old_masked,
                "new_value_masked": new_masked,
                "reason": reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
            db.refresh(row)
        return self.serialize_setting(defn, db=db)

    def _upsert_email_specialist(
        self,
        db: Session,
        *,
        defn: RuntimeSettingDefinition,
        value: Any,
        clear_secret: bool,
        actor_user_id: UUID | None,
        reason: str | None,
        ip_address: str | None,
        user_agent: str | None,
        old_source: str,
        commit: bool,
    ) -> dict[str, Any]:
        from app.email.settings_service import update_provider_settings

        updates: dict[str, Any] = {}
        action = "runtime_secret_replaced"
        new_masked = "Cleared" if clear_secret else "Configured · (specialist)"
        if defn.key == "smtp_password":
            if clear_secret:
                updates["clear_smtp_password"] = True
            elif value is not None and str(value).strip():
                updates["smtp_password"] = str(value).strip()
            else:
                return self.serialize_setting(defn, db=db)
        elif defn.key == "smtp_username":
            if clear_secret:
                updates["clear_smtp_username"] = True
            elif value is not None and str(value).strip():
                updates["smtp_username"] = str(value).strip()
            else:
                return self.serialize_setting(defn, db=db)
        elif defn.key == "smtp_port":
            try:
                plain = validate_value(defn, value)
            except ValueError as exc:
                _audit(
                    db,
                    action="runtime_setting_validation_failed",
                    actor_user_id=actor_user_id,
                    category=defn.category,
                    key=defn.key,
                    details={"reason": str(exc)[:200]},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                if commit:
                    db.commit()
                raise
            updates["smtp_port"] = plain
            action = "runtime_setting_updated"
            new_masked = _mask_non_secret(plain)
        else:
            raise PermissionError(f"Unsupported email specialist key: {defn.key}")

        try:
            update_provider_settings(
                db, updates=updates, actor_user_id=actor_user_id, commit=False
            )
        except ValueError as exc:
            _audit(
                db,
                action="runtime_setting_validation_failed",
                actor_user_id=actor_user_id,
                category=defn.category,
                key=defn.key,
                details={"reason": str(exc)[:200]},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if commit:
                db.commit()
            raise
        invalidate_runtime_settings_cache()
        _audit(
            db,
            action=action,
            actor_user_id=actor_user_id,
            category=defn.category,
            key=defn.key,
            details={
                "old_source": old_source,
                "new_source": "db",
                "old_value_masked": "Configured" if old_source == "db" else "Not configured",
                "new_value_masked": new_masked,
                "reason": reason,
                "managed_by": "email_provider_settings",
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
        return self.serialize_setting(defn, db=db)

    def _upsert_push_specialist(
        self,
        db: Session,
        *,
        defn: RuntimeSettingDefinition,
        value: Any,
        clear_secret: bool,
        actor_user_id: UUID | None,
        reason: str | None,
        ip_address: str | None,
        user_agent: str | None,
        old_source: str,
        commit: bool,
    ) -> dict[str, Any]:
        from app.notifications.settings_service import update_push_settings

        if defn.key != "vapid_private_key":
            raise PermissionError(f"Unsupported push specialist key: {defn.key}")

        if clear_secret:
            # No dedicated clear flag on push settings — clear encrypted fields directly.
            from app.notifications.settings_service import get_or_create_active_push_settings

            row = get_or_create_active_push_settings(db, actor_user_id=actor_user_id)
            row.vapid_private_key_encrypted = None
            row.vapid_private_last4 = None
            row.updated_by_user_id = actor_user_id
            db.flush()
        elif value is not None and str(value).strip():
            update_push_settings(
                db,
                updates={"vapid_private_key": str(value).strip()},
                actor_user_id=actor_user_id,
                commit=False,
            )
        else:
            return self.serialize_setting(defn, db=db)

        invalidate_runtime_settings_cache()
        _audit(
            db,
            action="runtime_secret_replaced",
            actor_user_id=actor_user_id,
            category=defn.category,
            key=defn.key,
            details={
                "old_source": old_source,
                "new_source": "db",
                "old_value_masked": "Configured" if old_source == "db" else "Not configured",
                "new_value_masked": "Cleared" if clear_secret else "Configured · (specialist)",
                "reason": reason,
                "managed_by": "push_provider_settings",
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
        return self.serialize_setting(defn, db=db)

    def clear_override(
        self,
        db: Session,
        *,
        category: str,
        key: str,
        actor_user_id: UUID | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        defn = get_definition(key)
        if defn is None or defn.category != category:
            raise LookupError(f"Unknown setting {category}/{key}")
        if is_class_a_key(key) or not defn.editable:
            raise PermissionError(f"Cannot clear non-editable key: {key}")

        old_source = self.resolve_source(key, db=db)

        if defn.managed_by == "email_provider_settings":
            return self._upsert_email_specialist(
                db,
                defn=defn,
                value=None,
                clear_secret=True,
                actor_user_id=actor_user_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                old_source=old_source,
                commit=commit,
            )
        if defn.managed_by == "push_provider_settings":
            return self._upsert_push_specialist(
                db,
                defn=defn,
                value=None,
                clear_secret=True,
                actor_user_id=actor_user_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                old_source=old_source,
                commit=commit,
            )

        row = db.scalar(select(RuntimeSetting).where(RuntimeSetting.key == key))
        old_masked = None
        if row is not None:
            if defn.is_secret:
                old_masked = _secret_masked(
                    configured=bool(row.value_encrypted),
                    first_four=row.first_four,
                    last_four=row.last_four,
                )
            else:
                old_masked = _mask_non_secret(
                    row.value_plain, admin_unit=defn.admin_unit
                )
            db.delete(row)
            db.flush()

        invalidate_runtime_settings_cache()
        new_source = self.resolve_source(key, db=db)
        _audit(
            db,
            action="runtime_setting_cleared_to_env",
            actor_user_id=actor_user_id,
            category=category,
            key=key,
            details={
                "old_source": old_source,
                "new_source": new_source,
                "old_value_masked": old_masked,
                "new_value_masked": None,
                "reason": reason,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if commit:
            db.commit()
        return self.serialize_setting(defn, db=db)

    def system_status(
        self,
        db: Session,
        *,
        actor_user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        record_view_audit: bool = True,
    ) -> dict[str, Any]:
        """Safe status only — never raw secrets/URLs/keys."""
        settings = get_settings()
        from app.core.redis import redis_health

        app_version = (
            os.environ.get("APP_VERSION")
            or os.environ.get("PADAYA_APP_VERSION")
            or "0.17.0"
        )
        build_sha = (
            os.environ.get("GIT_SHA")
            or os.environ.get("BUILD_SHA")
            or os.environ.get("SOURCE_COMMIT")
            or "unknown"
        )

        from app.payments.config import paystack_runtime

        cfg = paystack_runtime(db)
        paystack_secret = cfg.secret_configured
        paystack_webhook = bool(cfg.effective_webhook_secret.strip())
        paystack_public = cfg.public_configured
        ai_key = bool((settings.ai_api_key or "").strip())

        categories: dict[str, Any] = {}
        for cat, defs in DEFINITIONS_BY_CATEGORY.items():
            cat_states = []
            for d in defs:
                cat_states.append(
                    {
                        "key": d.key,
                        "status": self.status_state_for(d, db=db, settings=settings),
                        "configured": self._is_configured(d, db=db, settings=settings)
                        if (d.is_secret or d.managed_by == "env_only")
                        else True,
                    }
                )
            categories[cat] = cat_states

        payload = {
            "environment": settings.app_env,
            "app_version": app_version,
            "build_sha": build_sha,
            "last_boot_time": PROCESS_STARTED_AT.isoformat(),
            "redis": redis_health().get("redis", "unavailable"),
            "configured": {
                "paystack_mode": cfg.mode,
                "paystack_secret_key": paystack_secret,
                "paystack_webhook_secret": paystack_webhook,
                "paystack_public_key": paystack_public,
                "ai_api_key": ai_key,
                "paystack_public_key_last_four": secret_last4(cfg.public_key)
                if paystack_public
                else None,
                "paystack_public_key_first_four": secret_first4(cfg.public_key)
                if paystack_public
                else None,
                "ai_api_key_last_four": secret_last4(settings.ai_api_key) if ai_key else None,
                "ai_api_key_first_four": secret_first4(settings.ai_api_key) if ai_key else None,
            },
            "providers": {
                "ai_enabled": bool(settings.ai_enabled),
                "ai_provider": settings.ai_provider,
                "email_specialist_route": "/admin/email/settings",
                "push_specialist_route": "/admin/push/settings",
            },
            "category_states": categories,
            "status_enums": [
                "missing",
                "disabled",
                "needs_configuration",
                "using_env_fallback",
                "using_db_override",
            ],
        }

        if record_view_audit:
            _audit(
                db,
                action="runtime_setting_viewed_sensitive_status",
                actor_user_id=actor_user_id,
                category="system-status",
                key=None,
                details={
                    "configured_flags": {
                        "paystack_secret_key": paystack_secret,
                        "paystack_webhook_secret": paystack_webhook,
                        "ai_api_key": ai_key,
                    },
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.commit()

        return payload

    def list_audit(
        self,
        db: Session,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        from app.core.audit import AuditLog

        actions = (
            "runtime_setting_updated",
            "runtime_secret_replaced",
            "runtime_setting_cleared_to_env",
            "runtime_setting_tested",
            "runtime_setting_validation_failed",
            "runtime_setting_viewed_sensitive_status",
        )
        stmt = (
            select(AuditLog)
            .where(AuditLog.action.in_(actions))
            .order_by(AuditLog.created_at.desc())
            .offset(max(0, offset))
            .limit(min(200, max(1, limit)))
        )
        rows = list(db.scalars(stmt).all())
        return {
            "items": [
                {
                    "id": str(r.id),
                    "action": r.action,
                    "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "details": r.details,
                    "ip_address": r.ip_address,
                    "user_agent": r.user_agent,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
        }


runtime_settings_service = RuntimeSettingsService()


def get_runtime_setting(
    key: str, *, db: Session | None = None, settings: Settings | None = None
) -> Any:
    return runtime_settings_service.get_runtime_setting(key, db=db, settings=settings)


def get_runtime_secret(
    key: str, *, db: Session | None = None, settings: Settings | None = None
) -> str | None:
    return runtime_settings_service.get_runtime_secret(key, db=db, settings=settings)
