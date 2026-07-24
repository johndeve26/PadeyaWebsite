"""Optional malware / AV scan hook for chat attachments.

v1: type/size/MIME/magic validation runs in ``attachments.py``. No antivirus
engine is wired — ``NoOpAttachmentScanner`` always returns clean.

Future: set ``MESSAGING_ATTACHMENT_SCANNER=clamav`` (or similar) and implement
``ClamAVAttachmentScanner`` without changing upload call sites.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    engine: str
    detail: str | None = None


class AttachmentScanner(ABC):
    @abstractmethod
    def scan(
        self,
        *,
        data: bytes,
        content_type: str,
        filename: str | None,
    ) -> ScanResult:
        raise NotImplementedError


class NoOpAttachmentScanner(AttachmentScanner):
    """Placeholder — files are validated for type/size, not AV-scanned."""

    def scan(
        self,
        *,
        data: bytes,
        content_type: str,
        filename: str | None,
    ) -> ScanResult:
        return ScanResult(
            clean=True,
            engine="noop",
            detail="Type/size validated; antivirus not configured",
        )


class ClamAVAttachmentScanner(AttachmentScanner):
    """Reserved for a future ClamAV (or compatible) integration."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "ClamAV attachment scanning is not configured yet. "
            "Set MESSAGING_ATTACHMENT_SCANNER=noop until an engine is wired."
        )

    def scan(self, **kwargs) -> ScanResult:  # type: ignore[no-untyped-def]
        raise NotImplementedError


def get_attachment_scanner() -> AttachmentScanner:
    provider = (
        get_settings().messaging_attachment_scanner or "noop"
    ).strip().lower()
    if provider in {"noop", "none", "off", ""}:
        return NoOpAttachmentScanner()
    if provider in {"clamav", "clamd"}:
        return ClamAVAttachmentScanner()
    raise ValueError(
        f"Unknown MESSAGING_ATTACHMENT_SCANNER={provider!r}. Use noop (or clamav when wired)."
    )
