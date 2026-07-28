"""Extract and validate JSON from model text for Blog AI Studio."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_REPAIR_INSTRUCTION = (
    "Your previous reply was not valid JSON for the required schema. "
    "Reply again with JSON only — no markdown fences, no commentary."
)


def extract_json_object(text: str) -> dict | list | None:
    raw = (text or "").strip()
    if not raw:
        return None
    # Strip common markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, (dict, list)):
            return parsed
    except json.JSONDecodeError:
        pass
    # Find first {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw.find(opener)
        end = raw.rfind(closer)
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                continue
    return None


def parse_model(text: str, model: type[T]) -> T:
    data = extract_json_object(text)
    if data is None:
        raise ValueError("No JSON object found in model output")
    if isinstance(data, list):
        # Allow list roots for titles/faqs wrappers by wrapping when model expects object
        raise ValueError("Expected JSON object, got list")
    return model.model_validate(data)


def parse_list_field(text: str, *, field: str, item_model: type[T]) -> list[T]:
    data = extract_json_object(text)
    if data is None:
        raise ValueError("No JSON found in model output")
    if isinstance(data, list):
        return [item_model.model_validate(x) for x in data]
    if isinstance(data, dict) and field in data:
        items = data[field]
        if not isinstance(items, list):
            raise ValueError(f"Field {field} is not a list")
        return [item_model.model_validate(x) for x in items]
    raise ValueError(f"Missing list field {field}")


def repair_user_prompt(original_user_prompt: str) -> str:
    return f"{original_user_prompt}\n\n{_REPAIR_INSTRUCTION}"


def try_parse_or_repair_interface(
    *,
    first_text: str,
    model: type[T],
    repair_fn,
) -> tuple[T | None, str | None]:
    """
    Validate first_text; on failure call repair_fn() once for a second attempt.
    repair_fn should return new model text. Returns (parsed, error_code).
    """
    try:
        return parse_model(first_text, model), None
    except (ValueError, ValidationError):
        pass
    try:
        second = repair_fn()
        return parse_model(second, model), None
    except (ValueError, ValidationError):
        return None, "malformed_json"
    except Exception:
        return None, "parse_failed"
