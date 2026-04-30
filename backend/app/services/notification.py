"""
Notification service: in-app write (mandatory) + email dispatch (best-effort, silent fail).

FR-046: SMTP failure is logged to system log only. No retry. No in-app fallback for email.
In-app notifications are ALWAYS written regardless of SMTP availability.
"""
import logging
import smtplib
import uuid
from email.mime.text import MIMEText

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit_package import NotificationChannel, NotificationRecord

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_notification(
    db: AsyncSession,
    recipient_id: uuid.UUID,
    subject: str,
    body: str,
    related_document_id: uuid.UUID | None = None,
    recipient_email: str | None = None,
) -> None:
    """
    Write in-app notification record (always succeeds) and attempt email (FR-046).
    SMTP failure is silently swallowed — only logged at WARNING level.
    """
    # 1. In-app notification (mandatory)
    in_app = NotificationRecord(
        recipient_id=recipient_id,
        channel=NotificationChannel.IN_APP,
        subject=subject,
        body=body,
        related_document_id=related_document_id,
        email_failed=False,
    )
    db.add(in_app)

    # 2. Email (best-effort, FR-046)
    if recipient_email:
        email_failed = False
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = recipient_email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USER:
                    smtp.starttls()
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        except Exception as exc:
            # FR-046: silently log failure, do not raise, do not retry
            logger.warning(
                "Email delivery failed to %s (subject=%r): %s", recipient_email, subject, exc
            )
            email_failed = True

        email_record = NotificationRecord(
            recipient_id=recipient_id,
            channel=NotificationChannel.EMAIL,
            subject=subject,
            body=body,
            related_document_id=related_document_id,
            email_failed=email_failed,
        )
        db.add(email_record)

    await db.flush()
