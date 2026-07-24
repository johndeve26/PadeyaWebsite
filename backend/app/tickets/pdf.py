"""Buyer ticket PDF — VIP-style Pàdéyá official event access pass.

Implementation approach (Pillow + qrcode, not ReportLab / HTML-to-PDF):
- Raster compose one A4 page at print DPI, then embed as **lossless** FlateDecode PDF
  (Pillow's default RGB→PDF path uses JPEG/DCT and looked soft/distorted).
- Reusable drawing helpers below (header / detail cards / QR panel / badge / footer).
- Fonts and logo are bundled under ``app/tickets/assets/`` — no remote fonts.
- No CSS, WeasyPrint, or ReportLab. QR is a fixed-size black-on-white image.
"""

from __future__ import annotations

import io
import re
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Brand tokens — #8EF012 primary (frontend globals)
_INK = (0, 0, 0)
_PAPER = (255, 255, 255)
_PRIMARY = (0x8E, 0xF0, 0x12)  # #8EF012
_PRIMARY_SOFT = (0x6B, 0xB8, 0x14)
# High-contrast text (readable on phone + B&W print)
_MUTED = (180, 180, 180)
_SOFT = (245, 245, 245)
_PAGE_BG = (8, 8, 8)
_CARD = (16, 16, 16)
_CARD_LINE = (55, 55, 55)
_SURFACE = (30, 30, 30)
_SURFACE_LINE = (70, 70, 70)
_WELL = (255, 255, 255)
_CODE_WELL = (250, 250, 250)
_AMBER = (245, 200, 76)
_DANGER_SOFT = (255, 190, 180)

# Badge styles tuned for color + grayscale print (luminance separation)
_STATUS_STYLES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    # Lime plate + black type survives B&W as light box / dark text
    "Valid ticket": (_PRIMARY, _INK),
    "Used": ((55, 55, 55), _PAPER),
    "Cancelled": ((90, 28, 28), _PAPER),
    "Refunded": ((55, 55, 55), _PAPER),
    "Pending confirmation": (_AMBER, _INK),
}

# Print-quality A4 raster (~300 DPI). Design numbers below are authored at 2×;
# ``_s()`` scales them to the output canvas.
# Exact A4 MediaBox (595.27×841.89 pt) at 300 DPI:
_DPI = 300
_PAGE_W = round(595.27 * _DPI / 72)  # 2480
_PAGE_H = round(841.89 * _DPI / 72)  # 3508
_DESIGN_W = 595 * 2  # original design canvas width
_U = _PAGE_W / _DESIGN_W  # ~2.084


def _s(n: int | float) -> int:
    """Scale a design-2× pixel length to the current output canvas."""
    return int(round(n * _U))


_MIN_LABEL_PX = _s(12)
_MIN_BODY_PX = _s(13)
_MIN_VALUE_PX = _s(15)
_QR_CARD_PAD = _s(32)  # padding inside white scan card
_QR_EXTRA_QUIET = _s(12)  # extra white margin beyond encoded quiet zone
_FOOTER_BAND = _s(88)  # reserved footer zone inside pass card

_ASSETS = Path(__file__).resolve().parent / "assets"
_FONT_REG = _ASSETS / "fonts" / "DejaVuSans.ttf"
_FONT_BOLD = _ASSETS / "fonts" / "DejaVuSans-Bold.ttf"
_LOGO_DARK = _ASSETS / "brand" / "padeya-logo-dark.png"

_BRAND = "Pàdéyá"
_SUPPORT_URL = "padeya.com/support"

# Quiet zone in modules (ISO). Never draw under QR.
_QR_QUIET_MODULES = 4
_QR_MIN_MODULE_PX = _s(7)  # larger modules for phone + print scan reliability


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    path = _FONT_BOLD if bold else _FONT_REG
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        for fallback in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        ):
            try:
                return ImageFont.truetype(fallback, size)
            except OSError:
                continue
        return ImageFont.load_default()


def _safe_text(value: str | None, *, fallback: str = "—", limit: int = 80) -> str:
    raw = (value or "").strip() or fallback
    cleaned = "".join(ch if ch.isprintable() else " " for ch in raw)
    return cleaned[:limit]


