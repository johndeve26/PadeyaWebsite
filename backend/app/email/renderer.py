"""HTML + plain-text email renderer — light body, Pàdéyá green accent only."""

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any

from app.email.config import BRAND_NAME, email_runtime
from app.email.templates import TemplateDef, assert_brand_safe, get_template, render_subject

BRAND_LOGO_PATH = "/brand/padeya-logo-dark-v3.png"
EMAIL_ACCENT = "#0B6E4F"


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _context_scrub_fragments(context: dict[str, Any]) -> list[str]:
    """String context values are user/product data — not brand copy to police."""
    fragments: list[str] = []
    for value in context.values():
        if isinstance(value, str) and value.strip():
            fragments.append(value)
    return fragments


def _brand_logo_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{BRAND_LOGO_PATH}"


def _email_header_row(base_url: str) -> str:
    logo = _brand_logo_url(base_url)
    return (
        f'<tr><td style="background:{EMAIL_ACCENT};padding:20px 24px;">'
        f'<img src="{_escape(logo)}" alt="{_escape(BRAND_NAME)}" width="148" '
        f'style="display:block;border:0;height:auto;max-width:148px;" />'
        f"</td></tr>"
    )


def _email_footer_html(*, base_url: str, support_email: str) -> str:
    prefs = f"{base_url.rstrip('/')}/dashboard/settings/notifications"
    unsub = f"{base_url.rstrip('/')}/unsubscribe"
    return f"""<tr><td style="padding:8px 24px 28px;font-size:12px;line-height:1.5;color:#666666;">
          <p style="margin:0 0 8px;">Need help? <a href="mailto:{_escape(support_email)}" style="color:{EMAIL_ACCENT};">{_escape(support_email)}</a></p>
          <p style="margin:0 0 8px;"><a href="{_escape(prefs)}" style="color:{EMAIL_ACCENT};">Email preferences</a>
          · <a href="{_escape(unsub)}" style="color:{EMAIL_ACCENT};">Unsubscribe from marketing</a></p>
          <p style="margin:0;">© {_escape(BRAND_NAME)} · padeya.com</p>
        </td></tr>"""


def _validate_branded_html(doc: str, *, scrub: Iterable[str] = ()) -> str:
    scrubbed = doc
    for fragment in scrub:
        if not fragment:
            continue
        scrubbed = scrubbed.replace(_escape(fragment), "")
        scrubbed = scrubbed.replace(fragment, "")
    scrubbed = scrubbed.replace("padeya.com", "")
    for bad in ("Padeya", "Padéyá", "Pàdéyé"):
        if bad in scrubbed:
            raise ValueError(f"Forbidden brand spelling {bad!r} in email HTML")
    return doc


def _branded_email_document(
    *,
    page_title: str,
    headline: str,
    body_html: str,
    cta_block: str,
    base_url: str,
    support_email: str,
    eyebrow: str | None = None,
    validate: bool = True,
    scrub: Iterable[str] = (),
) -> str:
    eyebrow_html = ""
    if eyebrow:
        eyebrow_html = (
            f'<p style="margin:0 0 8px;font-size:13px;font-weight:700;'
            f'letter-spacing:0.06em;text-transform:uppercase;color:{EMAIL_ACCENT};">'
            f"{_escape(eyebrow)}</p>"
        )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_escape(page_title)}</title></head>
<body style="margin:0;padding:0;background:#f4f4f2;font-family:Georgia,'Times New Roman',serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f4f2;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e5e2dc;">
        {_email_header_row(base_url)}
        <tr><td style="padding:28px 24px 8px;">
          {eyebrow_html}
          <h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;color:#111111;">{_escape(headline)}</h1>
          {body_html}
          {cta_block}
        </td></tr>
        {_email_footer_html(base_url=base_url, support_email=support_email)}
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    if validate:
        return _validate_branded_html(doc, scrub=scrub)
    return doc


def split_host_announcement_body(body: str) -> list[str]:
    text = (body or "").strip()
    if not text:
        return [""]
    blocks = [p.strip() for p in text.split("\n\n") if p.strip()]
    if blocks:
        return blocks
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return lines or [text]


def resolve_cta(template: TemplateDef, context: dict[str, Any], base_url: str) -> tuple[str | None, str | None]:
    label = context.get("cta_label") or template.cta_label
    path = context.get("cta_path") or template.cta_path
    if context.get("cta_url"):
        return (str(label) if label else "Open Pàdéyá"), str(context["cta_url"])
    if not path:
        return None, None
    url = str(path)
    if url.startswith("http://") or url.startswith("https://"):
        return (str(label) if label else "Open Pàdéyá"), url
    return (str(label) if label else "Open Pàdéyá"), f"{base_url}{path}"


