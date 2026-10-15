"""Email sending and templates.

Unit tests use a fake SMTP server. The last test sends a real email to Mailpit and is
skipped when Mailpit is not running (start it with ``make mail``).
"""

import json
import socket
import urllib.request
from email.message import EmailMessage
from typing import Any, Self

import pytest

from deltaweb.config import Settings
from deltaweb.services import email as email_service
from deltaweb.services.email import password_reset_email, send_email, verification_email

LINK = "http://localhost:5173/verify?token=abc&next=/folders"


class FakeSMTP:
    """Records what send_email does instead of talking to a server."""

    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[str] = []
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("quit")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login:{user}")

    def send_message(self, message: EmailMessage) -> None:
        self.calls.append("send")
        self.sent.append(message)


@pytest.fixture
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.instances = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def use_settings(monkeypatch: pytest.MonkeyPatch, **values: Any) -> None:
    monkeypatch.setattr(email_service, "get_settings", lambda: Settings(**values))


# --- send_email ---


def test_local_settings_send_to_mailpit_without_tls_or_login(fake_smtp: type[FakeSMTP]) -> None:
    send_email("ana@example.com", "Hola", "<p>Hola</p>", "Hola")

    smtp = fake_smtp.instances[0]
    assert (smtp.host, smtp.port) == ("localhost", 1025)
    assert smtp.calls == ["send", "quit"]


def test_message_has_headers_and_both_parts(fake_smtp: type[FakeSMTP]) -> None:
    send_email("ana@example.com", "Asunto", "<p>Versión HTML</p>", "Versión texto")

    message = fake_smtp.instances[0].sent[0]
    assert message["To"] == "ana@example.com"
    assert message["Subject"] == "Asunto"
    assert message["From"] == "ProyectoDeltaWeb <no-reply@deltaweb.local>"
    assert message["Message-ID"]
    assert message.get_content_type() == "multipart/alternative"
    parts = {part.get_content_type(): part.get_content() for part in message.iter_parts()}
    assert parts["text/plain"].strip() == "Versión texto"
    assert parts["text/html"].strip() == "<p>Versión HTML</p>"


def test_production_relay_uses_starttls_and_login(
    fake_smtp: type[FakeSMTP], monkeypatch: pytest.MonkeyPatch
) -> None:
    use_settings(
        monkeypatch,
        smtp_host="smtp.resend.com",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="resend",
        smtp_password="re_secret",
        mail_from="ProyectoDeltaWeb <no-reply@deltaweb.dev>",
    )

    send_email("ana@example.com", "Hola", "<p>Hola</p>", "Hola")

    smtp = fake_smtp.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.resend.com", 587)
    assert smtp.calls == ["starttls", "login:resend", "send", "quit"]
    assert smtp.sent[0]["From"] == "ProyectoDeltaWeb <no-reply@deltaweb.dev>"


def test_ssl_mode_uses_smtp_ssl(fake_smtp: type[FakeSMTP], monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeSSL(FakeSMTP):
        def __init__(self, host: str, port: int, timeout: float) -> None:
            super().__init__(host, port, timeout)
            calls.append("ssl")

    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSSL)
    use_settings(monkeypatch, smtp_host="smtp.resend.com", smtp_port=465, smtp_security="ssl")

    send_email("ana@example.com", "Hola", "<p>Hola</p>", "Hola")

    assert calls == ["ssl"]
    assert "starttls" not in fake_smtp.instances[0].calls


# --- Templates ---


@pytest.mark.parametrize(
    "template",
    [verification_email(LINK), password_reset_email(LINK, valid_minutes=30)],
    ids=["verification", "password_reset"],
)
def test_templates_have_the_link_in_html_and_text(template: email_service.Email) -> None:
    assert LINK in template.text
    assert 'href="http://localhost:5173/verify?token=abc&amp;next=/folders"' in template.html
    assert template.html.lstrip().startswith("<!doctype html>")
    assert "<" not in template.text  # the text part has no HTML


def test_verification_template() -> None:
    template = verification_email(LINK)

    assert template.subject == "Verifica tu correo"
    assert "Verificar mi correo" in template.html


def test_password_reset_template_says_when_the_link_expires() -> None:
    template = password_reset_email(LINK, valid_minutes=30)

    assert template.subject == "Recupera tu contraseña"
    assert "30 minutos" in template.html
    assert "30 minutos" in template.text


def test_html_escapes_the_link() -> None:
    template = verification_email('http://x/"><script>alert(1)</script>')

    assert "<script>" not in template.html


# --- Real delivery to Mailpit ---


def mailpit_is_running() -> bool:
    try:
        with socket.create_connection(("localhost", 1025), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not mailpit_is_running(), reason="Mailpit is not running (make mail)")
def test_real_email_reaches_mailpit() -> None:
    subject = f"test-email-{id(object())}"
    template = verification_email(LINK)

    send_email("ana@example.com", subject, template.html, template.text)

    search = f"http://localhost:8025/api/v1/search?query=subject:{subject}"
    with urllib.request.urlopen(search, timeout=5) as response:
        found = json.load(response)
    assert found["messages_count"] == 1
    message_id = found["messages"][0]["ID"]
    with urllib.request.urlopen(f"http://localhost:8025/api/v1/message/{message_id}") as r:
        message = json.load(r)
    assert LINK in message["Text"]
    assert "Verificar mi correo" in message["HTML"]

    # Leave Mailpit clean
    delete = urllib.request.Request(
        "http://localhost:8025/api/v1/messages",
        data=json.dumps({"IDs": [message_id]}).encode(),
        method="DELETE",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(delete, timeout=5)
