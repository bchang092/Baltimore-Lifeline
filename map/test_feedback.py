from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings

from .feedback_security import client_ip
from .models import CommunityFeedback, FeedbackRateLimit


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    TURNSTILE_SITE_KEY="test-site-key",
    TURNSTILE_SECRET_KEY="test-secret-key",
    TURNSTILE_HOSTNAMES=["baltimorelifeline.site"],
    FEEDBACK_TRUST_HEROKU_PROXY=False,
    FEEDBACK_RATE_LIMIT=5,
)
class FeedbackProtectionTests(TestCase):
    def setUp(self):
        self.payload = {
            "name": "Neighbor", "category": "suggestion", "title": "A useful suggestion",
            "body": "Please add this resource.", "cf-turnstile-response": "test-token",
        }
        self.verify_patch = patch("map.feedback_security.urlopen")
        self.verify = self.verify_patch.start()
        self.addCleanup(self.verify_patch.stop)
        self.verification_result({
            "success": True, "hostname": "baltimorelifeline.site", "action": "community-feedback",
        })

    def verification_result(self, result):
        self.verify.side_effect = lambda *args, **kwargs: BytesIO(json.dumps(result).encode())

    def post(self, **changes):
        return self.client.post("/community/", self.payload | changes)

    def test_verified_submission_is_pending_and_not_public_until_approved(self):
        response = self.post()
        self.assertRedirects(response, "/community/?submitted=1")
        post = CommunityFeedback.objects.get()
        self.assertFalse(post.approved)
        for url in ("/", "/community/"):
            self.assertNotContains(self.client.get(url), post.title)
        post.approved = True
        post.save()
        for url in ("/", "/community/"):
            self.assertContains(self.client.get(url), post.title)
        request = self.verify.call_args.args[0]
        self.assertEqual(request.full_url, "https://challenges.cloudflare.com/turnstile/v0/siteverify")
        self.assertEqual(parse_qs(request.data.decode()), {
            "secret": ["test-secret-key"], "response": ["test-token"],
        })
        self.assertEqual(self.verify.call_args.kwargs["timeout"], 5)

    def test_missing_token_is_rejected_without_contacting_cloudflare(self):
        self.assertEqual(self.post(**{"cf-turnstile-response": ""}).status_code, 400)
        self.assertFalse(CommunityFeedback.objects.exists())
        self.verify.assert_not_called()

    @override_settings(TURNSTILE_SECRET_KEY="")
    def test_missing_configuration_disables_form_and_rejects_direct_post(self):
        page = self.client.get("/community/")
        self.assertContains(page, "temporarily unavailable")
        self.assertContains(page, 'type="submit" disabled')
        self.assertNotContains(page, "test-secret-key")
        self.assertEqual(self.post().status_code, 503)
        self.verify.assert_not_called()
        self.assertFalse(CommunityFeedback.objects.exists())

    def test_failed_expired_replayed_and_wrong_origin_tokens_are_rejected(self):
        for result in (
            {"success": False, "error-codes": ["timeout-or-duplicate"]},
            {"success": True, "hostname": "attacker.example", "action": "community-feedback"},
            {"success": True, "hostname": "baltimorelifeline.site", "action": "login"},
            [],
        ):
            with self.subTest(result=result):
                self.verification_result(result)
                response = self.post()
                self.assertEqual(response.status_code, 400)
                self.assertContains(response, self.payload["body"], status_code=400)
                self.assertFalse(CommunityFeedback.objects.exists())

    def test_network_failure_and_invalid_json_fail_closed(self):
        for error in (URLError("unavailable"), TimeoutError(), ValueError("invalid JSON")):
            with self.subTest(error=error):
                self.verify.side_effect = error
                self.assertEqual(self.post().status_code, 400)
                self.assertFalse(CommunityFeedback.objects.exists())

    def test_honeypot_blocks_submission_before_verification(self):
        self.assertEqual(self.post(website="spam.example").status_code, 400)
        self.verify.assert_not_called()
        self.assertFalse(CommunityFeedback.objects.exists())

    def test_server_enforces_field_lengths_without_browser_validation(self):
        for field, maximum in (("name", 120), ("title", 160), ("body", 5000)):
            with self.subTest(field=field):
                response = self.post(**{field: "x" * (maximum + 1)})
                self.assertIn(field, response.context["errors"])
        self.verify.assert_not_called()
        self.assertFalse(CommunityFeedback.objects.exists())

    def test_rate_limit_counts_failed_attempts_across_clients_and_resets(self):
        start = datetime(2026, 10, 5, 12, 30, tzinfo=timezone.utc)
        with patch("map.feedback_security.timezone.now", return_value=start):
            for _ in range(5):
                self.assertEqual(self.post(website="bot").status_code, 400)
            response = Client().post("/community/", self.payload)
            self.assertEqual(response.status_code, 429)
            self.assertGreater(int(response["Retry-After"]), 0)
            self.verify.assert_not_called()
            self.assertEqual(FeedbackRateLimit.objects.get().attempts, 5)
            other_ip = self.client.post("/community/", self.payload, REMOTE_ADDR="192.0.2.2")
            self.assertEqual(other_ip.status_code, 302)
        with patch("map.feedback_security.timezone.now", return_value=start + timedelta(hours=1)):
            self.assertEqual(self.post().status_code, 302)
            self.assertEqual(FeedbackRateLimit.objects.count(), 1)

    def test_forwarded_header_is_not_trusted_outside_heroku(self):
        request = RequestFactory().get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="192.0.2.2")
        self.assertEqual(client_ip(request), "192.0.2.1")

    @override_settings(FEEDBACK_TRUST_HEROKU_PROXY=True)
    def test_heroku_uses_rightmost_ip_so_spoofed_prefix_cannot_evade_limit(self):
        for index in range(6):
            response = self.client.post(
                "/community/", self.payload | {"website": "bot"},
                HTTP_X_FORWARDED_FOR=f"192.0.2.{index}, 198.51.100.1",
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(FeedbackRateLimit.objects.count(), 1)

    def test_csrf_is_still_required(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post("/community/", self.payload).status_code, 403)
        self.verify.assert_not_called()

    def test_admin_can_approve_and_hide_existing_feedback(self):
        user = get_user_model().objects.create_superuser("reviewer", "reviewer@example.com", "test-password")
        self.client.force_login(user)
        post = CommunityFeedback.objects.create(category="suggestion", title="Review me", body="Details")
        url = "/admin/map/communityfeedback/"
        for action, expected in (("approve_feedback", True), ("hide_feedback", False)):
            response = self.client.post(url, {"action": action, "_selected_action": [post.pk]})
            self.assertEqual(response.status_code, 302)
            post.refresh_from_db()
            self.assertEqual(post.approved, expected)
        self.assertNotIn("approved", admin.site._registry[CommunityFeedback].get_exclude(None) or ())
