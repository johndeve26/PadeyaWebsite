"""Event and ticket type schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.media import normalize_public_media_url
from app.events.constants import (
    AGENDA_ITEM_TYPES,
    CHECKOUT_QUESTION_TYPES,
    EVENT_STATUSES,
    EVENT_TYPES,
    EVENT_VISIBILITY,
    LOCATION_VISIBILITY,
    MEDIA_TYPES,
    ONLINE_URL_REVEAL_RULES,
    REFUND_POLICY_TYPES,
    REVEAL_TIMING,
    TICKET_STATUSES,
    TICKET_VISIBILITY,
    normalize_ticket_type_kind,
)


class EventCategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool


class EventVenueIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: str | None = Field(default=None, max_length=32)
    longitude: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class EventVenuePublic(EventVenueIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None


class EventAgendaItemIn(BaseModel):
    id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    type: str = "other"
    sort_order: int = 0

    @field_validator("type")
    @classmethod
    def validate_agenda_type(cls, value: str) -> str:
        raw = (value or "other").strip()
        if raw in AGENDA_ITEM_TYPES:
            return raw
        # Tolerate legacy labels / casing from older Studio clients.
        key = raw.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "doors": "doors_open",
            "doorsopen": "doors_open",
            "afterparty": "after_party",
            "after_party": "after_party",
            "set": "performance",
            "talk": "speaker",
            "panel": "speaker",
            "intermission": "break",
        }
        mapped = aliases.get(key, key)
        if mapped in AGENDA_ITEM_TYPES:
            return mapped
        return "other"

    @model_validator(mode="after")
    def end_after_start(self) -> "EventAgendaItemIn":
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("agenda end_time must be after start_time")
        return self


class EventAgendaItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    type: str = "other"
    sort_order: int = 0


class EventPersonIn(BaseModel):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    role: str | None = None
    bio: str | None = None
    image_url: str | None = None
    social_url: str | None = None
    performance_time: datetime | None = None
    sort_order: int = 0


class EventPersonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str | None = None
    bio: str | None = None
    image_url: str | None = None
    social_url: str | None = None
    performance_time: datetime | None = None
    sort_order: int = 0


class EventCheckoutQuestionIn(BaseModel):
    id: UUID | None = None
    label: str = Field(min_length=1, max_length=255)
    type: str = "short_text"
    required: bool = False
    options: list[str] | None = None
    help_text: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    status: str = "active"

    @field_validator("type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:
        if value not in CHECKOUT_QUESTION_TYPES:
            raise ValueError(f"type must be one of {CHECKOUT_QUESTION_TYPES}")
        return value

    @field_validator("status")
    @classmethod
    def validate_question_status(cls, value: str) -> str:
        if value not in {"active", "archived"}:
            raise ValueError("status must be active or archived")
        return value


class EventCheckoutQuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    type: str = "short_text"
    required: bool = False
    options: list[str] | None = None
    help_text: str | None = None
    sort_order: int = 0
    status: str = "active"
    archived_at: datetime | None = None


class EventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    short_tagline: str | None = Field(default=None, max_length=240)
    vibe: str | None = Field(default=None, max_length=120)
    event_type: str = "public"
    visibility: str = "listed"
    category_id: UUID | None = None
    start_datetime: datetime
    end_datetime: datetime
    doors_open_datetime: datetime | None = None
    timezone: str = "Africa/Lagos"
    venue_name: str | None = None
    venue_type: str | None = Field(default=None, max_length=64)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = Field(default=None, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    postcode: str | None = Field(default=None, max_length=32)
    latitude: str | None = Field(default=None, max_length=32)
    longitude: str | None = Field(default=None, max_length=32)
    google_place_id: str | None = Field(default=None, max_length=255)
    formatted_address: str | None = Field(default=None, max_length=500)
    google_maps_share_url: str | None = Field(default=None, max_length=500)
    google_maps_place_url: str | None = Field(default=None, max_length=500)
    location_id: UUID | None = None
    public_location_label: str | None = None
    approximate_latitude: str | None = Field(default=None, max_length=32)
    approximate_longitude: str | None = Field(default=None, max_length=32)
    approximate_map_label: str | None = Field(default=None, max_length=255)
    location_visibility: str = "full_public"
    reveal_timing: str = "immediately"
    reveal_note: str | None = None
    online_event_url: str | None = None
    online_url_reveal_rule: str = "after_payment"
    banner_url: str | None = None
    mobile_banner_url: str | None = None
    teaser_video_url: str | None = None
    social_share_image_url: str | None = None
    brand_accent_override: str | None = None
    sponsor_logo_urls: list[str] | None = None
    capacity: int | None = Field(default=None, ge=1)
    refund_policy: str | None = None
    refund_policy_type: str | None = None
    refund_policy_text: str | None = None
    cancellation_policy: str | None = None
    age_restriction: str | None = None
    id_required: bool = False
    safety_notice: str | None = None
    terms_acknowledgement: str | None = None
    door_sales_allowed: bool = True
    allow_merch_only_checkout: bool = False
    open_ambassadors_enabled: bool = False
    open_ambassador_commission_percent: Decimal = Field(
        default=Decimal("5.00"), ge=0, le=100
    )
    re_entry_allowed: bool = False
    check_in_start_time: datetime | None = None
    check_in_end_time: datetime | None = None
    dress_code: str | None = None
    accessibility_notes: str | None = None
    parking_info: str | None = None
    what_to_expect: str | None = None
    what_to_bring: str | None = None
    prohibited_items: str | None = None
    entry_requirements: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    social_share_title: str | None = None
    social_share_description: str | None = None
    hashtags: list[str] | None = None
    discoverable_keywords: list[str] | None = None
    venue: EventVenueIn | None = None
    agenda_items: list[EventAgendaItemIn] | None = None
    people: list[EventPersonIn] | None = None
    checkout_questions: list[EventCheckoutQuestionIn] | None = None
    gallery_urls: list[str] | None = None

    @field_validator("end_datetime")
    @classmethod
    def end_after_start(cls, value: datetime, info):  # type: ignore[no-untyped-def]
        start = info.data.get("start_datetime")
        if start and value <= start:
            raise ValueError("end_datetime must be after start_datetime")
        return value

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {EVENT_TYPES}")
        return value

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        if value not in EVENT_VISIBILITY:
            raise ValueError(f"visibility must be one of {EVENT_VISIBILITY}")
        return value

    @field_validator("location_visibility")
    @classmethod
    def validate_location_visibility(cls, value: str) -> str:
        if value not in LOCATION_VISIBILITY:
            raise ValueError(f"location_visibility must be one of {LOCATION_VISIBILITY}")
        return value

    @field_validator("reveal_timing")
    @classmethod
    def validate_reveal_timing(cls, value: str) -> str:
        if value not in REVEAL_TIMING:
            raise ValueError(f"reveal_timing must be one of {REVEAL_TIMING}")
        return value

    @field_validator("online_url_reveal_rule")
    @classmethod
    def validate_online_rule(cls, value: str) -> str:
        if value not in ONLINE_URL_REVEAL_RULES:
            raise ValueError(f"online_url_reveal_rule must be one of {ONLINE_URL_REVEAL_RULES}")
        return value

    @field_validator("refund_policy_type")
    @classmethod
    def validate_refund_type(cls, value: str | None) -> str | None:
        if value is not None and value not in REFUND_POLICY_TYPES:
            raise ValueError(f"refund_policy_type must be one of {REFUND_POLICY_TYPES}")
        return value

    @model_validator(mode="after")
    def validate_policy_details(self) -> "EventCreate":
        if self.refund_policy_type in {"custom", "partial_refund_only"}:
            if not (self.refund_policy_text or "").strip():
                raise ValueError(
                    "refund_policy_text is required for custom and partial_refund_only"
                )
        if (
            self.check_in_start_time
            and self.check_in_end_time
            and self.check_in_end_time <= self.check_in_start_time
        ):
            raise ValueError("check_in_end_time must be after check_in_start_time")
        return self


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, min_length=10)
    short_tagline: str | None = None
    vibe: str | None = None
    event_type: str | None = None
    visibility: str | None = None
    category_id: UUID | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    doors_open_datetime: datetime | None = None
    timezone: str | None = None
    venue_name: str | None = None
    venue_type: str | None = Field(default=None, max_length=64)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = Field(default=None, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    postcode: str | None = Field(default=None, max_length=32)
    latitude: str | None = Field(default=None, max_length=32)
    longitude: str | None = Field(default=None, max_length=32)
    google_place_id: str | None = Field(default=None, max_length=255)
    formatted_address: str | None = Field(default=None, max_length=500)
    google_maps_share_url: str | None = Field(default=None, max_length=500)
    google_maps_place_url: str | None = Field(default=None, max_length=500)
    location_id: UUID | None = None
    public_location_label: str | None = None
    approximate_latitude: str | None = Field(default=None, max_length=32)
    approximate_longitude: str | None = Field(default=None, max_length=32)
    approximate_map_label: str | None = Field(default=None, max_length=255)
    location_visibility: str | None = None
    reveal_timing: str | None = None
    reveal_note: str | None = None
    online_event_url: str | None = None
    online_url_reveal_rule: str | None = None
    banner_url: str | None = None
    mobile_banner_url: str | None = None
    teaser_video_url: str | None = None
    social_share_image_url: str | None = None
    brand_accent_override: str | None = None
    sponsor_logo_urls: list[str] | None = None
    capacity: int | None = Field(default=None, ge=1)
    refund_policy: str | None = None
    refund_policy_type: str | None = None
    refund_policy_text: str | None = None
    cancellation_policy: str | None = None
    age_restriction: str | None = None
    id_required: bool | None = None
    safety_notice: str | None = None
    terms_acknowledgement: str | None = None
    door_sales_allowed: bool | None = None
    allow_merch_only_checkout: bool | None = None
    open_ambassadors_enabled: bool | None = None
    open_ambassador_commission_percent: Decimal | None = Field(
        default=None, ge=0, le=100
    )
    re_entry_allowed: bool | None = None
    check_in_start_time: datetime | None = None
    check_in_end_time: datetime | None = None
    dress_code: str | None = None
    accessibility_notes: str | None = None
    parking_info: str | None = None
    what_to_expect: str | None = None
    what_to_bring: str | None = None
    prohibited_items: str | None = None
    entry_requirements: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    social_share_title: str | None = None
    social_share_description: str | None = None
    hashtags: list[str] | None = None
    discoverable_keywords: list[str] | None = None
    venue: EventVenueIn | None = None
    agenda_items: list[EventAgendaItemIn] | None = None
    people: list[EventPersonIn] | None = None
    checkout_questions: list[EventCheckoutQuestionIn] | None = None
    gallery_urls: list[str] | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str | None) -> str | None:
        if value is not None and value not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {EVENT_TYPES}")
        return value

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in EVENT_VISIBILITY:
            raise ValueError(f"visibility must be one of {EVENT_VISIBILITY}")
        return value

    @field_validator("location_visibility")
    @classmethod
    def validate_location_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in LOCATION_VISIBILITY:
            raise ValueError(f"location_visibility must be one of {LOCATION_VISIBILITY}")
        return value

    @field_validator("reveal_timing")
    @classmethod
    def validate_reveal_timing(cls, value: str | None) -> str | None:
        if value is not None and value not in REVEAL_TIMING:
            raise ValueError(f"reveal_timing must be one of {REVEAL_TIMING}")
        return value

    @field_validator("online_url_reveal_rule")
    @classmethod
    def validate_online_rule(cls, value: str | None) -> str | None:
        if value is not None and value not in ONLINE_URL_REVEAL_RULES:
            raise ValueError(f"online_url_reveal_rule must be one of {ONLINE_URL_REVEAL_RULES}")
        return value

    @field_validator("refund_policy_type")
    @classmethod
    def validate_refund_type(cls, value: str | None) -> str | None:
        if value is not None and value not in REFUND_POLICY_TYPES:
            raise ValueError(f"refund_policy_type must be one of {REFUND_POLICY_TYPES}")
        return value

    @model_validator(mode="after")
    def validate_policy_details(self) -> "EventUpdate":
        if self.refund_policy_type in {"custom", "partial_refund_only"}:
            if not (self.refund_policy_text or "").strip():
                raise ValueError(
                    "refund_policy_text is required for custom and partial_refund_only"
                )
        if (
            self.check_in_start_time
            and self.check_in_end_time
            and self.check_in_end_time <= self.check_in_start_time
        ):
            raise ValueError("check_in_end_time must be after check_in_start_time")
        if (
            self.start_datetime is not None
            and self.end_datetime is not None
            and self.end_datetime <= self.start_datetime
        ):
            raise ValueError("end_datetime must be after start_datetime")
        return self


class EventMediaCreate(BaseModel):
    url: str | None = Field(default=None, max_length=500)
    filename: str | None = Field(default=None, max_length=200)
    media_type: str = "gallery"
    alt_text: str | None = None
    sort_order: int = 0
    set_as_banner: bool = False

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if value not in MEDIA_TYPES:
            raise ValueError(f"media_type must be one of {MEDIA_TYPES}")
        return value


class EventMediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    media_type: str
    alt_text: str | None
    sort_order: int

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: str | None) -> str | None:
        return normalize_public_media_url(value)


class MediaUploadPublic(BaseModel):
    url: str
    key: str
    media_type: str
    event_id: UUID | None = None

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: str | None) -> str | None:
        return normalize_public_media_url(value)


class TicketTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str
    description: str | None = None
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    quantity: int = Field(ge=0)
    seats_per_unit: int = Field(default=1, ge=1, le=100)
    min_per_order: int = Field(default=1, ge=1)
    max_per_order: int = Field(default=10, ge=1)
    sale_start: datetime | None = None
    sale_end: datetime | None = None
    visibility: str = "public"
    benefits: str | None = None
    transfer_allowed: bool = True
    refund_allowed: bool = False
    access_code: str | None = None
    waitlist_enabled: bool = False
    table_perks: str | None = None
    reservation_hold_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: str = "active"

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        return normalize_ticket_type_kind(value)

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        if value not in TICKET_VISIBILITY:
            raise ValueError(f"visibility must be one of {TICKET_VISIBILITY}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in TICKET_STATUSES:
            raise ValueError(f"status must be one of {TICKET_STATUSES}")
        return value

    @model_validator(mode="after")
    def sale_end_after_start(self) -> "TicketTypeCreate":
        if self.sale_start and self.sale_end and self.sale_end <= self.sale_start:
            raise ValueError("sale_end must be after sale_start")
        return self


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=0)
    seats_per_unit: int | None = Field(default=None, ge=1, le=100)
    min_per_order: int | None = Field(default=None, ge=1)
    max_per_order: int | None = Field(default=None, ge=1)
    sale_start: datetime | None = None
    sale_end: datetime | None = None
    visibility: str | None = None
    benefits: str | None = None
    transfer_allowed: bool | None = None
    refund_allowed: bool | None = None
    access_code: str | None = None
    waitlist_enabled: bool | None = None
    table_perks: str | None = None
    reservation_hold_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_ticket_type_kind(value)

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str | None) -> str | None:
        if value is not None and value not in TICKET_VISIBILITY:
            raise ValueError(f"visibility must be one of {TICKET_VISIBILITY}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in TICKET_STATUSES:
            raise ValueError(f"status must be one of {TICKET_STATUSES}")
        return value

    @model_validator(mode="after")
    def sale_end_after_start(self) -> "TicketTypeUpdate":
        if self.sale_start and self.sale_end and self.sale_end <= self.sale_start:
            raise ValueError("sale_end must be after sale_start")
        return self


class TicketTypePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    name: str
    type: str
    description: str | None
    price: Decimal
    quantity: int
    seats_per_unit: int = 1
    min_per_order: int
    max_per_order: int
    sale_start: datetime | None
    sale_end: datetime | None
    visibility: str
    benefits: str | None
    transfer_allowed: bool = True
    refund_allowed: bool = False
    access_code: str | None = None
    waitlist_enabled: bool = False
    table_perks: str | None = None
    reservation_hold_minutes: int | None = None
    quantity_sold: int = 0
    quantity_reserved: int = 0
    status: str


class EventPublishChecklist(BaseModel):
    basics_complete: bool
    category_complete: bool = False
    venue_privacy_complete: bool
    date_complete: bool
    has_ticket_type: bool
    banner_ready: bool
    refund_policy_selected: bool
    check_in_settings_complete: bool
    seo_complete: bool
    preview_checked: bool = False
    ready_to_submit: bool


class EventLocationNode(BaseModel):
    slug: str
    name: str
    kind: str


class EventLocationPublic(BaseModel):
    slug: str
    name: str
    kind: str
    ancestors: list[EventLocationNode] = []


class EventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    description: str
    short_tagline: str | None = None
    vibe: str | None = None
    event_type: str = "public"
    visibility: str = "listed"
    category_id: UUID | None
    primary_category_id: UUID | None = None
    host_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    doors_open_datetime: datetime | None = None
    timezone: str = "Africa/Lagos"
    venue_name: str | None
    venue_type: str | None = None
    address: str | None
    city: str | None
    state: str | None
    country: str | None = None
    area: str | None = None
    postcode: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    google_place_id: str | None = None
    formatted_address: str | None = None
    google_maps_share_url: str | None = None
    google_maps_place_url: str | None = None
    location_id: UUID | None = None
    location: EventLocationPublic | None = None
    public_location_label: str | None = None
    approximate_latitude: str | None = None
    approximate_longitude: str | None = None
    approximate_map_label: str | None = None
    location_visibility: str = "full_public"
    reveal_timing: str = "immediately"
    reveal_note: str | None = None
    online_event_url: str | None = None
    online_url_reveal_rule: str = "after_payment"
    location_address_revealed: bool = True
    location_privacy_message: str | None = None
    location_map_mode: str = "none"
    map_latitude: str | None = None
    map_longitude: str | None = None
    map_label: str | None = None
    map_open_url: str | None = None
    distance_km: float | None = None
    distance_label: str | None = None
    distance_is_approximate: bool = False
    has_valid_coordinates: bool | None = None
    banner_url: str | None
    mobile_banner_url: str | None = None
    teaser_video_url: str | None = None
    social_share_image_url: str | None = None
    brand_accent_override: str | None = None
    sponsor_logo_urls: list[Any] | None = None
    capacity: int | None
    refund_policy: str | None
    refund_policy_type: str | None = None
    refund_policy_text: str | None = None
    cancellation_policy: str | None = None
    age_restriction: str | None
    id_required: bool = False
    safety_notice: str | None = None
    terms_acknowledgement: str | None = None
    door_sales_allowed: bool = True
    allow_merch_only_checkout: bool = False
    open_ambassadors_enabled: bool = False
    open_ambassador_commission_percent: Decimal = Field(
        default=Decimal("5.00"), ge=0, le=100
    )
    re_entry_allowed: bool = False
    check_in_start_time: datetime | None = None
    check_in_end_time: datetime | None = None
    dress_code: str | None = None
    accessibility_notes: str | None = None
    parking_info: str | None = None
    what_to_expect: str | None = None
    what_to_bring: str | None = None
    prohibited_items: str | None = None
    entry_requirements: str | None = None
    status: str
    featured: bool
    seo_title: str | None
    seo_description: str | None
    social_share_title: str | None = None
    social_share_description: str | None = None
    hashtags: list[Any] | None = None
    discoverable_keywords: list[Any] | None = None
    rejection_reason: str | None = None
    admin_flagged: bool = False
    admin_flagged_at: datetime | None = None
    admin_flag_reason: str | None = None
    published_at: datetime | None
    created_at: datetime
    category: EventCategoryPublic | None = None
    venue: EventVenuePublic | None = None
    media: list[EventMediaPublic] = []
    ticket_types: list[TicketTypePublic] = []
    agenda_items: list[EventAgendaItemPublic] = []
    people: list[EventPersonPublic] = []
    checkout_questions: list[EventCheckoutQuestionPublic] = []
    host_display_name: str | None = None
    host_slug: str | None = None
    publish_checklist: EventPublishChecklist | None = None

    @field_validator(
        "banner_url",
        "mobile_banner_url",
        "social_share_image_url",
        mode="before",
    )
    @classmethod
    def normalize_media_urls(cls, value: str | None) -> str | None:
        return normalize_public_media_url(value)


class EventRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class EventFlagRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class EventClearFlagRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class EventPostponeRequest(BaseModel):
    """Reschedule start/end without sending the listing back for review."""

    start_datetime: datetime
    end_datetime: datetime

    @field_validator("end_datetime")
    @classmethod
    def end_after_start(cls, value: datetime, info):  # type: ignore[no-untyped-def]
        start = info.data.get("start_datetime")
        if start and value <= start:
            raise ValueError("end_datetime must be after start_datetime")
        return value


class NearbyEventsResponse(BaseModel):
    items: list[EventPublic]
    total: int
    page: int
    limit: int
    radius_km: int
    lat: float
    lng: float
    location_label: str | None = None


class CalendarEventCompact(BaseModel):
    """Compact event row for calendar cells — not full EventPublic."""

    id: UUID
    slug: str
    title: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    banner_url: str | None = None
    city: str | None = None
    public_location_label: str | None = None
    featured: bool = False
    host_display_name: str | None = None
    host_id: UUID | None = None
    category_name: str | None = None
    category_slug: str | None = None
    min_price: float | None = None
    is_free: bool = False


class CalendarDay(BaseModel):
    date: str
    event_count: int
    events: list[CalendarEventCompact]


class CalendarMonthResponse(BaseModel):
    month: str
    days: list[CalendarDay]
    featured_event: CalendarEventCompact | None = None
    total_events: int


class MapEventCompact(BaseModel):
    """Compact map pin — never includes street address or private exact coords."""

    id: UUID
    slug: str
    title: str
    banner_url: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    price_label: str = "See tickets"
    min_price: float | None = None
    is_free: bool = False
    category_name: str | None = None
    category_slug: str | None = None
    host_display_name: str | None = None
    public_location_label: str | None = None
    city: str | None = None
    area: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    location_visibility: str = "full_public"
    location_map_mode: str = "none"
    location_privacy_message: str | None = None
    distance_km: float | None = None
    distance_label: str | None = None
    distance_is_approximate: bool = False


class MapEventsResponse(BaseModel):
    items: list[MapEventCompact]
    total: int
    north: float
    south: float
    east: float
    west: float
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = None


class MessageResponse(BaseModel):
    message: str


class EventForceDeleteRequest(BaseModel):
    """Admin permanent delete (intended for test/cleanup; cascades related rows)."""

    reason: str = Field(min_length=3, max_length=2000)


class EventCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str | None = Field(default=None, max_length=255)


class EventCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)


class EventTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    payload: dict[str, Any] | None = None


class EventTemplatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    host_id: UUID
    name: str
    description: str | None
    payload: dict[str, Any]
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


def assert_event_status(value: str) -> str:
    if value not in EVENT_STATUSES:
        raise ValueError(f"status must be one of {EVENT_STATUSES}")
    return value
