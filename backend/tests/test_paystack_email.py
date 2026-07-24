import pytest
from fastapi import HTTPException

from app.payments.paystack_email import (
    is_paystack_compatible_email,
    resolve_paystack_customer_email,
)


def test_demo_test_domain_not_paystack_compatible():
    assert is_paystack_compatible_email("admin@demo.padeye.test") is False
    assert is_paystack_compatible_email("you@gmail.com") is True


def test_resolve_allows_override_for_demo_account():
    email = resolve_paystack_customer_email(
        "admin@demo.padeye.test",
        payment_email_override="real.buyer@gmail.com",
    )
    assert email == "real.buyer@gmail.com"


def test_resolve_blocks_demo_without_override():
    with pytest.raises(HTTPException) as exc:
        resolve_paystack_customer_email("admin@demo.padeye.test")
    assert exc.value.status_code == 400
