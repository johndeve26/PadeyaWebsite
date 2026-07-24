"""Admin-tunable host recommendation settings (runtime_settings + defaults)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.hosts.recommendations import constants as C
from app.runtime_settings.service import get_runtime_setting


@dataclass(frozen=True)
class HostRecommendationConfig:
    enabled: bool = True
    min_score: int = C.SCORE_MIN_SHOW
    dismiss_days: int = C.DISMISS_EXCLUDE_DAYS
    pool_size: int = C.CANDIDATE_POOL_SIZE
    weight_interest: float = 1.0
    weight_location: float = 1.0
    weight_social: float = 1.0
    weight_trust: float = 1.0
    weight_freshness: float = 1.0
    max_per_category: int = C.MAX_HOSTS_PER_CATEGORY
    max_per_city: int = C.MAX_HOSTS_PER_CITY
    cold_start_mode: str = C.COLD_START_BASELINE
    category_hide_days: int = C.CATEGORY_HIDE_DAYS
    impression_penalty_threshold: int = C.FEEDBACK_IGNORE_THRESHOLD


def load_host_recommendation_config(
    db: Session | None = None,
    *,
    settings: Settings | None = None,
) -> HostRecommendationConfig:
    settings = settings or get_settings()

    def _bool(key: str, default: bool) -> bool:
        raw = get_runtime_setting(key, db=db, settings=settings)
        if raw is None:
            return default
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def _int(key: str, default: int, *, lo: int, hi: int) -> int:
        raw = get_runtime_setting(key, db=db, settings=settings)
        try:
            val = int(raw) if raw is not None else default
        except (TypeError, ValueError):
            val = default
        return max(lo, min(hi, val))

    def _float(key: str, default: float, *, lo: float, hi: float) -> float:
        raw = get_runtime_setting(key, db=db, settings=settings)
        try:
            val = float(raw) if raw is not None else default
        except (TypeError, ValueError):
            val = default
        return max(lo, min(hi, val))

    def _str(key: str, default: str) -> str:
        raw = get_runtime_setting(key, db=db, settings=settings)
        if raw is None or str(raw).strip() == "":
            return default
        return str(raw).strip().lower()

    return HostRecommendationConfig(
        enabled=_bool("host_recommendations_enabled", True),
        min_score=_int("host_recommendations_min_score", C.SCORE_MIN_SHOW, lo=0, hi=100),
        dismiss_days=_int(
            "host_recommendations_dismiss_days", C.DISMISS_EXCLUDE_DAYS, lo=1, hi=365
        ),
        pool_size=_int(
            "host_recommendations_pool_size", C.CANDIDATE_POOL_SIZE, lo=20, hi=200
        ),
        weight_interest=_float(
            "host_recommendations_weight_interest", 1.0, lo=0.0, hi=3.0
        ),
        weight_location=_float(
            "host_recommendations_weight_location", 1.0, lo=0.0, hi=3.0
        ),
        weight_social=_float(
            "host_recommendations_weight_social", 1.0, lo=0.0, hi=3.0
        ),
        weight_trust=_float(
            "host_recommendations_weight_trust", 1.0, lo=0.0, hi=3.0
        ),
        weight_freshness=_float(
            "host_recommendations_weight_freshness", 1.0, lo=0.0, hi=3.0
        ),
        max_per_category=_int(
            "host_recommendations_max_per_category", C.MAX_HOSTS_PER_CATEGORY, lo=1, hi=20
        ),
        max_per_city=_int(
            "host_recommendations_max_per_city", C.MAX_HOSTS_PER_CITY, lo=1, hi=30
        ),
        cold_start_mode=_str("host_recommendations_cold_start_mode", C.COLD_START_BASELINE),
        category_hide_days=_int(
            "host_recommendations_category_hide_days", C.CATEGORY_HIDE_DAYS, lo=1, hi=365
        ),
        impression_penalty_threshold=_int(
            "host_recommendations_impression_penalty_threshold",
            C.FEEDBACK_IGNORE_THRESHOLD,
            lo=1,
            hi=20,
        ),
    )
