import smtplib
import ssl
from mimetypes import guess_type
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings


class EmailConfigError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def _verification_company_signature() -> str:
    current = settings.verification_employer_display_name.strip()
    former = settings.verification_employer_former_name.strip()
    if former and former.lower() != current.lower():
        return f"{current} (formerly {former})"
    return current


def send_verification_email_with_attachment(
    *,
    recipient_email: str,
    recipient_name: str | None,
    employee_name: str,
    attachment_filename: str,
    attachment_bytes: bytes,
    extra_attachments: list[tuple[str, bytes, str | None]] | None = None,
) -> None:
    smtp_host = settings.smtp_host.strip()
    if not smtp_host:
        raise EmailConfigError("SMTP_HOST is not configured")

    smtp_username = settings.smtp_username.strip()
    smtp_password = settings.smtp_password
    if bool(smtp_username) != bool(smtp_password):
        raise EmailConfigError("Set both SMTP_USERNAME and SMTP_PASSWORD, or leave both empty")

    from_email = settings.smtp_from_email.strip() or settings.verification_signer_email.strip()
    if not from_email:
        raise EmailConfigError("SMTP_FROM_EMAIL is not configured")

    from_name = settings.smtp_from_name.strip()
    sender = formataddr((from_name, from_email)) if from_name else from_email
    to_name = (recipient_name or "").strip() or "Recipient"

    msg = EmailMessage()
    msg["Subject"] = f"Employment Verification - {employee_name}"
    msg["From"] = sender
    msg["To"] = recipient_email
    msg["Reply-To"] = settings.verification_signer_email.strip() or from_email
    msg.set_content(
        "\n".join(
            [
                f"Dear {to_name},",
                "",
                "Attached is the completed employment verification form for the above-referenced employee.",
                "",
                "Please let us know if any additional information or documentation is required. We are happy to assist further.",
                "",
                "Best regards,",
                settings.verification_email_signature_name.strip(),
                settings.verification_email_signature_title.strip(),
                _verification_company_signature(),
            ]
        )
    )
    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="pdf",
        filename=attachment_filename,
    )
    for filename, content, content_type in extra_attachments or []:
        effective_content_type = (content_type or "").strip()
        if not effective_content_type:
            guessed_type, _ = guess_type(filename)
            effective_content_type = guessed_type or "application/octet-stream"
        if "/" in effective_content_type:
            maintype, subtype = effective_content_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        msg.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                smtp_host, settings.smtp_port, timeout=30
            ) as server:
                if smtp_username:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            return

        with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if smtp_username:
                server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        raise EmailDeliveryError("Failed to send verification email via SMTP") from exc
