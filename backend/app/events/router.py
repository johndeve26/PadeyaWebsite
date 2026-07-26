"""Event API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user_optional, require_permission
from app.core.database import get_db
from app.events import templates_service
from app.events.rate_limit import rate_limit_map_events, rate_limit_nearby_events
from app.events.schemas import (
    CalendarMonthResponse,
    EventCategoryCreate,
    EventCategoryPublic,
    EventCategoryUpdate,
    EventClearFlagRequest,
    EventCreate,
    EventFlagRequest,
    EventMediaCreate,
    EventPostponeRequest,
    EventPublic,
    EventRejectRequest,
    EventTemplateCreate,
    EventTemplatePublic,
    EventTemplateUpdate,
    EventUpdate,
    MapEventCompact,
    MapEventsResponse,
    MediaUploadPublic,
    MessageResponse,
    NearbyEventsResponse,
    TicketTypeCreate,
    TicketTypePublic,
    TicketTypeUpdate,
)
from app.events.service import (
    add_event_media,
    approve_event,
    auto_complete_due_events,
    cancel_event,
    clear_event_flag,
    create_category,
    create_event,
    create_ticket_type,
    deactivate_category,
    deactivate_ticket_type,
    delete_ticket_type,
    discard_event,
    flag_event,
    get_event_by_id,
    list_admin_categories,
    list_admin_events,
    list_categories,
    list_host_events,
    list_pending_events,
    list_published_events,
    list_ticket_types,
    archive_event,
    delete_event_media,
    pause_event,
    postpone_event,
    public_event_detail,
    reject_event,
    resolve_event_access,
    restore_archived_event,
    restore_category,
    resume_event,
    serialize_event,
    set_event_featured,
    submit_event_for_review,
    update_category,
    update_event,
    update_ticket_type,
    upload_event_media_file,
    upload_host_media_file,
)
from app.hosts.service import get_host_by_user_id, require_user_host
from app.events.recommendations.router import router as event_recommendations_router
from app.users.models import User
from app.users.service import user_has_role

router = APIRouter(prefix="/events", tags=["events"])
router.include_router(event_recommendations_router)


def _to_public(event, *, access: str = "host") -> EventPublic:
    return EventPublic.model_validate(
        serialize_event(event, access=access, include_checklist=access in {"host", "admin"})
    )


def _can_see_all_tickets(db: Session, user: User, event) -> bool:
    if user_has_role(user, "super_admin"):
        return True
    host = get_host_by_user_id(db, user.id)
    return host is not None and host.id == event.host_id


@router.get("/health")
async def events_module_health() -> dict[str, str]:
    return {"module": "events", "status": "ok"}


@router.get("/categories", response_model=list[EventCategoryPublic])
def get_categories(db: Annotated[Session, Depends(get_db)]) -> list[EventCategoryPublic]:
    from app.events.public_cache import TTL, cached_public, events_categories_key

    def _produce() -> list[dict]:
        return [
            EventCategoryPublic.model_validate(c).model_dump(mode="json")
            for c in list_categories(db)
        ]

    cached = cached_public(events_categories_key(), TTL.taxonomy, _produce)
    return [EventCategoryPublic.model_validate(row) for row in cached]


@router.get(
    "/admin/categories",
    response_model=list[EventCategoryPublic],
    dependencies=[Depends(require_permission("admin.full_access"))],
)
def admin_get_categories(
    db: Annotated[Session, Depends(get_db)],
    include_inactive: bool = False,
) -> list[EventCategoryPublic]:
    return [
        EventCategoryPublic.model_validate(c)
        for c in list_admin_categories(db, include_inactive=include_inactive)
    ]


@router.post(
    "/admin/categories",
    response_model=EventCategoryPublic,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_category(
    payload: EventCategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventCategoryPublic:
    row = create_category(
        db,
        user=user,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    return EventCategoryPublic.model_validate(row)


@router.patch("/admin/categories/{category_id}", response_model=EventCategoryPublic)
def admin_update_category(
    category_id: UUID,
    payload: EventCategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventCategoryPublic:
    row = update_category(
        db,
        user=user,
        category_id=category_id,
        name=payload.name,
        description=payload.description,
    )
    return EventCategoryPublic.model_validate(row)


@router.post(
    "/admin/categories/{category_id}/deactivate",
    response_model=EventCategoryPublic,
)
def admin_deactivate_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventCategoryPublic:
    return EventCategoryPublic.model_validate(
        deactivate_category(db, user=user, category_id=category_id)
    )


@router.post(
    "/admin/categories/{category_id}/restore",
    response_model=EventCategoryPublic,
)
def admin_restore_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventCategoryPublic:
    return EventCategoryPublic.model_validate(
        restore_category(db, user=user, category_id=category_id)
    )


@router.post("/admin/{event_id}/feature", response_model=EventPublic)
def admin_feature_event(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventPublic:
    return _to_public(
        set_event_featured(db, user=user, event_id=event_id, featured=True),
        access="admin",
    )


@router.post("/admin/{event_id}/unfeature", response_model=EventPublic)
def admin_unfeature_event(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventPublic:
    return _to_public(
        set_event_featured(db, user=user, event_id=event_id, featured=False),
        access="admin",
    )


@router.post("/admin/{event_id}/padeya-pick", response_model=EventPublic)
def admin_set_padeya_pick(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access", "events.approve"))],
    context_type: Annotated[str, Query()] = "homepage",
    slot_number: Annotated[int | None, Query(ge=1, le=2)] = None,
) -> EventPublic:
    """Assign this listing into a global Pàdéyá Pick slot (homepage by default)."""
    from app.placements import service as placements_service

    placements_service.set_event_as_padeya_pick(
        db,
        user=user,
        event_id=event_id,
        context_type=context_type,
        slot_number=slot_number,
    )
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_public(event, access="admin")


@router.post("/admin/{event_id}/unpadeya-pick", response_model=EventPublic)
def admin_clear_padeya_pick(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access", "events.approve"))],
    context_type: Annotated[str, Query()] = "homepage",
) -> EventPublic:
    """Remove this listing from global Pàdéyá Pick slots."""
    from app.placements import service as placements_service

    placements_service.clear_event_padeya_pick(
        db,
        user=user,
        event_id=event_id,
        context_type=context_type,
    )
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_public(event, access="admin")


@router.post("/admin/{event_id}/regeocode", response_model=EventPublic)
def admin_regeocode_event(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("admin.full_access"))],
) -> EventPublic:
    """Re-geocode event address via Google (server key). Fills missing lat/lng."""
    from app.core.audit import write_audit_log
    from app.events.geocode import geocode_address
    from app.events.models import Event

    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    query = (
        event.formatted_address
        or event.address
        or ", ".join(
            p
            for p in (
                event.venue_name,
                event.area,
                event.city,
                event.state,
                event.country,
            )
            if p
        )
    )
    result = geocode_address(query, db=db)
    event.latitude = result["latitude"]
    event.longitude = result["longitude"]
    if result.get("formatted_address"):
        event.formatted_address = result["formatted_address"]
        if not event.address:
            event.address = result["formatted_address"]
    if result.get("place_id"):
        event.google_place_id = result["place_id"]
    if result.get("city") and not event.city:
        event.city = result["city"]
    if result.get("state") and not event.state:
        event.state = result["state"]
    if result.get("country") and not event.country:
        event.country = result["country"]
    if result.get("area") and not event.area:
        event.area = result["area"]
    if result.get("postcode") and not event.postcode:
        event.postcode = result["postcode"]
    write_audit_log(
        db,
        action="event.regeocode",
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event.id),
        details={"place_id": result.get("place_id")},
    )
    db.commit()
    db.refresh(event)
    return _to_public(event, access="admin")


# --- Event templates (host) ---


@router.get("/templates", response_model=list[EventTemplatePublic])
def list_event_templates(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    include_archived: bool = False,
) -> list[EventTemplatePublic]:
    rows = templates_service.list_templates(
        db, user=user, include_archived=include_archived
    )
    return [EventTemplatePublic.model_validate(r) for r in rows]


@router.post(
    "/templates",
    response_model=EventTemplatePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_event_template(
    payload: EventTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventTemplatePublic:
    row = templates_service.create_template(
        db,
        user=user,
        name=payload.name,
        description=payload.description,
        payload=payload.payload,
    )
    return EventTemplatePublic.model_validate(row)


@router.get("/templates/{template_id}", response_model=EventTemplatePublic)
def get_event_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventTemplatePublic:
    return EventTemplatePublic.model_validate(
        templates_service.get_template(db, user=user, template_id=template_id)
    )


@router.patch("/templates/{template_id}", response_model=EventTemplatePublic)
def patch_event_template(
    template_id: UUID,
    payload: EventTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventTemplatePublic:
    data = payload.model_dump(exclude_unset=True)
    return EventTemplatePublic.model_validate(
        templates_service.update_template(
            db, user=user, template_id=template_id, **data
        )
    )


@router.delete(
    "/templates/{template_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED
)
def delete_event_template() -> None:
    templates_service.delete_template_blocked()


@router.post("/templates/{template_id}/archive", response_model=EventTemplatePublic)
def archive_event_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventTemplatePublic:
    return EventTemplatePublic.model_validate(
        templates_service.archive_template(db, user=user, template_id=template_id)
    )


@router.post("/templates/{template_id}/restore", response_model=EventTemplatePublic)
def restore_event_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventTemplatePublic:
    return EventTemplatePublic.model_validate(
        templates_service.restore_template(db, user=user, template_id=template_id)
    )


@router.get("", response_model=list[EventPublic])
def list_public_events(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    category: str | None = None,
    city: str | None = None,
    location_kind: str | None = None,
    location_slug: str | None = None,
    weekend: bool = False,
    paid: str | None = None,
    sort: str | None = None,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> list[EventPublic]:
    """Public marketplace LIST — lean payload, SQL filters/order/limit."""
    from app.events.public_cache import TTL, cached_public, events_list_key
    from app.events.service import (
        PUBLIC_EVENTS_LIST_MAX,
        serialize_event_list_item,
    )

    effective_limit = limit or PUBLIC_EVENTS_LIST_MAX
    key = events_list_key(
        q=q,
        category=category,
        city=city,
        location_kind=location_kind,
        location_slug=location_slug,
        weekend=weekend,
        paid=paid,
        sort=sort,
        limit=effective_limit,
        v="listv2",
    )

    def _produce() -> list[dict]:
        result = []
        for event in list_published_events(
            db,
            q=q,
            category_slug=category,
            city_slug=city,
            location_kind=location_kind,
            location_slug=location_slug,
            weekend=weekend,
            paid=paid,
            sort=sort,
            limit=effective_limit,
        ):
            data = serialize_event_list_item(event)
            data["ticket_types"] = [
                TicketTypePublic.model_validate(tt).model_copy(
                    update={"access_code": None}
                )
                for tt in data["ticket_types"]
            ]
            result.append(EventPublic.model_validate(data).model_dump(mode="json"))
        return result

    cached = cached_public(key, TTL.list, _produce)
    return [EventPublic.model_validate(row) for row in cached]


@router.get("/padeya-picks", response_model=list[EventPublic])
def public_padeya_picks(
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[str | None, Query()] = None,
    location_kind: Annotated[str | None, Query()] = None,
    location_slug: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
) -> list[EventPublic]:
    """Editorial Pàdéyá Picks — Primary/Secondary Spotlight for a discovery context."""
    from app.events.public_cache import TTL, cached_public, events_picks_key
    from app.placements import service as placements_service

    key = events_picks_key(
        context=context,
        location_kind=location_kind,
        location_slug=location_slug,
        category=category,
    )

    def _produce() -> list[dict]:
        (
            context_type,
            location_id,
            category_id,
            _title,
            _loc_name,
            _cat_name,
        ) = placements_service.resolve_public_context(
            db,
            context_type=context,
            location_kind=location_kind,
            location_slug=location_slug,
            category_slug=category,
        )
        result: list[dict] = []
        for event in placements_service.list_padeya_picks(
            db,
            context_type=context_type,
            location_id=location_id,
            category_id=category_id,
        ):
            result.append(_to_public(event, access="public").model_dump(mode="json"))
        return result

    cached = cached_public(key, TTL.featured, _produce)
    return [EventPublic.model_validate(row) for row in cached]


@router.get(
    "/nearby",
    response_model=NearbyEventsResponse,
    dependencies=[Depends(rate_limit_nearby_events)],
)
def list_nearby_events_route(
    db: Annotated[Session, Depends(get_db)],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_km: Annotated[int, Query()] = 25,
    category: Annotated[str | None, Query()] = None,
    date: Annotated[str | None, Query(description="YYYY-MM-DD")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    page: Annotated[int, Query(ge=1)] = 1,
    location_label: Annotated[str | None, Query()] = None,
) -> NearbyEventsResponse:
    """Rank published events by privacy-safe distance from a user point."""
    from datetime import date as date_cls

    from app.events.geo import (
        format_distance_km,
        list_nearby_events,
        location_label_for_nearby,
        normalize_radius_km,
    )
    from app.events.public_cache import TTL, cached_public, events_nearby_key
    from app.events.service import serialize_event

    on_date = None
    if date:
        try:
            on_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="date must be YYYY-MM-DD"
            ) from exc

    radius = normalize_radius_km(radius_km)
    # Cache by bucketed GPS only — never key Redis on exact browser coords.
    # Ranking inside the producer still uses the request lat/lng for accuracy.
    from app.events.geo import bucket_lat_lng

    echo_lat, echo_lng = bucket_lat_lng(lat, lng)
    key = events_nearby_key(
        lat=lat,
        lng=lng,
        radius_km=radius,
        category=category,
        date=date,
        limit=limit,
        page=page,
    )

    def _produce() -> dict:
        scored, total = list_nearby_events(
            db,
            lat=lat,
            lng=lng,
            radius_km=radius,
            category_slug=category,
            on_date=on_date,
            limit=limit,
            page=page,
        )
        items: list[dict] = []
        for event, dist, mode in scored:
            data = serialize_event(event, access="public")
            data["ticket_types"] = [
                TicketTypePublic.model_validate(tt).model_copy(update={"access_code": None})
                for tt in event.ticket_types
                if tt.visibility == "public"
            ]
            approx = mode == "approximate"
            rounded = round(dist, 1 if dist < 10 else 0)
            data["distance_km"] = rounded
            data["distance_is_approximate"] = approx
            data["distance_label"] = format_distance_km(dist, approximate=approx)
            label = location_label_for_nearby(event)
            if label:
                data["public_location_label"] = data.get("public_location_label") or label
            items.append(EventPublic.model_validate(data).model_dump(mode="json"))

        return NearbyEventsResponse(
            items=[EventPublic.model_validate(i) for i in items],
            total=total,
            page=page,
            limit=limit,
            radius_km=radius,
            # Echo bucketed coords only — do not leak precise GPS in responses.
            lat=echo_lat,
            lng=echo_lng,
            location_label=location_label,
        ).model_dump(mode="json")

    # Short TTL (60–180s) — capacity-sensitive; purchases also invalidate.
    cached = cached_public(key, TTL.availability, _produce)
    return NearbyEventsResponse.model_validate(cached)


@router.get(
    "/map",
    response_model=MapEventsResponse,
    dependencies=[Depends(rate_limit_map_events)],
)
def list_map_events_route(
    db: Annotated[Session, Depends(get_db)],
    north: Annotated[float, Query()],
    south: Annotated[float, Query()],
    east: Annotated[float, Query()],
    west: Annotated[float, Query()],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=500)] = None,
    city: Annotated[str | None, Query()] = None,
    area: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    date: Annotated[str | None, Query(description="YYYY-MM-DD")] = None,
    price: Annotated[str | None, Query(description="any|free|paid")] = None,
    host: Annotated[UUID | None, Query(description="Host profile id")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> MapEventsResponse:
    """Compact, privacy-safe event pins for the current map viewport."""
    from datetime import date as date_cls

    from app.events.map_service import list_map_events
    from app.events.public_cache import TTL, cached_public, events_map_key

    on_date = None
    if date:
        try:
            on_date = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="date must be YYYY-MM-DD"
            ) from exc

    price_filter = (price or "any").strip().lower()
    if price_filter not in {"any", "free", "paid"}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="price must be one of: any, free, paid",
        )

    key = events_map_key(
        north=north,
        south=south,
        east=east,
        west=west,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        city=city,
        area=area,
        category=category,
        date=date,
        price=price_filter,
        host=str(host) if host else None,
        limit=limit,
    )

    def _produce() -> dict:
        items, total = list_map_events(
            db,
            north=north,
            south=south,
            east=east,
            west=west,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            city=city,
            area=area,
            category_slug=category,
            on_date=on_date,
            price=price_filter,  # type: ignore[arg-type]
            host_id=host,
            limit=limit,
        )
        return MapEventsResponse(
            items=[MapEventCompact.model_validate(row) for row in items],
            total=total,
            north=north,
            south=south,
            east=east,
            west=west,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        ).model_dump(mode="json")

    cached = cached_public(key, TTL.calendar_map, _produce)
    return MapEventsResponse.model_validate(cached)


@router.get("/calendar", response_model=CalendarMonthResponse)
def get_events_calendar(
    db: Annotated[Session, Depends(get_db)],
    month: Annotated[str, Query(description="YYYY-MM")],
    category: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    location_kind: Annotated[str | None, Query()] = None,
    location_slug: Annotated[str | None, Query()] = None,
    paid: Annotated[str | None, Query()] = None,
    host: Annotated[UUID | None, Query(description="Host profile id")] = None,
    include_featured: Annotated[bool, Query()] = True,
) -> CalendarMonthResponse:
    """Month-grouped published events for calendar discovery."""
    from app.events.calendar_service import list_calendar_month, parse_month
    from app.events.public_cache import TTL, cached_public, events_calendar_key

    try:
        parse_month(month)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="month must be YYYY-MM",
        ) from exc

    key = events_calendar_key(
        month=month,
        category=category,
        city=city,
        location_kind=location_kind,
        location_slug=location_slug,
        paid=paid,
        host=str(host) if host else None,
        include_featured=include_featured,
    )

    def _produce() -> dict:
        payload = list_calendar_month(
            db,
            month=month,
            category_slug=category,
            city_slug=city,
            location_kind=location_kind,
            location_slug=location_slug,
            paid=paid,
            host_id=host,
            include_featured=include_featured,
        )
        return CalendarMonthResponse.model_validate(payload).model_dump(mode="json")

    cached = cached_public(key, TTL.calendar_map, _produce)
    return CalendarMonthResponse.model_validate(cached)


@router.get("/mine", response_model=list[EventPublic])
def list_my_events(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[EventPublic]:
    host = require_user_host(db, user)
    return [_to_public(e, access="host") for e in list_host_events(db, host)]


@router.get("/admin/all", response_model=list[EventPublic])
def admin_list_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> list[EventPublic]:
    _ = user
    return [_to_public(e, access="admin") for e in list_admin_events(db)]


@router.get("/admin/pending", response_model=list[EventPublic])
def admin_pending_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> list[EventPublic]:
    _ = user
    return [_to_public(e, access="admin") for e in list_pending_events(db)]


@router.post("", response_model=EventPublic, status_code=status.HTTP_201_CREATED)
def create(
    payload: EventCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(create_event(db, user=user, payload=payload), access="host")


@router.get("/by-id/{event_id}", response_model=EventPublic)
def get_by_id(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    auto_complete_due_events(db, event_id=event_id)
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    access = resolve_event_access(db, event, user)
    if access not in {"host", "admin"}:
        if event.status != "published":
            raise HTTPException(status_code=404, detail="Event not found")
    return _to_public(event, access=access)


@router.patch("/by-id/{event_id}", response_model=EventPublic)
def patch_event(
    event_id: UUID,
    payload: EventUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(
        update_event(db, user=user, event_id=event_id, payload=payload),
        access="host",
    )


@router.post("/by-id/{event_id}/submit", response_model=EventPublic)
def submit(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(
        submit_event_for_review(db, user=user, event_id=event_id),
        access="host",
    )


@router.post("/by-id/{event_id}/approve", response_model=EventPublic)
def approve(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> EventPublic:
    return _to_public(approve_event(db, user=user, event_id=event_id), access="admin")


@router.post("/by-id/{event_id}/reject", response_model=EventPublic)
def reject(
    event_id: UUID,
    payload: EventRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> EventPublic:
    return _to_public(
        reject_event(db, user=user, event_id=event_id, payload=payload),
        access="admin",
    )


@router.post("/by-id/{event_id}/flag", response_model=EventPublic)
def flag(
    event_id: UUID,
    payload: EventFlagRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> EventPublic:
    return _to_public(
        flag_event(db, user=user, event_id=event_id, reason=payload.reason),
        access="admin",
    )


@router.post("/by-id/{event_id}/clear-flag", response_model=EventPublic)
def clear_flag(
    event_id: UUID,
    payload: EventClearFlagRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("events.approve", "admin.full_access"))],
) -> EventPublic:
    return _to_public(
        clear_event_flag(
            db, user=user, event_id=event_id, reason=payload.reason
        ),
        access="admin",
    )


@router.post("/by-id/{event_id}/complete", response_model=EventPublic)
def complete(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    """Mark event completed and recalculate host Legacy score/tier."""
    from app.legacy.service import complete_event_and_recalc

    return _to_public(
        complete_event_and_recalc(db, user=user, event_id=event_id),
        access="host",
    )


@router.post("/by-id/{event_id}/pause", response_model=EventPublic)
def pause(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(pause_event(db, user=user, event_id=event_id), access="host")


@router.post("/by-id/{event_id}/resume", response_model=EventPublic)
def resume(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(resume_event(db, user=user, event_id=event_id), access="host")


@router.post("/by-id/{event_id}/postpone", response_model=EventPublic)
def postpone(
    event_id: UUID,
    payload: EventPostponeRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    """Reschedule dates for a published/paused event without re-review."""
    return _to_public(
        postpone_event(
            db,
            user=user,
            event_id=event_id,
            start_datetime=payload.start_datetime,
            end_datetime=payload.end_datetime,
        ),
        access="host",
    )


@router.post("/by-id/{event_id}/cancel", response_model=EventPublic)
def cancel(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(cancel_event(db, user=user, event_id=event_id), access="host")


@router.post("/by-id/{event_id}/archive", response_model=EventPublic)
def archive(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(archive_event(db, user=user, event_id=event_id), access="host")


@router.post("/by-id/{event_id}/restore", response_model=EventPublic)
def restore(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    """Restore an archived event (draft if unused, cancelled if it had sales)."""
    return _to_public(
        restore_archived_event(db, user=user, event_id=event_id),
        access="host",
    )


@router.delete("/by-id/{event_id}", response_model=MessageResponse)
def discard(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    discard_event(db, user=user, event_id=event_id)
    return MessageResponse(message="Event discarded")


@router.post("/media/upload", response_model=MediaUploadPublic)
async def upload_staging_media(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
    media_type: Annotated[str, Form()] = "gallery",
) -> MediaUploadPublic:
    """Upload an image before/while creating an event. Returns a public URL."""
    data = await file.read()
    result = upload_host_media_file(
        db,
        user=user,
        data=data,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type or "application/octet-stream",
        media_type=media_type,
    )
    return MediaUploadPublic.model_validate(result)


@router.post("/by-id/{event_id}/media", response_model=EventPublic)
def upload_media(
    event_id: UUID,
    payload: EventMediaCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(
        add_event_media(db, user=user, event_id=event_id, payload=payload),
        access="host",
    )


@router.post("/by-id/{event_id}/media/upload", response_model=EventPublic)
async def upload_event_media(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    file: Annotated[UploadFile, File(...)],
    media_type: Annotated[str, Form()] = "gallery",
    alt_text: Annotated[str | None, Form()] = None,
    set_as_banner: Annotated[bool, Form()] = False,
) -> EventPublic:
    data = await file.read()
    event = upload_event_media_file(
        db,
        user=user,
        event_id=event_id,
        data=data,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type or "application/octet-stream",
        media_type=media_type,
        alt_text=alt_text,
        set_as_banner=set_as_banner,
    )
    return _to_public(event, access="host")


@router.delete(
    "/by-id/{event_id}/media/{media_id}",
    response_model=EventPublic,
)
def remove_event_media(
    event_id: UUID,
    media_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> EventPublic:
    return _to_public(
        delete_event_media(
            db, user=user, event_id=event_id, media_id=media_id
        ),
        access="host",
    )


@router.get("/by-id/{event_id}/ticket-types", response_model=list[TicketTypePublic])
def get_ticket_types(
    event_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[TicketTypePublic]:
    tickets = list_ticket_types(db, user=user, event_id=event_id)
    return [TicketTypePublic.model_validate(t) for t in tickets]


@router.post(
    "/by-id/{event_id}/ticket-types",
    response_model=TicketTypePublic,
    status_code=status.HTTP_201_CREATED,
)
def post_ticket_type(
    event_id: UUID,
    payload: TicketTypeCreate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTypePublic:
    ticket = create_ticket_type(db, user=user, event_id=event_id, payload=payload)
    return TicketTypePublic.model_validate(ticket)


@router.patch(
    "/by-id/{event_id}/ticket-types/{ticket_type_id}",
    response_model=TicketTypePublic,
)
def patch_ticket_type(
    event_id: UUID,
    ticket_type_id: UUID,
    payload: TicketTypeUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTypePublic:
    ticket = update_ticket_type(
        db,
        user=user,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        payload=payload,
    )
    return TicketTypePublic.model_validate(ticket)


@router.post(
    "/by-id/{event_id}/ticket-types/{ticket_type_id}/deactivate",
    response_model=TicketTypePublic,
)
def deactivate_ticket(
    event_id: UUID,
    ticket_type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> TicketTypePublic:
    ticket = deactivate_ticket_type(
        db, user=user, event_id=event_id, ticket_type_id=ticket_type_id
    )
    return TicketTypePublic.model_validate(ticket)


@router.delete(
    "/by-id/{event_id}/ticket-types/{ticket_type_id}",
    response_model=MessageResponse,
)
def remove_ticket_type(
    event_id: UUID,
    ticket_type_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> MessageResponse:
    delete_ticket_type(
        db, user=user, event_id=event_id, ticket_type_id=ticket_type_id
    )
    return MessageResponse(message="Ticket type removed")


@router.get("/{slug}/fan-connect")
def event_fan_connect(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_permission("fan_connect.use"))],
    limit: int = Query(default=12, ge=1, le=50),
    page: int = Query(default=1, ge=1),
):
    """Fans suggested for this public event — privacy-safe Connect surface."""
    from app.fan_connect import service as fan_connect_svc
    from app.fan_connect.schemas import SuggestionsPublic

    return SuggestionsPublic.model_validate(
        fan_connect_svc.suggestions_for_event_slug(
            db, user, event_slug=slug, limit=limit, page=page
        )
    )


@router.get("/{slug}", response_model=EventPublic)
def get_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> EventPublic:
    from app.core.cache import cache_get, cache_set
    from app.events.public_cache import TTL, events_detail_key

    # Anonymous public detail — try cache before DB.
    if user is None:
        key = events_detail_key(slug)
        hit = cache_get(key)
        if hit is not None:
            return EventPublic.model_validate(hit)

    event = public_event_detail(db, slug)
    access = resolve_event_access(db, event, user)

    if user is None and access == "public":
        data = serialize_event(event, access="public")
        data["ticket_types"] = [
            TicketTypePublic.model_validate(tt).model_copy(update={"access_code": None})
            for tt in event.ticket_types
            if tt.visibility == "public"
        ]
        payload = EventPublic.model_validate(data)
        cache_set(events_detail_key(slug), payload.model_dump(mode="json"), TTL.detail)
        return payload

    data = serialize_event(event, access=access)
    if user is None or not _can_see_all_tickets(db, user, event):
        data["ticket_types"] = [
            TicketTypePublic.model_validate(tt).model_copy(update={"access_code": None})
            for tt in event.ticket_types
            if tt.visibility == "public" or access in {"host", "admin", "buyer"}
        ]
        if access == "public":
            data["ticket_types"] = [
                tt for tt in data["ticket_types"] if tt.visibility == "public"
            ]
    return EventPublic.model_validate(data)
