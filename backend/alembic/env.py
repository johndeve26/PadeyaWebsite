"""Alembic migration environment — uses app Settings for DATABASE_URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.audit import AuditLog  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base
from app.auth import models as auth_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.hosts import models as host_models  # noqa: F401
from app.hosts.recommendations import models as host_recommendation_models  # noqa: F401
from app.events.recommendations import models as event_recommendation_models  # noqa: F401
from app.events import models as event_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.tickets import models as ticket_models  # noqa: F401
from app.checkins import models as checkin_models  # noqa: F401
from app.reviews import models as review_models  # noqa: F401
from app.legacy import models as legacy_models  # noqa: F401
from app.promos import models as promo_models  # noqa: F401
from app.crm import models as crm_models  # noqa: F401
from app.finance import models as finance_models  # noqa: F401
from app.finance.fees import models as finance_fee_models  # noqa: F401
from app.vault import models as vault_models  # noqa: F401
from app.passport import models as passport_models  # noqa: F401
from app.memories import models as memories_models  # noqa: F401
from app.merch import models as merch_models  # noqa: F401
from app.messaging import models as messaging_models  # noqa: F401
from app.fan_connect import models as fan_connect_models  # noqa: F401
from app.analytics import models as analytics_models  # noqa: F401
from app.ai import models as ai_models  # noqa: F401
from app.sponsorships import models as sponsorships_models  # noqa: F401
from app.sponsor_profiles.recommendations import models as sponsor_campaign_rec_models  # noqa: F401
from app.tickets import advanced_models as ticket_advanced_models  # noqa: F401
from app.demo import models as demo_models  # noqa: F401
from app.support import models as support_models  # noqa: F401
from app.blog import models as blog_models  # noqa: F401
from app.knowledge_base import models as knowledge_base_models  # noqa: F401
from app.cms import models as cms_models  # noqa: F401
from app.taxonomy import models as taxonomy_models  # noqa: F401
from app.placements import models as placements_models  # noqa: F401
from app.email import models as email_models  # noqa: F401
from app.notifications import models as notifications_models  # noqa: F401
from app.push import models as push_models  # noqa: F401
from app.runtime_settings import models as runtime_settings_models  # noqa: F401
from app.public_media import models as public_media_models  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
