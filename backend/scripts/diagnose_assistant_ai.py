"""Diagnose Ask Pàdéyá / Copilot AI provider routing.

Usage:
  python -m scripts.diagnose_assistant_ai
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.constants import FEATURE_PLATFORM_ASSISTANT_CHAT
from app.ai.feature_routing import (
    complete_for_feature,
    ensure_default_provider_profiles,
    get_or_create_feature_route,
)
from app.ai.feature_toggles import is_feature_enabled
from app.ai.models import AIProviderProfile
from app.ai.providers_admin import _mask_key
from app.ai.runtime_config import resolve_ai_settings
from app.ai.seed import seed_ai_prompt_templates
from app.assistant.constants import MODE_PUBLIC
from app.assistant.prompts import get_system_prompt
from app.core.config import get_settings
from app.core.database import SessionLocal

from app.ai import models as ai_models  # noqa: F401
from app.assistant import models as assistant_models  # noqa: F401


def main() -> int:
    settings = get_settings()
    print("=== Env / settings ===")
    print(f"assistant_enabled={settings.assistant_enabled}")
    print(f"assistant_public_enabled={settings.assistant_public_enabled}")
    print(f"ai_enabled={settings.ai_enabled}")
    print(f"ai_provider={settings.ai_provider}")
    print(f"ai_model={settings.ai_model}")
    print(f"ai_api_key={'set' if (settings.ai_api_key or '').strip() else 'MISSING'}")

    db = SessionLocal()
    try:
        seed_ai_prompt_templates(db)
        ensure_default_provider_profiles(db)
        db.commit()

        runtime = resolve_ai_settings(db)
        print("\n=== Runtime (DB overlay) ===")
        print(f"ai_enabled={runtime.ai_enabled}")
        print(f"ai_provider={runtime.ai_provider}")

        print("\n=== Provider profiles ===")
        for profile in db.query(AIProviderProfile).order_by(AIProviderProfile.priority).all():
            mask = _mask_key(profile)
            print(
                f"- {profile.display_name} ({profile.provider_type}) "
                f"enabled={profile.is_enabled} configured={mask.get('configured')}"
            )

        route = get_or_create_feature_route(db, FEATURE_PLATFORM_ASSISTANT_CHAT)
        db.commit()
        primary = (
            db.get(AIProviderProfile, route.primary_provider_id)
            if route.primary_provider_id
            else None
        )
        print("\n=== platform.assistant.chat route ===")
        print(f"enabled={route.enabled} status={route.status}")
        print(f"primary={getattr(primary, 'display_name', None)}")
        print(f"feature_enabled={is_feature_enabled(FEATURE_PLATFORM_ASSISTANT_CHAT, db=db)}")

        if not settings.assistant_enabled:
            print("\nBLOCKER: ASSISTANT_ENABLED=false")
        if not settings.assistant_public_enabled:
            print("BLOCKER: ASSISTANT_PUBLIC_ENABLED=false (for logged-out chat)")

        print("\n=== Live completion probe ===")
        routed = complete_for_feature(
            db,
            feature_key=FEATURE_PLATFORM_ASSISTANT_CHAT,
            system_prompt=get_system_prompt(MODE_PUBLIC, None),
            user_prompt="Reply with one short sentence confirming you are connected.",
        )
        result = routed.result
        print(f"chain={' -> '.join(routed.chain)}")
        print(f"provider={result.provider} model={result.model_name}")
        print(f"used_fallback={result.used_fallback}")
        if result.error_message:
            print(f"error={result.error_message[:300]}")
        print(f"text={(result.text or '')[:200]}")

        ok = bool(result.text) and not result.used_fallback
        print("\nRESULT:", "CONNECTED" if ok else "FALLBACK / NOT CONNECTED")
        return 0 if ok else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
