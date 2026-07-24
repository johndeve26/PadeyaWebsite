"""Default model catalogs and auto-selection helpers for feature routing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.models import AIProviderProfile

AUTO_MODEL_TOKENS = frozenset({"", "*", "all", "auto", "__auto__"})

DEFAULT_AVAILABLE_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-mini",
        "gpt-4.1",
    ],
    "openai_compatible": [
        "gpt-4o-mini",
        "gpt-4o",
    ],
    "anthropic": [
        "claude-3-5-haiku-latest",
        "claude-3-5-sonnet-latest",
        "claude-3-5-opus-latest",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ],
    "grok": [
        "grok-2-latest",
        "grok-beta",
    ],
    "template_fallback": ["template-v1"],
}


def default_available_models(provider_type: str) -> list[str]:
    ptype = (provider_type or "openai_compatible").strip().lower()
    return list(DEFAULT_AVAILABLE_MODELS.get(ptype, DEFAULT_AVAILABLE_MODELS["openai_compatible"]))


def is_auto_model_selection(model: str | None) -> bool:
    if model is None:
        return True
    return model.strip().lower() in AUTO_MODEL_TOKENS


def normalize_model_selection(model: str | None) -> str | None:
    if is_auto_model_selection(model):
        return None
    text = (model or "").strip()
    return text or None


def model_selection_label(model: str | None) -> str:
    if is_auto_model_selection(model):
        return "All (auto)"
    return model or "All (auto)"


def models_to_try_for_profile(
    profile: AIProviderProfile,
    route_model: str | None,
) -> list[str]:
    """Ordered models to attempt for one provider (auto = full available list)."""
    if profile.provider_type == "template_fallback":
        return ["template-v1"]

    if not is_auto_model_selection(route_model):
        fixed = normalize_model_selection(route_model)
        return [fixed] if fixed else [profile.default_model or "gpt-4o-mini"]

    catalog = [m for m in (profile.available_models or []) if isinstance(m, str) and m.strip()]
    if not catalog:
        catalog = default_available_models(profile.provider_type)

    default = (profile.default_model or "").strip()
    ordered: list[str] = []
    if default:
        ordered.append(default)
    for m in catalog:
        m = m.strip()
        if m and m not in ordered:
            ordered.append(m)
    if not ordered:
        ordered = default_available_models(profile.provider_type)
    return ordered
