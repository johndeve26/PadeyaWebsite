"""Verified review lifecycle services."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.service import require_user_host
from app.legacy.service import refresh_host_legacy_score
from app.reviews.eligibility import evaluate_review_eligibility
from app.reviews.models import ReviewReply, ReviewReport, VerifiedReview
from app.reviews.schemas import (
    ReviewCreate,
    ReviewModerateRequest,
    ReviewReplyCreate,
    ReviewReportCreate,
    ReviewUpdate,
)
from app.users.models import User
from app.users.service import user_has_permission


def _user_name(db: Session, user_id: UUID) -> str | None:
    user = db.get(User, user_id)
    return user.full_name if user else None


def serialize_reply(db: Session, reply: ReviewReply | None) -> dict | None:
    if reply is None:
        return None
    return {
        "id": reply.id,
        "body": reply.body,
        "author_name": _user_name(db, reply.author_user_id),
        "created_at": reply.created_at,
    }


def serialize_review(
    db: Session,
    review: VerifiedReview,
    *,
    include_moderation: bool = False,
) -> dict:
    event = db.get(Event, review.event_id)
    reply = db.scalar(select(ReviewReply).where(ReviewReply.review_id == review.id))
    report_count = db.scalar(
        select(func.count()).select_from(ReviewReport).where(ReviewReport.review_id == review.id)
    )
    data = {
        "id": review.id,
        "event_id": review.event_id,
        "host_id": review.host_id,
        "reviewer_user_id": review.reviewer_user_id,
        "ticket_id": review.ticket_id,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "status": review.status,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "reviewer_name": _user_name(db, review.reviewer_user_id),
        "created_at": review.created_at,
        "reply": serialize_reply(db, reply),
        "report_count": int(report_count or 0),
        "moderation_reason": review.moderation_reason if include_moderation else None,
    }
    return data


def check_eligibility(
    db: Session,
    *,
    user: User,
    ticket_id: UUID | None = None,
    event_id: UUID | None = None,
) -> dict:
    if ticket_id is None and event_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide ticket_id or event_id",
        )
    eligible, reason, ticket, event = evaluate_review_eligibility(
        db, user_id=user.id, ticket_id=ticket_id, event_id=event_id
    )
    return {
        "eligible": eligible,
        "reason": reason,
        "ticket_id": ticket.id if ticket else None,
        "event_id": event.id if event else (ticket.event_id if ticket else None),
        "event_title": event.title if event else None,
        "host_id": event.host_id if event else None,
    }


def submit_review(
    db: Session,
    *,
    user: User,
    payload: ReviewCreate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VerifiedReview:
    from app.hosts.fan_self_abuse import (
        REVIEW_OWN_HOST_DETAIL,
        assert_not_own_host_public_review,
    )
    from app.users.restrictions import assert_can_submit_review

    assert_can_submit_review(db, user)

    eligible, reason, ticket, event = evaluate_review_eligibility(
        db, user_id=user.id, ticket_id=payload.ticket_id
    )
    if not eligible or ticket is None or event is None:
        status_code = (
            status.HTTP_403_FORBIDDEN
            if reason == REVIEW_OWN_HOST_DETAIL
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=reason or "Not eligible to review",
        )

    # Defense in depth — owner must never publish a public review on own host.
    assert_not_own_host_public_review(
        db, user_id=user.id, host_id=event.host_id
    )

    review = VerifiedReview(
        event_id=event.id,
        host_id=event.host_id,
        reviewer_user_id=user.id,
        ticket_id=ticket.id,
        rating=payload.rating,
        title=payload.title.strip() if payload.title else None,
        body=payload.body.strip(),
        status="visible",
    )
    db.add(review)
    write_audit_log(
        db,
        action="reviews.create",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review.id),
        details={"event_id": str(event.id), "rating": payload.rating},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()

    from app.analytics.trusted import emit_review_submitted

    emit_review_submitted(
        db,
        event_id=event.id,
        host_id=event.host_id,
        user_id=user.id,
        review_id=review.id,
    )

    refresh_host_legacy_score(db, event.host_id, reason="review_update")
    from app.email.service import enqueue_template
    from app.hosts.models import Host
    from app.users.models import User as UserModel

    host = db.get(Host, event.host_id)
    if host is not None:
        host_user = db.get(UserModel, host.user_id)
        if host_user is not None:
            if host_user.email:
                enqueue_template(
                    db,
                    template="host_new_review",
                    to=host_user.email,
                    recipient_user_id=host_user.id,
                    dedupe_key=f"review:{review.id}:host_new_review",
                    context={"subject_label": event.title},
                )
            from app.notifications.service import notify_user

            notify_user(
                db,
                user_id=host_user.id,
                kind="review.new",
                title="New review on Pàdéyá",
                body=f"Someone left a verified review for {event.title}.",
                link_path="/host/reviews",
                dedupe_key=f"review:{review.id}:host.notif",
            )
    db.commit()
    db.refresh(review)
    return review


def list_my_reviews(db: Session, user: User) -> list[dict]:
    reviews = db.scalars(
        select(VerifiedReview)
        .where(VerifiedReview.reviewer_user_id == user.id)
        .order_by(VerifiedReview.created_at.desc())
    ).all()
    return [serialize_review(db, r, include_moderation=True) for r in reviews]


def list_host_reviews(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    reviews = db.scalars(
        select(VerifiedReview)
        .where(VerifiedReview.host_id == host.id)
        .order_by(VerifiedReview.created_at.desc())
    ).all()
    return [serialize_review(db, r, include_moderation=True) for r in reviews]


def list_visible_host_reviews(db: Session, host_id: UUID, *, limit: int = 50) -> list[dict]:
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    reviews = db.scalars(
        select(VerifiedReview)
        .where(
            VerifiedReview.host_id == host_id,
            VerifiedReview.status == "visible",
        )
        .order_by(VerifiedReview.created_at.desc())
    ).all()
    external = [
        r
        for r in reviews
        if not is_user_owner_of_host(
            db, user_id=r.reviewer_user_id, host_profile_id=host_id
        )
    ][:limit]
    return [serialize_review(db, r) for r in external]


def reply_to_review(
    db: Session,
    *,
    user: User,
    review_id: UUID,
    payload: ReviewReplyCreate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VerifiedReview:
    if not user_has_permission(user, "reviews.reply") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reply to reviews")

    review = db.get(VerifiedReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    host = require_user_host(db, user)
    if host.id != review.host_id and not user_has_permission(user, "admin.full_access"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your review")

    existing = db.scalar(select(ReviewReply).where(ReviewReply.review_id == review.id))
    if existing is not None:
        existing.body = payload.body.strip()
        existing.updated_at = datetime.now(UTC)
    else:
        db.add(
            ReviewReply(
                review_id=review.id,
                host_id=host.id,
                author_user_id=user.id,
                body=payload.body.strip(),
            )
        )

    write_audit_log(
        db,
        action="reviews.reply",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    from app.email.service import enqueue_template
    from app.events.models import Event
    from app.users.models import User as UserModel

    reviewer = db.get(UserModel, review.reviewer_user_id)
    event = db.get(Event, review.event_id)
    if reviewer is not None:
        if reviewer.email:
            enqueue_template(
                db,
                template="review_host_reply",
                to=reviewer.email,
                recipient_user_id=reviewer.id,
                dedupe_key=f"review:{review.id}:host_reply",
                context={"event_title": event.title if event else "your event"},
            )
        from app.notifications.service import notify_user

        notify_user(
            db,
            user_id=reviewer.id,
            kind="review.reply",
            title="Host replied to your review",
            body=f"A host replied on Pàdéyá about {event.title if event else 'your event'}.",
            link_path="/dashboard/reviews",
            dedupe_key=f"review:{review.id}:reply.notif",
        )
    db.commit()
    db.refresh(review)
    return review


def report_review(
    db: Session,
    *,
    user: User,
    review_id: UUID,
    payload: ReviewReportCreate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ReviewReport:
    review = db.get(VerifiedReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    existing = db.scalar(
        select(ReviewReport).where(
            ReviewReport.review_id == review_id,
            ReviewReport.reporter_user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reported")

    report = ReviewReport(
        review_id=review_id,
        reporter_user_id=user.id,
        reason=payload.reason.strip(),
        status="open",
    )
    db.add(report)
    write_audit_log(
        db,
        action="reviews.report",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review_id),
        details={"reason": payload.reason[:200]},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    from app.notifications.triggers import notify_admins_report

    notify_admins_report(
        db,
        report_id=report.id,
        report_kind="review",
        title="New review report on Pàdéyá",
        body="A verified review was reported and needs moderation.",
        link_path="/admin/reviews",
    )
    db.commit()
    db.refresh(report)
    return report


def refuse_delete_review(user: User) -> None:
    """Hosts cannot delete reviews. Hard deletes are not allowed."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Reviews cannot be hard-deleted. Buyers may withdraw; hosts may reply or report; admins may hide.",
    )