def _as_local(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def _format_date(value: datetime | None) -> str:
    dt = _as_local(value)
    if dt is None:
        return "Date TBA"
    return dt.strftime("%d %b %Y")


def _format_time(value: datetime | None) -> str:
    dt = _as_local(value)
    if dt is None:
        return "Time TBA"
    return dt.strftime("%H:%M")


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    x0: int,
    x1: int,
) -> None:
    w = _text_width(draw, text, font)
    draw.text((x0 + max(0, (x1 - x0 - w) // 2), y), text, fill=fill, font=font)


def _wrap_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int = 3,
) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if _text_width(draw, trial, font) <= max_width:
            current = trial
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            rest_words = [current] + words[words.index(word) + 1 :]
            rest = " ".join(rest_words)
            while rest and _text_width(draw, rest + "…", font) > max_width:
                rest = rest[:-1].rstrip()
            lines.append((rest + "…") if rest else "…")
            return lines
    lines.append(current)
    return lines[:max_lines]


def mask_email(email: str | None) -> str:
    """Privacy-safe email: fan2@demo.padeya.test -> fa•••@demo.padeya.test"""
    raw = (email or "").strip()
    if not raw or "@" not in raw:
        return "—"
    local, _, domain = raw.partition("@")
    if not local or not domain:
        return "—"
    keep = min(2, len(local))
    return f"{local[:keep]}•••@{domain}"


@dataclass(frozen=True)
class TicketStatusVariant:
    """Visual + copy rules for each ticket status on the PDF pass."""

    badge: str
    watermark: str | None
    show_qr: bool
    entry_valid: bool
    accent: tuple[int, int, int]
    scan_label: str
    instruction: str
    security_note: str
    placeholder: str


_DOOR_INSTRUCTION = "Show this QR code or entry code at the door."
_SECURITY_NOTE = (
    "This ticket can be used once. Cancelled, refunded, or already-used "
    "tickets will be rejected."
)


def status_variant(status: str | None) -> TicketStatusVariant:
    key = (status or "").strip().lower()
    if key == "active":
        return TicketStatusVariant(
            badge="Valid ticket",
            watermark=None,
            show_qr=True,
            entry_valid=True,
            accent=_PRIMARY,
            scan_label="Scan at entry",
            instruction=_DOOR_INSTRUCTION,
            security_note=_SECURITY_NOTE,
            placeholder="",
        )
    if key == "checked_in":
        return TicketStatusVariant(
            badge="Used",
            watermark="USED",
            show_qr=True,  # visible for audit; status must stay obvious
            entry_valid=False,
            accent=(110, 110, 110),
            scan_label="Scan at entry",
            instruction="This ticket has already been used.",
            security_note=_SECURITY_NOTE,
            placeholder="Already used",
        )
    if key in {"cancelled", "canceled", "expired", "invalid"}:
        return TicketStatusVariant(
            badge="Cancelled",
            watermark="CANCELLED",
            show_qr=False,
            entry_valid=False,
            accent=(110, 110, 110),
            scan_label="Scan at entry",
            instruction="This ticket is no longer valid.",
            security_note=_SECURITY_NOTE,
            placeholder="Not valid for entry",
        )
    if key == "refunded":
        return TicketStatusVariant(
            badge="Refunded",
            watermark="REFUNDED",
            show_qr=False,
            entry_valid=False,
            accent=(110, 110, 110),
            scan_label="Scan at entry",
            instruction="This ticket is no longer valid.",
            security_note=_SECURITY_NOTE,
            placeholder="Not valid for entry",
        )
    # pending / reserved / unknown — never imply verified access
    return TicketStatusVariant(
        badge="Pending confirmation",
        watermark=None,
        show_qr=False,
        entry_valid=False,
        accent=_AMBER,
        scan_label="Awaiting confirmation",
        instruction="Payment not verified — not valid for entry yet.",
        security_note=(
            "Access is only granted after payment is verified. "
            "This pass is not valid for entry until confirmed."
        ),
        placeholder="Pending confirmation",
    )


def status_badge_label(status: str | None) -> str:
    return status_variant(status).badge


def is_entry_valid_status(status: str | None) -> bool:
    return status_variant(status).entry_valid


def status_watermark_text(status: str | None) -> str | None:
    return status_variant(status).watermark


def _qr_image(payload: str, *, max_side: int) -> Image.Image:
    """Black-on-white QR with quiet zone. Never exceeds ``max_side`` (no clip/resize)."""
    probe = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=_QR_QUIET_MODULES,
    )
    probe.add_data(payload)
    probe.make(fit=True)
    total_modules = probe.modules_count + (2 * _QR_QUIET_MODULES)
    # Fit within max_side first; prefer larger modules when space allows
    box = max(1, max_side // max(total_modules, 1))
    if total_modules * _QR_MIN_MODULE_PX <= max_side:
        box = max(box, _QR_MIN_MODULE_PX)
    while total_modules * box > max_side and box > 1:
        box -= 1

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box,
        border=_QR_QUIET_MODULES,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # Hard guarantee — never return a bitmap wider/taller than the stage
    if img.width > max_side or img.height > max_side:
        # Integer-safe downscale by nearest neighbor only if generator overshot
        scale = min(max_side / img.width, max_side / img.height)
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        img = img.resize((new_w, new_h), Image.Resampling.NEAREST)
    return img


def _load_logo(max_w: int, max_h: int) -> Image.Image | None:
    if not _LOGO_DARK.is_file():
        return None
    logo = Image.open(_LOGO_DARK).convert("RGBA")
    logo.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return logo


def _page_atmosphere() -> Image.Image:
    """Near-black canvas with a soft green wash in the upper third only."""
    base = Image.new("RGB", (_PAGE_W, _PAGE_H), _PAGE_BG)
    glow = Image.new("RGB", (_PAGE_W, _PAGE_H), _PAGE_BG)
    gdraw = ImageDraw.Draw(glow)
    # Soft lime bloom behind the header — never reaches the QR body
    for i, strength in enumerate((55, 36, 22, 12)):
        pad = _s(60 + i * 90)
        color = (
            min(255, _PRIMARY[0] * strength // 55),
            min(255, _PRIMARY[1] * strength // 55),
            min(255, _PRIMARY[2] * strength // 55),
        )
        gdraw.ellipse(
            (
                _PAGE_W // 2 - _s(280) - pad,
                -_s(200) - pad,
                _PAGE_W // 2 + _s(280) + pad,
                _s(320) + pad,
            ),
            fill=color,
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=_s(64)))
    return Image.blend(base, glow, 0.18)


def _pdf_escape(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode(
        "latin-1", errors="replace"
    )


def _encode_lossless_pdf(img: Image.Image, *, dpi: float, title: str = "Pàdéyá ticket") -> bytes:
    """Embed RGB image as FlateDecode (zlib) — no JPEG banding/blur on text or QR."""
    rgb = img.convert("RGB")
    width, height = rgb.size
    raw = zlib.compress(rgb.tobytes(), level=9)
    page_w = width * 72.0 / dpi
    page_h = height * 72.0 / dpi

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    add(
        b"<< /Type /Catalog /Pages 2 0 R >>"
    )
    add(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {page_w:.4f} {page_h:.4f}] "
            f"/Resources << /XObject << /Im0 4 0 R >> /ProcSet [/PDF /ImageC] >> "
            f"/Contents 5 0 R >>"
        ).encode("ascii")
    )
    add(
        (
            f"<< /Type /XObject /Subtype /Image "
            f"/Width {width} /Height {height} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
            f"/Filter /FlateDecode /Length {len(raw)} >>\n"
            f"stream\n"
        ).encode("ascii")
        + raw
        + b"\nendstream"
    )
    content = (
        f"q\n{page_w:.4f} 0 0 {page_h:.4f} 0 0 cm\n/Im0 Do\nQ\n"
    ).encode("ascii")
    add(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"endstream")
    add(
        b"<< /Title ("
        + _pdf_escape(title)
        + b") /Producer (Padeya) /Creator (Padeya) >>"
    )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))
    out.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    return out.getvalue()


def draw_status_badge(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    label: str,
    font: ImageFont.ImageFont,
) -> int:
    """Status pill (Valid ticket / Used / Cancelled / …). Returns badge width."""
    fill, text = _STATUS_STYLES.get(label, _STATUS_STYLES["Pending confirmation"])
    pad_x, pad_y = _s(12), _s(7)
    tw = _text_width(draw, label, font)
    w = tw + pad_x * 2
    h = _s(28)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=_s(14), fill=fill)
    draw.text((x + pad_x, y + pad_y - 1), label, fill=text, font=font)
    return w


