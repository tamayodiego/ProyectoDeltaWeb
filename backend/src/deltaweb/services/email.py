"""Sending email over SMTP, and the templates for account emails.

Every message has an HTML part and a plain-text part ("multipart/alternative"): clients
that cannot or will not show HTML use the text one. The SMTP server comes from the
settings: Mailpit locally, a provider's relay (Resend, Brevo...) in production.

The templates are in Spanish because they are read by the users; only the code is in
English. Links are built from ``settings.app_url``.
"""

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape

from deltaweb.config import get_settings


@dataclass(frozen=True)
class Email:
    subject: str
    html: str
    text: str


def send_email(to: str, subject: str, html: str, text: str) -> None:
    """Send one email through the configured SMTP server. Raises smtplib/OSError on failure."""
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid()
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
    with smtp_class(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
    ) as smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


# --- Templates ---


def _layout(title: str, body: str) -> str:
    """Simple HTML wrapper with inline styles (many email clients ignore <style> blocks)."""
    return f"""\
<!doctype html>
<html lang="es">
  <body style="margin:0;padding:24px;background:#f4f4f5;font-family:Arial,sans-serif;color:#18181b">
    <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:8px;padding:32px">
      <h1 style="margin:0 0 16px;font-size:20px">{escape(title)}</h1>
      {body}
      <p style="margin:32px 0 0;font-size:12px;color:#71717a">ProyectoDeltaWeb</p>
    </div>
  </body>
</html>
"""


def _button(url: str, label: str) -> str:
    href = escape(url, quote=True)
    return (
        f'<p style="margin:24px 0"><a href="{href}" style="background:#2563eb;color:#ffffff;'
        f'padding:12px 20px;border-radius:6px;text-decoration:none;display:inline-block">'
        f"{escape(label)}</a></p>"
        f'<p style="font-size:13px;color:#52525b">Si el botón no funciona, copia este enlace '
        f'en tu navegador:<br><a href="{href}" style="color:#2563eb">{escape(url)}</a></p>'
    )


def verification_email(link: str) -> Email:
    """ "Verifica tu correo": sent after registering."""
    subject = "Verifica tu correo"
    html = _layout(
        subject,
        "<p>¡Bienvenido a ProyectoDeltaWeb! Para confirmar que este correo es tuyo, "
        "pulsa el botón:</p>"
        + _button(link, "Verificar mi correo")
        + '<p style="font-size:13px;color:#52525b">Si no creaste una cuenta, ignora este '
        "mensaje.</p>",
    )
    text = (
        "¡Bienvenido a ProyectoDeltaWeb!\n\n"
        "Para confirmar que este correo es tuyo, abre este enlace:\n"
        f"{link}\n\n"
        "Si no creaste una cuenta, ignora este mensaje.\n"
    )
    return Email(subject, html, text)


def password_reset_email(link: str, valid_minutes: int) -> Email:
    """ "Recupera tu contraseña": sent when someone asks to reset the password."""
    subject = "Recupera tu contraseña"
    html = _layout(
        subject,
        "<p>Recibimos una solicitud para cambiar la contraseña de tu cuenta. "
        "Pulsa el botón para elegir una nueva:</p>"
        + _button(link, "Cambiar mi contraseña")
        + f'<p style="font-size:13px;color:#52525b">El enlace caduca en {valid_minutes} '
        "minutos y solo se puede usar una vez. Si no lo pediste tú, ignora este mensaje: "
        "tu contraseña no cambiará.</p>",
    )
    text = (
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta.\n\n"
        "Para elegir una nueva, abre este enlace:\n"
        f"{link}\n\n"
        f"El enlace caduca en {valid_minutes} minutos y solo se puede usar una vez.\n"
        "Si no lo pediste tú, ignora este mensaje: tu contraseña no cambiará.\n"
    )
    return Email(subject, html, text)
