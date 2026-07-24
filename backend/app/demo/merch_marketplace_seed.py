"""Marketplace-focused demo merch catalog (standalone, drops, Vault, add-ons).

Local / non-production only. Idempotent by host+name (standalone) or event+name.
Never runs when APP_ENV=production; NODE_ENV=production also blocked unless
DEMO_SEED_ENABLED=true.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.demo.assets import merch_image
from app.demo.guards import assert_demo_ops_allowed
from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.merch.schemas import MerchProductCreate, MerchVariantCreate
from app.merch.service import create_product, create_standalone_product
from app.users.models import User
from app.vault.models import VaultItem

_APPAREL_VARIANTS = [
    {"label": "S / Black", "size": "S", "color": "Black", "inventory_count": 10},
    {"label": "M / Black", "size": "M", "color": "Black", "inventory_count": 18},
    {"label": "L / Black", "size": "L", "color": "Black", "inventory_count": 16},
    {"label": "XL / Black", "size": "XL", "color": "Black", "inventory_count": 8},
    {"label": "S / White", "size": "S", "color": "White", "inventory_count": 8},
    {"label": "M / White", "size": "M", "color": "White", "inventory_count": 14},
    {"label": "L / Green", "size": "L", "color": "Green", "inventory_count": 12},
    {"label": "XL / Green", "size": "XL", "color": "Green", "inventory_count": 6},
]

_CAP_VARIANTS = [
    {"label": "Black", "color": "Black", "inventory_count": 20},
    {"label": "White", "color": "White", "inventory_count": 16},
    {"label": "Green", "color": "Green", "inventory_count": 12},
]

_WRISTBAND_VARIANTS = [
    {"label": "Standard", "inventory_count": 40},
    {"label": "VIP", "inventory_count": 20},
    {"label": "Glow", "inventory_count": 25},
]


def _tee(**extra: Any) -> list[dict[str, Any]]:
    return [{**v, **extra} for v in _APPAREL_VARIANTS]


# host_slug → standalone shop products
_STANDALONE_BY_HOST: dict[str, list[dict[str, Any]]] = {
    "mainlandvibes": [
        {
            "name": "Mainland Vibes Logo Tee",
            "slug_hint": "mainland-vibes-logo-tee",
            "description": "Soft cotton tee with the Mainland Vibes mark — wear the city.",
            "product_type": "t_shirt",
            "category": "apparel",
            "tags": ["standalone", "logo", "lagos"],
            "base_price": Decimal("7500.00"),
            "image_kind": "tee",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "is_featured": True,
            "pickup_enabled": True,
            "shipping_enabled": True,
            "pickup_location_label": "Mainland Vibes studio desk",
            "pickup_instructions": "Collect weekdays 12–6pm with your pickup code",
            "variants": _tee(),
        },
        {
            "name": "Alte Cruise Tote Bag",
            "description": "Heavy canvas tote for island nights and mainland days.",
            "product_type": "tote_bag",
            "category": "accessories",
            "tags": ["standalone", "tote"],
            "base_price": Decimal("5500.00"),
            "image_kind": "tote",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": [{"label": "One size", "inventory_count": 30}],
        },
    ],
    "djmaze": [
        {
            "name": "Island Nights Dad Cap",
            "description": "Low-profile dad cap with embroidered Island Nights wordmark.",
            "product_type": "cap",
            "category": "caps",
            "tags": ["standalone", "cap", "nightlife"],
            "base_price": Decimal("6000.00"),
            "image_kind": "cap",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "is_featured": True,
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": _CAP_VARIANTS,
        },
        {
            "name": "Lagos Nightlife Sticker Pack",
            "description": "Die-cut sticker pack — laptop and phone ready.",
            "product_type": "souvenir",
            "category": "collectibles",
            "tags": ["standalone", "stickers"],
            "base_price": Decimal("2500.00"),
            "image_kind": "sticker",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "pickup_enabled": True,
            "shipping_enabled": True,
            "print_on_demand_enabled": True,
            "variants": [
                {
                    "label": "Pack",
                    "inventory_count": 100,
                    "print_on_demand_variant_ref": "demo-sticker-nightlife",
                }
            ],
        },
        {
            "name": "Exclusive Digital Wallpaper Pack",
            "description": "Vault-ready digital wallpapers for members (demo digital fulfill).",
            "product_type": "souvenir",
            "category": "digital",
            "tags": ["digital", "vault", "wallpaper"],
            "base_price": Decimal("1500.00"),
            "image_kind": "digital",
            "marketplace_kind": "vault_exclusive",
            "storefront_visibility": "vault_exclusive",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_access_type": "paid_vault_member",
            "vault_slug": "unreleased-set",
            "pickup_enabled": False,
            "shipping_enabled": False,
            "print_on_demand_enabled": True,
            "variants": [{"label": "Digital pack", "inventory_count": 9999}],
        },
    ],
    "techconnectafrica": [
        {
            "name": "Campus Rave Hoodie",
            "description": "Heavyweight hoodie for late builders and campus nights.",
            "product_type": "hoodie",
            "category": "apparel",
            "tags": ["standalone", "hoodie", "campus"],
            "base_price": Decimal("16500.00"),
            "image_kind": "hoodie",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "is_featured": True,
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": [
                {"label": "M / Black", "size": "M", "color": "Black", "inventory_count": 3},
                {"label": "L / Black", "size": "L", "color": "Black", "inventory_count": 2},
                {"label": "XL / Green", "size": "XL", "color": "Green", "inventory_count": 4},
            ],
        },
        {
            "name": "Vault Member Hoodie",
            "description": "Members-only Tech Connect Vault hoodie.",
            "product_type": "hoodie",
            "category": "apparel",
            "tags": ["vault", "hoodie"],
            "base_price": Decimal("19000.00"),
            "image_kind": "hoodie",
            "marketplace_kind": "vault_exclusive",
            "storefront_visibility": "vault_exclusive",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_access_type": "paid_vault_member",
            "vault_slug": "founder-deck",
            "pickup_enabled": True,
            "shipping_enabled": False,
            "pickup_location_label": "Tech Connect merch desk",
            "variants": [
                {"label": "M / Black", "size": "M", "color": "Black", "inventory_count": 8},
                {"label": "L / Black", "size": "L", "color": "Black", "inventory_count": 8},
            ],
        },
    ],
    "lagoscomedyhub": [
        {
            "name": "Host Legacy Collector Poster",
            "description": "Vault-exclusive signed-style collector poster (demo).",
            "product_type": "poster",
            "category": "posters",
            "tags": ["vault", "poster", "collector"],
            "base_price": Decimal("8000.00"),
            "image_kind": "poster",
            "marketplace_kind": "vault_exclusive",
            "storefront_visibility": "vault_exclusive",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_access_type": "paid_vault_member",
            "vault_slug": "comedy-early",
            "is_featured": True,
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": [{"label": "A2", "inventory_count": 25}],
        },
        {
            "name": "Comedy Night Mug",
            "description": "Ceramic mug for late punchlines.",
            "product_type": "souvenir",
            "category": "collectibles",
            "tags": ["standalone", "mug"],
            "base_price": Decimal("4500.00"),
            "image_kind": "mug",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": [{"label": "Standard", "inventory_count": 22}],
        },
    ],
    "praiseexperience": [
        {
            "name": "Praise Experience Soft Cap",
            "description": "Everyday soft cap from Praise Experience — host shop staple.",
            "product_type": "cap",
            "category": "caps",
            "tags": ["standalone", "cap"],
            "base_price": Decimal("4800.00"),
            "image_kind": "cap",
            "marketplace_kind": "standalone",
            "storefront_visibility": "host_storefront",
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": _CAP_VARIANTS,
        },
        {
            "name": "Private Listening Party Tee",
            "description": "Vault members tee from the private listening drop.",
            "product_type": "t_shirt",
            "category": "apparel",
            "tags": ["vault", "tee"],
            "base_price": Decimal("9000.00"),
            "image_kind": "tee",
            "marketplace_kind": "vault_exclusive",
            "storefront_visibility": "vault_exclusive",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_access_type": "paid_vault_member",
            "vault_slug": "worship-rehearsal",
            "pickup_enabled": True,
            "shipping_enabled": False,
            "variants": _tee()[:4],
        },
        {
            "name": "Vault Gold Wristband",
            "description": "Gold-finish Vault member wristband.",
            "product_type": "wristband",
            "category": "wristbands",
            "tags": ["vault", "wristband"],
            "base_price": Decimal("3500.00"),
            "image_kind": "wristband",
            "marketplace_kind": "vault_exclusive",
            "storefront_visibility": "vault_exclusive",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_access_type": "paid_vault_member",
            "vault_slug": "worship-rehearsal",
            "pickup_enabled": True,
            "shipping_enabled": False,
            "variants": _WRISTBAND_VARIANTS,
        },
    ],
}

# Additional event-attached products (beyond classic merch_seed catalog)
_EVENT_MARKETPLACE_CATALOG: list[tuple[str, list[dict[str, Any]]]] = [
    (
        "afrobeats-night-live",
        [
            {
                "name": "Glow Wristband Add-on",
                "description": "Checkout add-on glow wristband for ticket holders.",
                "product_type": "wristband",
                "category": "wristbands",
                "tags": ["add-on", "glow"],
                "base_price": Decimal("2800.00"),
                "image_kind": "wristband",
                "marketplace_kind": "event_addon",
                "storefront_visibility": "event_only",
                "requires_ticket": True,
                "show_on_event_page": True,
                "pickup_location_label": "VIP merch desk",
                "variants": _WRISTBAND_VARIANTS,
            },
            {
                "name": "VIP Photo Booth Pass",
                "description": "Add-on pass for the VIP photo booth lane.",
                "product_type": "souvenir",
                "category": "vouchers",
                "tags": ["add-on", "vip"],
                "base_price": Decimal("5000.00"),
                "image_kind": "voucher",
                "marketplace_kind": "event_addon",
                "storefront_visibility": "event_only",
                "requires_ticket": True,
                "requires_vip": True,
                "pickup_location_label": "VIP photo booth",
                "variants": [{"label": "Pass", "inventory_count": 40}],
            },
            {
                "name": "Checked-in Only Event Tee",
                "description": "Post-event drop for checked-in fans only.",
                "product_type": "t_shirt",
                "category": "apparel",
                "tags": ["drop", "checked-in"],
                "base_price": Decimal("8000.00"),
                "image_kind": "tee",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "requires_check_in": True,
                "required_access_type": "checked_in_attendee",
                "post_event_drop_at": "live",
                "is_featured": True,
                "variants": _tee()[:4],
            },
            {
                "name": "Limited Backstage Lanyard",
                "description": "VIP-only post-event lanyard drop.",
                "product_type": "souvenir",
                "category": "accessories",
                "tags": ["drop", "vip", "limited"],
                "base_price": Decimal("4000.00"),
                "image_kind": "lanyard",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "requires_vip": True,
                "required_access_type": "vip_ticket_holder",
                "post_event_drop_at": "live",
                "variants": [
                    {"label": "Lanyard", "inventory_count": 3},  # limited
                ],
            },
            {
                "name": "Sold Out Island Tee",
                "description": "Demo sold-out listing for marketplace badges.",
                "product_type": "t_shirt",
                "category": "apparel",
                "tags": ["sold-out"],
                "base_price": Decimal("7000.00"),
                "image_kind": "tee",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "host_storefront",
                "status": "sold_out",
                "variants": [
                    {
                        "label": "M / Black",
                        "size": "M",
                        "color": "Black",
                        "inventory_count": 0,
                        "status": "sold_out",
                    }
                ],
            },
            {
                "name": "Pickup-Only Stage Cap",
                "description": "Event pickup only — no shipping.",
                "product_type": "cap",
                "category": "caps",
                "tags": ["pickup"],
                "base_price": Decimal("5500.00"),
                "image_kind": "cap",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "event_only",
                "pickup_enabled": True,
                "shipping_enabled": False,
                "pickup_location_label": "Merch stand",
                "pickup_instructions": "Pickup only at the merch stand before midnight",
                "variants": _CAP_VARIANTS,
            },
        ],
    ),
    (
        "detty-friday-live",
        [
            {
                "name": "Detty December Poster",
                "description": "Official Detty December art print.",
                "product_type": "poster",
                "category": "posters",
                "tags": ["event", "poster"],
                "base_price": Decimal("4500.00"),
                "image_kind": "poster",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "event_only",
                "is_featured": True,
                "pickup_location_label": "Detty merch wall",
                "variants": [{"label": "A2", "inventory_count": 35}],
            },
            {
                "name": "Afterparty Access Band",
                "description": "Checkout add-on for afterparty door access.",
                "product_type": "wristband",
                "category": "wristbands",
                "tags": ["add-on", "afterparty"],
                "base_price": Decimal("3500.00"),
                "image_kind": "wristband",
                "marketplace_kind": "event_addon",
                "storefront_visibility": "event_only",
                "requires_ticket": True,
                "variants": _WRISTBAND_VARIANTS,
            },
            {
                "name": "VIP Aftermovie Poster",
                "description": "VIP-only post-event aftermovie poster drop.",
                "product_type": "poster",
                "category": "posters",
                "tags": ["drop", "vip"],
                "base_price": Decimal("6000.00"),
                "image_kind": "poster",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "requires_vip": True,
                "required_access_type": "vip_ticket_holder",
                "post_event_drop_at": "live",
                "variants": [{"label": "A2", "inventory_count": 20}],
            },
        ],
    ),
    (
        "lagos-comedy-jam",
        [
            {
                "name": "Event Face Mask",
                "description": "Soft comedy-night face mask add-on.",
                "product_type": "face_mask",
                "category": "accessories",
                "tags": ["add-on", "mask"],
                "base_price": Decimal("2000.00"),
                "image_kind": "mask",
                "marketplace_kind": "event_addon",
                "storefront_visibility": "event_only",
                "requires_ticket": True,
                "variants": [{"label": "One size", "inventory_count": 50}],
            },
            {
                "name": "Event Crew Cap",
                "description": "Ticket buyers post-event crew cap drop.",
                "product_type": "cap",
                "category": "caps",
                "tags": ["drop", "ticket-buyers"],
                "base_price": Decimal("5000.00"),
                "image_kind": "cap",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "requires_ticket": True,
                "required_access_type": "ticket_holder",
                "post_event_drop_at": "live",
                "variants": _CAP_VARIANTS,
            },
        ],
    ),
    (
        "founders-mixer-lagos",
        [
            {
                "name": "Silent Disco LED Band",
                "description": "LED band for mixer silent-disco corner.",
                "product_type": "wristband",
                "category": "wristbands",
                "tags": ["event", "led"],
                "base_price": Decimal("4200.00"),
                "image_kind": "wristband",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "event_only",
                "is_featured": True,
                "variants": _WRISTBAND_VARIANTS,
            },
            {
                "name": "Fan Memory Photo Pack",
                "description": "Checked-in fans photo pack drop.",
                "product_type": "souvenir",
                "category": "digital",
                "tags": ["drop", "photos"],
                "base_price": Decimal("3000.00"),
                "image_kind": "digital",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "requires_check_in": True,
                "required_access_type": "checked_in_attendee",
                "post_event_drop_at": "live",
                "pickup_enabled": False,
                "shipping_enabled": False,
                "print_on_demand_enabled": True,
                "variants": [{"label": "Digital pack", "inventory_count": 500}],
            },
        ],
    ),
    (
        "food-and-flow",
        [
            {
                "name": "Drink Voucher Bundle",
                "description": "Checkout add-on drink vouchers for food court.",
                "product_type": "vip_pack",
                "category": "vouchers",
                "tags": ["add-on", "voucher"],
                "base_price": Decimal("7000.00"),
                "image_kind": "voucher",
                "marketplace_kind": "event_addon",
                "storefront_visibility": "event_only",
                "requires_ticket": True,
                "variants": [{"label": "3 vouchers", "inventory_count": 60}],
            },
            {
                "name": "Beach Fest Bucket Hat",
                "description": "Sun-ready fest bucket hat with delivery option.",
                "product_type": "cap",
                "category": "caps",
                "tags": ["event", "delivery"],
                "base_price": Decimal("6500.00"),
                "image_kind": "cap",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "host_storefront",
                "pickup_enabled": True,
                "shipping_enabled": True,
                "variants": _CAP_VARIANTS,
            },
            {
                "name": "Delivery Manual Merch Kit",
                "description": "Manual delivery fulfillment demo kit.",
                "product_type": "souvenir",
                "category": "collectibles",
                "tags": ["delivery", "manual"],
                "base_price": Decimal("9000.00"),
                "image_kind": "bundle",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "host_storefront",
                "pickup_enabled": False,
                "shipping_enabled": True,
                "variants": [{"label": "Kit", "inventory_count": 15}],
            },
        ],
    ),
    (
        "mainland-vibes-summer",
        [
            {
                "name": "Afrobeat Night Live Tee",
                "description": "Summer night live tee for Mainland Vibes.",
                "product_type": "t_shirt",
                "category": "apparel",
                "tags": ["event", "tee"],
                "base_price": Decimal("8500.00"),
                "image_kind": "tee",
                "marketplace_kind": "event_merch",
                "storefront_visibility": "event_only",
                "is_featured": True,
                "variants": _tee(),
            },
        ],
    ),
    (
        "worship-under-stars",
        [
            {
                "name": "Vault Members Praise Drop Tee",
                "description": "Vault members-only post-event praise drop.",
                "product_type": "t_shirt",
                "category": "apparel",
                "tags": ["drop", "vault"],
                "base_price": Decimal("7800.00"),
                "image_kind": "tee",
                "marketplace_kind": "post_event_drop",
                "storefront_visibility": "post_event_drop",
                "is_vault_exclusive": True,
                "requires_vault_access": True,
                "required_access_type": "paid_vault_member",
                "vault_slug": "worship-rehearsal",
                "post_event_drop_at": "live",
                "variants": _tee()[:4],
            },
        ],
    ),
]


def _safe(db: Session, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _enable_host_storefront(db: Session, host: Host) -> None:
    profile = db.scalar(select(HostProfile).where(HostProfile.host_id == host.id))
    if profile is None:
        return
    profile.merch_storefront_enabled = True
    if (profile.merch_storefront_visibility or "hidden") == "hidden":
        profile.merch_storefront_visibility = "public"
    if not profile.merch_storefront_title:
        profile.merch_storefront_title = f"{host.display_name} Merch"
    db.flush()


def _resolve_drop_at(value: Any) -> datetime | None:
    if value == "live":
        return datetime.now(UTC) - timedelta(hours=3)
    if value == "soon":
        return datetime.now(UTC) + timedelta(days=2)
    if isinstance(value, datetime):
        return value
    return None


def _find_standalone(db: Session, *, host_id, name: str) -> EventMerchProduct | None:
    return db.scalar(
        select(EventMerchProduct).where(
            EventMerchProduct.host_id == host_id,
            EventMerchProduct.event_id.is_(None),
            EventMerchProduct.name == name,
            EventMerchProduct.archived_at.is_(None),
        )
    )


def _find_event_product(
    db: Session, *, event_id, name: str
) -> EventMerchProduct | None:
    return db.scalar(
        select(EventMerchProduct).where(
            EventMerchProduct.event_id == event_id,
            EventMerchProduct.name == name,
            EventMerchProduct.archived_at.is_(None),
        )
    )


def _apply_marketplace_fields(product: EventMerchProduct, spec: dict[str, Any]) -> None:
    product.category = spec.get("category")
    product.tags = list(spec.get("tags") or [])
    product.marketplace_kind = spec.get("marketplace_kind")
    product.marketplace_listed = bool(spec.get("marketplace_listed", True))
    if spec.get("storefront_visibility"):
        product.storefront_visibility = spec["storefront_visibility"]
    if "is_vault_exclusive" in spec:
        product.is_vault_exclusive = bool(spec["is_vault_exclusive"])
        product.requires_vault_access = bool(
            spec.get("requires_vault_access", spec["is_vault_exclusive"])
        )
    if "requires_ticket" in spec:
        product.requires_ticket = bool(spec["requires_ticket"])
    if "requires_check_in" in spec:
        product.requires_check_in = bool(spec["requires_check_in"])
    if "requires_vip" in spec:
        product.requires_vip = bool(spec["requires_vip"])
    if spec.get("required_access_type"):
        product.required_access_type = spec["required_access_type"]
    drop_at = _resolve_drop_at(spec.get("post_event_drop_at"))
    if drop_at is not None:
        product.post_event_drop_at = drop_at
    if spec.get("image_url"):
        product.image_url = spec["image_url"]
    elif spec.get("image_kind"):
        product.image_url = merch_image(str(spec["image_kind"]))
    if "status" in spec and spec["status"]:
        product.status = spec["status"]
    if "is_featured" in spec:
        product.is_featured = bool(spec["is_featured"])
    if "show_on_event_page" in spec:
        product.show_on_event_page = bool(spec["show_on_event_page"])
    if "pickup_enabled" in spec:
        product.pickup_enabled = bool(spec["pickup_enabled"])
    if "shipping_enabled" in spec:
        product.shipping_enabled = bool(spec["shipping_enabled"])
    if "print_on_demand_enabled" in spec:
        product.print_on_demand_enabled = bool(spec["print_on_demand_enabled"])
    if product.marketplace_kind == "standalone" or product.event_id is None:
        product.is_event_linked = False
        product.is_merch_only_enabled = True


def _link_vault(db: Session, product: EventMerchProduct, spec: dict[str, Any]) -> None:
    slug = spec.get("vault_slug")
    if not slug:
        return
    vault = db.scalar(
        select(VaultItem).where(
            VaultItem.host_id == product.host_id,
            VaultItem.slug == slug,
        )
    )
    if vault is not None:
        product.required_vault_item_id = vault.id


def ensure_standalone_demo_product(
    db: Session,
    *,
    host_owner: User,
    host: Host,
    spec: dict[str, Any],
) -> bool:
    """Create standalone host-shop product when missing."""
    existing = _find_standalone(db, host_id=host.id, name=spec["name"])
    if existing is not None:
        _apply_marketplace_fields(existing, spec)
        _link_vault(db, existing, spec)
        db.flush()
        return False

    image = merch_image(str(spec.get("image_kind") or "apparel"))
    payload = MerchProductCreate(
        name=spec["name"],
        description=spec.get("description"),
        product_type=spec.get("product_type"),
        base_price=spec["base_price"],
        status=spec.get("status") or "active",
        image_url=image,
        cover_image_url=image,
        pickup_instructions=spec.get("pickup_instructions"),
        pickup_location_label=spec.get("pickup_location_label"),
        is_featured=bool(spec.get("is_featured")),
        pickup_enabled=bool(spec.get("pickup_enabled", True)),
        shipping_enabled=bool(spec.get("shipping_enabled", False)),
        print_on_demand_enabled=bool(spec.get("print_on_demand_enabled", False)),
        is_vault_exclusive=bool(spec.get("is_vault_exclusive", False)),
        requires_vault_access=bool(spec.get("requires_vault_access", False)),
        required_access_type=spec.get("required_access_type"),
        storefront_visibility=spec.get("storefront_visibility") or "host_storefront",
        marketplace_kind=spec.get("marketplace_kind") or "standalone",
        category=spec.get("category"),
        tags=list(spec.get("tags") or []),
        marketplace_listed=True,
        variants=[
            MerchVariantCreate(
                label=v["label"],
                size=v.get("size"),
                color=v.get("color"),
                sku=v.get("sku"),
                inventory_count=v["inventory_count"],
                status=v.get("status") or "active",
                print_on_demand_variant_ref=v.get("print_on_demand_variant_ref"),
            )
            for v in spec["variants"]
        ],
    )
    row = _safe(db, create_standalone_product, db, user=host_owner, payload=payload)
    if row is None:
        return False
    product = _find_standalone(db, host_id=host.id, name=spec["name"])
    if product is not None:
        _apply_marketplace_fields(product, {**spec, "image_url": image})
        _link_vault(db, product, spec)
        db.flush()
    return True


def ensure_event_marketplace_product(
    db: Session,
    *,
    host_owner: User,
    event: Event,
    spec: dict[str, Any],
) -> bool:
    existing = _find_event_product(db, event_id=event.id, name=spec["name"])
    if existing is not None:
        _apply_marketplace_fields(existing, spec)
        _link_vault(db, existing, spec)
        db.flush()
        return False

    image = merch_image(str(spec.get("image_kind") or "apparel"))
    payload = MerchProductCreate(
        name=spec["name"],
        description=spec.get("description"),
        product_type=spec.get("product_type"),
        base_price=spec["base_price"],
        status="active" if spec.get("status") != "sold_out" else "active",
        image_url=image,
        cover_image_url=image,
        pickup_instructions=spec.get("pickup_instructions"),
        pickup_location_label=spec.get("pickup_location_label"),
        requires_ticket=bool(spec.get("requires_ticket")),
        show_on_event_page=bool(spec.get("show_on_event_page", True)),
        is_featured=bool(spec.get("is_featured")),
        pickup_enabled=bool(spec.get("pickup_enabled", True)),
        shipping_enabled=bool(spec.get("shipping_enabled", False)),
        print_on_demand_enabled=bool(spec.get("print_on_demand_enabled", False)),
        is_vault_exclusive=bool(spec.get("is_vault_exclusive", False)),
        requires_vault_access=bool(spec.get("requires_vault_access", False)),
        required_access_type=spec.get("required_access_type"),
        requires_check_in=bool(spec.get("requires_check_in")),
        storefront_visibility=spec.get("storefront_visibility") or "event_only",
        post_event_drop_at=_resolve_drop_at(spec.get("post_event_drop_at")),
        marketplace_kind=spec.get("marketplace_kind"),
        category=spec.get("category"),
        tags=list(spec.get("tags") or []),
        marketplace_listed=True,
        variants=[
            MerchVariantCreate(
                label=v["label"],
                size=v.get("size"),
                color=v.get("color"),
                sku=v.get("sku"),
                inventory_count=v["inventory_count"],
                status=v.get("status") or "active",
                print_on_demand_variant_ref=v.get("print_on_demand_variant_ref"),
            )
            for v in spec["variants"]
        ],
    )
    row = _safe(
        db,
        create_product,
        db,
        user=host_owner,
        event_id=event.id,
        payload=payload,
    )
    if row is None:
        return False
    product = _find_event_product(db, event_id=event.id, name=spec["name"])
    if product is not None:
        _apply_marketplace_fields(product, {**spec, "image_url": image})
        _link_vault(db, product, spec)
        if spec.get("status") == "sold_out":
            product.status = "sold_out"
            for v in product.variants or []:
                v.inventory_count = 0
                v.status = "sold_out"
        db.flush()
    return True


def seed_marketplace_merch_catalog(
    db: Session,
    *,
    users: dict[str, User],
    events: dict[str, Event],
) -> dict[str, int]:
    """Seed standalone + extended event marketplace merch. Idempotent."""
    assert_demo_ops_allowed(operation="demo merch marketplace seed")

    created_standalone = 0
    created_event = 0
    hosts_touched: set[str] = set()

    # Standalone shops
    for host_slug, products in _STANDALONE_BY_HOST.items():
        host = db.scalar(select(Host).where(Host.slug == host_slug))
        if host is None:
            continue
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        _enable_host_storefront(db, host)
        hosts_touched.add(host_slug)
        for spec in products:
            if ensure_standalone_demo_product(
                db, host_owner=owner, host=host, spec=spec
            ):
                created_standalone += 1

    # Event marketplace extras
    for event_key, products in _EVENT_MARKETPLACE_CATALOG:
        event = events.get(event_key)
        if event is None:
            continue
        event = db.get(Event, event.id)
        if event is None:
            continue
        host = db.get(Host, event.host_id)
        if host is None:
            continue
        owner = db.get(User, host.user_id)
        if owner is None:
            continue
        _enable_host_storefront(db, host)
        if event_key in {
            "afrobeats-night-live",
            "detty-friday-live",
            "lagos-comedy-jam",
            "founders-mixer-lagos",
            "food-and-flow",
            "mainland-vibes-summer",
        }:
            event.allow_merch_only_checkout = True
        for spec in products:
            if ensure_event_marketplace_product(
                db, host_owner=owner, event=event, spec=spec
            ):
                created_event += 1

    # Backfill marketplace fields + images on classic catalog products
    for product in db.scalars(
        select(EventMerchProduct)
        .where(EventMerchProduct.archived_at.is_(None))
        .options(selectinload(EventMerchProduct.variants))
    ).all():
        if not product.image_url:
            kind = {
                "t_shirt": "tee",
                "hoodie": "hoodie",
                "cap": "cap",
                "tote_bag": "tote",
                "wristband": "wristband",
                "poster": "poster",
                "face_mask": "mask",
                "souvenir": "sticker",
            }.get(product.product_type or "", "apparel")
            product.image_url = merch_image(kind)
        if not product.marketplace_kind:
            if product.is_vault_exclusive:
                product.marketplace_kind = "vault_exclusive"
            elif product.storefront_visibility == "post_event_drop":
                product.marketplace_kind = "post_event_drop"
            elif not product.is_event_linked or product.event_id is None:
                product.marketplace_kind = "standalone"
            elif product.requires_ticket:
                product.marketplace_kind = "event_addon"
            else:
                product.marketplace_kind = "event_merch"
        if not product.category:
            product.category = {
                "t_shirt": "apparel",
                "hoodie": "apparel",
                "cap": "caps",
                "wristband": "wristbands",
                "poster": "posters",
                "face_mask": "accessories",
                "tote_bag": "accessories",
                "vip_pack": "vouchers",
                "souvenir": "collectibles",
            }.get(product.product_type or "", "other")
        product.marketplace_listed = True

    db.flush()
    return {
        "standalone_products": created_standalone,
        "event_marketplace_products": created_event,
        "hosts_with_shops": len(hosts_touched),
    }