# Back-compat alias used by older call sites / tests
_draw_badge = draw_status_badge


def _draw_status_watermark(
    img: Image.Image,
    *,
    card: tuple[int, int, int, int],
    text: str,
) -> Image.Image:
    """Large diagonal stamp so non-valid passes cannot look valid."""
    base = img.convert("RGBA")
    font = _font(_s(86), bold=True)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = _text_width(probe, text, font)
    th = _s(100)
    stamp = Image.new("RGBA", (tw + _s(80), th + _s(40)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    # USED stays lighter so audit QR remains readable underneath
    colors = {
        "USED": (170, 170, 170, 110),
        "CANCELLED": (200, 60, 50, 160),
        "REFUNDED": (160, 160, 160, 150),
    }
    fill = colors.get(text, (180, 180, 180, 140))
    sd.text((_s(40), _s(20)), text, fill=fill, font=font)
    stamp = stamp.rotate(28, expand=True, resample=Image.Resampling.BICUBIC)

    x0, y0, x1, y1 = card
    cx = x0 + (x1 - x0 - stamp.width) // 2
    # Bias watermark toward upper/mid card so it doesn't sit on the QR stage
    cy = y0 + int((y1 - y0) * 0.28) - stamp.height // 2
    base.alpha_composite(stamp, dest=(max(0, cx), max(0, cy)))
    return base.convert("RGB")


def _perforation(
    draw: ImageDraw.ImageDraw,
    *,
    y: int,
    x0: int,
    x1: int,
    fill_bg: tuple[int, int, int],
) -> None:
    draw.line((x0 + _s(32), y, x1 - _s(32), y), fill=(55, 55, 55), width=max(1, _s(1)))
    dash, gap = _s(8), _s(7)
    x = x0 + _s(40)
    while x < x1 - _s(40):
        draw.line(
            (x, y, min(x + dash, x1 - _s(40)), y),
            fill=(72, 72, 72),
            width=max(1, _s(1)),
        )
        x += dash + gap
    r = _s(11)
    draw.ellipse((x0 - r, y - r, x0 + r, y + r), fill=fill_bg)
    draw.ellipse((x1 - r, y - r, x1 + r, y + r), fill=fill_bg)


def draw_ticket_detail_card(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
) -> None:
    """One compact detail chip with wrapped value (no overflow)."""
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(
        box,
        radius=_s(14),
        fill=_SURFACE,
        outline=_SURFACE_LINE,
        width=max(1, _s(1)),
    )
    pad = _s(12)
    draw.text((x0 + pad, y0 + _s(10)), label.upper(), fill=_MUTED, font=label_font)
    max_w = max(_s(40), (x1 - x0) - pad * 2)
    lines = _wrap_lines(draw, value, font=value_font, max_width=max_w, max_lines=2)
    vy = y0 + _s(30)
    for line in lines:
        draw.text((x0 + pad, vy), line, fill=_PAPER, font=value_font)
        vy += _s(20)


_detail_chip = draw_ticket_detail_card


def _estimate_scan_card_height(*, column_width: int, qr_side: int) -> int:
    return (
        _QR_CARD_PAD
        + _s(28)  # scan label
        + _QR_EXTRA_QUIET
        + qr_side
        + _QR_EXTRA_QUIET
        + _s(16)
        + _s(58)  # entry code well
        + _s(14)
        + _s(36)  # instruction
        + _QR_CARD_PAD
    )


def draw_qr_panel(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    width: int,
    qr_payload: str,
    entry_code: str,
    label_font: ImageFont.ImageFont,
    code_font: ImageFont.ImageFont,
    code_tracking_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
    variant: TicketStatusVariant,
) -> int:
    """White QR panel with fixed-size QR image, entry code, and instruction.

    Returns the y coordinate just below the panel. Never wider than ``width``.
    """
    card_w = width  # hard cap: never overflow the column / page
    card_pad = _QR_CARD_PAD
    # QR must fit inside card with pad + extra quiet margin on all sides
    max_qr_side = max(
        _s(200),
        card_w - (card_pad * 2) - (_QR_EXTRA_QUIET * 2),
    )
    show_qr = variant.show_qr and bool(qr_payload.strip())
    if show_qr:
        qr = _qr_image(qr_payload, max_side=max_qr_side)
        qr_w, qr_h = qr.size
        # Safety: if generator exceeded budget, do not paste clipped — regenerate smaller
        if qr_w > max_qr_side:
            qr = _qr_image(qr_payload, max_side=max_qr_side - _s(8))
            qr_w, qr_h = qr.size
    else:
        qr = None
        qr_w = qr_h = min(max_qr_side, _s(260))

    code = _safe_text(entry_code, fallback="PDY", limit=40)
    spaced = "  ".join(list(code))

    header_h = _s(28)
    gap_after_qr = _s(16)
    code_block_h = _s(58)
    instruct_h = _s(36)
    qr_block_h = _QR_EXTRA_QUIET + qr_h + _QR_EXTRA_QUIET
    card_h = (
        card_pad
        + header_h
        + qr_block_h
        + gap_after_qr
        + code_block_h
        + _s(14)
        + instruct_h
        + card_pad
    )
    card_x = x

    # Border drawn inside the box so the card never bleeds past `width`
    draw.rounded_rectangle(
        (card_x, y, card_x + card_w - 1, y + card_h - 1),
        radius=_s(18),
        fill=_WELL,
        outline=(200, 200, 200),
        width=max(1, _s(1)),
    )

    cy = y + card_pad
    _draw_centered(
        draw,
        cy,
        variant.scan_label,
        font=label_font,
        fill=_INK,
        x0=card_x,
        x1=card_x + card_w,
    )
    cy += header_h

    # White stage with extra quiet margin — no clipping
    stage_w = qr_w + _QR_EXTRA_QUIET * 2
    stage_h = qr_h + _QR_EXTRA_QUIET * 2
    stage_x = card_x + (card_w - stage_w) // 2
    draw.rectangle(
        (stage_x, cy, stage_x + stage_w, cy + stage_h),
        fill=_PAPER,
    )
    qr_x = stage_x + _QR_EXTRA_QUIET
    qr_y = cy + _QR_EXTRA_QUIET
    if qr is not None:
        img.paste(qr, (qr_x, qr_y))
    else:
        _draw_centered(
            draw,
            cy + stage_h // 2 - _s(10),
            variant.placeholder or "Not valid for entry",
            font=label_font,
            fill=(80, 80, 80),
            x0=card_x,
            x1=card_x + card_w,
        )
    cy += stage_h + gap_after_qr

    well_h = code_block_h
    well_m = card_pad
    well = (card_x + well_m, cy, card_x + card_w - well_m, cy + well_h)
    draw.rounded_rectangle(
        well,
        radius=_s(10),
        fill=_CODE_WELL,
        outline=(200, 200, 200),
        width=max(1, _s(1)),
    )
    _draw_centered(
        draw,
        cy + _s(8),
        "Entry code",
        font=label_font,
        fill=(70, 70, 70),
        x0=well[0],
        x1=well[2],
    )
    code_font_use = code_tracking_font
    display = spaced
    if _text_width(draw, display, code_font_use) > (well[2] - well[0] - _s(20)):
        display = code
        code_font_use = code_font
    _draw_centered(
        draw,
        cy + _s(28),
        display,
        font=code_font_use,
        fill=_INK if variant.entry_valid else (70, 70, 70),
        x0=well[0],
        x1=well[2],
    )
    cy += well_h + _s(14)
    for line in _wrap_lines(
        draw,
        variant.instruction,
        font=body_font,
        max_width=card_w - card_pad * 2,
        max_lines=2,
    ):
        _draw_centered(
            draw,
            cy,
            line,
            font=body_font,
            fill=(55, 55, 55),
            x0=card_x,
            x1=card_x + card_w,
        )
        cy += _s(16)
    return y + card_h


_draw_qr_scan_card = draw_qr_panel


def draw_ticket_header(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    card: tuple[int, int, int, int],
    pad: int,
    inner_l: int,
    inner_r: int,
    title_lines: list[str],
    variant: TicketStatusVariant,
    brand_font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
    title_font: ImageFont.ImageFont,
) -> int:
    """Dark premium header: logo, status badge, Pàdéyá ticket label, event title.

    Returns ``header_bottom`` y (content below this starts the body).
    """
    card_x0, card_y0, card_x1, _card_y1 = card
    accent = variant.accent
    header_body_h = _s(52) + _s(24) + len(title_lines) * _s(42) + _s(12)
    header_bottom = card_y0 + pad + header_body_h

    draw.rounded_rectangle(
        (card_x0 + 1, card_y0 + 1, card_x1 - 1, header_bottom),
        radius=_s(27),
        fill=(12, 12, 12),
    )
    draw.rectangle(
        (card_x0 + 1, header_bottom - _s(28), card_x1 - 1, header_bottom),
        fill=(12, 12, 12),
    )
    draw.rectangle(
        (card_x0 + _s(40), header_bottom - _s(3), card_x0 + _s(120), header_bottom),
        fill=accent,
    )

    y = card_y0 + pad
    logo = _load_logo(_s(180), _s(42))
    if logo is not None:
        img.paste(logo, (inner_l, y), logo)
    else:
        draw.text((inner_l, y), _BRAND, fill=_PAPER, font=brand_font)

    badge_w = _text_width(draw, variant.badge, label_font) + _s(24)
    draw_status_badge(
        draw,
        x=max(inner_l, inner_r - badge_w),
        y=y + _s(4),
        label=variant.badge,
        font=label_font,
    )

    y += _s(50)
    top_label_fill = accent if variant.entry_valid else _MUTED
    draw.text((inner_l, y), "Pàdéyá ticket", fill=top_label_fill, font=label_font)
    y += _s(24)
    for line in title_lines:
        draw.text((inner_l, y), line, fill=_PAPER, font=title_font)
        y += _s(42)

    return header_bottom


def draw_ticket_detail_cards(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    width: int,
    fields: list[tuple[str, str]],
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
    chip_h: int | None = None,
    chip_gap: int | None = None,
    bottom_limit: int | None = None,
) -> int:
    """2-column grid of detail chips. ``fields`` are (label, value). Returns bottom y."""
    if chip_h is None:
        chip_h = _s(70)
    if chip_gap is None:
        chip_gap = _s(10)
    half = (width - chip_gap) // 2
    # Pair consecutive fields; last odd/full-width email handled by caller flags
    # Convention: last field alone if label == "Email", else pair
    ly = y
    i = 0
    while i < len(fields):
        if bottom_limit is not None and ly + chip_h > bottom_limit:
            break
        label, value = fields[i]
        # Email + location stay full width so values don't truncate mid-chip
        full = label.lower() in {"email", "location"} or (
            i == len(fields) - 1 and len(fields) % 2 == 1
        )
        if full:
            draw_ticket_detail_card(
                draw,
                box=(x, ly, x + width, ly + chip_h),
                label=label,
                value=value,
                label_font=label_font,
                value_font=value_font,
            )
            ly += chip_h + chip_gap
            i += 1
            continue
        if i + 1 < len(fields) and fields[i + 1][0].lower() not in {
            "email",
            "location",
        }:
            l2, v2 = fields[i + 1]
            draw_ticket_detail_card(
                draw,
                box=(x, ly, x + half, ly + chip_h),
                label=label,
                value=value,
                label_font=label_font,
                value_font=value_font,
            )
            draw_ticket_detail_card(
                draw,
                box=(x + half + chip_gap, ly, x + width, ly + chip_h),
                label=l2,
                value=v2,
                label_font=label_font,
                value_font=value_font,
            )
            ly += chip_h + chip_gap
            i += 2
        else:
            draw_ticket_detail_card(
                draw,
                box=(x, ly, x + width, ly + chip_h),
                label=label,
                value=value,
                label_font=label_font,
                value_font=value_font,
            )
            ly += chip_h + chip_gap
            i += 1
    return ly


def draw_security_footer(
    draw: ImageDraw.ImageDraw,
    *,
    inner_l: int,
    inner_r: int,
    footer_top: int,
    card_bottom: int,
    pad: int,
    variant: TicketStatusVariant,
    label_font: ImageFont.ImageFont,
    foot_font: ImageFont.ImageFont,
) -> None:
    """Pinned security note + Powered by Pàdéyá / padeya.com."""
    draw.line(
        (inner_l, footer_top, inner_r, footer_top),
        fill=_CARD_LINE,
        width=max(1, _s(1)),
    )
    fy = footer_top + _s(14)
    inner_w = inner_r - inner_l
    for line in _wrap_lines(
        draw, variant.security_note, font=foot_font, max_width=inner_w, max_lines=2
    ):
        draw.text((inner_l, fy), line, fill=_MUTED, font=foot_font)
        fy += _s(17)

    brand_y = card_bottom - pad - _s(18)
    draw.text((inner_l, brand_y), f"Powered by {_BRAND}", fill=_SOFT, font=label_font)
    domain = "padeya.com"
    sw = _text_width(draw, domain, foot_font)
    draw.text(
        (inner_r - sw, brand_y + 1),
        domain,
        fill=_PAPER if variant.entry_valid else _MUTED,
        font=foot_font,
    )


def render_ticket_pdf(
    *,
    event_title: str,
    ticket_type_name: str,
    public_code: str,
    holder_name: str,
    holder_email: str,
    qr_payload: str,
    starts_at: datetime | None,
    location_label: str | None,
    host_name: str | None,
    status: str | None = None,
) -> bytes:
    """Render an A4 VIP-style official event access pass.

    Tuned for phone PDF viewers, print, email attachment, and dashboard download:
    high contrast, no QR clipping/overflow, footer pinned to card bottom.
    """
    img = _page_atmosphere()
    draw = ImageDraw.Draw(img)
    variant = status_variant(status)
    accent = variant.accent

    # Print-safe outer margin
    side = _s(48)
    card_x0 = side
    card_x1 = _PAGE_W - side
    pad = _s(36)
    inner_w = (card_x1 - card_x0) - pad * 2

    # Readable type at 300 DPI (design sizes × layout scale)
    brand_font = _font(_s(26), bold=True)
    label_font = _font(max(_MIN_LABEL_PX, _s(12)), bold=True)
    title_font = _font(_s(36), bold=True)
    value_font = _font(max(_MIN_VALUE_PX, _s(15)), bold=True)
    code_font = _font(_s(18), bold=True)
    code_track_font = _font(_s(15), bold=True)
    body_font = _font(max(_MIN_BODY_PX, _s(13)))
    foot_font = _font(max(_MIN_BODY_PX, _s(13)))

    title = _safe_text(event_title, fallback="Event", limit=56)
    title_lines = _wrap_lines(
        draw, title, font=title_font, max_width=inner_w - _s(8), max_lines=2
    )

    col_gap = _s(20)
    left_w = int(inner_w * 0.40)
    right_w = inner_w - left_w - col_gap
    qr_budget = max(
        _s(200),
        right_w - (_QR_CARD_PAD * 2) - (_QR_EXTRA_QUIET * 2),
    )
    scan_card_h = _estimate_scan_card_height(column_width=right_w, qr_side=qr_budget)

    chip_h = _s(70)
    chip_gap = _s(10)
    # type|date, time, location, host|holder, email ≈ 5 rows
    left_block_h = 5 * chip_h + 4 * chip_gap

    header_body_h = _s(52) + _s(24) + len(title_lines) * _s(42) + _s(12)
    body_h = max(left_block_h, scan_card_h)
    # Card height = content + reserved footer band (footer always at bottom)
    card_h = (
        pad
        + header_body_h
        + _s(24)
        + _s(22)
        + body_h
        + _s(20)
        + _FOOTER_BAND
        + pad
    )
    # Keep pass on one page with breathing room
    max_card_h = _PAGE_H - _s(72)
    if card_h > max_card_h:
        # Shrink QR budget rather than clipping text/footer
        overflow = card_h - max_card_h
        qr_budget = max(_s(180), qr_budget - overflow)
        scan_card_h = _estimate_scan_card_height(
            column_width=right_w, qr_side=qr_budget
        )
        body_h = max(left_block_h, scan_card_h)
        card_h = (
            pad
            + header_body_h
            + _s(24)
            + _s(22)
            + body_h
            + _s(20)
            + _FOOTER_BAND
            + pad
        )

    card_y0 = max(_s(36), (_PAGE_H - card_h) // 2)
    card_y1 = min(card_y0 + card_h, _PAGE_H - _s(36))
    inner_l = card_x0 + pad
    inner_r = card_x1 - pad
    footer_top = card_y1 - pad - _FOOTER_BAND

    draw.rounded_rectangle(
        (card_x0, card_y0, card_x1, card_y1),
        radius=_s(28),
        fill=_CARD,
        outline=_CARD_LINE,
        width=max(2, _s(2)),
    )

    header_bottom = draw_ticket_header(
        img,
        draw,
        card=(card_x0, card_y0, card_x1, card_y1),
        pad=pad,
        inner_l=inner_l,
        inner_r=inner_r,
        title_lines=title_lines,
        variant=variant,
        brand_font=brand_font,
        label_font=label_font,
        title_font=title_font,
    )

    y = header_bottom + _s(18)
    _perforation(draw, y=y, x0=card_x0, x1=card_x1, fill_bg=_PAGE_BG)
    y += _s(22)

    body_bottom_limit = footer_top - _s(12)
    left_x = inner_l
    right_x = inner_l + left_w + col_gap

    fields: list[tuple[str, str]] = [
        ("Ticket type", _safe_text(ticket_type_name, fallback="Ticket", limit=28)),
        ("Date", _format_date(starts_at)),
        ("Time", _format_time(starts_at)),
        ("Location", _safe_text(location_label, fallback="Location TBA", limit=40)),
        ("Host", _safe_text(host_name, fallback="—", limit=32) if host_name else "—"),
        ("Holder", _safe_text(holder_name, fallback="Guest", limit=36)),
        ("Email", mask_email(holder_email)),
    ]
    entry_code = _safe_text(public_code, fallback="—", limit=40)

    draw_ticket_detail_cards(
        draw,
        x=left_x,
        y=y,
        width=left_w,
        fields=fields,
        label_font=label_font,
        value_font=value_font,
        chip_h=chip_h,
        chip_gap=chip_gap,
        bottom_limit=body_bottom_limit,
    )

    scan_payload = qr_payload if variant.show_qr else ""
    draw_qr_panel(
        img,
        draw,
        x=right_x,
        y=y,
        width=right_w,
        qr_payload=scan_payload,
        entry_code=entry_code,
        label_font=label_font,
        code_font=code_font,
        code_tracking_font=code_track_font,
        body_font=body_font,
        variant=variant,
    )

    if variant.watermark:
        img = _draw_status_watermark(
            img,
            card=(card_x0, card_y0, card_x1, footer_top),
            text=variant.watermark,
        )
        draw = ImageDraw.Draw(img)

    draw_security_footer(
        draw,
        inner_l=inner_l,
        inner_r=inner_r,
        footer_top=footer_top,
        card_bottom=card_y1,
        pad=pad,
        variant=variant,
        label_font=label_font,
        foot_font=foot_font,
    )

    # Lossless FlateDecode embed — Pillow's RGB→PDF path uses JPEG and looked soft.
    return _encode_lossless_pdf(
        img,
        dpi=float(_DPI),
        title=f"Pàdéyá ticket — {_safe_text(event_title, fallback='Event', limit=48)}",
    )


def render_order_receipt_pdf(
    *,
    order_reference: str,
    buyer_name: str,
    buyer_email: str,
    event_title: str | None,
    host_name: str | None,
    line_items: list[str],
    total_amount: str,
    currency: str,
    pickups: list[tuple[str, str, str | None]] | None = None,
) -> bytes:
    """Merch-only or summary receipt.

    ``pickups`` is an optional list of (item_label, pickup_code, qr_token)
    for merch lines fulfilled by in-person pickup — each with a scannable
    QR the buyer can present at the stand (app.merch.qr_pickup). Shipping/
    print-on-demand lines and already-picked-up/cancelled ones are omitted
    by the caller.
    """
    img = _page_atmosphere()
    draw = ImageDraw.Draw(img)
    side = _s(48)
    card_x0 = side
    card_x1 = _PAGE_W - side
    pad = _s(36)
    inner_w = (card_x1 - card_x0) - pad * 2
    title_font = _font(_s(32), bold=True)
    label_font = _font(max(_MIN_LABEL_PX, _s(12)), bold=True)
    body_font = _font(max(_MIN_BODY_PX, _s(14)))
    value_font = _font(max(_MIN_VALUE_PX, _s(16)), bold=True)

    y = pad + _s(40)
    draw.text((card_x0 + pad, y), _BRAND, fill=_PRIMARY, font=_font(_s(24), bold=True))
    y += _s(44)
    draw.text((card_x0 + pad, y), "Order receipt", fill=_PAPER, font=title_font)
    y += _s(48)
    draw.text(
        (card_x0 + pad, y),
        _safe_text(order_reference, fallback="Order", limit=32),
        fill=_PAPER,
        font=value_font,
    )
    y += _s(36)
    draw.text((card_x0 + pad, y), "Buyer", fill=_MUTED, font=label_font)
    y += _s(22)
    draw.text(
        (card_x0 + pad, y),
        _safe_text(buyer_name, fallback="Buyer", limit=48),
        fill=_PAPER,
        font=body_font,
    )
    y += _s(28)
    draw.text(
        (card_x0 + pad, y),
        _safe_text(buyer_email, fallback="", limit=56),
        fill=_MUTED,
        font=body_font,
    )
    y += _s(40)
    if event_title:
        draw.text((card_x0 + pad, y), "Event", fill=_MUTED, font=label_font)
        y += _s(22)
        draw.text(
            (card_x0 + pad, y),
            _safe_text(event_title, limit=56),
            fill=_PAPER,
            font=body_font,
        )
        y += _s(32)
    if host_name:
        draw.text((card_x0 + pad, y), "Host", fill=_MUTED, font=label_font)
        y += _s(22)
        draw.text(
            (card_x0 + pad, y),
            _safe_text(host_name, limit=48),
            fill=_PAPER,
            font=body_font,
        )
        y += _s(32)
    draw.text((card_x0 + pad, y), "Items", fill=_MUTED, font=label_font)
    y += _s(22)
    for line in line_items[:12]:
        draw.text(
            (card_x0 + pad, y),
            _safe_text(line, limit=72),
            fill=_PAPER,
            font=body_font,
        )
        y += _s(26)
    y += _s(16)
    draw.text(
        (card_x0 + pad, y),
        f"Total ({currency})",
        fill=_MUTED,
        font=label_font,
    )
    y += _s(24)
    draw.text((card_x0 + pad, y), total_amount, fill=_PRIMARY, font=value_font)
    y += _s(48)

    if pickups:
        max_shown = 3
        qr_max_side = _s(170)
        qr_pad = _s(14)
        small_font = _font(max(_MIN_LABEL_PX, _s(11)))
        draw.text((card_x0 + pad, y), "Pickup", fill=_MUTED, font=label_font)
        y += _s(24)
        for label, code, token in pickups[:max_shown]:
            draw.text(
                (card_x0 + pad, y),
                _safe_text(label, limit=48),
                fill=_PAPER,
                font=body_font,
            )
            y += _s(24)
            draw.text((card_x0 + pad, y), code, fill=_PRIMARY, font=value_font)
            y += _s(30)
            if token:
                qr_img = _qr_image(token, max_side=qr_max_side)
                box_w = qr_img.width + qr_pad * 2
                box_h = qr_img.height + qr_pad * 2
                draw.rectangle(
                    [card_x0 + pad, y, card_x0 + pad + box_w, y + box_h],
                    fill=_PAPER,
                )
                img.paste(qr_img, (card_x0 + pad + qr_pad, y + qr_pad))
                y += box_h + _s(10)
                draw.text(
                    (card_x0 + pad, y),
                    "Show this QR at pickup",
                    fill=_MUTED,
                    font=small_font,
                )
                y += _s(28)
            y += _s(10)
        if len(pickups) > max_shown:
            draw.text(
                (card_x0 + pad, y),
                f"+{len(pickups) - max_shown} more pickup code(s) — see your dashboard",
                fill=_MUTED,
                font=body_font,
            )
            y += _s(28)
        y += _s(12)

    draw.text(
        (card_x0 + pad, y),
        "Payment confirmed on Pàdéyá. Keep this receipt for your records.",
        fill=_MUTED,
        font=body_font,
    )

    return _encode_lossless_pdf(
        img,
        dpi=float(_DPI),
        title=f"Pàdéyá order — {order_reference}",
    )


def pdf_filename_for_code(public_code: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", (public_code or "ticket").strip())
    safe = safe.strip("-")[:48] or "ticket"
    return f"padeya-ticket-{safe}.pdf"
