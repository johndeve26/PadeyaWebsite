"""Fan host recommendations — scoring and dismiss."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crm.models import HostFollower
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile, HostVerification
from app.legacy.models import HostLegacyPage
from app.passport.models import FanPassport
from app.users.models import User
from app.users.service import get_role_by_name


def _buyer(client: TestClient, db_session: Session, email: str) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Fan Buyer",
        is_active=True,
    )
    role = get_role_by_name(db_session, "buyer")
    assert role is not None
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()
    db_session.add(
        FanPassport(
            user_id=user.id,
            display_name="Fan Buyer",
            username=email.split("@")[0],
            visibility="public",
            favorite_categories=["music"],
        )
    )
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return user, token


def _listed_host(
    db_session: Session,
    *,
    slug: str,
    display: str,
    city: str = "Lagos",
    category_slug: str = "music",
) -> Host:
    host_user = User(
        email=f"{slug}@host.example.com",
        password_hash=hash_password("securepass1"),
        full_name=display,
        is_active=True,
    )
    host_role = get_role_by_name(db_session, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db_session.add(host_user)
    db_session.flush()
    host = Host(
        user_id=host_user.id,
        display_name=display,
        slug=slug,
        status="active",
    )
    db_session.add(host)
    db_session.flush()
    db_session.add(
        HostProfile(host_id=host.id, bio="Bio", city=city, avatar_url="https://x/a.jpg")
    )
    db_session.add(HostVerification(host_id=host.id, status="verified"))
    db_session.add(
        HostLegacyPage(
            host_id=host.id,
            tagline="Tag",
            primary_category_slug=category_slug,
            host_type_slug="dj",
        )
    )
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    db_session.add(
        Event(
            title=f"{display} Night",
            slug=f"{slug}-night",
            description="Listed",
            category_id=category.id if category else None,
            host_id=host.id,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            city=city,
            venue_name="Hall",
            address="Hidden",
            status="published",
            visibility="listed",
            location_visibility="city_only",
            featured=False,
            published_at=datetime.now(UTC) - timedelta(hours=2),
        )
    )
    db_session.commit()
    return host


def test_recommendations_rank_similar_category(
    client: TestClient, db_session: Session
) -> None:
    followed = _listed_host(
        db_session, slug="followed-host", display="Followed Host", category_slug="music"
    )
    similar = _listed_host(
        db_session, slug="similar-host", display="Similar Host", category_slug="music"
    )
    _listed_host(
        db_session, slug="other-host", display="Other Host", category_slug="comedy"
    )

    fan, token = _buyer(client, db_session, "fan-rec@example.com")
    db_session.add(HostFollower(host_id=followed.id, user_id=fan.id))
    db_session.commit()

    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("legacy", "discover", "hosts"))

    res = client.get(
        "/api/v1/hosts/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    usernames = [item["host"]["username"] for item in data["items"]]
    assert "followed-host" not in usernames
    assert "similar-host" in usernames
    top = data["items"][0]
    assert top["score"] >= 35
    assert any(r["code"] == "shared_category" for r in top["reasons"])


def test_dismiss_hides_host(
    client: TestClient, db_session: Session
) -> None:
    host = _listed_host(db_session, slug="dismiss-host", display="Dismiss Host")
    _, token = _buyer(client, db_session, "fan-dismiss@example.com")

    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("legacy", "discover", "hosts"))

    before = client.get(
        "/api/v1/hosts/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert before.status_code == 200
    assert any(
        i["host"]["username"] == "dismiss-host" for i in before.json()["items"]
    )

    dismiss = client.post(
        f"/api/v1/hosts/recommendations/{host.id}/dismiss",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "not for me"},
    )
    assert dismiss.status_code == 200

    after = client.get(
        "/api/v1/hosts/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 200
    assert not any(
        i["host"]["username"] == "dismiss-host" for i in after.json()["items"]
    )


def _clear_discover_cache() -> None:
    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("legacy", "discover", "hosts"))


def test_recommendations_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/hosts/recommendations")
    assert res.status_code == 401


def test_own_host_excluded(client: TestClient, db_session: Session) -> None:
    fan, token = _buyer(client, db_session, "fan-own-host@example.com")
    own = _listed_host(db_session, slug="my-own-host", display="My Host")
    own.user_id = fan.id
    db_session.commit()
    _clear_discover_cache()

    res = client.get(
        "/api/v1/hosts/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    usernames = [i["host"]["username"] for i in res.json()["items"]]
    assert "my-own-host" not in usernames


def test_impressions_endpoint(client: TestClient, db_session: Session) -> None:
    host = _listed_host(db_session, slug="imp-host", display="Imp Host")
    _, token = _buyer(client, db_session, "fan-imp@example.com")
    _clear_discover_cache()

    res = client.post(
        "/api/v1/hosts/recommendations/impressions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "items": [
                {
                    "host_id": str(host.id),
                    "surface": "hosts_recommended_rail",
                    "position": 0,
                    "recommendation_score": 72,
                    "reason_codes": ["verified_host"],
                }
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["recorded"] == 1

    from app.hosts.recommendations.models import HostRecommendationImpression

    count = (
        db_session.query(HostRecommendationImpression)
        .filter(HostRecommendationImpression.host_id == host.id)
        .count()
    )
    assert count == 1


def test_safe_reason_labels(client: TestClient, db_session: Session) -> None:
    _listed_host(db_session, slug="safe-host", display="Safe Host")
    _, token = _buyer(client, db_session, "fan-safe@example.com")
    _clear_discover_cache()

    res = client.get(
        "/api/v1/hosts/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    forbidden = ("vip", "table", "spend", "vault", "message", "private")
    for item in res.json()["items"]:
        for reason in item["reasons"]:
            label = reason["label"].lower()
            for word in forbidden:
                assert word not in label


def test_expired_dismiss_applies_penalty_not_suppression(
    db_session: Session,
) -> None:
    from app.hosts.recommendations.models import HostRecommendationDismissal
    from app.hosts.recommendations.scoring import score_host_for_fan
    from app.hosts.recommendations.affinity import load_fan_host_affinity
    from app.hosts.recommendations.settings import HostRecommendationConfig
    from app.legacy.discover import list_discover_hosts

    host = _listed_host(db_session, slug="exp-dismiss", display="Exp Dismiss")
    fan = User(
        email="fan-scoring@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Fan",
        is_active=True,
    )
    db_session.add(fan)
    db_session.flush()
    db_session.add(
        HostRecommendationDismissal(
            user_id=fan.id,
            host_id=host.id,
            reason="old",
            dismissed_at=datetime.now(UTC) - timedelta(days=90),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    db_session.commit()
    _clear_discover_cache()

    card = next(
        row for row in list_discover_hosts(db_session, limit=50) if row["host_id"] == host.id
    )
    affinity = load_fan_host_affinity(db_session, user_id=fan.id, own_host_ids=set())
    result = score_host_for_fan(
        db_session,
        user_id=fan.id,
        card=card,
        affinity=affinity,
        config=HostRecommendationConfig(),
    )
    assert result.breakdown.get("_exclude_dismissed") is None
    assert result.breakdown.get("dismissed") == -30
