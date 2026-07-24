"""Rich demo merch catalog + persona fulfillments (local demo only)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.demo.merch_commerce_seed import ensure_catalog_product, seed_merch_commerce_extras
from app.events.models import Event
from app.hosts.models import Host
from app.merch.models import EventMerchProduct
from app.users.models import User

# Event key → product specs (idempotent by product name).
_MERCH_CATALOG: list[tuple[str, list[dict[str, Any]]]] = [
    (
        "afrobeats-night-live",
        [
            {
                "name": "Afrobeats Night Tee",
                "description": "Official event tee — pickup at the merch stand.",
                "product_type": "t_shirt",
                "base_price": Decimal("8500.00"),
                "pickup_location_label": "Merch stand",
                "pickup_instructions": "Collect at the merch stand near the main entrance",
                "variants": [
                    {"label": "S / Black", "size": "S", "color": "Black", "inventory_count": 12},
                    {"label": "M / Black", "size": "M", "color": "Black", "inventory_count": 20},
                    {"label": "L / Black", "size": "L", "color": "Black", "inventory_count": 18},
                    {"label": "XL / Black", "size": "XL", "color": "Black", "inventory_count": 10},
                    {"label": "S / White", "size": "S", "color": "White", "inventory_count": 8},
                    {"label": "M / White", "size": "M", "color": "White", "inventory_count": 15},
                    {"label": "L / White", "size": "L", "color": "White", "inventory_count": 14},
                    {
                        "label": "XL / White",
                        "size": "XL",
                        "color": "White",
                        "inventory_count": 0,
                        "status": "sold_out",
                    },
                ],
            },
            {
                "name": "Neon Cap",
                "description": "Sponsor-branded glow-trim cap for the night.",
                "product_type": "cap",
                "base_price": Decimal("5000.00"),
                "pickup_location_label": "Merch stand",
                "pickup_instructions": "Collect at the merch stand",
                "is_sponsor_branded": True,
                "sponsor_brand_name": "Lagos Beats Co",
                "sponsor_split_type": "percent",
                "sponsor_split_value": Decimal("8"),
                "variants": [
                    {"label": "One size", "inventory_count": 4, "sku": "MAZE-NEON-OS"},
                ],
            },
            {
                "name": "VIP Glow Wristband",
                "description": "Wristband pack for ticket holders.",
                "product_type": "wristband",
                "base_price": Decimal("3000.00"),
                "requires_ticket": True,
                "pickup_location_label": "VIP merch desk",
                "pickup_instructions": "Show your ticket at the VIP merch desk",
                "variants": [{"label": "Pack", "inventory_count": 30}],
            },
            {
                "name": "Backstage Hoodie",
                "description": "Vault-exclusive backstage hoodie — unlock Vault to buy.",
                "product_type": "hoodie",
                "base_price": Decimal("18000.00"),
                "pickup_location_label": "VIP merch desk",
                "pickup_instructions": "Show Vault access + pickup code",
                "is_featured": True,
                "variants": [
                    {"label": "M / Black", "size": "M", "color": "Black", "inventory_count": 10},
                    {"label": "L / Black", "size": "L", "color": "Black", "inventory_count": 10},
                ],
            },
            {
                "name": "Afrobeats Recap Poster",
                "description": "Post-event drop — limited recap poster after the show.",
                "product_type": "souvenir",
                "base_price": Decimal("4500.00"),
                "pickup_location_label": "Merch stand",
                "is_featured": True,
                "variants": [{"label": "A2 print", "inventory_count": 40}],
            },
        ],
    ),
    (
        "lagos-comedy-jam",
        [
            {
                "name": "Comedy Cap",
                "description": "Laugh Lagos night cap.",
                "product_type": "cap",
                "base_price": Decimal("4500.00"),
                "pickup_location_label": "Comedy merch table",
                "variants": [{"label": "One size", "inventory_count": 25}],
            },
            {
                "name": "I Survived The Front Row T-shirt",
                "description": "Front-row survivor tee.",
                "product_type": "t_shirt",
                "base_price": Decimal("7500.00"),
                "pickup_location_label": "Comedy merch table",
                "variants": [
                    {"label": "M", "size": "M", "inventory_count": 12},
                    {"label": "L", "size": "L", "inventory_count": 12},
                    {"label": "XL", "size": "XL", "inventory_count": 8},
                ],
            },
        ],
    ),
    (
        "founders-mixer-lagos",
        [
            {
                "name": "Founder Mode Tote Bag",
                "description": "Canvas tote for builders.",
                "product_type": "tote_bag",
                "base_price": Decimal("6000.00"),
                "pickup_location_label": "Registration desk",
                "variants": [{"label": "One size", "inventory_count": 20}],
            },
            {
                "name": "Product Builder Notebook",
                "description": "Lined notebook with mixer stamp.",
                "product_type": "souvenir",
                "base_price": Decimal("4000.00"),
                "pickup_location_label": "Registration desk",
                "variants": [{"label": "Standard", "inventory_count": 35}],
            },
            {
                "name": "Startup Pack",
                "description": "Sponsor-branded starter pack for founders.",
                "product_type": "souvenir",
                "base_price": Decimal("12000.00"),
                "pickup_location_label": "Registration desk",
                "is_sponsor_branded": True,
                "sponsor_brand_name": "Tech Connect Partners",
                "sponsor_split_type": "percent",
                "sponsor_split_value": Decimal("10"),
                "is_featured": True,
                "variants": [{"label": "Pack", "inventory_count": 15}],
            },
            {
                "name": "Builder Sticker Sheet",
                "description": "Print-on-demand sticker sheet demo item.",
                "product_type": "souvenir",
                "base_price": Decimal("2500.00"),
                "pickup_location_label": "Registration desk",
                "print_on_demand_enabled": True,
                "variants": [
                    {
                        "label": "Sheet",
                        "inventory_count": 100,
                        "print_on_demand_variant_ref": "demo-pod-sticker-sheet",
                    }
                ],
            },
        ],
    ),
    (
        "worship-under-stars",
        [
            {
                "name": "Worship Night Wristband",
                "description": "Soft silicone wristband.",
                "product_type": "wristband",
                "base_price": Decimal("2000.00"),
                "pickup_location_label": "Merch tent",
                "variants": [{"label": "One size", "inventory_count": 50}],
            },
            {
                "name": "Praise Experience Tee",
                "description": "Night-of worship tee with size guide.",
                "product_type": "t_shirt",
                "base_price": Decimal("7000.00"),
                "pickup_location_label": "Merch tent",
                "variants": [
                    {"label": "M", "size": "M", "inventory_count": 15},
                    {"label": "L", "size": "L", "inventory_count": 15},
                    {"label": "XL", "size": "XL", "inventory_count": 10},
                ],
            },
            {
                "name": "Praise Night Recap Pin",
                "description": "Post-event drop — enamel pin after worship night.",
                "product_type": "souvenir",
                "base_price": Decimal("3000.00"),
                "pickup_location_label": "Merch tent",
                "variants": [{"label": "Pin", "inventory_count": 60}],
            },
        ],
    ),
    (
        "food-and-flow",
        [
            {
                "name": "Culture Fest Face Mask",
                "description": "Soft fabric mask with fest print.",
                "product_type": "face_mask",
                "base_price": Decimal("2500.00"),
                "pickup_location_label": "Food court merch",
                "shipping_enabled": True,
                "variants": [{"label": "One size", "inventory_count": 40}],
            },
            {
                "name": "Culture Fest Bucket Hat",
                "description": "Sun-ready bucket hat.",
                "product_type": "cap",
                "base_price": Decimal("6500.00"),
                "pickup_location_label": "Food court merch",
                "shipping_enabled": True,
                "variants": [{"label": "One size", "inventory_count": 18}],
            },
        ],
    ),
]

# Legacy product names → current names (idempotent rename on re-seed).
_PRODUCT_RENAMES: list[tuple[str, str, str]] = [
    ("founders-mixer-lagos", "Founder Mode Tote", "Founder Mode Tote Bag"),
    ("worship-under-stars", "Worship Wristband", "Worship Night Wristband"),
    (
        "lagos-comedy-jam",
        "I Survived The Front Row Tee",
        "I Survived The Front Row T-shirt",
    ),
    ("afrobeats-night-live", "Afterglow Drop Tee", "Afrobeats Recap Poster"),
]


def _rename_legacy_products(db: Session, events: dict[str, Event]) -> None:
    for event_key, old_name, new_name in _PRODUCT_RENAMES:
        event = events.get(event_key)
        if event is None:
            continue
        row = db.scalar(
            select(EventMerchProduct).where(
                EventMerchProduct.event_id == event.id,
                EventMerchProduct.name == old_name,
                EventMerchProduct.archived_at.is_(None),
            )
        )
        if row is None:
            continue
        clash = db.scalar(
            select(EventMerchProduct.id).where(
                EventMerchProduct.event_id == event.id,
                EventMerchProduct.name == new_name,
                EventMerchProduct.archived_at.is_(None),
            )
        )
        if clash is None:
            row.name = new_name
    db.flush()


def seed_demo_merch(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, int]:
    """Idempotent rich merch catalog + marketplace + persona commerce for local demo."""
    from app.demo.guards import assert_demo_ops_allowed
    from app.demo.merch_marketplace_seed import seed_marketplace_merch_catalog

    assert_demo_ops_allowed(operation="demo merch seed")

    created_products = 0

    _rename_legacy_products(db, events)

    # --- Classic event catalog ---
    for event_key, products in _MERCH_CATALOG:
        event = events.get(event_key)
        if event is None:
            continue
        event = db.get(Event, event.id)
        if event is None:
            continue
        host = db.get(Host, event.host_id)
        if host is None:
            continue
        host_owner = db.get(User, host.user_id)
        if host_owner is None:
            continue
        if event_key in {
            "afrobeats-night-live",
            "founders-mixer-lagos",
            "lagos-comedy-jam",
            "food-and-flow",
        }:
            event.allow_merch_only_checkout = True
            db.flush()
        for spec in products:
            if ensure_catalog_product(
                db, host_owner=host_owner, event=event, spec=spec
            ):
                created_products += 1

    db.flush()
    db.commit()  # classic catalog durable

    marketplace = seed_marketplace_merch_catalog(db, users=users, events=events)
    db.commit()

    # Reload events with ticket types for commerce extras / orders.
    loaded: dict[str, Event] = {}
    for key, ev in events.items():
        row = db.scalar(
            select(Event)
            .where(Event.id == ev.id)
            .options(selectinload(Event.ticket_types))
        )
        if row is not None:
            loaded[key] = row

    commerce = seed_merch_commerce_extras(db, users=users, events=loaded)

    db.commit()
    return {
        "products": created_products
        + marketplace.get("standalone_products", 0)
        + marketplace.get("event_marketplace_products", 0),
        "standalone_products": marketplace.get("standalone_products", 0),
        "event_marketplace_products": marketplace.get("event_marketplace_products", 0),
        "hosts_with_shops": marketplace.get("hosts_with_shops", 0),
        "fulfillments": commerce.get("commerce_orders", 0),
        "bundles": commerce.get("bundles", 0),
        "discounts": commerce.get("discounts", 0),
        "abandoned_carts": commerce.get("abandoned_carts", 0),
        "reviews": commerce.get("reviews", 0),
        "notifications": commerce.get("notifications", 0),
    }