def render_plain(
    template: TemplateDef,
    context: dict[str, Any],
    *,
    base_url: str,
    support_email: str,
) -> str:
    paragraphs = template.body_fn(context)
    cta_label, cta_url = resolve_cta(template, context, base_url)
    lines = [template.headline, ""]
    lines.extend(paragraphs)
    if cta_url:
        lines.extend(["", f"{cta_label}: {cta_url}"])
    lines.extend(
        [
            "",
            f"— {BRAND_NAME}",
            f"Support: {support_email}",
            f"Email preferences: {base_url}/dashboard/settings/notifications",
            f"Unsubscribe from marketing: {base_url}/unsubscribe",
        ]
    )
    text = "\n".join(lines)
    assert_brand_safe(text, scrub=_context_scrub_fragments(context))
    return text


def render_html(
    template: TemplateDef,
    context: dict[str, Any],
    *,
    base_url: str,
    support_email: str,
) -> str:
    paragraphs = template.body_fn(context)
    cta_label, cta_url = resolve_cta(template, context, base_url)
    body_html = "".join(f"<p style=\"margin:0 0 14px;line-height:1.55;color:#1a1a1a;\">{_escape(p)}</p>" for p in paragraphs)
    cta_block = ""
    if cta_url and cta_label:
        cta_block = (
            f'<p style="margin:24px 0 8px;">'
            f'<a href="{_escape(cta_url)}" '
            f'style="display:inline-block;background:{EMAIL_ACCENT};color:#ffffff;'
            f'text-decoration:none;padding:12px 20px;border-radius:8px;'
            f'font-weight:700;font-size:15px;">{_escape(cta_label)}</a></p>'
        )
    return _branded_email_document(
        page_title=template.headline,
        headline=template.headline,
        body_html=body_html,
        cta_block=cta_block,
        base_url=base_url,
        support_email=support_email,
        scrub=_context_scrub_fragments(context),
    )


def render_host_announcement(
    *,
    title: str,
    body: str,
    host_name: str,
    host_slug: str,
    db=None,
) -> tuple[str, str, str]:
    """Branded host CRM blast — subject, plain text, HTML."""
    cfg = email_runtime(db=db)
    base = cfg.app_base_url.rstrip("/")
    subject = title.strip()
    paragraphs = split_host_announcement_body(body)
    host_path = f"/hosts/{host_slug.strip('/')}"
    host_url = f"{base}{host_path}"
    cta_label = f"View {host_name} on {BRAND_NAME}"

    text_lines = [
        subject,
        "",
        f"From {host_name} on {BRAND_NAME}",
        "",
        *paragraphs,
        "",
        f"{cta_label}: {host_url}",
        "",
        f"— {BRAND_NAME}",
        f"Support: {cfg.support_email}",
        f"Email preferences: {base}/dashboard/settings/notifications",
        f"Unsubscribe from marketing: {base}/unsubscribe",
    ]
    text = "\n".join(text_lines)

    body_html = "".join(
        f'<p style="margin:0 0 14px;line-height:1.55;color:#1a1a1a;">{_escape(p)}</p>'
        for p in paragraphs
    )
    cta_block = (
        f'<p style="margin:24px 0 8px;">'
        f'<a href="{_escape(host_url)}" '
        f'style="display:inline-block;background:{EMAIL_ACCENT};color:#ffffff;'
        f'text-decoration:none;padding:12px 20px;border-radius:8px;'
        f'font-weight:700;font-size:15px;">{_escape(cta_label)}</a></p>'
    )
    html_body = _branded_email_document(
        page_title=subject,
        headline=subject,
        body_html=body_html,
        cta_block=cta_block,
        base_url=base,
        support_email=cfg.support_email,
        eyebrow=f"From {host_name}",
        validate=False,
    )
    return subject, text, html_body


def render_template(name: str, context: dict[str, Any] | None = None) -> tuple[str, str, str]:
    """Return (subject, text, html)."""
    cfg = email_runtime()
    template = get_template(name)
    ctx = dict(context or {})
    subject = render_subject(template, ctx)
    text = render_plain(
        template, ctx, base_url=cfg.app_base_url, support_email=cfg.support_email
    )
    html_body = render_html(
        template, ctx, base_url=cfg.app_base_url, support_email=cfg.support_email
    )
    return subject, text, html_body
