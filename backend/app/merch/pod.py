"""Print-on-demand provider-ready interface — manual now; no live Printful required."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.sensitive import encrypt_sensitive
from app.merch.constants import POD_INTEGRATION_STATUSES, POD_PROVIDERS
from app.merch.models import (
    EventMerchProduct,
    MerchFulfillment,
    MerchPodIntegration,
    MerchPodJob,
)
from app.payments.models import Order
from app.users.models import User

MANUAL_FULFILLMENT_NOTE = "Manual POD fulfillment required"


def job_status_label(job: MerchPodJob) -> str:
    if job.status == "manual_required" or job.manual_required:
        return MANUAL_FULFILLMENT_NOTE
    if job.status == "failed":
        return job.error_note or "POD job failed — retry or fulfill manually"
    if job.status == "fulfilled":
        return "Fulfilled"
    if job.status == "cancelled":
        return "Cancelled"
    if job.status == "queued":
        return "Queued with provider (live sync is future)"
    return job.error_note or job.status.replace("_", " ").title()


class MerchPodProvider(ABC):
    provider_name: str = "manual"

    @abstractmethod
    def create_order(self, job: MerchPodJob) -> MerchPodJob:
        raise NotImplementedError

    @abstractmethod
    def sync_status(self, job: MerchPodJob) -> MerchPodJob:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, job: MerchPodJob) -> MerchPodJob:
        raise NotImplementedError


class ManualPodProvider(MerchPodProvider):
    provider_name = "manual"

    def create_order(self, job: MerchPodJob) -> MerchPodJob:
        job.status = "manual_required"
        job.manual_required = True
        job.error_note = MANUAL_FULFILLMENT_NOTE
        return job

    def sync_status(self, job: MerchPodJob) -> MerchPodJob:
        return job

    def cancel(self, job: MerchPodJob) -> MerchPodJob:
        job.status = "cancelled"
        return job


class PlaceholderPodProvider(MerchPodProvider):
    """printful / printify / custom — store refs only; fall back to manual."""

    def __init__(self, name: str) -> None:
        self.provider_name = name

    def create_order(self, job: MerchPodJob) -> MerchPodJob:
        job.status = "manual_required"
        job.manual_required = True
        job.error_note = (
            f"{self.provider_name} live sync is not enabled — "
            f"{MANUAL_FULFILLMENT_NOTE.lower()}"
        )
        return job

    def sync_status(self, job: MerchPodJob) -> MerchPodJob:
        job.error_note = f"{self.provider_name} sync not implemented"
        return job

    def cancel(self, job: MerchPodJob) -> MerchPodJob:
        job.status = "cancelled"
        return job


def get_provider(name: str) -> MerchPodProvider:
    if name == "manual":
        return ManualPodProvider()
    if name in POD_PROVIDERS:
        return PlaceholderPodProvider(name)
    return ManualPodProvider()


def upsert_integration(
    db: Session,
    *,
    host_id: uuid.UUID,
    provider: str,
    status: str = "connected",
    provider_store_ref: str | None = None,
    credentials: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    commit: bool = True,
) -> MerchPodIntegration:
    if provider not in POD_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown POD provider")
    if status not in POD_INTEGRATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid POD integration status")
    row = db.scalar(
        select(MerchPodIntegration).where(
            MerchPodIntegration.host_id == host_id,
            MerchPodIntegration.provider == provider,
        )
    )
    if row is None:
        row = MerchPodIntegration(host_id=host_id, provider=provider)
        db.add(row)
    row.status = status
    row.provider_store_ref = (provider_store_ref or "").strip() or None
    if credentials is not None and credentials.strip():
        row.credentials_enc = encrypt_sensitive(credentials.strip())
    if provider == "manual":
        row.sync_note = "Manual POD fulfillment"
    else:
        row.sync_note = "Not synced — live Printful/Printify sync is future"
    db.flush()
    write_audit_log(
        db,
        action="merch.pod_integration_upsert",
        actor_user_id=actor_user_id,
        resource_type="merch_pod_integration",
        resource_id=str(row.id),
        details={"provider": provider, "status": status},
    )
    if commit:
        db.commit()
        db.refresh(row)
    return row


def serialize_integration(row: MerchPodIntegration) -> dict:
    return {
        "id": row.id,
        "host_id": row.host_id,
        "provider": row.provider,
        "status": row.status,
        "provider_store_ref": row.provider_store_ref,
        "sync_note": row.sync_note,
        "sync_status": row.status,
        "has_credentials": bool(row.credentials_enc),
        # Never return decrypted credentials
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_host_integrations(db: Session, *, host_id: uuid.UUID) -> list[dict]:
    rows = list(
        db.scalars(
            select(MerchPodIntegration)
            .where(MerchPodIntegration.host_id == host_id)
            .order_by(MerchPodIntegration.provider.asc())
        )
    )
    return [serialize_integration(r) for r in rows]


def serialize_job(row: MerchPodJob, *, include_host: bool = False) -> dict:
    data = {
        "id": row.id,
        "order_id": row.order_id,
        "order_item_id": row.order_item_id,
        "merch_fulfillment_id": row.merch_fulfillment_id,
        "provider": row.provider,
        "status": row.status,
        "status_label": job_status_label(row),
        "manual_required": row.manual_required,
        "error_note": row.error_note,
        "provider_ref": row.provider_ref,
        "fulfilled_at": row.fulfilled_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if include_host:
        data["host_id"] = row.host_id
    return data


def create_jobs_for_paid_order(db: Session, order: Order) -> list[MerchPodJob]:
    """Idempotent POD job creation after verified payment only."""
    jobs: list[MerchPodJob] = []
    for item in order.items or []:
        if not item.merch_product_id:
            continue
        product = db.get(EventMerchProduct, item.merch_product_id)
        if product is None or not product.print_on_demand_enabled:
            continue
        existing = db.scalar(
            select(MerchPodJob).where(MerchPodJob.order_item_id == item.id)
        )
        if existing:
            jobs.append(existing)
            continue
        fulfillment = db.scalar(
            select(MerchFulfillment).where(MerchFulfillment.order_item_id == item.id)
        )
        integration = db.scalar(
            select(MerchPodIntegration).where(
                MerchPodIntegration.host_id == product.host_id,
                MerchPodIntegration.status == "connected",
            )
        )
        provider_name = integration.provider if integration else "manual"
        job = MerchPodJob(
            order_id=order.id,
            order_item_id=item.id,
            merch_fulfillment_id=fulfillment.id if fulfillment else None,
            host_id=product.host_id,
            provider=provider_name,
            status="pending",
            manual_required=True,
        )
        provider = get_provider(provider_name)
        provider.create_order(job)
        db.add(job)
        db.flush()
        if fulfillment is not None:
            fulfillment.pod_job_id = job.id
            fulfillment.fulfillment_method = "print_on_demand"
            if fulfillment.status == "awaiting_pickup":
                fulfillment.status = "awaiting_shipment"
        jobs.append(job)
    db.flush()
    return jobs


def list_host_jobs(db: Session, *, host_id: uuid.UUID, status: str | None = None) -> list[dict]:
    stmt = select(MerchPodJob).where(MerchPodJob.host_id == host_id)
    if status:
        stmt = stmt.where(MerchPodJob.status == status)
    rows = list(db.scalars(stmt.order_by(MerchPodJob.created_at.desc())))
    return [serialize_job(r) for r in rows]


def list_admin_jobs(db: Session, *, limit: int = 200) -> list[dict]:
    rows = list(
        db.scalars(
            select(MerchPodJob).order_by(MerchPodJob.created_at.desc()).limit(limit)
        )
    )
    return [serialize_job(r, include_host=True) for r in rows]


def mark_job_manually_fulfilled(
    db: Session,
    *,
    user: User,
    job_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict:
    job = db.get(MerchPodJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="POD job not found")
    if host_id is not None and job.host_id != host_id:
        raise HTTPException(status_code=403, detail="Not your POD job")
    if job.status == "fulfilled":
        return serialize_job(job, include_host=host_id is None)
    job.status = "fulfilled"
    job.fulfilled_at = datetime.now(UTC)
    job.manual_required = False
    job.error_note = None
    if job.merch_fulfillment_id:
        fulfillment = db.get(MerchFulfillment, job.merch_fulfillment_id)
        if fulfillment is not None:
            fulfillment.status = "fulfilled"
            fulfillment.fulfilled_at = job.fulfilled_at
            fulfillment.fulfilled_by_user_id = user.id
    write_audit_log(
        db,
        action="merch.pod_manual_fulfilled",
        actor_user_id=user.id,
        resource_type="merch_pod_job",
        resource_id=str(job.id),
        details={"provider": job.provider},
    )
    db.commit()
    db.refresh(job)
    return serialize_job(job, include_host=host_id is None)


def retry_failed_job(
    db: Session,
    *,
    user: User,
    job_id: uuid.UUID,
    host_id: uuid.UUID | None = None,
) -> dict:
    """Stub retry for failed jobs — re-runs local provider create_order only."""
    job = db.get(MerchPodJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="POD job not found")
    if host_id is not None and job.host_id != host_id:
        raise HTTPException(status_code=403, detail="Not your POD job")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed POD jobs can be retried")
    provider = get_provider(job.provider)
    job.status = "pending"
    job.error_note = None
    provider.create_order(job)
    # Placeholders still land on manual_required — live provider sync is future.
    if job.provider != "manual" and job.status == "manual_required":
        job.error_note = (
            f"{job.provider} live sync is not enabled — "
            f"{MANUAL_FULFILLMENT_NOTE.lower()}"
        )
    write_audit_log(
        db,
        action="merch.pod_job_retry",
        actor_user_id=user.id,
        resource_type="merch_pod_job",
        resource_id=str(job.id),
        details={"provider": job.provider, "status": job.status},
    )
    db.commit()
    db.refresh(job)
    return serialize_job(job, include_host=host_id is None)
