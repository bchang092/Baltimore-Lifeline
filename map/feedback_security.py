"""Server-side protection for anonymous community feedback."""

from datetime import datetime, timezone as dt_timezone
from ipaddress import ip_address
import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import FeedbackRateLimit


def client_ip(request):
    address = request.META.get("REMOTE_ADDR", "")
    if settings.FEEDBACK_TRUST_HEROKU_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            address = forwarded.split(",")[-1].strip()
    try:
        return str(ip_address(address))
    except ValueError:
        return "unknown"


def reserve_submission_attempt(request):
    """Atomically count attempts across workers. Return seconds to retry or 0."""
    now = timezone.now()
    window = int(now.timestamp()) // 3600
    expires_at = datetime.fromtimestamp((window + 1) * 3600, dt_timezone.utc)
    key = salted_hmac(
        "community-feedback-rate", f"{client_ip(request)}:{window}", algorithm="sha256"
    ).hexdigest()
    FeedbackRateLimit.objects.filter(expires_at__lte=now).delete()
    FeedbackRateLimit.objects.get_or_create(key=key, defaults={"expires_at": expires_at})
    accepted = FeedbackRateLimit.objects.filter(
        key=key, attempts__lt=settings.FEEDBACK_RATE_LIMIT
    ).update(attempts=F("attempts") + 1)
    return 0 if accepted else max(1, int((expires_at - now).total_seconds()) + 1)


def turnstile_ready():
    return bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY)


def verify_turnstile(token):
    """Return an error message or None. Never accept missing/failed verification."""
    if not turnstile_ready():
        return "Feedback submissions are temporarily unavailable. Please try again later."
    if not token or len(token) > 2048:
        return "Please complete the bot check and submit again."
    request = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=urlencode({"secret": settings.TURNSTILE_SECRET_KEY, "response": token}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.load(response)
    except (URLError, OSError, ValueError):
        return "The bot check is temporarily unavailable. Please try again shortly."
    if (
        not isinstance(result, dict)
        or result.get("success") is not True
        or result.get("hostname") not in settings.TURNSTILE_HOSTNAMES
        or result.get("action") != "community-feedback"
    ):
        return "The bot check could not be verified. Please complete it again and resubmit."
    return None
