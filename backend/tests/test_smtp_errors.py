from app.email.smtp_errors import humanize_smtp_error_for_admin


def test_humanize_from_domain_rejected() -> None:
    raw = (
        "{'bankole@example.com': (550, b'\"Your IP: 1.2.3.4 : "
        "Your domain padeya.com is not allowed in header\\nFrom\"')}"
    )
    msg = humanize_smtp_error_for_admin(
        raw,
        from_email="noreply@padeya.com",
        smtp_username="bankoleabiodun366@gmail.com",
    )
    assert "From address" in msg
    assert "bankoleabiodun366@gmail.com" in msg
    assert "padeya.com" in msg
