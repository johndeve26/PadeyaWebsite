"""Central transactional email system for Pàdéyá."""

from app.email.service import enqueue_template, send_template

__all__ = ["enqueue_template", "send_template"]
