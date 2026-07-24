"""Clear demo-scoped data only (idempotent-safe)."""

from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.demo.constants import DEMO_EMAIL_DOMAIN, DEMO_EVENT_SLUG_PREFIX, HOST_SLUGS
from app.demo.guards import assert_demo_ops_allowed
from app.demo.models import DemoEntityMarker, DemoSupportCase
from app.events.models import Event
from app.hosts.models import Host
from app.merch.models import (
    EventMerchProduct,
    MerchBundle,
    MerchCart,
    MerchDiscountCode,
    MerchShippingZone,
    MerchSizeChart,
)
from app.payments.models import Order
from app.promos.models import Ambassador, PromoCode
from app.tickets.models import Ticket
from app.users.models import User


def reset_demo_data(db: Session) -> dict[str, int]:
    """Delete demo users/hosts/events/markers. Does not touch non-demo rows."""
    assert_demo_ops_allowed(operation="demo reset")

    counts = {
        "tickets": 0,
        "orders": 0,
        "merch_bundles": 0,
        "merch_products": 0,
        "merch_carts": 0,
        "merch_discounts": 0,
        "merch_zones": 0,
        "merch_size_charts": 0,
        "events": 0,
        "promos": 0,
        "ambassadors": 0,
        "hosts": 0,
        "users": 0,
        "support_cases": 0,
        "markers": 0,
    }

    host_ids = list(
        db.scalars(select(Host.id).where(Host.slug.in_(HOST_SLUGS))).all()
    )
    event_filters = [Event.slug.startswith(DEMO_EVENT_SLUG_PREFIX)]
    if host_ids:
        event_filters.append(Event.host_id.in_(host_ids))
    event_ids = list(db.scalars(select(Event.id).where(or_(*event_filters))).all())

    # Tickets RESTRICT ticket_types — remove dependents before events/ticket_types.
    # Merch bundles also RESTRICT ticket_types; carts/products block clean event delete.
    if event_ids:
        tickets = list(
            db.scalars(select(Ticket).where(Ticket.event_id.in_(event_ids))).all()
        )
        for ticket in tickets:
            db.delete(ticket)
            counts["tickets"] += 1
        db.flush()

        orders = list(
            db.scalars(select(Order).where(Order.event_id.in_(event_ids))).all()
        )
        for order in orders:
            db.delete(order)
            counts["orders"] += 1
        db.flush()

        bundles = list(
            db.scalars(
                select(MerchBundle).where(MerchBundle.event_id.in_(event_ids))
            ).all()
        )
        for bundle in bundles:
            db.delete(bundle)
            counts["merch_bundles"] += 1
        db.flush()

        carts = list(
            db.scalars(select(MerchCart).where(MerchCart.event_id.in_(event_ids))).all()
        )
        for cart in carts:
            db.delete(cart)
            counts["merch_carts"] += 1
        db.flush()

        products = list(
            db.scalars(
                select(EventMerchProduct).where(
                    EventMerchProduct.event_id.in_(event_ids)
                )
            ).all()
        )
        for product in products:
            db.delete(product)
            counts["merch_products"] += 1
        db.flush()

        events = list(db.scalars(select(Event).where(Event.id.in_(event_ids))).all())
        for event in events:
            db.delete(event)
            counts["events"] += 1
        db.flush()

    if host_ids:
        for row in db.scalars(
            select(MerchDiscountCode).where(MerchDiscountCode.host_id.in_(host_ids))
        ).all():
            db.delete(row)
            counts["merch_discounts"] += 1
        for row in db.scalars(
            select(MerchShippingZone).where(MerchShippingZone.host_id.in_(host_ids))
        ).all():
            db.delete(row)
            counts["merch_zones"] += 1
        for row in db.scalars(
            select(MerchSizeChart).where(MerchSizeChart.host_id.in_(host_ids))
        ).all():
            db.delete(row)
            counts["merch_size_charts"] += 1
        # Evergreen / host-scoped merch (event_id null) still owned by demo hosts.
        for row in db.scalars(
            select(EventMerchProduct).where(
                EventMerchProduct.host_id.in_(host_ids),
                EventMerchProduct.event_id.is_(None),
            )
        ).all():
            db.delete(row)
            counts["merch_products"] += 1
        db.flush()

    if host_ids:
        promos = list(
            db.scalars(select(PromoCode).where(PromoCode.host_id.in_(host_ids))).all()
        )
        for promo in promos:
            db.delete(promo)
            counts["promos"] += 1
        ambs = list(
            db.scalars(select(Ambassador).where(Ambassador.host_id.in_(host_ids))).all()
        )
        for amb in ambs:
            db.delete(amb)
            counts["ambassadors"] += 1
        db.flush()

        hosts = list(db.scalars(select(Host).where(Host.id.in_(host_ids))).all())
        for host in hosts:
            db.delete(host)
            counts["hosts"] += 1
        db.flush()

    users = list(
        db.scalars(select(User).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))).all()
    )
    for user in users:
        db.delete(user)
        counts["users"] += 1
    db.flush()

    cases = list(db.scalars(select(DemoSupportCase)).all())
    for case in cases:
        db.delete(case)
        counts["support_cases"] += 1

    markers = db.execute(delete(DemoEntityMarker))
    counts["markers"] = markers.rowcount or 0

    db.commit()
    return counts
