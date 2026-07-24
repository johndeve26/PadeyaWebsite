"""Prompt rendering helpers (deterministic, testable)."""

from __future__ import annotations

import re
from string import Formatter


_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def extract_placeholders(template: str) -> list[str]:
    names: list[str] = []
    for _, field_name, _, _ in Formatter().parse(template):
        if field_name and field_name not in names:
            names.append(field_name)
    return names


def render_prompt(template: str, context: dict[str, str]) -> str:
    """Render `{placeholders}` with missing keys replaced by empty string.

    Does not evaluate expressions — only simple named fields.
    """
    safe = {k: str(v) if v is not None else "" for k, v in context.items()}

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return safe.get(key, "")

    return _PLACEHOLDER_RE.sub(repl, template)