def update_review(
    db: Session,
    *,
    user: User,
    review_id: UUID,
    payload: ReviewUpdate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VerifiedReview:
    """Buyer update. Editing a withdrawn review restores it to ``visible``."""
    review = db.get(VerifiedReview, review_id)
    if review is None or review.reviewer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.status == "hidden":
        raise HTTPException(
            status_code=400,
            detail="Hidden reviews cannot be edited — contact support if needed",
        )
    if review.status not in {"visible", "withdrawn"}:
        raise HTTPException(status_code=400, detail="This review cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    restored = review.status == "withdrawn"
    if not data and not restored:
        return review
    for key, value in data.items():
        if key == "title":
            setattr(review, key, value.strip() if value else None)
        elif key == "body" and value is not None:
            setattr(review, key, value.strip())
        elif value is not None:
            setattr(review, key, value)
    if restored:
        review.status = "visible"
    write_audit_log(
        db,
        action="reviews.restore" if restored else "reviews.update",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review.id),
        details={"restored": restored} if restored else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(review)
    if restored:
        refresh_host_legacy_score(db, review.host_id)
    return review


def withdraw_review(
    db: Session,
    *,
    user: User,
    review_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VerifiedReview:
    """Buyer soft-withdraw — not a hard delete. Hosts cannot withdraw others' reviews."""
    review = db.get(VerifiedReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.reviewer_user_id != user.id:
        refuse_delete_review(user)
    if review.status == "withdrawn":
        return review
    review.status = "withdrawn"
    write_audit_log(
        db,
        action="reviews.withdraw",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review.id),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(review)
    refresh_host_legacy_score(db, review.host_id)
    return review


def list_reported_reviews(db: Session) -> list[dict]:
    open_reports = db.scalars(
        select(ReviewReport)
        .where(ReviewReport.status == "open")
        .order_by(ReviewReport.created_at.desc())
    ).all()
    seen: set[UUID] = set()
    out: list[dict] = []
    for report in open_reports:
        if report.review_id in seen:
            continue
        seen.add(report.review_id)
        review = db.get(VerifiedReview, report.review_id)
        if review is None:
            continue
        out.append(
            {
                "id": report.id,
                "review_id": report.review_id,
                "reporter_user_id": report.reporter_user_id,
                "reason": report.reason,
                "status": report.status,
                "created_at": report.created_at,
                "review": serialize_review(db, review, include_moderation=True),
            }
        )
    return out


def moderate_review(
    db: Session,
    *,
    user: User,
    review_id: UUID,
    payload: ReviewModerateRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VerifiedReview:
    if not user_has_permission(user, "reviews.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot moderate reviews")

    review = db.get(VerifiedReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    now = datetime.now(UTC)
    if payload.action == "hide":
        review.status = "hidden"
    else:
        review.status = "visible"
    review.moderation_reason = payload.reason.strip()
    review.moderated_by_user_id = user.id
    review.moderated_at = now

    db.execute(
        update(ReviewReport)
        .where(
            ReviewReport.review_id == review.id,
            ReviewReport.status == "open",
        )
        .values(status="resolved")
    )

    write_audit_log(
        db,
        action=f"reviews.moderate.{payload.action}",
        actor_user_id=user.id,
        resource_type="verified_review",
        resource_id=str(review.id),
        details={"reason": payload.reason, "status": review.status},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()
    refresh_host_legacy_score(db, review.host_id, reason="review_moderation")
    db.commit()
    db.refresh(review)
    return review


def get_review_or_404(db: Session, review_id: UUID) -> VerifiedReview:
    review = db.get(VerifiedReview, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review
