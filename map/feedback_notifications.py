"""Email the moderator after a feedback submission has been committed."""

import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse


logger = logging.getLogger(__name__)


def notify_feedback_pending(feedback):
    if not (
        settings.EMAIL_HOST_USER
        and settings.EMAIL_HOST_PASSWORD
        and settings.FEEDBACK_NOTIFICATION_EMAIL
    ):
        logger.warning(
            "Feedback %s saved; email notification skipped because Gmail settings are incomplete.",
            feedback.pk,
        )
        return

    review_url = settings.FEEDBACK_SITE_URL + reverse(
        "admin:map_communityfeedback_change", args=[feedback.pk]
    )
    # Keep user-supplied text out of email headers and send it as plain text.
    body = (
        "New community feedback is waiting for your approval. It is not public yet.\n\n"
        f"Review in Django admin (sign-in required):\n{review_url}\n\n"
        f"Type: {feedback.get_category_display()}\n"
        f"Name or alias: {feedback.name or 'Anonymous'}\n"
        f"Title: {feedback.title}\n\n"
        f"Feedback:\n{feedback.body}\n"
    )
    try:
        sent = send_mail(
            subject=f"[Baltimore Lifeline] Feedback #{feedback.pk} awaiting approval",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.FEEDBACK_NOTIFICATION_EMAIL],
            fail_silently=False,
        )
        if not sent:
            logger.error("Feedback %s saved, but notification email was not sent.", feedback.pk)
    except (SMTPException, OSError, ValueError):
        # A delivery problem must never lose feedback or cause duplicate submissions.
        # Do not log credentials, feedback text, or the SMTP server's response.
        logger.error(
            "Feedback %s saved, but notification email failed. Check Gmail configuration and limits.",
            feedback.pk,
        )
