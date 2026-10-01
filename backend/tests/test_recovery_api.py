from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import AuthSession, PasswordResetToken
from app.services import email_service, recovery_service
from test_auth_api import NEW_PASSWORD, PASSWORD, login, register


@pytest.fixture()
def outbox(monkeypatch, test_engine):
    messages = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "noreply@example.com")
    monkeypatch.setattr(settings, "recovery_rate_limit", 100)
    monkeypatch.setattr(recovery_service, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(email_service, "send_reset_email", lambda email, url: messages.append((email, url)))
    return messages


def token_from(outbox):
    return parse_qs(urlsplit(outbox[-1][1]).fragment.split("?", 1)[1])["token"][0]


def reset(client, token, password=NEW_PASSWORD):
    return client.post("/auth/reset-password", json={"token": token, "new_password": password})


def test_real_recovery_flow_with_mock_delivery(anonymous_client, db_session, outbox):
    client = anonymous_client
    register(client)
    login(client)
    existing = client.post("/auth/forgot-password", json={"email": "student@example.com"})
    missing = client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()
    assert len(outbox) == 1
    assert outbox[0][0] == "student@example.com"
    token = token_from(outbox)
    record = db_session.scalar(select(PasswordResetToken))
    assert record.token_hash != token and len(record.token_hash) == 64
    assert token not in existing.text
    assert reset(client, token, PASSWORD).status_code == 400
    assert reset(client, token).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert db_session.scalar(select(AuthSession)) is None
    db_session.refresh(record)
    assert record.consumed_at is not None
    assert reset(client, token).status_code == 400
    assert login(client).status_code == 401
    assert login(client, password=NEW_PASSWORD).status_code == 200


def test_expired_and_unknown_tokens(anonymous_client, db_session, outbox):
    register(anonymous_client)
    anonymous_client.post("/auth/forgot-password", json={"email": "student@example.com"})
    record = db_session.scalar(select(PasswordResetToken))
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    assert reset(anonymous_client, token_from(outbox)).status_code == 400
    assert reset(anonymous_client, "x" * 43).status_code == 400
    assert login(anonymous_client).status_code == 200


def test_email_change_revokes_links_sent_to_old_address(anonymous_client, outbox):
    register(anonymous_client)
    login(anonymous_client)
    anonymous_client.post("/auth/forgot-password", json={"email": "student@example.com"})
    assert anonymous_client.patch("/users/me", json={"email": "new@example.com", "current_password": PASSWORD}).status_code == 200
    assert reset(anonymous_client, token_from(outbox)).status_code == 400


def test_delivery_failure_does_not_leak_or_leave_active_token(anonymous_client, outbox, monkeypatch, caplog, db_session):
    register(anonymous_client)
    def fail(*args):
        raise RuntimeError("SECRET SMTP ERROR")
    monkeypatch.setattr(email_service, "send_reset_email", fail)
    assert anonymous_client.post("/auth/forgot-password", json={"email": "student@example.com"}).status_code == 202
    assert "SECRET SMTP ERROR" not in caplog.text
    assert "delivery failed" in caplog.text
    assert db_session.scalar(select(PasswordResetToken)) is None


def test_unconfigured_email_fails_explicitly(anonymous_client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    assert anonymous_client.post("/auth/forgot-password", json={"email": "student@example.com"}).status_code == 503


@pytest.mark.parametrize("mode,port", [("starttls", 587), ("ssl", 465)])
def test_smtp_uses_tls_and_delivers_link(monkeypatch, mode, port):
    from pydantic import SecretStr
    monkeypatch.setattr(settings, "smtp_tls_mode", mode)
    monkeypatch.setattr(settings, "smtp_port", port)
    monkeypatch.setattr(settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "smtp_password", SecretStr("smtp-secret"))
    monkeypatch.setattr(settings, "smtp_from", "sender@example.com")
    smtp_class = MagicMock()
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL" if mode == "ssl" else "SMTP", smtp_class)
    email_service.send_reset_email("recipient@example.com", "http://localhost:5173/#/reset-password?token=example")
    smtp = smtp_class.return_value.__enter__.return_value
    smtp.login.assert_called_once_with("smtp-user", "smtp-secret")
    assert smtp.starttls.called == (mode == "starttls")
    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "recipient@example.com"
    assert "token=example" in message.get_content()
