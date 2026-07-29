"""Unit tests for Fan Connect multi-select request policies."""

from app.fan_connect import constants as C
from app.fan_connect.policies import (
    normalize_request_policies,
    policies_allow_shared,
    primary_request_policy,
)


def test_normalize_nobody_exclusive():
    assert normalize_request_policies(
        [C.POLICY_NOBODY, C.POLICY_SAME_EVENT]
    ) == [C.POLICY_NOBODY]


def test_normalize_orders_and_dedupes():
    assert normalize_request_policies(
        [C.POLICY_PUBLIC_PASSPORTS, C.POLICY_SAME_EVENT, C.POLICY_SAME_EVENT]
    ) == [C.POLICY_SAME_EVENT, C.POLICY_PUBLIC_PASSPORTS]


def test_normalize_empty_defaults_to_all_open_paths():
    assert normalize_request_policies(None) == list(C.DEFAULT_REQUEST_POLICIES)
    assert normalize_request_policies([]) == list(C.DEFAULT_REQUEST_POLICIES)
    assert normalize_request_policies(["nope"]) == list(C.DEFAULT_REQUEST_POLICIES)


def test_primary_is_most_permissive():
    assert (
        primary_request_policy([C.POLICY_SAME_EVENT, C.POLICY_SAME_HOST])
        == C.POLICY_SAME_HOST
    )


def test_policies_allow_shared_or():
    shared_hosts = {
        "_has_shared_hosts": True,
        "_has_shared_events": False,
        "_has_shared_upcoming": False,
    }
    assert policies_allow_shared([C.POLICY_SAME_EVENT], shared_hosts) is False
    assert (
        policies_allow_shared(
            [C.POLICY_SAME_EVENT, C.POLICY_SAME_HOST], shared_hosts
        )
        is True
    )
    assert policies_allow_shared([C.POLICY_NOBODY], shared_hosts) is False
