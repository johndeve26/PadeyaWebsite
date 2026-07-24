"""Reuse blog sanitizer for knowledge base HTML."""

from app.blog.sanitize import sanitize_html, validate_image_url

__all__ = ["sanitize_html", "validate_image_url"]
